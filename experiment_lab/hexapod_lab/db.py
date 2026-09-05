from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, Iterable, Optional
import uuid


TERMINAL = {"succeeded", "failed", "cancelled"}
EXECUTION_MODES = {"builtin", "external_guarded"}
WAITING_FOR_OPERATOR = "waiting_for_operator"


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
              started_at TEXT, finished_at TEXT, error TEXT,
              cancel_requested INTEGER NOT NULL DEFAULT 0,
              execution_mode TEXT NOT NULL DEFAULT 'builtin',
              completion_sha256 TEXT
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
            CREATE TABLE IF NOT EXISTS calibrations (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              id TEXT NOT NULL UNIQUE,
              request_sha256 TEXT NOT NULL UNIQUE,
              report_sha256 TEXT NOT NULL,
              report_json TEXT NOT NULL,
              pose_config_sha256 TEXT,
              pose_config_json TEXT,
              observed_at TEXT NOT NULL,
              created_at TEXT NOT NULL,
              created_by TEXT NOT NULL,
              robot_id TEXT,
              kind TEXT NOT NULL,
              schema_version INTEGER NOT NULL,
              replay_ready INTEGER NOT NULL,
              tag_layout_revision_json TEXT,
              source_metadata_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS calibration_import_keys (
              idempotency_key TEXT PRIMARY KEY,
              calibration_id TEXT NOT NULL,
              request_sha256 TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(calibration_id) REFERENCES calibrations(id)
            );
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
            CREATE TRIGGER IF NOT EXISTS calibrations_no_update
              BEFORE UPDATE ON calibrations BEGIN
                SELECT RAISE(ABORT, 'calibrations are immutable');
              END;
            CREATE TRIGGER IF NOT EXISTS calibrations_no_delete
              BEFORE DELETE ON calibrations BEGIN
                SELECT RAISE(ABORT, 'calibrations are immutable');
              END;
            CREATE TRIGGER IF NOT EXISTS calibration_import_keys_no_update
              BEFORE UPDATE ON calibration_import_keys BEGIN
                SELECT RAISE(ABORT, 'calibration import keys are immutable');
              END;
            CREATE TRIGGER IF NOT EXISTS calibration_import_keys_no_delete
              BEFORE DELETE ON calibration_import_keys BEGIN
                SELECT RAISE(ABORT, 'calibration import keys are immutable');
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
            calibration_columns = {
                row["name"] for row in con.execute("PRAGMA table_info(calibrations)")
            }
            if "source_metadata_json" not in calibration_columns:
                con.execute(
                    "ALTER TABLE calibrations ADD COLUMN "
                    "source_metadata_json TEXT NOT NULL DEFAULT '{}'"
                )
            experiment_columns = {
                row["name"] for row in con.execute("PRAGMA table_info(experiments)")
            }
            if "execution_mode" not in experiment_columns:
                con.execute(
                    "ALTER TABLE experiments ADD COLUMN "
                    "execution_mode TEXT NOT NULL DEFAULT 'builtin'"
                )
            if "completion_sha256" not in experiment_columns:
                con.execute(
                    "ALTER TABLE experiments ADD COLUMN completion_sha256 TEXT"
                )
            # Rows registered through the external-result API predate the
            # explicit execution-mode column. Preserve that provenance during
            # migration instead of mislabeling them as built-in worker runs.
            con.execute(
                "UPDATE experiments SET execution_mode='external_guarded' "
                "WHERE execution_mode='builtin' AND EXISTS ("
                "SELECT 1 FROM events WHERE events.experiment_id=experiments.id "
                "AND events.kind IN ('imported','external_result_registered')"
                ")"
            )
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
        execution_mode = spec.get("execution_mode", "builtin")
        if execution_mode not in EXECUTION_MODES:
            raise ValueError("invalid execution mode")
        status = (
            WAITING_FOR_OPERATOR
            if execution_mode == "external_guarded"
            else "queued"
        )
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "INSERT INTO experiments(id,name,description,duration_seconds,"
                "parameters_json,status,submitted_by,created_at,execution_mode) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (experiment_id, spec["name"], spec.get("description", ""), spec["duration_seconds"],
                 json.dumps(spec.get("parameters", {}), sort_keys=True), status,
                 submitted_by, now, execution_mode),
            )
            message = (
                "External guarded experiment is waiting for an operator"
                if execution_mode == "external_guarded"
                else "Experiment added to queue"
            )
            con.execute(
                "INSERT INTO events(experiment_id,timestamp,kind,message) "
                "VALUES(?,?,?,?)",
                (experiment_id, now, "submitted", message),
            )
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
        completion_sha256: Optional[str] = None,
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
                    existing_item = self.row(existing)
                    if existing["status"] in TERMINAL:
                        if (
                            completion_sha256
                            and existing["completion_sha256"] == completion_sha256
                        ):
                            con.execute("COMMIT")
                            return existing_item
                        con.execute("ROLLBACK")
                        raise ValueError(
                            "experiment already has a different terminal result"
                        )
                    if not (
                        existing["status"] == WAITING_FOR_OPERATOR
                        and existing["execution_mode"] == "external_guarded"
                    ):
                        con.execute("ROLLBACK")
                        raise ValueError(
                            "only a waiting external-guarded experiment can be completed"
                        )
                    requested_parameters = spec.get("parameters", {})
                    if (
                        existing["name"] != spec["name"]
                        or existing["description"] != spec.get("description", "")
                        or existing["duration_seconds"] != spec["duration_seconds"]
                        or existing_item["parameters"] != requested_parameters
                    ):
                        con.execute("ROLLBACK")
                        raise ValueError(
                            "completed result does not match the queued experiment spec"
                        )
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
                    started_at = tag_layout_recorded_at or now
                    updated = con.execute(
                        "UPDATE experiments SET status=?,started_at=?,finished_at=?,"
                        "error=?,completion_sha256=? WHERE id=? AND status=? "
                        "AND execution_mode='external_guarded'",
                        (
                            status,
                            started_at,
                            now,
                            error,
                            completion_sha256,
                            result_id,
                            WAITING_FOR_OPERATOR,
                        ),
                    )
                    if updated.rowcount != 1:
                        con.execute("ROLLBACK")
                        raise ValueError("experiment state changed during completion")
                    con.execute(
                        "INSERT INTO events(experiment_id,timestamp,kind,message) "
                        "VALUES(?,?,?,?)",
                        (
                            result_id,
                            now,
                            "external_result_registered",
                            "Completed result registered from an external guarded runner",
                        ),
                    )
                    con.execute("COMMIT")
                    return self.get(result_id)
            con.execute(
                "INSERT INTO experiments(id,name,description,duration_seconds,"
                "parameters_json,status,submitted_by,created_at,started_at,"
                "finished_at,error,execution_mode,completion_sha256) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
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
                    "external_guarded",
                    completion_sha256,
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
            row = con.execute(
                "SELECT id FROM experiments WHERE status='queued' "
                "AND execution_mode='builtin' ORDER BY created_at LIMIT 1"
            ).fetchone()
            if not row:
                con.execute("COMMIT")
                return None
            now = utcnow()
            con.execute(
                "UPDATE experiments SET status='running',started_at=? "
                "WHERE id=? AND status='queued' AND execution_mode='builtin'",
                (now, row["id"]),
            )
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
            # Serialize with claim/completion. Without this transaction a
            # completion can land between the SELECT and cancellation UPDATE,
            # overwriting a successful immutable result with "cancelled".
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT status FROM experiments WHERE id=?", (experiment_id,)).fetchone()
            if not row:
                con.execute("COMMIT")
                return None
            now = utcnow()
            if row["status"] in {"queued", WAITING_FOR_OPERATOR}:
                con.execute(
                    "UPDATE experiments SET status='cancelled',cancel_requested=1,finished_at=? "
                    "WHERE id=? AND status IN ('queued','waiting_for_operator')",
                    (now, experiment_id),
                )
            elif row["status"] == "running":
                con.execute("UPDATE experiments SET cancel_requested=1 WHERE id=? AND status='running'", (experiment_id,))
            con.execute("INSERT INTO events(experiment_id,timestamp,kind,message) VALUES(?,?,?,?)",
                        (experiment_id, now, "cancel_requested", "Cancellation requested"))
            con.execute("COMMIT")
        return self.get(experiment_id)

    def events(self, experiment_id: str):
        with self.connect() as con:
            return [dict(row) for row in con.execute(
                "SELECT timestamp,kind,message FROM events WHERE experiment_id=? ORDER BY id", (experiment_id,)).fetchall()]
