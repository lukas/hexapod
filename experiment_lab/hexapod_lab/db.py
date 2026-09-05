from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, Iterable, Optional
import uuid


TERMINAL = {"succeeded", "failed", "cancelled"}
EXECUTION_MODES = {"builtin", "external_guarded"}
WAITING_FOR_OPERATOR = "waiting_for_operator"
LEGACY_PRE_RUN_PIN_BASIS = "legacy_backfill_by_recorded_time"


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
            # Experiment pins remain immutable except for one migration artifact:
            # an external-guarded plan may have been backfilled at queue time before
            # its real recording timestamp existed.  The completion transaction
            # below revalidates the resolved revision and interval before issuing
            # this narrowly shaped UPDATE; keep the same constraints in the trigger
            # so an ad-hoc SQL write cannot bypass them.
            con.executescript(f"""
                BEGIN IMMEDIATE;
                DROP TRIGGER IF EXISTS experiment_tag_layouts_no_update;
                CREATE TRIGGER experiment_tag_layouts_no_update
                  BEFORE UPDATE ON experiment_tag_layouts
                  WHEN NOT (
                    OLD.experiment_id = NEW.experiment_id
                    AND OLD.revision_id = NEW.revision_id
                    AND OLD.pinned_at = NEW.pinned_at
                    AND OLD.pin_basis = NEW.pin_basis
                    AND OLD.pin_basis = '{LEGACY_PRE_RUN_PIN_BASIS}'
                    AND OLD.recorded_at <> NEW.recorded_at
                    AND julianday(NEW.recorded_at) IS NOT NULL
                    AND EXISTS (
                      SELECT 1 FROM experiments e
                      WHERE e.id = OLD.experiment_id
                        AND e.status = '{WAITING_FOR_OPERATOR}'
                        AND e.execution_mode = 'external_guarded'
                    )
                    AND OLD.revision_id = (
                      SELECT a.revision_id
                      FROM tag_layout_activations a
                      WHERE julianday(a.effective_from) <= julianday(NEW.recorded_at)
                      ORDER BY julianday(a.effective_from) DESC
                      LIMIT 1
                    )
                    AND NOT EXISTS (
                      SELECT 1
                      FROM tag_layout_activations a
                      JOIN experiments e ON e.id = OLD.experiment_id
                      WHERE julianday(a.effective_from) > julianday(NEW.recorded_at)
                        AND julianday(a.effective_from) < (
                          julianday(NEW.recorded_at)
                          + (e.duration_seconds / 86400.0)
                        )
                    )
                    AND (
                      julianday(NEW.recorded_at)
                      + (
                        SELECT e.duration_seconds / 86400.0
                        FROM experiments e
                        WHERE e.id = OLD.experiment_id
                      )
                    ) <= julianday('now')
                  ) BEGIN
                    SELECT RAISE(ABORT, 'experiment layout pins are immutable');
                  END;
                COMMIT;
            """)
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
    def _recording_time(value: str) -> datetime:
        raw = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("tag layout recorded_at must be an RFC 3339 timestamp") from exc
        if parsed.tzinfo is None:
            raise ValueError("tag layout recorded_at must include a timezone")
        return parsed.astimezone(timezone.utc)

    def _rebind_legacy_pre_run_pin(
        self,
        con: sqlite3.Connection,
        *,
        experiment: sqlite3.Row,
        pin: sqlite3.Row,
        requested_revision_id: str,
        requested_recorded_at: Optional[str],
        completed_at: str,
    ) -> Optional[str]:
        """Validate and update only a legacy queue-time recording timestamp.

        The caller owns an IMMEDIATE transaction. Resolving the timestamp and
        transitioning the experiment therefore observe the same activation
        history and commit atomically.
        """

        if pin["pin_basis"] != LEGACY_PRE_RUN_PIN_BASIS:
            raise ValueError("existing result has a different immutable tag layout pin")
        if pin["revision_id"] != requested_revision_id:
            raise ValueError(
                "truthful recording time resolves to a different tag layout revision"
            )
        if not requested_recorded_at:
            raise ValueError("tag layout recorded_at is required for a legacy pin rebind")

        start = self._recording_time(requested_recorded_at)
        end = start + timedelta(seconds=float(experiment["duration_seconds"]))
        if end > self._recording_time(completed_at):
            raise ValueError("truthful recording interval extends into the future")
        activation_rows = con.execute(
            "SELECT revision_id,effective_from FROM tag_layout_activations "
        ).fetchall()
        activations = sorted(
            (
                (self._recording_time(row["effective_from"]), row["revision_id"])
                for row in activation_rows
            ),
            key=lambda item: item[0],
        )
        resolved_revision_id = None
        boundaries = []
        for effective, revision_id in activations:
            if effective <= start:
                resolved_revision_id = revision_id
            elif effective < end:
                boundaries.append(effective)

        if resolved_revision_id != pin["revision_id"]:
            raise ValueError(
                "truthful recording time resolves to a different tag layout revision"
            )
        if boundaries:
            raise ValueError(
                "truthful recording interval crosses a known tag layout revision boundary"
            )

        previous_recorded_at = pin["recorded_at"]
        if previous_recorded_at == requested_recorded_at:
            return None
        try:
            updated = con.execute(
                "UPDATE experiment_tag_layouts SET recorded_at=? "
                "WHERE experiment_id=? AND revision_id=? AND recorded_at=? "
                "AND pin_basis=?",
                (
                    requested_recorded_at,
                    experiment["id"],
                    pin["revision_id"],
                    previous_recorded_at,
                    LEGACY_PRE_RUN_PIN_BASIS,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("legacy tag layout recording-time rebind was rejected") from exc
        if updated.rowcount != 1:
            raise ValueError("tag layout pin changed during completion")
        return previous_recorded_at

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
                    rebound_from = None
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
                        if existing_pin:
                            if existing_pin["pin_basis"] == LEGACY_PRE_RUN_PIN_BASIS:
                                try:
                                    rebound_from = self._rebind_legacy_pre_run_pin(
                                        con,
                                        experiment=existing,
                                        pin=existing_pin,
                                        requested_revision_id=tag_layout_revision_id,
                                        requested_recorded_at=tag_layout_recorded_at,
                                        completed_at=now,
                                    )
                                except ValueError:
                                    con.execute("ROLLBACK")
                                    raise
                            elif tuple(existing_pin) != requested_pin:
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
                    if rebound_from is not None:
                        con.execute(
                            "INSERT INTO events(experiment_id,timestamp,kind,message) "
                            "VALUES(?,?,?,?)",
                            (
                                result_id,
                                now,
                                "tag_layout_recording_time_rebound",
                                "Rebound legacy queue-time AprilTag pin recording start "
                                f"from {rebound_from} to {tag_layout_recorded_at}; "
                                f"revision {tag_layout_revision_id} is unchanged",
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

    def finish(self, experiment_id: str, status: str, error: Optional[str] = None,
               *, finished_at: Optional[str] = None) -> None:
        if status not in TERMINAL:
            raise ValueError("invalid terminal status")
        now = finished_at or utcnow()
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
