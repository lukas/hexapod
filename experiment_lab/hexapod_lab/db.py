from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, Iterable, Optional
import uuid


TERMINAL = {"succeeded", "failed", "cancelled"}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    @contextmanager
    def connect(self):
        con = sqlite3.connect(str(self.path), timeout=30, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
        try:
            yield con
        finally:
            con.close()

    def init(self) -> None:
        with self.connect() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS experiments (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
              duration_seconds REAL NOT NULL, parameters_json TEXT NOT NULL,
              status TEXT NOT NULL, submitted_by TEXT NOT NULL, created_at TEXT NOT NULL,
              started_at TEXT, finished_at TEXT, error TEXT, cancel_requested INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS experiments_queue ON experiments(status, created_at);
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT, experiment_id TEXT NOT NULL,
              timestamp TEXT NOT NULL, kind TEXT NOT NULL, message TEXT NOT NULL,
              FOREIGN KEY(experiment_id) REFERENCES experiments(id)
            );
            CREATE TABLE IF NOT EXISTS tag_layout_revisions (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              id TEXT NOT NULL UNIQUE,
              robot_id TEXT NOT NULL,
              layout_sha256 TEXT NOT NULL,
              pose_config_sha256 TEXT,
              floor_map_sha256 TEXT,
              part_map_sha256 TEXT,
              layout_json TEXT NOT NULL,
              pose_config_json TEXT,
              floor_map_json TEXT,
              part_map_json TEXT,
              observed_at TEXT NOT NULL,
              created_at TEXT NOT NULL,
              created_by TEXT NOT NULL,
              source_kind TEXT NOT NULL,
              source_experiment_id TEXT UNIQUE,
              parent_revision_id TEXT,
              baseline_sha256 TEXT,
              review_ready INTEGER NOT NULL,
              changed_tag_ids_json TEXT NOT NULL,
              FOREIGN KEY(source_experiment_id) REFERENCES experiments(id),
              FOREIGN KEY(parent_revision_id) REFERENCES tag_layout_revisions(id)
            );
            CREATE TABLE IF NOT EXISTS tag_layout_activations (
              revision_id TEXT PRIMARY KEY,
              effective_from TEXT NOT NULL UNIQUE,
              activated_at TEXT NOT NULL,
              activated_by TEXT NOT NULL,
              note TEXT NOT NULL,
              idempotency_key TEXT NOT NULL UNIQUE,
              request_sha256 TEXT NOT NULL,
              FOREIGN KEY(revision_id) REFERENCES tag_layout_revisions(id)
            );
            CREATE TABLE IF NOT EXISTS experiment_tag_layouts (
              experiment_id TEXT PRIMARY KEY,
              revision_id TEXT NOT NULL,
              recorded_at TEXT NOT NULL,
              pinned_at TEXT NOT NULL,
              pin_basis TEXT NOT NULL,
              FOREIGN KEY(experiment_id) REFERENCES experiments(id),
              FOREIGN KEY(revision_id) REFERENCES tag_layout_revisions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_experiment_tag_layouts_revision
              ON experiment_tag_layouts(revision_id);
            CREATE TRIGGER IF NOT EXISTS tag_layout_revisions_no_update
              BEFORE UPDATE ON tag_layout_revisions BEGIN
                SELECT RAISE(ABORT, 'tag layout revisions are immutable');
              END;
            CREATE TRIGGER IF NOT EXISTS tag_layout_revisions_no_delete
              BEFORE DELETE ON tag_layout_revisions BEGIN
                SELECT RAISE(ABORT, 'tag layout revisions are immutable');
              END;
            CREATE TRIGGER IF NOT EXISTS tag_layout_activations_no_update
              BEFORE UPDATE ON tag_layout_activations BEGIN
                SELECT RAISE(ABORT, 'tag layout activations are append-only');
              END;
            CREATE TRIGGER IF NOT EXISTS tag_layout_activations_no_delete
              BEFORE DELETE ON tag_layout_activations BEGIN
                SELECT RAISE(ABORT, 'tag layout activations are append-only');
              END;
            CREATE TRIGGER IF NOT EXISTS experiment_tag_layouts_no_update
              BEFORE UPDATE ON experiment_tag_layouts BEGIN
                SELECT RAISE(ABORT, 'experiment layout pins are immutable');
              END;
            CREATE TRIGGER IF NOT EXISTS experiment_tag_layouts_no_delete
              BEFORE DELETE ON experiment_tag_layouts BEGIN
                SELECT RAISE(ABORT, 'experiment layout pins are immutable');
              END;
            """)
            # These columns were added while the history feature was still in
            # development. Keep startup safe for a database created by an
            # earlier preview build.
            columns = {
                row["name"]
                for row in con.execute("PRAGMA table_info(tag_layout_revisions)")
            }
            for name in (
                "floor_map_sha256",
                "part_map_sha256",
                "floor_map_json",
                "part_map_json",
            ):
                if name not in columns:
                    con.execute(f"ALTER TABLE tag_layout_revisions ADD COLUMN {name} TEXT")
            con.execute("PRAGMA optimize")

    @staticmethod
    def row(row: sqlite3.Row) -> Dict[str, Any]:
        item = dict(row)
        item["parameters"] = json.loads(item.pop("parameters_json"))
        item["cancel_requested"] = bool(item["cancel_requested"])
        return item

    def create(
        self,
        spec: Dict[str, Any],
        submitted_by: str,
        *,
        tag_layout_revision_id: Optional[str] = None,
        tag_layout_recorded_at: Optional[str] = None,
        tag_layout_pin_basis: str = "active_at_submission",
    ) -> Dict[str, Any]:
        experiment_id = uuid.uuid4().hex
        now = utcnow()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "INSERT INTO experiments(id,name,description,duration_seconds,parameters_json,status,submitted_by,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (experiment_id, spec["name"], spec.get("description", ""), spec["duration_seconds"],
                 json.dumps(spec.get("parameters", {}), sort_keys=True), "queued", submitted_by, now),
            )
            con.execute("INSERT INTO events(experiment_id,timestamp,kind,message) VALUES(?,?,?,?)",
                        (experiment_id, now, "submitted", "Experiment added to queue"))
            if tag_layout_revision_id:
                con.execute(
                    "INSERT INTO experiment_tag_layouts("
                    "experiment_id,revision_id,recorded_at,pinned_at,pin_basis"
                    ") VALUES(?,?,?,?,?)",
                    (
                        experiment_id,
                        tag_layout_revision_id,
                        tag_layout_recorded_at or now,
                        now,
                        tag_layout_pin_basis,
                    ),
                )
            con.execute("COMMIT")
        return self.get(experiment_id)

    def import_result(
        self,
        spec: Dict[str, Any],
        submitted_by: str,
        status: str,
        error: Optional[str] = None,
        experiment_id: Optional[str] = None,
        tag_layout_revision_id: Optional[str] = None,
        tag_layout_recorded_at: Optional[str] = None,
        tag_layout_pin_basis: str = "active_at_registration",
    ) -> Dict[str, Any]:
        """Register evidence produced by an external guarded runner."""
        if status not in TERMINAL:
            raise ValueError("invalid terminal status")
        result_id = experiment_id or uuid.uuid4().hex
        now = utcnow()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            if experiment_id:
                existing = con.execute(
                    "SELECT * FROM experiments WHERE id=?", (result_id,)
                ).fetchone()
                if existing:
                    if tag_layout_revision_id:
                        existing_pin = con.execute(
                            "SELECT revision_id,recorded_at,pin_basis "
                            "FROM experiment_tag_layouts WHERE experiment_id=?",
                            (result_id,),
                        ).fetchone()
                        requested_pin = (
                            tag_layout_revision_id,
                            tag_layout_recorded_at or now,
                            tag_layout_pin_basis,
                        )
                        if existing_pin and tuple(existing_pin) != requested_pin:
                            con.execute("ROLLBACK")
                            raise ValueError(
                                "existing result has a different immutable tag layout pin"
                            )
                        if not existing_pin:
                            con.execute(
                                "INSERT INTO experiment_tag_layouts("
                                "experiment_id,revision_id,recorded_at,pinned_at,pin_basis"
                                ") VALUES(?,?,?,?,?)",
                                (result_id, *requested_pin[:2], now, requested_pin[2]),
                            )
                    con.execute("COMMIT")
                    return self.row(existing)
            con.execute(
                "INSERT INTO experiments(id,name,description,duration_seconds,"
                "parameters_json,status,submitted_by,created_at,started_at,"
                "finished_at,error) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    result_id,
                    spec["name"],
                    spec.get("description", ""),
                    spec["duration_seconds"],
                    json.dumps(spec.get("parameters", {}), sort_keys=True),
                    status,
                    submitted_by,
                    now,
                    tag_layout_recorded_at or now,
                    now,
                    error,
                ),
            )
            con.execute(
                "INSERT INTO events(experiment_id,timestamp,kind,message) "
                "VALUES(?,?,?,?)",
                (
                    result_id,
                    now,
                    "imported",
                    "Completed result registered from an external guarded runner",
                ),
            )
            if tag_layout_revision_id:
                con.execute(
                    "INSERT INTO experiment_tag_layouts("
                    "experiment_id,revision_id,recorded_at,pinned_at,pin_basis"
                    ") VALUES(?,?,?,?,?)",
                    (
                        result_id,
                        tag_layout_revision_id,
                        tag_layout_recorded_at or now,
                        now,
                        tag_layout_pin_basis,
                    ),
                )
            con.execute("COMMIT")
        return self.get(result_id)

    def get(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as con:
            row = con.execute("SELECT * FROM experiments WHERE id=?", (experiment_id,)).fetchone()
        return self.row(row) if row else None

    def list(self, limit: int = 100) -> Iterable[Dict[str, Any]]:
        with self.connect() as con:
            rows = con.execute("SELECT * FROM experiments ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self.row(row) for row in rows]

    def claim_next(self) -> Optional[Dict[str, Any]]:
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT id FROM experiments WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
            if not row:
                con.execute("COMMIT")
                return None
            now = utcnow()
            con.execute("UPDATE experiments SET status='running',started_at=? WHERE id=? AND status='queued'", (now, row["id"]))
            con.execute("INSERT INTO events(experiment_id,timestamp,kind,message) VALUES(?,?,?,?)",
                        (row["id"], now, "started", "Worker claimed experiment"))
            con.execute("COMMIT")
        return self.get(row["id"])

    def finish(self, experiment_id: str, status: str, error: Optional[str] = None) -> None:
        if status not in TERMINAL:
            raise ValueError("invalid terminal status")
        now = utcnow()
        with self.connect() as con:
            con.execute("UPDATE experiments SET status=?,finished_at=?,error=? WHERE id=?", (status, now, error, experiment_id))
            con.execute("INSERT INTO events(experiment_id,timestamp,kind,message) VALUES(?,?,?,?)",
                        (experiment_id, now, status, error or ("Experiment " + status)))

    def cancel(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as con:
            row = con.execute("SELECT status FROM experiments WHERE id=?", (experiment_id,)).fetchone()
            if not row:
                return None
            now = utcnow()
            if row["status"] == "queued":
                con.execute("UPDATE experiments SET status='cancelled',cancel_requested=1,finished_at=? WHERE id=?", (now, experiment_id))
            elif row["status"] == "running":
                con.execute("UPDATE experiments SET cancel_requested=1 WHERE id=?", (experiment_id,))
            con.execute("INSERT INTO events(experiment_id,timestamp,kind,message) VALUES(?,?,?,?)",
                        (experiment_id, now, "cancel_requested", "Cancellation requested"))
        return self.get(experiment_id)

    def events(self, experiment_id: str):
        with self.connect() as con:
            return [dict(row) for row in con.execute(
                "SELECT timestamp,kind,message FROM events WHERE experiment_id=? ORDER BY id", (experiment_id,)).fetchall()]
