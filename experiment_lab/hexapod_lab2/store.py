"""Three tables and a spend ledger. Plain sqlite3, one writer."""
from __future__ import annotations

import json
import shutil
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
  updated_at TEXT NOT NULL,
  robot TEXT NOT NULL DEFAULT 'hexapod1'
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
  log_tail TEXT,
  robot TEXT NOT NULL DEFAULT 'hexapod1'
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
        self._migrate()

    def _migrate(self) -> None:
        # Databases created before the second robot lack the column.
        for table in ("plans", "runs"):
            cols = {r["name"] for r in self.con.execute(f"PRAGMA table_info({table})")}
            if "robot" not in cols:
                self.con.execute(
                    f"ALTER TABLE {table} ADD COLUMN robot TEXT NOT NULL DEFAULT 'hexapod1'")
        cols = {r["name"] for r in self.con.execute("PRAGMA table_info(plans)")}
        if "needs_robot" not in cols:
            self.con.execute("ALTER TABLE plans ADD COLUMN needs_robot INTEGER NOT NULL DEFAULT 0")
        self.con.commit()

    # -- plans -------------------------------------------------------------
    def add_plan(self, *, title: str, why: str, kind: str, protocol: Optional[str],
                 build_spec: Optional[str], force: bool = False,
                 source: str = "planner", robot: str = "hexapod1",
                 status: Optional[str] = None, needs_robot: bool = False) -> str:
        pid = new_id()
        now = now_iso()
        self.con.execute(
            "INSERT INTO plans (id, created_at, title, why, protocol, kind, build_spec,"
            " force, status, source, updated_at, robot, needs_robot) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (pid, now, title, why, protocol, kind, build_spec, int(force),
             status or ("queued" if kind == "existing" else "building"), source, now, robot, int(needs_robot)),
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

    def next_runnable(self, robot: str = "hexapod1") -> Optional[Dict[str, Any]]:
        row = self.con.execute(
            "SELECT * FROM plans WHERE status='queued' AND kind='existing' AND robot=?"
            " ORDER BY created_at, rowid LIMIT 1", (robot,)
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

    def release_stuck_builds(self) -> int:
        """A restart kills the builder thread with the loop; its plan must not
        stay marked as running forever."""
        cur = self.con.execute(
            "UPDATE plans SET status_note='builder interrupted by restart', updated_at=?"
            " WHERE status='building' AND status_note='builder running'", (now_iso(),))
        self.con.commit()
        return cur.rowcount

    def building_plans(self) -> List[Dict[str, Any]]:
        return self.plans(["building"])

    def queued_count(self) -> int:
        return self.con.execute(
            "SELECT COUNT(*) FROM plans WHERE status IN ('queued','building')"
        ).fetchone()[0]

    # -- runs --------------------------------------------------------------
    def start_run(self, plan_id: str) -> str:
        rid = new_id()
        plan = self.plan(plan_id) or {}
        self.con.execute(
            "INSERT INTO runs (id, plan_id, started_at, status, robot) VALUES (?,?,?,?,?)",
            (rid, plan_id, now_iso(), "running", plan.get("robot") or "hexapod1"),
        )
        self.set_plan_status(plan_id, "running")
        return rid

    def import_run(self, *, robot: str, title: str, why: str, found: str,
                   source_dir: Optional[Path], runs_dir: Path,
                   status: str = "ok") -> str:
        """Record a hand-run experiment: a folder of video/telemetry plus a paragraph.

        Nothing is parsed. The folder is copied whole so a phone video or a
        CSV is one link on the dashboard, and the paragraph joins the
        learnings the planner reads.
        """
        pid = self.add_plan(title=title, why=why, kind="existing", protocol=None,
                            build_spec=None, source="operator", robot=robot, status="done")
        rid = new_id()
        run_dir = runs_dir / rid
        run_dir.mkdir(parents=True, exist_ok=True)
        files = []
        if source_dir is not None:
            for src in sorted(Path(source_dir).iterdir()):
                if src.name.startswith("."):
                    continue
                dest = run_dir / src.name
                shutil.copytree(src, dest) if src.is_dir() else shutil.copy2(src, dest)
                files.append(src.name)
        now = now_iso()
        self.con.execute(
            "INSERT INTO runs (id, plan_id, started_at, finished_at, status, exit_code, run_dir,"
            " summary_json, log_tail, robot) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (rid, pid, now, now, status, None, str(run_dir),
             json.dumps({"imported": True, "files": files}), "", robot),
        )
        self.con.commit()
        if found.strip():
            self.add_learning(f"[{robot}] {found.strip()}", run_id=rid)
        return rid

    def robots(self) -> List[str]:
        return [r[0] for r in self.con.execute(
            "SELECT DISTINCT robot FROM runs UNION SELECT DISTINCT robot FROM plans ORDER BY 1")]

    def finish_run(self, run_id: str, *, status: str, exit_code: Optional[int],
                   run_dir: Optional[str], summary: Optional[dict], log_tail: str) -> None:
        self.con.execute(
            "UPDATE runs SET finished_at=?, status=?, exit_code=?, run_dir=?,"
            " summary_json=?, log_tail=? WHERE id=?",
            (now_iso(), status, exit_code, run_dir,
             json.dumps(summary) if summary is not None else None, log_tail[-4000:], run_id),
        )
        self.con.commit()

    def update_run_summary(self, run_id: str, **fields) -> None:
        """Merge fields into the run's summary JSON (eyes, deploy, gate results)."""
        row = self.run(run_id)
        if not row:
            return
        try:
            summary = json.loads(row.get("summary_json") or "{}")
        except ValueError:
            summary = {}
        if not isinstance(summary, dict):
            summary = {"runner": summary}
        summary.update(fields)
        self.con.execute("UPDATE runs SET summary_json=? WHERE id=?", (json.dumps(summary), run_id))
        self.con.commit()

    def running_run(self) -> Optional[Dict[str, Any]]:
        row = self.con.execute("SELECT * FROM runs WHERE status='running' LIMIT 1").fetchone()
        return dict(row) if row else None

    def run(self, run_id: str) -> Optional[Dict[str, Any]]:
        row = self.con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        return dict(row) if row else None

    def runs(self, limit: int = 30, robot: Optional[str] = None) -> List[Dict[str, Any]]:
        where = " WHERE runs.robot=?" if robot else ""
        args = (robot, limit) if robot else (limit,)
        rows = self.con.execute(
            "SELECT runs.*, plans.title, plans.why, plans.protocol FROM runs"
            " JOIN plans ON plans.id = runs.plan_id" + where +
            " ORDER BY runs.started_at DESC, runs.rowid DESC LIMIT ?", args)
        return [dict(r) for r in rows]

    def run_files(self, run_id: str) -> List[str]:
        run = self.run(run_id)
        if not run or not run.get("run_dir"):
            return []
        root = Path(run["run_dir"])
        if not root.is_dir():
            return []
        return sorted(p.name for p in root.iterdir() if not p.name.startswith("."))

    def consecutive_failed_runs(self, since: Optional[str] = None) -> int:
        """Failed runs since the last success, optionally only those started
        after `since` (the loop passes its own start time, so an operator
        restart after a stop is a fresh three strikes, not an instant re-stop)."""
        n = 0
        for row in self.con.execute(
            "SELECT status FROM runs WHERE status != 'running' AND started_at >= ?"
            " AND COALESCE(json_extract(summary_json, '$.recovery'), 0) = 0"
            " ORDER BY started_at DESC, rowid DESC LIMIT 20", (since or "",)
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
