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
            """)

    @staticmethod
    def row(row: sqlite3.Row) -> Dict[str, Any]:
        item = dict(row)
        item["parameters"] = json.loads(item.pop("parameters_json"))
        item["cancel_requested"] = bool(item["cancel_requested"])
        return item

    def create(self, spec: Dict[str, Any], submitted_by: str) -> Dict[str, Any]:
        experiment_id = uuid.uuid4().hex
        now = utcnow()
        with self.connect() as con:
            con.execute(
                "INSERT INTO experiments(id,name,description,duration_seconds,parameters_json,status,submitted_by,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (experiment_id, spec["name"], spec.get("description", ""), spec["duration_seconds"],
                 json.dumps(spec.get("parameters", {}), sort_keys=True), "queued", submitted_by, now),
            )
            con.execute("INSERT INTO events(experiment_id,timestamp,kind,message) VALUES(?,?,?,?)",
                        (experiment_id, now, "submitted", "Experiment added to queue"))
        return self.get(experiment_id)

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
