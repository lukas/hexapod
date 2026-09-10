"""Three tables and a spend ledger. Plain sqlite3, one writer."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS plans (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  title TEXT NOT NULL,
  why TEXT NOT NULL,
  protocol TEXT,
  kind TEXT NOT NULL,            -- existing | needs_code
  build_spec TEXT,
  force INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL,          -- queued | building | running | done | failed | skipped | cancelled
  status_note TEXT,
  source TEXT NOT NULL,          -- planner | operator
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  plan_id TEXT NOT NULL REFERENCES plans(id),
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,          -- running | ok | failed | timeout | unreachable
  exit_code INTEGER,
  run_dir TEXT,
  summary_json TEXT,
  log_tail TEXT
);
CREATE TABLE IF NOT EXISTS learnings (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  run_id TEXT REFERENCES runs(id),
  text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS spend (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  kind TEXT NOT NULL,            -- planner | builder
  usd REAL NOT NULL,
  note TEXT
);
CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  kind TEXT NOT NULL,            -- stop | note | builder
  text TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


class Store:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(self.path), check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)

    # -- plans -------------------------------------------------------------
    def add_plan(self, *, title: str, why: str, kind: str, protocol: Optional[str],
                 build_spec: Optional[str], force: bool = False,
                 source: str = "planner") -> str:
        pid = new_id()
        now = now_iso()
        self.con.execute(
            "INSERT INTO plans (id, created_at, title, why, protocol, kind, build_spec,"
            " force, status, source, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (pid, now, title, why, protocol, kind, build_spec, int(force),
             "queued" if kind == "existing" else "building", source, now),
        )
        self.con.commit()
        return pid

    def set_plan_status(self, plan_id: str, status: str, note: str = "") -> None:
        self.con.execute(
            "UPDATE plans SET status=?, status_note=?, updated_at=? WHERE id=?",
            (status, note or None, now_iso(), plan_id),
        )
        self.con.commit()

    def mark_built(self, plan_id: str, protocol: str) -> None:
        self.con.execute(
            "UPDATE plans SET kind='existing', protocol=?, status='queued',"
            " status_note='built', updated_at=? WHERE id=?",
            (protocol, now_iso(), plan_id),
        )
        self.con.commit()

    def next_runnable(self) -> Optional[Dict[str, Any]]:
        row = self.con.execute(
            "SELECT * FROM plans WHERE status='queued' AND kind='existing'"
            " ORDER BY created_at, rowid LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def plans(self, statuses: Optional[List[str]] = None, limit: int = 50) -> List[Dict[str, Any]]:
        if statuses:
            marks = ",".join("?" * len(statuses))
            rows = self.con.execute(
                f"SELECT * FROM plans WHERE status IN ({marks}) ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (*statuses, limit),
            )
        else:
            rows = self.con.execute("SELECT * FROM plans ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]

    def plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        row = self.con.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
        return dict(row) if row else None

    def building_plans(self) -> List[Dict[str, Any]]:
        return self.plans(["building"])

    def queued_count(self) -> int:
        return self.con.execute(
            "SELECT COUNT(*) FROM plans WHERE status IN ('queued','building')"
        ).fetchone()[0]

    # -- runs --------------------------------------------------------------
    def start_run(self, plan_id: str) -> str:
        rid = new_id()
        self.con.execute(
            "INSERT INTO runs (id, plan_id, started_at, status) VALUES (?,?,?,?)",
            (rid, plan_id, now_iso(), "running"),
        )
        self.set_plan_status(plan_id, "running")
        return rid

    def finish_run(self, run_id: str, *, status: str, exit_code: Optional[int],
                   run_dir: Optional[str], summary: Optional[dict], log_tail: str) -> None:
        self.con.execute(
            "UPDATE runs SET finished_at=?, status=?, exit_code=?, run_dir=?,"
            " summary_json=?, log_tail=? WHERE id=?",
            (now_iso(), status, exit_code, run_dir,
             json.dumps(summary) if summary is not None else None, log_tail[-4000:], run_id),
        )
        self.con.commit()

    def run(self, run_id: str) -> Optional[Dict[str, Any]]:
        row = self.con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        return dict(row) if row else None

    def runs(self, limit: int = 30) -> List[Dict[str, Any]]:
        rows = self.con.execute(
            "SELECT runs.*, plans.title, plans.why, plans.protocol FROM runs"
            " JOIN plans ON plans.id = runs.plan_id"
            " ORDER BY runs.started_at DESC, runs.rowid DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]

    def consecutive_failed_runs(self) -> int:
        n = 0
        for row in self.con.execute(
            "SELECT status FROM runs WHERE status != 'running' ORDER BY started_at DESC, rowid DESC LIMIT 20"
        ):
            if row["status"] in ("ok",):
                break
            if row["status"] == "unreachable":
                continue
            n += 1
        return n

    # -- learnings / spend / events ---------------------------------------
    def add_learning(self, text: str, run_id: Optional[str] = None) -> str:
        lid = new_id()
        self.con.execute(
            "INSERT INTO learnings (id, created_at, run_id, text) VALUES (?,?,?,?)",
            (lid, now_iso(), run_id, text),
        )
        self.con.commit()
        return lid

    def learnings(self, limit: int = 8) -> List[Dict[str, Any]]:
        rows = self.con.execute(
            "SELECT * FROM learnings ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]

    def learning_for_run(self, run_id: str) -> Optional[str]:
        row = self.con.execute(
            "SELECT text FROM learnings WHERE run_id=? ORDER BY created_at DESC LIMIT 1",
            (run_id,)).fetchone()
        return row["text"] if row else None

    def add_spend(self, kind: str, usd: float, note: str = "") -> None:
        self.con.execute(
            "INSERT INTO spend (id, created_at, kind, usd, note) VALUES (?,?,?,?,?)",
            (new_id(), now_iso(), kind, float(usd), note or None),
        )
        self.con.commit()

    def spend_last_24h(self) -> float:
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec="seconds")
        row = self.con.execute(
            "SELECT COALESCE(SUM(usd),0) FROM spend WHERE created_at >= ?", (since,)).fetchone()
        return float(row[0])

    def add_event(self, kind: str, text: str) -> None:
        self.con.execute(
            "INSERT INTO events (id, created_at, kind, text) VALUES (?,?,?,?)",
            (new_id(), now_iso(), kind, text),
        )
        self.con.commit()

    def events(self, limit: int = 20) -> List[Dict[str, Any]]:
        rows = self.con.execute("SELECT * FROM events ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]

    def last_stop(self) -> Optional[Dict[str, Any]]:
        row = self.con.execute(
            "SELECT * FROM events WHERE kind='stop' ORDER BY created_at DESC, rowid DESC LIMIT 1").fetchone()
        return dict(row) if row else None
