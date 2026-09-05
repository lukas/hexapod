from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import fcntl
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Callable, Dict, Iterable, Optional
import uuid


TERMINAL = {"succeeded", "failed", "cancelled"}
EXECUTION_MODES = {"builtin", "external_guarded"}
WAITING_FOR_OPERATOR = "waiting_for_operator"
LEGACY_PRE_RUN_PIN_BASIS = "legacy_backfill_by_recorded_time"
CODEX_JOB_KINDS = {"analysis", "advance"}
CODEX_JOB_TERMINAL = {"succeeded", "blocked", "dead"}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: Path, *, codex_max_attempts: int = 5):
        self.path = path
        self.codex_max_attempts = max(1, int(codex_max_attempts))
        # Keep the legacy finish/retry call shape safe for the in-process
        # workers.  A claim also returns its token so callers that hand work to
        # another thread or process can pass it explicitly.
        self._codex_lease_tokens = threading.local()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.init()
        self._tighten_database_permissions()

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
            self._tighten_database_permissions()

    def _tighten_database_permissions(self) -> None:
        """Keep the database and transient SQLite files private to this user."""
        for candidate in (
            self.path,
            Path(f"{self.path}-wal"),
            Path(f"{self.path}-shm"),
        ):
            try:
                candidate.chmod(0o600)
            except FileNotFoundError:
                pass

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
            CREATE TABLE IF NOT EXISTS experiment_learnings (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              experiment_id TEXT NOT NULL,
              text TEXT NOT NULL,
              sources_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              created_by TEXT NOT NULL,
              FOREIGN KEY(experiment_id) REFERENCES experiments(id)
            );
            CREATE INDEX IF NOT EXISTS experiment_learnings_latest
              ON experiment_learnings(experiment_id, sequence DESC);
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
            CREATE TABLE IF NOT EXISTS codex_jobs (
              id TEXT PRIMARY KEY,
              dedupe_key TEXT NOT NULL UNIQUE,
              kind TEXT NOT NULL CHECK(kind IN ('analysis','advance')),
              trigger_kind TEXT NOT NULL,
              experiment_id TEXT,
              evidence_manifest_sha256 TEXT,
              status TEXT NOT NULL CHECK(status IN (
                'awaiting_evidence','queued','running','retry','succeeded','blocked','dead'
              )),
              depends_on_job_id TEXT,
              attempts INTEGER NOT NULL DEFAULT 0,
              max_attempts INTEGER NOT NULL DEFAULT 5,
              not_before TEXT NOT NULL,
              lease_owner TEXT,
              lease_token TEXT,
              lease_expires_at TEXT,
              created_at TEXT NOT NULL,
              started_at TEXT,
              finished_at TEXT,
              updated_at TEXT NOT NULL,
              result_json TEXT,
              error TEXT,
              FOREIGN KEY(experiment_id) REFERENCES experiments(id),
              FOREIGN KEY(depends_on_job_id) REFERENCES codex_jobs(id)
            );
            CREATE INDEX IF NOT EXISTS codex_jobs_claim
              ON codex_jobs(kind,status,not_before,created_at);
            CREATE INDEX IF NOT EXISTS codex_jobs_experiment
              ON codex_jobs(experiment_id,created_at);
            CREATE TABLE IF NOT EXISTS codex_transcript_attempts (
              job_id TEXT NOT NULL,
              attempt INTEGER NOT NULL CHECK(attempt > 0),
              experiment_id TEXT,
              kind TEXT NOT NULL CHECK(kind IN ('analysis','advance','engineering')),
              manifest_sha256 TEXT NOT NULL,
              created_at TEXT NOT NULL,
              PRIMARY KEY(job_id,attempt),
              FOREIGN KEY(experiment_id) REFERENCES experiments(id)
            );
            CREATE INDEX IF NOT EXISTS codex_transcripts_experiment
              ON codex_transcript_attempts(experiment_id,job_id,attempt);
            CREATE TABLE IF NOT EXISTS codex_followup_proposals (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              analysis_job_id TEXT NOT NULL,
              source_experiment_id TEXT NOT NULL,
              root_experiment_id TEXT NOT NULL,
              proposal_index INTEGER NOT NULL,
              recommendation_key TEXT NOT NULL,
              proposal_sha256 TEXT NOT NULL,
              spec_sha256 TEXT NOT NULL,
              spec_json TEXT NOT NULL,
              rationale TEXT NOT NULL,
              lineage_depth INTEGER NOT NULL,
              disposition TEXT NOT NULL,
              disposition_reason TEXT NOT NULL,
              child_experiment_id TEXT,
              created_at TEXT NOT NULL,
              UNIQUE(analysis_job_id,proposal_index),
              FOREIGN KEY(analysis_job_id) REFERENCES codex_jobs(id),
              FOREIGN KEY(source_experiment_id) REFERENCES experiments(id),
              FOREIGN KEY(root_experiment_id) REFERENCES experiments(id),
              FOREIGN KEY(child_experiment_id) REFERENCES experiments(id)
            );
            CREATE INDEX IF NOT EXISTS codex_followups_root
              ON codex_followup_proposals(root_experiment_id,disposition);
            CREATE UNIQUE INDEX IF NOT EXISTS codex_followups_accepted_spec
              ON codex_followup_proposals(root_experiment_id,spec_sha256)
              WHERE disposition='accepted';
            CREATE TABLE IF NOT EXISTS codex_followup_reconsiderations (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              proposal_id INTEGER NOT NULL UNIQUE,
              analysis_job_id TEXT NOT NULL,
              proposal_index INTEGER NOT NULL,
              original_disposition TEXT NOT NULL
                CHECK(original_disposition='rejected'),
              original_disposition_reason TEXT NOT NULL,
              expected_proposal_sha256 TEXT NOT NULL,
              expected_spec_sha256 TEXT NOT NULL,
              admission_json TEXT NOT NULL,
              child_experiment_id TEXT NOT NULL UNIQUE,
              child_record_sha256 TEXT NOT NULL,
              reconsidered_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(proposal_id) REFERENCES codex_followup_proposals(id),
              FOREIGN KEY(analysis_job_id) REFERENCES codex_jobs(id),
              FOREIGN KEY(child_experiment_id) REFERENCES experiments(id)
            );
            CREATE TABLE IF NOT EXISTS codex_hardware_lane (
              lane TEXT PRIMARY KEY,
              job_id TEXT NOT NULL,
              experiment_id TEXT,
              lease_owner TEXT NOT NULL,
              lease_token TEXT NOT NULL,
              lease_expires_at TEXT NOT NULL,
              acquired_at TEXT NOT NULL,
              FOREIGN KEY(job_id) REFERENCES codex_jobs(id),
              FOREIGN KEY(experiment_id) REFERENCES experiments(id)
            );
            CREATE TABLE IF NOT EXISTS codex_queue_controls (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              dedupe_key TEXT NOT NULL UNIQUE,
              action TEXT NOT NULL CHECK(action IN ('pause','resume')),
              source_job_id TEXT,
              resumes_control_sequence INTEGER,
              reason TEXT NOT NULL,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(source_job_id) REFERENCES codex_jobs(id),
              FOREIGN KEY(resumes_control_sequence)
                REFERENCES codex_queue_controls(sequence)
            );
            CREATE TABLE IF NOT EXISTS runner_safety_control (
              singleton INTEGER PRIMARY KEY CHECK(singleton=1),
              latched INTEGER NOT NULL CHECK(latched IN (0,1)),
              reason TEXT NOT NULL,
              created_by TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            INSERT OR IGNORE INTO runner_safety_control(
              singleton,latched,reason,created_by,updated_at
            ) VALUES(1,0,'','system','1970-01-01T00:00:00+00:00');
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
            CREATE TRIGGER IF NOT EXISTS experiment_learnings_no_update
              BEFORE UPDATE ON experiment_learnings BEGIN
                SELECT RAISE(ABORT, 'experiment learnings are append-only');
              END;
            CREATE TRIGGER IF NOT EXISTS experiment_learnings_no_delete
              BEFORE DELETE ON experiment_learnings BEGIN
                SELECT RAISE(ABORT, 'experiment learnings are append-only');
              END;
            CREATE TRIGGER IF NOT EXISTS codex_followup_reconsiderations_no_update
              BEFORE UPDATE ON codex_followup_reconsiderations BEGIN
                SELECT RAISE(ABORT, 'follow-up reconsiderations are append-only');
              END;
            CREATE TRIGGER IF NOT EXISTS codex_followup_reconsiderations_no_delete
              BEFORE DELETE ON codex_followup_reconsiderations BEGIN
                SELECT RAISE(ABORT, 'follow-up reconsiderations are append-only');
              END;
            CREATE TRIGGER IF NOT EXISTS codex_transcript_attempts_no_update
              BEFORE UPDATE ON codex_transcript_attempts BEGIN
                SELECT RAISE(ABORT, 'Codex transcript receipts are immutable');
              END;
            CREATE TRIGGER IF NOT EXISTS codex_transcript_attempts_no_delete
              BEFORE DELETE ON codex_transcript_attempts BEGIN
                SELECT RAISE(ABORT, 'Codex transcript receipts are immutable');
              END;
            """)
            # These columns were added while the history feature was still in
            # development. Keep startup safe for a database created by an
            # earlier preview build. The web and Codex LaunchAgents can start
            # together, so lock before re-reading columns and applying ALTERs.
            con.execute("BEGIN IMMEDIATE")
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
            if "evidence_manifest_sha256" not in experiment_columns:
                con.execute(
                    "ALTER TABLE experiments ADD COLUMN evidence_manifest_sha256 TEXT"
                )
            if "evidence_sealed_at" not in experiment_columns:
                con.execute(
                    "ALTER TABLE experiments ADD COLUMN evidence_sealed_at TEXT"
                )
            # A waiting external plan may carry a queue-time pin created by the
            # legacy backfill. Replace the unconditional update guard while the
            # migration write lock is held. The new trigger permits only a
            # same-revision, boundary-free, fully elapsed recording-time repair;
            # every other pin update remains forbidden.
            con.execute("DROP TRIGGER IF EXISTS experiment_tag_layouts_no_update")
            con.execute(f"""
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
                  END
            """)
            codex_job_columns = {
                row["name"] for row in con.execute("PRAGMA table_info(codex_jobs)")
            }
            if "lease_token" not in codex_job_columns:
                con.execute("ALTER TABLE codex_jobs ADD COLUMN lease_token TEXT")
            con.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS codex_jobs_lease_token "
                "ON codex_jobs(lease_token) WHERE lease_token IS NOT NULL"
            )
            followup_columns = {
                row["name"]
                for row in con.execute("PRAGMA table_info(codex_followup_proposals)")
            }
            if "proposal_sha256" not in followup_columns:
                # SQLite cannot add a NOT NULL column without a constant
                # default.  Backfill the canonical digest under the migration
                # write lock; all new receipts always provide it.
                con.execute(
                    "ALTER TABLE codex_followup_proposals "
                    "ADD COLUMN proposal_sha256 TEXT"
                )
                legacy_rows = con.execute(
                    "SELECT id,recommendation_key,spec_json,rationale "
                    "FROM codex_followup_proposals"
                ).fetchall()
                for legacy in legacy_rows:
                    proposal = {
                        "recommendation_key": legacy["recommendation_key"],
                        "rationale": legacy["rationale"],
                        "spec": json.loads(legacy["spec_json"]),
                    }
                    con.execute(
                        "UPDATE codex_followup_proposals SET proposal_sha256=? "
                        "WHERE id=?",
                        (self._proposal_sha256(proposal), legacy["id"]),
                    )
            queue_control_columns = {
                row["name"]
                for row in con.execute("PRAGMA table_info(codex_queue_controls)")
            }
            if "resumes_control_sequence" not in queue_control_columns:
                con.execute(
                    "ALTER TABLE codex_queue_controls ADD COLUMN "
                    "resumes_control_sequence INTEGER REFERENCES "
                    "codex_queue_controls(sequence)"
                )
            hardware_lane_columns = {
                row["name"]
                for row in con.execute("PRAGMA table_info(codex_hardware_lane)")
            }
            if "lease_token" not in hardware_lane_columns:
                # Existing lane rows cannot safely authorize a newly claimed
                # job. They remain harmless until normal lease recovery
                # removes them because assignment checks require a token match.
                con.execute(
                    "ALTER TABLE codex_hardware_lane ADD COLUMN lease_token TEXT"
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
            # Upgrade terminal experiments created before the durable Codex
            # outbox existed. Deterministic keys make this safe on every
            # startup. Sealed evidence is immediately runnable; older
            # filesystem evidence is left for the reconciler to hash and seal.
            terminal_rows = con.execute(
                "SELECT id,created_at,finished_at,evidence_manifest_sha256 "
                "FROM experiments WHERE status IN "
                "('succeeded','failed','cancelled') AND NOT EXISTS ("
                "SELECT 1 FROM codex_jobs WHERE "
                "codex_jobs.experiment_id=experiments.id AND "
                "codex_jobs.trigger_kind='experiment_terminal')"
            ).fetchall()
            for terminal in terminal_rows:
                terminal_at = (
                    terminal["finished_at"] or terminal["created_at"] or utcnow()
                )
                self._enqueue_terminal_codex_jobs(con, terminal["id"], terminal_at)
                if terminal["evidence_manifest_sha256"]:
                    con.execute(
                        "UPDATE codex_jobs SET status='queued',"
                        "evidence_manifest_sha256=?,not_before=?,updated_at=? "
                        "WHERE experiment_id=? AND status='awaiting_evidence'",
                        (
                            terminal["evidence_manifest_sha256"],
                            terminal_at,
                            terminal_at,
                            terminal["id"],
                        ),
                    )
            con.execute("COMMIT")
            con.execute("PRAGMA optimize")

    @staticmethod
    def _recording_time(value: str) -> datetime:
        raw = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "tag layout recorded_at must be an RFC 3339 timestamp"
            ) from exc
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
            raise ValueError(
                "legacy tag layout recording-time rebind was rejected"
            ) from exc
        if updated.rowcount != 1:
            raise ValueError("tag layout pin changed during completion")
        return previous_recorded_at

    @staticmethod
    def row(row: sqlite3.Row) -> Dict[str, Any]:
        item = dict(row)
        item["parameters"] = json.loads(item.pop("parameters_json"))
        item["cancel_requested"] = bool(item["cancel_requested"])
        return item

    @staticmethod
    def _proposal_sha256(proposal: Dict[str, Any]) -> str:
        canonical = json.dumps(
            proposal,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _lease_token_map(self) -> Dict[tuple, str]:
        tokens = getattr(self._codex_lease_tokens, "tokens", None)
        if tokens is None:
            tokens = {}
            self._codex_lease_tokens.tokens = tokens
        return tokens

    def _remember_lease_token(
        self, job_id: str, lease_owner: str, lease_token: str
    ) -> None:
        self._lease_token_map()[(job_id, lease_owner)] = lease_token

    def _resolve_lease_token(
        self, job_id: str, lease_owner: str, lease_token: Optional[str]
    ) -> Optional[str]:
        if lease_token:
            return lease_token
        return self._lease_token_map().get((job_id, lease_owner))

    def _forget_lease_token(
        self, job_id: str, lease_owner: str, lease_token: str
    ) -> None:
        tokens = self._lease_token_map()
        key = (job_id, lease_owner)
        if tokens.get(key) == lease_token:
            tokens.pop(key, None)

    @staticmethod
    def codex_job_row(
        row: sqlite3.Row, *, include_lease_token: bool = False
    ) -> Dict[str, Any]:
        item = dict(row)
        if not include_lease_token:
            item.pop("lease_token", None)
        raw_result = item.pop("result_json", None)
        item["result"] = json.loads(raw_result) if raw_result else None
        return item

    @contextmanager
    def evidence_lock(self, experiment_id: str):
        """Serialize artifact commits and sealing across web/worker processes."""
        lock_dir = self.path.parent / ".evidence-locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_name = hashlib.sha256(experiment_id.encode("utf-8")).hexdigest() + ".lock"
        with (lock_dir / lock_name).open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def finalize_evidence(
        self,
        experiment_id: str,
        run_dir: Path,
        manifest_writer,
        guard: Optional[Callable[[], None]] = None,
    ) -> Dict[str, Any]:
        """Write the final manifest and seal its digest under one file lock."""
        with self.evidence_lock(experiment_id):
            if guard is not None:
                guard()
            try:
                active_upload = any(
                    path.is_file() and path.name.endswith(".upload")
                    for path in run_dir.iterdir()
                )
            except FileNotFoundError:
                active_upload = False
            if active_upload:
                raise ValueError(
                    "Experiment still has an unfinished artifact upload"
                )
            current = self.get(experiment_id)
            if current and current.get("evidence_manifest_sha256"):
                manifest_path = run_dir / "manifest.json"
                if not manifest_path.is_file():
                    raise ValueError("Sealed evidence manifest is missing")
                actual = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
                if actual != current["evidence_manifest_sha256"]:
                    raise ValueError("Sealed evidence manifest no longer matches its digest")
                return current
            manifest_sha256 = manifest_writer(run_dir)
            return self._seal_evidence_record(experiment_id, manifest_sha256)

    def seal_evidence(
        self, experiment_id: str, manifest_sha256: str
    ) -> Dict[str, Any]:
        with self.evidence_lock(experiment_id):
            return self._seal_evidence_record(experiment_id, manifest_sha256)

    def _enqueue_terminal_codex_jobs(
        self,
        con: sqlite3.Connection,
        experiment_id: str,
        now: str,
        *,
        max_attempts: Optional[int] = None,
    ) -> None:
        """Write the completion outbox in the same transaction as terminal state."""
        max_attempts = max_attempts or self.codex_max_attempts
        analysis_key = f"terminal:{experiment_id}:analysis"
        analysis_id = uuid.uuid4().hex
        con.execute(
            "INSERT OR IGNORE INTO codex_jobs("
            "id,dedupe_key,kind,trigger_kind,experiment_id,status,max_attempts,"
            "not_before,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                analysis_id,
                analysis_key,
                "analysis",
                "experiment_terminal",
                experiment_id,
                "awaiting_evidence",
                max_attempts,
                now,
                now,
                now,
            ),
        )
        analysis = con.execute(
            "SELECT id FROM codex_jobs WHERE dedupe_key=?", (analysis_key,)
        ).fetchone()
        advance_key = f"terminal:{experiment_id}:advance"
        con.execute(
            "INSERT OR IGNORE INTO codex_jobs("
            "id,dedupe_key,kind,trigger_kind,experiment_id,status,"
            "depends_on_job_id,max_attempts,not_before,created_at,updated_at"
            ") VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                uuid.uuid4().hex,
                advance_key,
                "advance",
                "experiment_terminal",
                experiment_id,
                "awaiting_evidence",
                analysis["id"],
                max_attempts,
                now,
                now,
                now,
            ),
        )

    def _seal_evidence_record(
        self, experiment_id: str, manifest_sha256: str
    ) -> Dict[str, Any]:
        """Seal immutable evidence and make its completion jobs runnable."""
        if not (
            isinstance(manifest_sha256, str)
            and len(manifest_sha256) == 64
            and all(char in "0123456789abcdef" for char in manifest_sha256)
        ):
            raise ValueError("manifest_sha256 must be a lowercase SHA-256")
        now = utcnow()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT status,evidence_manifest_sha256 FROM experiments WHERE id=?",
                (experiment_id,),
            ).fetchone()
            if not row:
                con.execute("ROLLBACK")
                raise ValueError("Experiment not found")
            if row["status"] not in TERMINAL:
                con.execute("ROLLBACK")
                raise ValueError("Evidence may only be sealed for a completed experiment")
            current = row["evidence_manifest_sha256"]
            if current and current != manifest_sha256:
                con.execute("ROLLBACK")
                raise ValueError("Experiment evidence is already sealed with a different manifest")
            self._enqueue_terminal_codex_jobs(con, experiment_id, now)
            repaired_analysis_id = None
            if not current:
                analysis = con.execute(
                    "SELECT id,status,result_json FROM codex_jobs "
                    "WHERE dedupe_key=?",
                    (f"terminal:{experiment_id}:analysis",),
                ).fetchone()
                prior_result = None
                if analysis and analysis["result_json"]:
                    try:
                        prior_result = json.loads(analysis["result_json"])
                    except (TypeError, json.JSONDecodeError):
                        prior_result = None
                if (
                    analysis
                    and analysis["status"] == "dead"
                    and isinstance(prior_result, dict)
                    and prior_result.get("action") == "evidence_timeout"
                ):
                    # Late valid evidence repairs the analysis lane only. The
                    # dependent advance stays blocked until this analysis has
                    # succeeded and an operator explicitly resumes the queue.
                    con.execute(
                        "UPDATE codex_jobs SET status='queued',attempts=0,"
                        "evidence_manifest_sha256=?,not_before=?,started_at=NULL,"
                        "finished_at=NULL,updated_at=?,lease_owner=NULL,"
                        "lease_token=NULL,lease_expires_at=NULL,result_json=NULL,"
                        "error=NULL WHERE id=? AND status='dead'",
                        (manifest_sha256, now, now, analysis["id"]),
                    )
                    repaired_analysis_id = analysis["id"]
            if not current:
                con.execute(
                    "UPDATE experiments SET evidence_manifest_sha256=?,"
                    "evidence_sealed_at=? WHERE id=? AND evidence_manifest_sha256 IS NULL",
                    (manifest_sha256, now, experiment_id),
                )
                con.execute(
                    "INSERT INTO events(experiment_id,timestamp,kind,message) "
                    "VALUES(?,?,?,?)",
                    (
                        experiment_id,
                        now,
                        "evidence_sealed",
                        f"Evidence sealed at manifest SHA-256 {manifest_sha256}",
                    ),
                )
            con.execute(
                "UPDATE codex_jobs SET status='queued',evidence_manifest_sha256=?,"
                "not_before=?,updated_at=? WHERE experiment_id=? "
                "AND status='awaiting_evidence'",
                (manifest_sha256, now, now, experiment_id),
            )
            if repaired_analysis_id:
                con.execute(
                    "INSERT INTO events(experiment_id,timestamp,kind,message) "
                    "VALUES(?,?,?,?)",
                    (
                        experiment_id,
                        now,
                        "codex_evidence_repaired",
                        "Late sealed evidence requeued its timed-out Codex analysis",
                    ),
                )
            con.execute("COMMIT")
        result = self.get(experiment_id)
        if result is None:
            raise ValueError("Experiment not found")
        return result

    def codex_jobs_for_experiment(self, experiment_id: str) -> list:
        with self.connect() as con:
            rows = con.execute(
                "SELECT * FROM codex_jobs WHERE experiment_id=? "
                "ORDER BY created_at,id",
                (experiment_id,),
            ).fetchall()
        return [self.codex_job_row(row) for row in rows]

    def register_codex_transcript_attempt(
        self,
        job_id: str,
        attempt: int,
        manifest_sha256: str,
        *,
        kind: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persist the immutable digest that makes an attempt downloadable."""
        if (
            not isinstance(attempt, int)
            or isinstance(attempt, bool)
            or attempt < 1
            or not isinstance(manifest_sha256, str)
            or len(manifest_sha256) != 64
            or any(char not in "0123456789abcdef" for char in manifest_sha256)
        ):
            raise ValueError("Invalid Codex transcript receipt")
        now = utcnow()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            job = self._codex_transcript_source_job(con, job_id, kind=kind)
            if job is None:
                con.execute("ROLLBACK")
                raise ValueError("Codex job not found")
            if kind is not None and job["kind"] != kind:
                con.execute("ROLLBACK")
                raise ValueError("Codex transcript kind does not match its job")
            if attempt > int(job["attempts"]):
                con.execute("ROLLBACK")
                raise ValueError("Codex transcript attempt was never claimed")
            existing = con.execute(
                "SELECT * FROM codex_transcript_attempts "
                "WHERE job_id=? AND attempt=?",
                (job_id, attempt),
            ).fetchone()
            if existing is not None:
                if existing["manifest_sha256"] != manifest_sha256:
                    con.execute("ROLLBACK")
                    raise ValueError(
                        "Codex transcript attempt is already sealed differently"
                    )
                con.execute("COMMIT")
                return dict(existing)
            con.execute(
                "INSERT INTO codex_transcript_attempts("
                "job_id,attempt,experiment_id,kind,manifest_sha256,created_at"
                ") VALUES(?,?,?,?,?,?)",
                (
                    job_id,
                    attempt,
                    job["experiment_id"],
                    job["kind"],
                    manifest_sha256,
                    now,
                ),
            )
            row = con.execute(
                "SELECT * FROM codex_transcript_attempts "
                "WHERE job_id=? AND attempt=?",
                (job_id, attempt),
            ).fetchone()
            con.execute("COMMIT")
        return dict(row)

    @staticmethod
    def _codex_transcript_source_job(
        con: sqlite3.Connection, job_id: str, *, kind: Optional[str] = None
    ):
        if kind != "engineering":
            job = con.execute(
                "SELECT id,experiment_id,kind,attempts,status "
                "FROM codex_jobs WHERE id=?",
                (job_id,),
            ).fetchone()
            if job is not None:
                return job
        engineering_exists = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='codex_engineering_jobs'"
        ).fetchone()
        if engineering_exists is None:
            return None
        return con.execute(
            "SELECT id,experiment_id,'engineering' AS kind,attempts,status "
            "FROM codex_engineering_jobs WHERE id=?",
            (job_id,),
        ).fetchone()

    def get_codex_transcript_source_job(
        self, job_id: str
    ) -> Optional[Dict[str, Any]]:
        with self.connect() as con:
            row = self._codex_transcript_source_job(con, job_id)
        return dict(row) if row else None

    def codex_engineering_jobs_for_experiment(self, experiment_id: str) -> list:
        with self.connect() as con:
            exists = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='codex_engineering_jobs'"
            ).fetchone()
            if exists is None:
                return []
            rows = con.execute(
                "SELECT * FROM codex_engineering_jobs WHERE experiment_id=? "
                "ORDER BY created_at,id",
                (experiment_id,),
            ).fetchall()
        results = []
        for row in rows:
            result = dict(row)
            result.pop("lease_token", None)
            result["kind"] = "engineering"
            for source, target in (
                ("source_context_json", "source_context"),
                ("result_json", "result"),
            ):
                raw = result.pop(source, None)
                result[target] = json.loads(raw) if raw else None
            results.append(result)
        return results

    def codex_transcript_attempt(
        self, job_id: str, attempt: int
    ) -> Optional[Dict[str, Any]]:
        with self.connect() as con:
            row = con.execute(
                "SELECT * FROM codex_transcript_attempts "
                "WHERE job_id=? AND attempt=?",
                (job_id, attempt),
            ).fetchone()
        return dict(row) if row else None

    def list_codex_jobs(self, limit: int = 100) -> list:
        with self.connect() as con:
            rows = con.execute(
                "SELECT * FROM codex_jobs ORDER BY created_at DESC,id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self.codex_job_row(row) for row in rows]

    def get_codex_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as con:
            row = con.execute(
                "SELECT * FROM codex_jobs WHERE id=?", (job_id,)
            ).fetchone()
        return self.codex_job_row(row) if row else None

    def unsealed_codex_experiments(self, limit: int = 100) -> list:
        """Completed experiments with a new outbox awaiting final evidence."""
        with self.connect() as con:
            rows = con.execute(
                "SELECT DISTINCT experiment.* FROM experiments AS experiment "
                "JOIN codex_jobs AS job ON job.experiment_id=experiment.id "
                "WHERE experiment.status IN ('succeeded','failed','cancelled') "
                "AND experiment.evidence_sealed_at IS NULL "
                "AND job.status='awaiting_evidence' "
                "ORDER BY experiment.finished_at,experiment.id LIMIT ?",
                (limit,),
            ).fetchall()
        return [self.row(row) for row in rows]

    def fail_stale_awaiting_evidence(
        self,
        experiment_id: str,
        reason: str,
        *,
        created_by: str = "codex-orchestrator",
    ) -> Dict[str, Any]:
        """Fail closed after the reconciler decides evidence is stale.

        The caller owns the age and filesystem checks.  This method only
        rechecks durable state and atomically terminates the waiting outbox and
        latches a queue pause.  Taking the evidence lock prevents a final seal
        and a stale decision from crossing in flight.
        """
        reason = reason.strip()
        if not reason:
            raise ValueError("Stale evidence reason must not be blank")
        reason = reason[:6000]
        now = utcnow()
        with self.evidence_lock(experiment_id):
            with self.connect() as con:
                con.execute("BEGIN IMMEDIATE")
                experiment = con.execute(
                    "SELECT status,evidence_sealed_at FROM experiments WHERE id=?",
                    (experiment_id,),
                ).fetchone()
                if experiment is None:
                    con.execute("ROLLBACK")
                    raise ValueError("Experiment not found")
                if experiment["status"] not in TERMINAL:
                    con.execute("ROLLBACK")
                    raise ValueError(
                        "Only a terminal experiment can have stale final evidence"
                    )
                waiting = con.execute(
                    "SELECT * FROM codex_jobs WHERE experiment_id=? "
                    "AND status='awaiting_evidence' "
                    "AND kind IN ('analysis','advance') ORDER BY "
                    "CASE kind WHEN 'analysis' THEN 0 ELSE 1 END,created_at,id",
                    (experiment_id,),
                ).fetchall()
                if experiment["evidence_sealed_at"] is not None or not waiting:
                    con.execute("COMMIT")
                    return {
                        "experiment_id": experiment_id,
                        "affected_count": 0,
                        "analysis_dead_count": 0,
                        "advance_blocked_count": 0,
                        "jobs": [],
                        "queue_control": None,
                    }
                job_ids = []
                analysis_dead = 0
                advance_blocked = 0
                for job in waiting:
                    status = "dead" if job["kind"] == "analysis" else "blocked"
                    changed = con.execute(
                        "UPDATE codex_jobs SET status=?,finished_at=?,updated_at=?,"
                        "lease_owner=NULL,lease_token=NULL,lease_expires_at=NULL,"
                        "result_json=?,error=? WHERE id=? "
                        "AND status='awaiting_evidence'",
                        (
                            status,
                            now,
                            now,
                            json.dumps(
                                {
                                    "action": "evidence_timeout",
                                    "reason": reason,
                                },
                                sort_keys=True,
                            ),
                            reason,
                            job["id"],
                        ),
                    ).rowcount
                    if changed:
                        job_ids.append(job["id"])
                        if job["kind"] == "analysis":
                            analysis_dead += 1
                        else:
                            advance_blocked += 1
                if not job_ids:
                    con.execute("COMMIT")
                    return {
                        "experiment_id": experiment_id,
                        "affected_count": 0,
                        "analysis_dead_count": 0,
                        "advance_blocked_count": 0,
                        "jobs": [],
                        "queue_control": None,
                    }
                source_job_id = job_ids[0]
                pause = con.execute(
                    "INSERT INTO codex_queue_controls("
                    "dedupe_key,action,source_job_id,reason,created_by,created_at"
                    ") VALUES(?,'pause',?,?,?,?)",
                    (
                        f"pause:stale-evidence:{source_job_id}",
                        source_job_id,
                        reason,
                        created_by,
                        now,
                    ),
                )
                con.execute("DELETE FROM codex_hardware_lane")
                con.execute(
                    "INSERT INTO events(experiment_id,timestamp,kind,message) "
                    "VALUES(?,?,?,?)",
                    (experiment_id, now, "codex_evidence_timeout", reason),
                )
                placeholders = ",".join("?" for _ in job_ids)
                updated = con.execute(
                    f"SELECT * FROM codex_jobs WHERE id IN ({placeholders}) "
                    "ORDER BY CASE kind WHEN 'analysis' THEN 0 ELSE 1 END,"
                    "created_at,id",
                    tuple(job_ids),
                ).fetchall()
                control = con.execute(
                    "SELECT * FROM codex_queue_controls WHERE sequence=?",
                    (pause.lastrowid,),
                ).fetchone()
                con.execute("COMMIT")
        control_result = dict(control)
        control_result["paused"] = True
        return {
            "experiment_id": experiment_id,
            "affected_count": len(updated),
            "analysis_dead_count": analysis_dead,
            "advance_blocked_count": advance_blocked,
            "jobs": [self.codex_job_row(job) for job in updated],
            "queue_control": control_result,
        }

    def enqueue_advance(
        self,
        dedupe_key: str,
        trigger_kind: str,
        *,
        experiment_id: Optional[str] = None,
        depends_on_job_id: Optional[str] = None,
        max_attempts: Optional[int] = None,
    ) -> Dict[str, Any]:
        now = utcnow()
        max_attempts = max_attempts or self.codex_max_attempts
        job_id = uuid.uuid4().hex
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "INSERT OR IGNORE INTO codex_jobs("
                "id,dedupe_key,kind,trigger_kind,experiment_id,status,"
                "depends_on_job_id,max_attempts,not_before,created_at,updated_at"
                ") VALUES(?,?,?,?,?,'queued',?,?,?,?,?)",
                (
                    job_id,
                    dedupe_key,
                    "advance",
                    trigger_kind,
                    experiment_id,
                    depends_on_job_id,
                    max_attempts,
                    now,
                    now,
                    now,
                ),
            )
            row = con.execute(
                "SELECT * FROM codex_jobs WHERE dedupe_key=?", (dedupe_key,)
            ).fetchone()
            con.execute("COMMIT")
        return self.codex_job_row(row)

    def recover_expired_codex_jobs(self) -> int:
        now = utcnow()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            exhausted_analyses = con.execute(
                "SELECT id,error FROM codex_jobs WHERE status='running' "
                "AND kind='analysis' AND attempts>=max_attempts "
                "AND lease_expires_at IS NOT NULL AND lease_expires_at<? "
                "ORDER BY created_at,id",
                (now,),
            ).fetchall()
            exhausted_advances = con.execute(
                "SELECT id,error FROM codex_jobs WHERE status='running' "
                "AND kind='advance' AND attempts>=max_attempts "
                "AND lease_expires_at IS NOT NULL AND lease_expires_at<? "
                "ORDER BY created_at,id",
                (now,),
            ).fetchall()
            dead_advances = con.execute(
                "UPDATE codex_jobs SET status='dead',lease_owner=NULL,"
                "lease_token=NULL,lease_expires_at=NULL,finished_at=?,updated_at=?,"
                "error=COALESCE(error,'Advisory advance lease expired at its retry limit') "
                "WHERE status='running' AND kind='advance' "
                "AND attempts>=max_attempts "
                "AND lease_expires_at IS NOT NULL AND lease_expires_at<?",
                (now, now, now),
            ).rowcount
            for advance in exhausted_advances:
                self._insert_codex_queue_pause(
                    con,
                    advance["id"],
                    advance["error"]
                    or "Advisory queue review exhausted its retry limit",
                    "codex-orchestrator",
                    now,
                )
            retried_advances = con.execute(
                "UPDATE codex_jobs SET status='retry',lease_owner=NULL,"
                "lease_token=NULL,lease_expires_at=NULL,not_before=?,updated_at=?,"
                "error=COALESCE(error,'Advisory advance lease expired; retrying') "
                "WHERE status='running' AND kind='advance' "
                "AND attempts<max_attempts "
                "AND lease_expires_at IS NOT NULL AND lease_expires_at<?",
                (now, now, now),
            ).rowcount
            dead = con.execute(
                "UPDATE codex_jobs SET status='dead',lease_owner=NULL,"
                "lease_token=NULL,lease_expires_at=NULL,finished_at=?,updated_at=?,"
                "error=COALESCE(error,'Analysis lease expired at its retry limit') "
                "WHERE status='running' AND kind='analysis' "
                "AND attempts>=max_attempts AND lease_expires_at IS NOT NULL "
                "AND lease_expires_at<?",
                (now, now, now),
            ).rowcount
            for analysis in exhausted_analyses:
                self._insert_codex_queue_pause(
                    con,
                    analysis["id"],
                    analysis["error"]
                    or "Analysis lease expired at its retry limit",
                    "codex-orchestrator",
                    now,
                )
            retried = con.execute(
                "UPDATE codex_jobs SET status='retry',lease_owner=NULL,"
                "lease_token=NULL,lease_expires_at=NULL,not_before=?,updated_at=?,"
                "error=COALESCE(error,'Worker lease expired; retrying') "
                "WHERE status='running' AND kind='analysis' "
                "AND attempts<max_attempts AND lease_expires_at IS NOT NULL "
                "AND lease_expires_at<?",
                (now, now, now),
            ).rowcount
            con.execute(
                "DELETE FROM codex_hardware_lane WHERE lease_expires_at<?", (now,)
            )
            con.execute("COMMIT")
        return dead_advances + retried_advances + dead + retried

    def expire_codex_job_lease(self, job_id: str, reason: str) -> bool:
        """Fence an unfinished child discovered during supervisor startup."""
        expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            changed = con.execute(
                "UPDATE codex_jobs SET lease_expires_at=?,error=? "
                "WHERE id=? AND status='running'",
                (expired, reason[:6000], job_id),
            ).rowcount
            if changed:
                con.execute(
                    "DELETE FROM codex_hardware_lane WHERE job_id=?", (job_id,)
                )
            con.execute("COMMIT")
        return changed == 1

    @staticmethod
    def _insert_codex_queue_pause(
        con: sqlite3.Connection,
        source_job_id: str,
        reason: str,
        created_by: str,
        now: str,
    ) -> None:
        con.execute(
            "INSERT OR IGNORE INTO codex_queue_controls("
            "dedupe_key,action,source_job_id,reason,created_by,created_at"
            ") VALUES(?,'pause',?,?,?,?)",
            (
                f"pause:{source_job_id}",
                source_job_id,
                (reason or "Codex advance stopped")[:6000],
                created_by,
                now,
            ),
        )
        # There is only one physical lane. A durable safety pause revokes it
        # immediately so any action-capable child fails its next lease poll.
        con.execute("DELETE FROM codex_hardware_lane")

    def claim_codex_job(
        self,
        kind: str,
        lease_owner: str,
        *,
        lease_seconds: int,
    ) -> Optional[Dict[str, Any]]:
        if kind not in CODEX_JOB_KINDS:
            raise ValueError("invalid Codex job kind")
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        lease_expires = (now_dt + timedelta(seconds=lease_seconds)).isoformat()
        lease_token = uuid.uuid4().hex
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT job.id FROM codex_jobs AS job "
                "LEFT JOIN codex_jobs AS dependency ON dependency.id=job.depends_on_job_id "
                "LEFT JOIN codex_queue_controls AS control ON control.sequence=("
                "SELECT MAX(sequence) FROM codex_queue_controls) "
                "WHERE job.kind=? AND job.status IN ('queued','retry') "
                "AND job.not_before<=? "
                "AND (job.depends_on_job_id IS NULL "
                "OR dependency.status IN ('succeeded','blocked','dead')) "
                "AND (?<>'advance' OR NOT EXISTS ("
                "SELECT 1 FROM codex_jobs AS analysis "
                "WHERE analysis.kind='analysis' AND analysis.status IN ("
                "'awaiting_evidence','queued','running','retry'))) "
                "AND (?<>'advance' OR control.action IS NULL "
                "OR control.action<>'pause' OR ("
                "job.depends_on_job_id IS NOT NULL "
                "AND dependency.kind='analysis' "
                "AND job.trigger_kind='experiment_terminal' "
                "AND control.source_job_id=job.depends_on_job_id)) "
                "ORDER BY job.created_at,job.id LIMIT 1",
                (kind, now, kind, kind),
            ).fetchone()
            if not row:
                con.execute("COMMIT")
                return None
            updated = con.execute(
                "UPDATE codex_jobs SET status='running',attempts=attempts+1,"
                "lease_owner=?,lease_token=?,lease_expires_at=?,"
                "started_at=COALESCE(started_at,?),"
                "updated_at=?,error=NULL WHERE id=? AND status IN ('queued','retry')",
                (lease_owner, lease_token, lease_expires, now, now, row["id"]),
            )
            if updated.rowcount != 1:
                con.execute("ROLLBACK")
                return None
            claimed = con.execute(
                "SELECT * FROM codex_jobs WHERE id=?", (row["id"],)
            ).fetchone()
            con.execute("COMMIT")
        self._remember_lease_token(row["id"], lease_owner, lease_token)
        return self.codex_job_row(claimed, include_lease_token=True)

    def finish_codex_job(
        self,
        job_id: str,
        lease_owner: str,
        status: str,
        *,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        lease_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if status not in CODEX_JOB_TERMINAL:
            raise ValueError("invalid terminal Codex job status")
        now = utcnow()
        resolved_token = self._resolve_lease_token(job_id, lease_owner, lease_token)
        if not resolved_token:
            raise ValueError("Codex job claim token is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            owned = con.execute(
                "SELECT kind FROM codex_jobs WHERE id=? AND status='running' "
                "AND lease_owner=? AND lease_token=? AND lease_expires_at>=?",
                (job_id, lease_owner, resolved_token, now),
            ).fetchone()
            if owned is None:
                con.execute("ROLLBACK")
                raise ValueError("Codex job lease is no longer owned by this worker")
            updated = con.execute(
                "UPDATE codex_jobs SET status=?,finished_at=?,updated_at=?,"
                "lease_owner=NULL,lease_token=NULL,lease_expires_at=NULL,"
                "result_json=?,error=? WHERE id=? AND status='running' "
                "AND lease_owner=? AND lease_token=? AND lease_expires_at>=?",
                (
                    status,
                    now,
                    now,
                    json.dumps(result, sort_keys=True) if result is not None else None,
                    error,
                    job_id,
                    lease_owner,
                    resolved_token,
                    now,
                ),
            )
            if updated.rowcount != 1:
                con.execute("ROLLBACK")
                raise ValueError("Codex job lease is no longer owned by this worker")
            if status in {"blocked", "dead"}:
                self._insert_codex_queue_pause(
                    con,
                    job_id,
                    error or f"Codex {owned['kind']} stopped without a clear completion",
                    "codex-orchestrator",
                    now,
                )
            con.execute("DELETE FROM codex_hardware_lane WHERE job_id=?", (job_id,))
            row = con.execute("SELECT * FROM codex_jobs WHERE id=?", (job_id,)).fetchone()
            con.execute("COMMIT")
        self._forget_lease_token(job_id, lease_owner, resolved_token)
        return self.codex_job_row(row)

    def finish_advisory_advance(
        self,
        job_id: str,
        lease_owner: str,
        target_experiment_id: str,
        *,
        blocked_result: Dict[str, Any],
        blocked_error: str,
        superseded_result: Dict[str, Any],
        lease_token: Optional[str] = None,
    ) -> tuple[Dict[str, Any], bool]:
        """Atomically block-and-pause only while the reviewed plan is waiting.

        Manual completion or cancellation may race the read-only Codex review.
        Checking the target and committing the receipt in one transaction keeps
        a now-terminal plan from creating a stale global queue pause.
        """
        now = utcnow()
        resolved_token = self._resolve_lease_token(job_id, lease_owner, lease_token)
        if not resolved_token:
            raise ValueError("Codex job claim token is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            owned = con.execute(
                "SELECT kind FROM codex_jobs WHERE id=? AND status='running' "
                "AND lease_owner=? AND lease_token=? AND lease_expires_at>=?",
                (job_id, lease_owner, resolved_token, now),
            ).fetchone()
            if owned is None or owned["kind"] != "advance":
                con.execute("ROLLBACK")
                raise ValueError("Codex advance job lease is no longer owned")
            target = con.execute(
                "SELECT status FROM experiments WHERE id=?",
                (target_experiment_id,),
            ).fetchone()
            target_still_waiting = bool(
                target is not None and target["status"] == WAITING_FOR_OPERATOR
            )
            status = "blocked" if target_still_waiting else "succeeded"
            result = blocked_result if target_still_waiting else superseded_result
            error = blocked_error if target_still_waiting else None
            updated = con.execute(
                "UPDATE codex_jobs SET status=?,finished_at=?,updated_at=?,"
                "lease_owner=NULL,lease_token=NULL,lease_expires_at=NULL,"
                "result_json=?,error=? WHERE id=? AND status='running' "
                "AND lease_owner=? AND lease_token=? AND lease_expires_at>=?",
                (
                    status,
                    now,
                    now,
                    json.dumps(result, sort_keys=True),
                    error,
                    job_id,
                    lease_owner,
                    resolved_token,
                    now,
                ),
            )
            if updated.rowcount != 1:
                con.execute("ROLLBACK")
                raise ValueError("Codex advance job lease is no longer owned")
            if target_still_waiting:
                self._insert_codex_queue_pause(
                    con,
                    job_id,
                    blocked_error,
                    "codex-orchestrator",
                    now,
                )
            con.execute("DELETE FROM codex_hardware_lane WHERE job_id=?", (job_id,))
            row = con.execute(
                "SELECT * FROM codex_jobs WHERE id=?", (job_id,)
            ).fetchone()
            con.execute("COMMIT")
        self._forget_lease_token(job_id, lease_owner, resolved_token)
        return self.codex_job_row(row), target_still_waiting

    def checkpoint_codex_job_result(
        self,
        job_id: str,
        lease_owner: str,
        result: Dict[str, Any],
        *,
        lease_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Durably freeze a validated receipt before applying side effects.

        An analysis process may die after creating learnings or follow-up rows
        but before its final status update.  Keeping one immutable normalized
        receipt on the leased job makes that retry deterministic.
        """
        now = utcnow()
        resolved_token = self._resolve_lease_token(job_id, lease_owner, lease_token)
        if not resolved_token:
            raise ValueError("Codex job claim token is required")
        canonical = json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT result_json FROM codex_jobs WHERE id=? "
                "AND status='running' AND lease_owner=? AND lease_token=? "
                "AND lease_expires_at>=?",
                (job_id, lease_owner, resolved_token, now),
            ).fetchone()
            if row is None:
                con.execute("ROLLBACK")
                raise ValueError("Codex job lease is no longer owned by this worker")
            if row["result_json"] is not None:
                existing = json.dumps(
                    json.loads(row["result_json"]),
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                )
                if existing != canonical:
                    con.execute("ROLLBACK")
                    raise ValueError("Codex job already has a different result checkpoint")
            else:
                con.execute(
                    "UPDATE codex_jobs SET result_json=?,updated_at=? WHERE id=? "
                    "AND status='running' AND lease_owner=? AND lease_token=? "
                    "AND lease_expires_at>=?",
                    (canonical, now, job_id, lease_owner, resolved_token, now),
                )
            con.execute("COMMIT")
        return json.loads(canonical)

    def retry_codex_job(
        self,
        job_id: str,
        lease_owner: str,
        error: str,
        *,
        delay_seconds: float,
        result: Optional[Dict[str, Any]] = None,
        lease_token: Optional[str] = None,
        pause_on_exhaustion: bool = True,
    ) -> Dict[str, Any]:
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        not_before = (now_dt + timedelta(seconds=max(0, delay_seconds))).isoformat()
        resolved_token = self._resolve_lease_token(job_id, lease_owner, lease_token)
        if not resolved_token:
            raise ValueError("Codex job claim token is required")
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT attempts,max_attempts,kind FROM codex_jobs "
                "WHERE id=? AND status='running' AND lease_owner=? "
                "AND lease_token=? AND lease_expires_at>=?",
                (job_id, lease_owner, resolved_token, now),
            ).fetchone()
            if not row:
                con.execute("ROLLBACK")
                raise ValueError("Codex job lease is no longer owned by this worker")
            terminal = row["attempts"] >= row["max_attempts"]
            status = "dead" if terminal else "retry"
            con.execute(
                "UPDATE codex_jobs SET status=?,not_before=?,updated_at=?,"
                "finished_at=?,lease_owner=NULL,lease_token=NULL,"
                "lease_expires_at=NULL,error=?,"
                "result_json=COALESCE(?,result_json) WHERE id=? "
                "AND status='running' AND lease_owner=? AND lease_token=?",
                (
                    status,
                    not_before,
                    now,
                    now if terminal else None,
                    error,
                    json.dumps(result, sort_keys=True) if result is not None else None,
                    job_id,
                    lease_owner,
                    resolved_token,
                ),
            )
            if terminal and pause_on_exhaustion:
                self._insert_codex_queue_pause(
                    con,
                    job_id,
                    error or f"Codex {row['kind']} exhausted its retry limit",
                    "codex-orchestrator",
                    now,
                )
            con.execute("DELETE FROM codex_hardware_lane WHERE job_id=?", (job_id,))
            updated = con.execute(
                "SELECT * FROM codex_jobs WHERE id=?", (job_id,)
            ).fetchone()
            con.execute("COMMIT")
        self._forget_lease_token(job_id, lease_owner, resolved_token)
        return self.codex_job_row(updated)

    def acquire_hardware_lane(
        self,
        job_id: str,
        experiment_id: Optional[str],
        lease_owner: str,
        *,
        lease_seconds: int,
        lease_token: Optional[str] = None,
    ) -> bool:
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        lease_expires = (now_dt + timedelta(seconds=lease_seconds)).isoformat()
        resolved_token = self._resolve_lease_token(job_id, lease_owner, lease_token)
        if not resolved_token:
            return False
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute("DELETE FROM codex_hardware_lane WHERE lease_expires_at<?", (now,))
            job = con.execute(
                "SELECT 1 FROM codex_jobs WHERE id=? AND kind='advance' "
                "AND status='running' AND lease_owner=? AND lease_token=? "
                "AND lease_expires_at>=?",
                (job_id, lease_owner, resolved_token, now),
            ).fetchone()
            if job is None:
                con.execute("ROLLBACK")
                return False
            if experiment_id is not None:
                experiment = con.execute(
                    "SELECT status,execution_mode FROM experiments WHERE id=?",
                    (experiment_id,),
                ).fetchone()
                if (
                    experiment is None
                    or experiment["status"] != WAITING_FOR_OPERATOR
                    or experiment["execution_mode"] != "external_guarded"
                ):
                    con.execute("ROLLBACK")
                    return False
            try:
                con.execute(
                    "INSERT INTO codex_hardware_lane("
                    "lane,job_id,experiment_id,lease_owner,lease_token,"
                    "lease_expires_at,acquired_at) VALUES('physical',?,?,?,?,?,?)",
                    (
                        job_id,
                        experiment_id,
                        lease_owner,
                        resolved_token,
                        lease_expires,
                        now,
                    ),
                )
            except sqlite3.IntegrityError:
                con.execute("ROLLBACK")
                return False
            con.execute("COMMIT")
        return True

    def automation_assignment_active(self, experiment_id: str) -> bool:
        """Whether the scoped automation token currently owns this one plan."""
        now = utcnow()
        with self.connect() as con:
            row = con.execute(
                "SELECT 1 FROM codex_hardware_lane AS lane "
                "JOIN codex_jobs AS job ON job.id=lane.job_id "
                "WHERE lane.lane='physical' AND lane.experiment_id=? "
                "AND lane.lease_expires_at>=? AND job.kind='advance' "
                "AND job.status='running' AND job.lease_expires_at>=? "
                "AND lane.lease_owner=job.lease_owner "
                "AND lane.lease_token=job.lease_token "
                "AND NOT EXISTS (SELECT 1 FROM codex_queue_controls "
                "WHERE action='pause' AND sequence=(SELECT MAX(sequence) "
                "FROM codex_queue_controls)) LIMIT 1",
                (experiment_id, now, now),
            ).fetchone()
        return row is not None

    def next_external_experiment(self) -> Optional[Dict[str, Any]]:
        """Return the oldest saved physical plan; the agent still checks readiness."""
        with self.connect() as con:
            row = con.execute(
                "SELECT * FROM experiments WHERE status=? "
                "AND execution_mode='external_guarded' "
                "ORDER BY created_at,id LIMIT 1",
                (WAITING_FOR_OPERATOR,),
            ).fetchone()
        return self.row(row) if row else None

    def queue_counts(self) -> Dict[str, int]:
        with self.connect() as con:
            rows = con.execute(
                "SELECT status,COUNT(*) AS count FROM experiments "
                "WHERE status IN ('queued','running',?) GROUP BY status",
                (WAITING_FOR_OPERATOR,),
            ).fetchall()
        counts = {"queued": 0, "running": 0, WAITING_FOR_OPERATOR: 0}
        counts.update({row["status"]: row["count"] for row in rows})
        return counts

    def codex_queue_control(self) -> Dict[str, Any]:
        with self.connect() as con:
            row = con.execute(
                "SELECT * FROM codex_queue_controls ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return {"paused": False, "action": None}
        result = dict(row)
        result["paused"] = row["action"] == "pause"
        return result

    def runner_safety_control(self) -> Dict[str, Any]:
        with self.connect() as con:
            row = con.execute(
                "SELECT * FROM runner_safety_control WHERE singleton=1"
            ).fetchone()
        return {
            "latched": bool(row["latched"]),
            "reason": row["reason"],
            "created_by": row["created_by"],
            "updated_at": row["updated_at"],
        }

    def latch_runner_safety(self, reason: str, *, created_by: str) -> Dict[str, Any]:
        reason = reason.strip()
        if not reason:
            raise ValueError("Runner safety latch reason must not be blank")
        now = utcnow()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "UPDATE runner_safety_control SET latched=1,reason=?,"
                "created_by=?,updated_at=? WHERE singleton=1",
                (reason[:6000], created_by, now),
            )
            con.execute("COMMIT")
        return self.runner_safety_control()

    def resume_runner_safety(self, reason: str, *, created_by: str) -> Dict[str, Any]:
        reason = reason.strip()
        if not reason:
            raise ValueError("Runner safety resume reason must not be blank")
        now = utcnow()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "UPDATE runner_safety_control SET latched=0,reason=?,"
                "created_by=?,updated_at=? WHERE singleton=1",
                (f"Inspection acknowledged: {reason}"[:6000], created_by, now),
            )
            con.execute("COMMIT")
        return self.runner_safety_control()

    def pause_codex_queue(
        self, source_job_id: str, reason: str, *, created_by: str = "codex-orchestrator"
    ) -> Dict[str, Any]:
        now = utcnow()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            self._insert_codex_queue_pause(
                con,
                source_job_id,
                reason,
                created_by,
                now,
            )
            row = con.execute(
                "SELECT * FROM codex_queue_controls ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            con.execute("COMMIT")
        result = dict(row)
        result["paused"] = result["action"] == "pause"
        return result

    def resume_codex_queue(
        self, reason: str, *, created_by: str
    ) -> Dict[str, Any]:
        reason = reason.strip()
        if not reason:
            raise ValueError("Codex queue resume reason must not be blank")
        now = utcnow()
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            previous = con.execute(
                "SELECT * FROM codex_queue_controls "
                "ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            # A repeated HTTP request after a successful resume must not create
            # another runnable kick.  Resume is an acknowledgement of one
            # specific pause, not a general-purpose enqueue endpoint.
            if previous is None or previous["action"] != "pause":
                kick = None
                if previous is not None and previous["action"] == "resume":
                    kick = con.execute(
                        "SELECT id FROM codex_jobs WHERE dedupe_key=?",
                        (f"queue-resume:{previous['sequence']}:advance",),
                    ).fetchone()
                con.execute("COMMIT")
                result = dict(previous) if previous is not None else {
                    "action": None,
                    "source_job_id": None,
                    "resumes_control_sequence": None,
                }
                result.update(
                    {
                        "paused": False,
                        "resumed": False,
                        "advance_job_id": kick["id"] if kick else None,
                        "superseded_count": 0,
                        "superseded_jobs": [],
                    }
                )
                return result
            source = con.execute(
                "SELECT kind,status FROM codex_jobs WHERE id=?",
                (previous["source_job_id"],),
            ).fetchone()
            if source is not None and source["status"] not in CODEX_JOB_TERMINAL:
                con.execute("ROLLBACK")
                raise ValueError(
                    "Cannot resume until the Codex job that paused the queue has finished"
                )
            unresolved_analysis = con.execute(
                "SELECT id FROM codex_jobs WHERE kind='analysis' AND status IN "
                "('awaiting_evidence','queued','running','retry') "
                "ORDER BY created_at,id LIMIT 1"
            ).fetchone()
            if unresolved_analysis is not None:
                con.execute("ROLLBACK")
                raise ValueError(
                    "Cannot resume while a Codex evidence analysis is unresolved"
                )
            unsealed = con.execute(
                "SELECT id FROM experiments WHERE status IN "
                "('succeeded','failed','cancelled') "
                "AND evidence_sealed_at IS NULL ORDER BY finished_at,id LIMIT 1"
            ).fetchone()
            if unsealed is not None:
                con.execute("ROLLBACK")
                raise ValueError(
                    "Cannot resume while a completed experiment has unsealed evidence"
                )
            timed_out_rows = con.execute(
                "SELECT result_json FROM codex_jobs WHERE kind='analysis' "
                "AND status='dead' AND result_json IS NOT NULL"
            ).fetchall()
            for timed_out in timed_out_rows:
                try:
                    timed_out_result = json.loads(timed_out["result_json"])
                except (TypeError, json.JSONDecodeError):
                    continue
                if (
                    isinstance(timed_out_result, dict)
                    and timed_out_result.get("action") == "evidence_timeout"
                ):
                    con.execute("ROLLBACK")
                    raise ValueError(
                        "Cannot resume until timed-out experiment evidence is "
                        "sealed and analyzed"
                    )
            running = con.execute(
                "SELECT id FROM codex_jobs WHERE kind='advance' "
                "AND status='running' ORDER BY created_at,id LIMIT 1"
            ).fetchone()
            if running is not None:
                con.execute("COMMIT")
                result = dict(previous)
                result.update(
                    {
                        "paused": True,
                        "resumed": False,
                        "advance_job_id": None,
                        "superseded_count": 0,
                        "superseded_jobs": [],
                        "blocked_by_running_job_id": running["id"],
                    }
                )
                return result
            inserted = con.execute(
                "INSERT INTO codex_queue_controls("
                "dedupe_key,action,source_job_id,resumes_control_sequence,"
                "reason,created_by,created_at"
                ") VALUES(?,'resume',?,?,?,?,?)",
                (
                    f"resume:control:{previous['sequence']}",
                    previous["source_job_id"],
                    previous["sequence"],
                    reason[:6000],
                    created_by,
                    now,
                ),
            )
            row = con.execute(
                "SELECT * FROM codex_queue_controls WHERE sequence=?",
                (inserted.lastrowid,),
            ).fetchone()
            superseded = con.execute(
                "SELECT id,status,error,result_json FROM codex_jobs "
                "WHERE kind='advance' AND depends_on_job_id IS NOT NULL "
                "AND status IN ('blocked','queued','retry') "
                "ORDER BY created_at,id"
            ).fetchall()
            for stale in superseded:
                prior_result = (
                    json.loads(stale["result_json"])
                    if stale["result_json"] else None
                )
                receipt = {
                    "action": "superseded",
                    "resume_control_sequence": row["sequence"],
                    "resumed_pause_sequence": previous["sequence"],
                    "source_pause_job_id": previous["source_job_id"],
                    "prior_status": stale["status"],
                    "prior_error": stale["error"],
                    "prior_result": prior_result,
                }
                con.execute(
                    "UPDATE codex_jobs SET status='succeeded',finished_at=?,"
                    "updated_at=?,lease_owner=NULL,lease_token=NULL,"
                    "lease_expires_at=NULL,result_json=?,error=NULL WHERE id=? "
                    "AND kind='advance' AND depends_on_job_id IS NOT NULL "
                    "AND status IN ('blocked','queued','retry')",
                    (now, now, json.dumps(receipt, sort_keys=True), stale["id"]),
                )
            target = con.execute(
                "SELECT id FROM experiments WHERE status=? "
                "AND execution_mode='external_guarded' ORDER BY created_at,id LIMIT 1",
                (WAITING_FOR_OPERATOR,),
            ).fetchone()
            kick_id = uuid.uuid4().hex
            con.execute(
                "INSERT INTO codex_jobs("
                "id,dedupe_key,kind,trigger_kind,experiment_id,status,"
                "max_attempts,not_before,created_at,updated_at"
                ") VALUES(?,?,?,?,?,'queued',?,?,?,?)",
                (
                    kick_id,
                    f"queue-resume:{row['sequence']}:advance",
                    "advance",
                    "operator_resume",
                    target["id"] if target else None,
                    self.codex_max_attempts,
                    now,
                    now,
                    now,
                ),
            )
            superseded_rows = []
            if superseded:
                placeholders = ",".join("?" for _ in superseded)
                superseded_rows = con.execute(
                    f"SELECT * FROM codex_jobs WHERE id IN ({placeholders}) "
                    "ORDER BY created_at,id",
                    tuple(item["id"] for item in superseded),
                ).fetchall()
            con.execute("COMMIT")
        result = dict(row)
        result["paused"] = False
        result["resumed"] = True
        result["advance_job_id"] = kick_id
        result["superseded_count"] = len(superseded_rows)
        result["superseded_jobs"] = [
            self.codex_job_row(item) for item in superseded_rows
        ]
        return result

    def apply_analysis_followups(
        self,
        analysis_job_id: str,
        source_experiment_id: str,
        proposals: list,
        *,
        max_depth: int,
        max_per_root: int,
        max_attempts: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Validate-once receipt layer for bounded, analysis-proposed work."""
        now = utcnow()
        max_attempts = max_attempts or self.codex_max_attempts
        accepted = []
        rejected = []
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            source = con.execute(
                "SELECT id FROM experiments WHERE id=?", (source_experiment_id,)
            ).fetchone()
            job = con.execute(
                "SELECT kind,experiment_id FROM codex_jobs WHERE id=?",
                (analysis_job_id,),
            ).fetchone()
            if not source or not job or job["kind"] != "analysis":
                con.execute("ROLLBACK")
                raise ValueError("Analysis job or source experiment not found")
            if job["experiment_id"] != source_experiment_id:
                con.execute("ROLLBACK")
                raise ValueError("Analysis job does not belong to source experiment")
            lineage = con.execute(
                "SELECT root_experiment_id,lineage_depth FROM codex_followup_proposals "
                "WHERE child_experiment_id=? AND disposition='accepted' "
                "ORDER BY id DESC LIMIT 1",
                (source_experiment_id,),
            ).fetchone()
            root_id = (
                lineage["root_experiment_id"] if lineage else source_experiment_id
            )
            depth = (lineage["lineage_depth"] if lineage else 0) + 1
            accepted_count = con.execute(
                "SELECT COUNT(*) AS count FROM codex_followup_proposals "
                "WHERE root_experiment_id=? AND disposition='accepted'",
                (root_id,),
            ).fetchone()["count"]
            for index, proposal in enumerate(proposals):
                proposal_sha256 = self._proposal_sha256(proposal)
                spec = proposal["spec"]
                canonical = json.dumps(
                    spec,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                )
                spec_sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                existing = con.execute(
                    "SELECT proposal_sha256,disposition,disposition_reason,"
                    "child_experiment_id "
                    "FROM codex_followup_proposals "
                    "WHERE analysis_job_id=? AND proposal_index=?",
                    (analysis_job_id, index),
                ).fetchone()
                if existing:
                    if existing["proposal_sha256"] != proposal_sha256:
                        con.execute("ROLLBACK")
                        raise ValueError(
                            "Analysis follow-up proposal changed for an existing "
                            f"receipt index: {index}"
                        )
                    receipt = dict(existing)
                    receipt.pop("proposal_sha256", None)
                    receipt["proposal_index"] = index
                    (accepted if existing["disposition"] == "accepted" else rejected).append(receipt)
                    continue
                reason = proposal.get("rejection_reason", "")
                if not reason and depth > max_depth:
                    reason = f"adaptive lineage depth {depth} exceeds limit {max_depth}"
                if not reason and accepted_count >= max_per_root:
                    reason = f"adaptive root already has {max_per_root} accepted follow-ups"
                if not reason:
                    duplicate = con.execute(
                        "SELECT child_experiment_id FROM codex_followup_proposals "
                        "WHERE root_experiment_id=? AND spec_sha256=? "
                        "AND disposition='accepted'",
                        (root_id, spec_sha256),
                    ).fetchone()
                    if duplicate:
                        reason = (
                            "exact experiment specification already exists in this "
                            f"adaptive lineage as {duplicate['child_experiment_id']}"
                        )
                child_id = None
                disposition = "rejected"
                if not reason:
                    child_id = uuid.uuid4().hex
                    parameters = dict(spec.get("parameters", {}))
                    parameters["_automation"] = {
                        "analysis_job_id": analysis_job_id,
                        "parent_experiment_id": source_experiment_id,
                        "root_experiment_id": root_id,
                        "lineage_depth": depth,
                        "recommendation_key": proposal["recommendation_key"],
                        "rationale": proposal.get("rationale", ""),
                    }
                    execution_mode = spec.get("execution_mode", "external_guarded")
                    status = (
                        WAITING_FOR_OPERATOR
                        if execution_mode == "external_guarded" else "queued"
                    )
                    con.execute(
                        "INSERT INTO experiments("
                        "id,name,description,duration_seconds,parameters_json,status,"
                        "submitted_by,created_at,execution_mode"
                        ") VALUES(?,?,?,?,?,?,?,?,?)",
                        (
                            child_id,
                            spec["name"],
                            spec.get("description", ""),
                            spec["duration_seconds"],
                            json.dumps(parameters, sort_keys=True),
                            status,
                            "codex-analysis",
                            now,
                            execution_mode,
                        ),
                    )
                    con.execute(
                        "INSERT INTO events(experiment_id,timestamp,kind,message) "
                        "VALUES(?,?,?,?)",
                        (
                            child_id,
                            now,
                            "submitted",
                            f"Queued from Codex analysis job {analysis_job_id}",
                        ),
                    )
                    disposition = "accepted"
                    accepted_count += 1
                con.execute(
                    "INSERT INTO codex_followup_proposals("
                    "analysis_job_id,source_experiment_id,root_experiment_id,"
                    "proposal_index,recommendation_key,proposal_sha256,"
                    "spec_sha256,spec_json,"
                    "rationale,lineage_depth,disposition,disposition_reason,"
                    "child_experiment_id,created_at"
                    ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        analysis_job_id,
                        source_experiment_id,
                        root_id,
                        index,
                        proposal["recommendation_key"],
                        proposal_sha256,
                        spec_sha256,
                        canonical,
                        proposal.get("rationale", ""),
                        depth,
                        disposition,
                        reason,
                        child_id,
                        now,
                    ),
                )
                receipt = {
                    "proposal_index": index,
                    "disposition": disposition,
                    "disposition_reason": reason,
                    "child_experiment_id": child_id,
                }
                (accepted if disposition == "accepted" else rejected).append(receipt)
            con.execute("COMMIT")
        return {"accepted": accepted, "rejected": rejected, "root_experiment_id": root_id}

    def reconsider_rejected_followup(
        self,
        analysis_job_id: str,
        proposal_index: int,
        *,
        expected_recommendation_key: str,
        expected_proposal_sha256: str,
        expected_spec_sha256: str,
        expected_original_reason: str,
        adaptive_admission: Dict[str, Any],
        max_depth: int,
        max_per_root: int,
        reconsidered_by: str,
    ) -> Dict[str, Any]:
        """Promote one exact historical policy rejection without replaying Codex.

        This is deliberately narrower than ``apply_analysis_followups``.  It
        exists for a reviewed policy migration where the model output and its
        scientific specification are unchanged, but a former hard rejection
        is now a readiness-only blocker.  The original analysis result remains
        immutable; an append-only audit row records the reconsideration.
        """

        def valid_sha256(value: Any) -> bool:
            return (
                isinstance(value, str)
                and len(value) == 64
                and value == value.lower()
                and all(character in "0123456789abcdef" for character in value)
            )

        if not analysis_job_id or not isinstance(analysis_job_id, str):
            raise ValueError("Analysis job id is required")
        if (
            not isinstance(proposal_index, int)
            or isinstance(proposal_index, bool)
            or proposal_index < 0
        ):
            raise ValueError("Proposal index must be a non-negative integer")
        if not expected_recommendation_key or not isinstance(
            expected_recommendation_key, str
        ):
            raise ValueError("Expected recommendation key is required")
        if not valid_sha256(expected_proposal_sha256):
            raise ValueError("Expected proposal SHA-256 is invalid")
        if not valid_sha256(expected_spec_sha256):
            raise ValueError("Expected specification SHA-256 is invalid")
        if not isinstance(expected_original_reason, str) or not expected_original_reason:
            raise ValueError("Expected original rejection reason is required")
        if (
            not isinstance(max_depth, int)
            or isinstance(max_depth, bool)
            or max_depth < 0
            or not isinstance(max_per_root, int)
            or isinstance(max_per_root, bool)
            or max_per_root < 0
        ):
            raise ValueError("Adaptive limits must be non-negative integers")
        if (
            not isinstance(reconsidered_by, str)
            or not reconsidered_by.strip()
            or len(reconsidered_by) > 160
        ):
            raise ValueError("Reconsideration actor is required")
        if not isinstance(adaptive_admission, dict):
            raise ValueError("Adaptive admission must be an object")
        if set(adaptive_admission) != {
            "policy",
            "analysis_generated",
            "ready",
            "reason",
        }:
            raise ValueError("Adaptive admission has unexpected fields")
        if adaptive_admission.get("analysis_generated") is not True:
            raise ValueError("Adaptive admission must retain analysis provenance")
        if adaptive_admission.get("ready") is not False:
            raise ValueError("A reconsidered rejection must remain not ready")
        if (
            not isinstance(adaptive_admission.get("policy"), str)
            or not adaptive_admission["policy"].strip()
            or len(adaptive_admission["policy"]) > 160
        ):
            raise ValueError("Adaptive admission policy is invalid")
        if (
            not isinstance(adaptive_admission.get("reason"), str)
            or not adaptive_admission["reason"].strip()
            or len(adaptive_admission["reason"]) > 4000
        ):
            raise ValueError("Adaptive admission must include a readiness reason")

        def canonical(value: Any) -> str:
            return json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )

        # Round-trip the caller-owned object so later mutations cannot affect
        # the child or the audit receipt.
        admission_json = canonical(adaptive_admission)
        admission = json.loads(admission_json)
        now = utcnow()

        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            receipt = con.execute(
                "SELECT p.*,j.kind AS job_kind,j.status AS job_status,"
                "j.experiment_id AS job_experiment_id,j.result_json AS job_result_json "
                "FROM codex_followup_proposals p "
                "JOIN codex_jobs j ON j.id=p.analysis_job_id "
                "WHERE p.analysis_job_id=? AND p.proposal_index=?",
                (analysis_job_id, proposal_index),
            ).fetchone()
            if receipt is None:
                raise ValueError("Rejected follow-up receipt was not found")
            if receipt["recommendation_key"] != expected_recommendation_key:
                raise ValueError("Recommendation key does not match the stored receipt")
            if receipt["proposal_sha256"] != expected_proposal_sha256:
                raise ValueError("Proposal SHA-256 does not match the stored receipt")
            if receipt["spec_sha256"] != expected_spec_sha256:
                raise ValueError("Specification SHA-256 does not match the stored receipt")
            if (
                receipt["job_kind"] != "analysis"
                or receipt["job_status"] != "succeeded"
                or receipt["job_experiment_id"] != receipt["source_experiment_id"]
            ):
                raise ValueError("Receipt is not owned by a succeeded source analysis")

            try:
                stored_spec = json.loads(receipt["spec_json"])
                analysis_result = json.loads(receipt["job_result_json"])
            except (TypeError, json.JSONDecodeError) as exc:
                raise ValueError("Stored follow-up provenance is invalid JSON") from exc
            if not isinstance(stored_spec, dict) or not isinstance(analysis_result, dict):
                raise ValueError("Stored follow-up provenance is malformed")
            canonical_spec = canonical(stored_spec)
            if hashlib.sha256(canonical_spec.encode("utf-8")).hexdigest() != expected_spec_sha256:
                raise ValueError("Stored specification does not match its expected digest")
            if analysis_result.get("safety_disposition") != "clear":
                raise ValueError("Source analysis did not clear physical safety")

            recommendations = analysis_result.get("recommended_experiments")
            if (
                not isinstance(recommendations, list)
                or proposal_index >= len(recommendations)
                or not isinstance(recommendations[proposal_index], dict)
            ):
                raise ValueError("Analysis result does not contain the stored proposal")
            result_proposal = recommendations[proposal_index]
            if self._proposal_sha256(result_proposal) != expected_proposal_sha256:
                raise ValueError("Analysis result proposal does not match its receipt")
            if result_proposal.get("recommendation_key") != expected_recommendation_key:
                raise ValueError("Analysis result recommendation key does not match")
            if canonical(result_proposal.get("spec")) != canonical_spec:
                raise ValueError("Analysis result specification does not match its receipt")

            result_receipts = analysis_result.get("followup_receipts")
            rejected_result_receipts = (
                result_receipts.get("rejected")
                if isinstance(result_receipts, dict)
                else None
            )
            matching_result_receipts = [
                item
                for item in rejected_result_receipts or []
                if isinstance(item, dict)
                and item.get("proposal_index") == proposal_index
            ]
            if len(matching_result_receipts) != 1:
                raise ValueError("Analysis result lacks the original rejected receipt")
            result_receipt = matching_result_receipts[0]
            if (
                result_receipt.get("disposition") != "rejected"
                or result_receipt.get("disposition_reason")
                != expected_original_reason
                or result_receipt.get("child_experiment_id") is not None
            ):
                raise ValueError("Analysis result does not preserve the original rejection")
            if result_receipts.get("root_experiment_id") != receipt["root_experiment_id"]:
                raise ValueError("Analysis result adaptive root does not match its receipt")

            source = con.execute(
                "SELECT id,status FROM experiments WHERE id=?",
                (receipt["source_experiment_id"],),
            ).fetchone()
            if source is None or source["status"] not in TERMINAL:
                raise ValueError("Source experiment is missing or is not terminal")
            if stored_spec.get("execution_mode") != "external_guarded":
                raise ValueError("Only external-guarded proposals may be reconsidered")
            parameters = stored_spec.get("parameters")
            if not isinstance(parameters, dict):
                raise ValueError("Stored follow-up parameters are malformed")
            if "_automation" in parameters or "_adaptive_admission" in parameters:
                raise ValueError("Stored proposal already contains reserved automation metadata")

            audit = con.execute(
                "SELECT * FROM codex_followup_reconsiderations WHERE proposal_id=?",
                (receipt["id"],),
            ).fetchone()
            if receipt["disposition"] == "accepted":
                if audit is None or receipt["child_experiment_id"] is None:
                    raise ValueError("Accepted receipt lacks a reconsideration audit")
                if (
                    audit["analysis_job_id"] != analysis_job_id
                    or audit["proposal_index"] != proposal_index
                    or audit["original_disposition"] != "rejected"
                    or audit["original_disposition_reason"]
                    != expected_original_reason
                    or audit["expected_proposal_sha256"]
                    != expected_proposal_sha256
                    or audit["expected_spec_sha256"] != expected_spec_sha256
                    or audit["admission_json"] != admission_json
                    or audit["reconsidered_by"] != reconsidered_by.strip()
                    or audit["child_experiment_id"]
                    != receipt["child_experiment_id"]
                ):
                    raise ValueError("Reconsideration replay does not match its audit")
                child = con.execute(
                    "SELECT * FROM experiments WHERE id=?",
                    (receipt["child_experiment_id"],),
                ).fetchone()
                if child is None:
                    raise ValueError("Reconsidered child experiment is missing")
                child_payload = {
                    "id": child["id"],
                    "name": child["name"],
                    "description": child["description"],
                    "duration_seconds": child["duration_seconds"],
                    "parameters": json.loads(child["parameters_json"]),
                    "submitted_by": child["submitted_by"],
                    "created_at": child["created_at"],
                    "execution_mode": child["execution_mode"],
                }
                child_record_sha256 = hashlib.sha256(
                    canonical(child_payload).encode("utf-8")
                ).hexdigest()
                if child_record_sha256 != audit["child_record_sha256"]:
                    raise ValueError("Reconsidered child no longer matches its audit")
                con.execute("COMMIT")
                return {
                    "proposal_index": proposal_index,
                    "disposition": "accepted",
                    "disposition_reason": "",
                    "child_experiment_id": child["id"],
                    "root_experiment_id": receipt["root_experiment_id"],
                    "lineage_depth": receipt["lineage_depth"],
                    "reconsidered": True,
                    "idempotent": True,
                }

            if receipt["disposition"] != "rejected":
                raise ValueError("Only a rejected follow-up may be reconsidered")
            if audit is not None:
                raise ValueError("Rejected receipt unexpectedly has a reconsideration audit")
            if receipt["child_experiment_id"] is not None:
                raise ValueError("Rejected receipt unexpectedly links a child experiment")
            if receipt["disposition_reason"] != expected_original_reason:
                raise ValueError("Original rejection reason does not match the receipt")

            parent_rows = con.execute(
                "SELECT root_experiment_id,lineage_depth "
                "FROM codex_followup_proposals "
                "WHERE child_experiment_id=? AND disposition='accepted'",
                (receipt["source_experiment_id"],),
            ).fetchall()
            if len(parent_rows) > 1:
                raise ValueError("Source experiment has ambiguous adaptive lineage")
            root_id = (
                parent_rows[0]["root_experiment_id"]
                if parent_rows
                else receipt["source_experiment_id"]
            )
            depth = (parent_rows[0]["lineage_depth"] if parent_rows else 0) + 1
            if (
                root_id != receipt["root_experiment_id"]
                or depth != receipt["lineage_depth"]
            ):
                raise ValueError("Stored adaptive lineage no longer matches the source")
            if depth > max_depth:
                raise ValueError(
                    f"Adaptive lineage depth {depth} exceeds limit {max_depth}"
                )
            accepted_count = con.execute(
                "SELECT COUNT(*) AS count FROM codex_followup_proposals "
                "WHERE root_experiment_id=? AND disposition='accepted'",
                (root_id,),
            ).fetchone()["count"]
            if accepted_count >= max_per_root:
                raise ValueError(
                    f"Adaptive root already has {max_per_root} accepted follow-ups"
                )
            duplicate = con.execute(
                "SELECT child_experiment_id FROM codex_followup_proposals "
                "WHERE root_experiment_id=? AND spec_sha256=? "
                "AND disposition='accepted'",
                (root_id, expected_spec_sha256),
            ).fetchone()
            if duplicate is not None:
                raise ValueError(
                    "Exact experiment specification already exists in this "
                    f"adaptive lineage as {duplicate['child_experiment_id']}"
                )

            child_id = uuid.uuid4().hex
            child_parameters = dict(parameters)
            child_parameters["_adaptive_admission"] = admission
            child_parameters["_automation"] = {
                "analysis_job_id": analysis_job_id,
                "parent_experiment_id": receipt["source_experiment_id"],
                "root_experiment_id": root_id,
                "lineage_depth": depth,
                "recommendation_key": receipt["recommendation_key"],
                "rationale": receipt["rationale"],
                "reconsidered_from_proposal_id": receipt["id"],
                "reconsidered_by": reconsidered_by.strip(),
            }
            child_payload = {
                "id": child_id,
                "name": stored_spec.get("name"),
                "description": stored_spec.get("description", ""),
                "duration_seconds": stored_spec.get("duration_seconds"),
                "parameters": child_parameters,
                "submitted_by": "codex-analysis",
                "created_at": now,
                "execution_mode": "external_guarded",
            }
            if (
                not isinstance(child_payload["name"], str)
                or not child_payload["name"].strip()
                or not isinstance(child_payload["description"], str)
                or not isinstance(child_payload["duration_seconds"], (int, float))
                or isinstance(child_payload["duration_seconds"], bool)
                or child_payload["duration_seconds"] <= 0
            ):
                raise ValueError("Stored follow-up experiment specification is malformed")
            child_record_sha256 = hashlib.sha256(
                canonical(child_payload).encode("utf-8")
            ).hexdigest()
            con.execute(
                "INSERT INTO experiments("
                "id,name,description,duration_seconds,parameters_json,status,"
                "submitted_by,created_at,execution_mode"
                ") VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    child_id,
                    child_payload["name"],
                    child_payload["description"],
                    child_payload["duration_seconds"],
                    canonical(child_parameters),
                    WAITING_FOR_OPERATOR,
                    child_payload["submitted_by"],
                    now,
                    child_payload["execution_mode"],
                ),
            )
            con.execute(
                "INSERT INTO events(experiment_id,timestamp,kind,message) "
                "VALUES(?,?,?,?)",
                (
                    child_id,
                    now,
                    "submitted",
                    "Saved after a reviewed Codex follow-up policy reconsideration "
                    f"for analysis job {analysis_job_id}",
                ),
            )
            promoted = con.execute(
                "UPDATE codex_followup_proposals SET disposition='accepted',"
                "disposition_reason='',child_experiment_id=? "
                "WHERE id=? AND disposition='rejected' "
                "AND disposition_reason=? AND child_experiment_id IS NULL "
                "AND proposal_sha256=? AND spec_sha256=?",
                (
                    child_id,
                    receipt["id"],
                    expected_original_reason,
                    expected_proposal_sha256,
                    expected_spec_sha256,
                ),
            )
            if promoted.rowcount != 1:
                raise ValueError("Rejected follow-up changed during reconsideration")
            con.execute(
                "INSERT INTO codex_followup_reconsiderations("
                "proposal_id,analysis_job_id,proposal_index,original_disposition,"
                "original_disposition_reason,expected_proposal_sha256,"
                "expected_spec_sha256,admission_json,child_experiment_id,"
                "child_record_sha256,reconsidered_by,created_at"
                ") VALUES(?,?,?,'rejected',?,?,?,?,?,?,?,?)",
                (
                    receipt["id"],
                    analysis_job_id,
                    proposal_index,
                    expected_original_reason,
                    expected_proposal_sha256,
                    expected_spec_sha256,
                    admission_json,
                    child_id,
                    child_record_sha256,
                    reconsidered_by.strip(),
                    now,
                ),
            )
            con.execute("COMMIT")
        return {
            "proposal_index": proposal_index,
            "disposition": "accepted",
            "disposition_reason": "",
            "child_experiment_id": child_id,
            "root_experiment_id": root_id,
            "lineage_depth": depth,
            "reconsidered": True,
            "idempotent": False,
        }

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
                "External guarded experiment is waiting for the serialized guarded runner"
                if execution_mode == "external_guarded"
                else "Experiment added to queue"
            )
            con.execute(
                "INSERT INTO events(experiment_id,timestamp,kind,message) "
                "VALUES(?,?,?,?)",
                (experiment_id, now, "submitted", message),
            )
            if execution_mode == "external_guarded":
                con.execute(
                    "INSERT OR IGNORE INTO codex_jobs("
                    "id,dedupe_key,kind,trigger_kind,experiment_id,status,"
                    "max_attempts,not_before,created_at,updated_at"
                    ") VALUES(?,?,?,?,?,'queued',?,?,?,?)",
                    (
                        uuid.uuid4().hex,
                        f"submission:{experiment_id}:advance",
                        "advance",
                        "experiment_submission",
                        experiment_id,
                        self.codex_max_attempts,
                        now,
                        now,
                        now,
                    ),
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
                            self._enqueue_terminal_codex_jobs(con, result_id, now)
                            if existing["evidence_manifest_sha256"]:
                                con.execute(
                                    "UPDATE codex_jobs SET status='queued',"
                                    "evidence_manifest_sha256=?,not_before=?,updated_at=? "
                                    "WHERE experiment_id=? AND status='awaiting_evidence'",
                                    (
                                        existing["evidence_manifest_sha256"],
                                        now,
                                        now,
                                        result_id,
                                    ),
                                )
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
                    self._enqueue_terminal_codex_jobs(con, result_id, now)
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
            self._enqueue_terminal_codex_jobs(con, result_id, now)
            con.execute("COMMIT")
        return self.get(result_id)

    def get(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as con:
            row = con.execute("SELECT * FROM experiments WHERE id=?", (experiment_id,)).fetchone()
        return self.row(row) if row else None

    @staticmethod
    def _learnings_row(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "text": row["text"],
            "sources": json.loads(row["sources_json"]),
            "created_at": row["created_at"],
            "created_by": row["created_by"],
            "revision": row["sequence"],
        }

    def learnings(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as con:
            row = con.execute(
                "SELECT * FROM experiment_learnings WHERE experiment_id=? "
                "ORDER BY sequence DESC LIMIT 1", (experiment_id,),
            ).fetchone()
        return self._learnings_row(row) if row else None

    def record_learnings(
        self, experiment_id: str, text: str, sources: Any, created_by: str
    ) -> Dict[str, Any]:
        """Append a completed experiment's interpretation without changing evidence."""
        text = text.strip()
        if not text:
            raise ValueError("Learnings text must not be blank")
        sources_json = json.dumps(sources, sort_keys=True)
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            experiment = con.execute(
                "SELECT status FROM experiments WHERE id=?", (experiment_id,)
            ).fetchone()
            if not experiment:
                raise ValueError("Experiment not found")
            if experiment["status"] not in TERMINAL:
                raise ValueError("Learnings may only be recorded for a completed experiment")
            latest = con.execute(
                "SELECT * FROM experiment_learnings WHERE experiment_id=? "
                "ORDER BY sequence DESC LIMIT 1", (experiment_id,),
            ).fetchone()
            if latest and latest["text"] == text and latest["sources_json"] == sources_json:
                con.execute("COMMIT")
                return self._learnings_row(latest)
            now = utcnow()
            inserted = con.execute(
                "INSERT INTO experiment_learnings("
                "experiment_id,text,sources_json,created_at,created_by"
                ") VALUES(?,?,?,?,?)",
                (experiment_id, text, sources_json, now, created_by),
            )
            revision = inserted.lastrowid
            con.execute(
                "INSERT INTO events(experiment_id,timestamp,kind,message) "
                "VALUES(?,?,?,?)",
                (experiment_id, now, "learnings_updated",
                 f"{created_by} recorded learnings revision {revision}"),
            )
            recorded = con.execute(
                "SELECT * FROM experiment_learnings WHERE sequence=?", (revision,)
            ).fetchone()
            con.execute("COMMIT")
        return self._learnings_row(recorded)

    def list(self, limit: int = 100) -> Iterable[Dict[str, Any]]:
        with self.connect() as con:
            rows = con.execute("SELECT * FROM experiments ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self.row(row) for row in rows]

    def running_experiments(self) -> Iterable[Dict[str, Any]]:
        with self.connect() as con:
            rows = con.execute(
                "SELECT * FROM experiments WHERE status='running' "
                "ORDER BY started_at,id"
            ).fetchall()
        return [self.row(row) for row in rows]

    def claim_next(
        self, *, require_codex_clear: bool = False
    ) -> Optional[Dict[str, Any]]:
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            if require_codex_clear:
                gate = con.execute(
                    "SELECT EXISTS(SELECT 1 FROM codex_jobs WHERE kind='analysis' "
                    "AND status IN ('awaiting_evidence','queued','running','retry')) "
                    "AS analysis_pending, COALESCE((SELECT action FROM "
                    "codex_queue_controls ORDER BY sequence DESC LIMIT 1),'') "
                    "AS latest_control"
                ).fetchone()
                if gate["analysis_pending"] or gate["latest_control"] == "pause":
                    con.execute("COMMIT")
                    return None
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
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT status FROM experiments WHERE id=?", (experiment_id,)
            ).fetchone()
            if not row:
                con.execute("ROLLBACK")
                raise ValueError("Experiment not found")
            if row["status"] in TERMINAL:
                if row["status"] != status:
                    con.execute("ROLLBACK")
                    raise ValueError("Experiment is already terminal with a different status")
                self._enqueue_terminal_codex_jobs(con, experiment_id, now)
                con.execute("COMMIT")
                return
            updated = con.execute(
                "UPDATE experiments SET status=?,finished_at=?,error=? "
                "WHERE id=? AND status NOT IN ('succeeded','failed','cancelled')",
                (status, now, error, experiment_id),
            )
            if updated.rowcount != 1:
                con.execute("ROLLBACK")
                raise ValueError("Experiment state changed during completion")
            con.execute(
                "INSERT INTO events(experiment_id,timestamp,kind,message) VALUES(?,?,?,?)",
                (experiment_id, now, status, error or ("Experiment " + status)),
            )
            self._enqueue_terminal_codex_jobs(con, experiment_id, now)
            con.execute("COMMIT")

    def cancel(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        # Serialize cancellation against external completion and sealing. If
        # cancellation wins, it also revokes the scoped automation lane so the
        # supervisor can terminate the action-capable child immediately.
        with self.evidence_lock(experiment_id):
            with self.connect() as con:
                con.execute("BEGIN IMMEDIATE")
                row = con.execute(
                    "SELECT status FROM experiments WHERE id=?", (experiment_id,)
                ).fetchone()
                if not row:
                    con.execute("ROLLBACK")
                    return None
                now = utcnow()
                if row["status"] in {"queued", WAITING_FOR_OPERATOR}:
                    updated = con.execute(
                        "UPDATE experiments SET status='cancelled',cancel_requested=1,"
                        "finished_at=? WHERE id=? AND status IN ('queued',?)",
                        (now, experiment_id, WAITING_FOR_OPERATOR),
                    )
                    if updated.rowcount == 1:
                        con.execute(
                            "DELETE FROM codex_hardware_lane WHERE experiment_id=?",
                            (experiment_id,),
                        )
                        self._enqueue_terminal_codex_jobs(con, experiment_id, now)
                elif row["status"] == "running":
                    con.execute(
                        "UPDATE experiments SET cancel_requested=1 WHERE id=?",
                        (experiment_id,),
                    )
                con.execute(
                    "INSERT INTO events(experiment_id,timestamp,kind,message) "
                    "VALUES(?,?,?,?)",
                    (
                        experiment_id,
                        now,
                        "cancel_requested",
                        "Cancellation requested",
                    ),
                )
                con.execute("COMMIT")
        return self.get(experiment_id)

    def events(self, experiment_id: str):
        with self.connect() as con:
            return [dict(row) for row in con.execute(
                "SELECT timestamp,kind,message FROM events WHERE experiment_id=? ORDER BY id", (experiment_id,)).fetchall()]
