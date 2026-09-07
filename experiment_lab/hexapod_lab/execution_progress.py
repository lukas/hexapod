"""Durable runner progress reports, independent of experiment execution."""

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExecutionProgressIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: Literal["preparing", "blocked", "running", "idle"]
    summary: str = Field(min_length=1, max_length=600)
    detail: str = Field(default="", max_length=2000)
    next_action: str = Field(min_length=1, max_length=1000)
    experiment_id: Optional[str] = None
    task_name: Optional[str] = Field(default=None, max_length=200)
    ttl_seconds: int = Field(default=900, ge=30, le=3600)

    @field_validator("summary", "next_action", mode="before")
    @classmethod
    def strip_required_text(cls, value):
        return value.strip() if isinstance(value, str) else value


def _utcnow():
    return datetime.now(timezone.utc)


class ExecutionProgressStore:
    def __init__(self, store):
        self.store = store
        with store.connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS execution_progress_reports (
                  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                  payload_json TEXT NOT NULL,
                  updated_by TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  expires_at TEXT NOT NULL
                );
                CREATE TRIGGER IF NOT EXISTS execution_progress_no_update
                  BEFORE UPDATE ON execution_progress_reports BEGIN
                    SELECT RAISE(ABORT, 'execution progress reports are append-only');
                  END;
                CREATE TRIGGER IF NOT EXISTS execution_progress_no_delete
                  BEFORE DELETE ON execution_progress_reports BEGIN
                    SELECT RAISE(ABORT, 'execution progress reports are append-only');
                  END;
            """)

    @staticmethod
    def _report(row):
        if row is None:
            return None
        return {
            **json.loads(row["payload_json"]),
            "revision": row["sequence"],
            "updated_by": row["updated_by"],
            "updated_at": row["updated_at"],
            "expires_at": row["expires_at"],
            "stale": _utcnow() >= datetime.fromisoformat(row["expires_at"]),
        }

    def record(self, report: Any, actor: str):
        validated = ExecutionProgressIn.model_validate(report)
        now = _utcnow()
        expires_at = now + timedelta(seconds=validated.ttl_seconds)
        with self.store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            inserted = connection.execute(
                "INSERT INTO execution_progress_reports("
                "payload_json,updated_by,updated_at,expires_at) VALUES(?,?,?,?)",
                (json.dumps(validated.model_dump(mode="json"), sort_keys=True),
                 actor, now.isoformat(), expires_at.isoformat()),
            )
            row = connection.execute(
                "SELECT * FROM execution_progress_reports WHERE sequence=?",
                (inserted.lastrowid,),
            ).fetchone()
            connection.execute("COMMIT")
        return self._report(row)

    def latest(self):
        with self.store.connect() as connection:
            row = connection.execute(
                "SELECT * FROM execution_progress_reports ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
        return self._report(row)


def execution_summary(status, experiments, report):
    """Combine reported work with observed robot activity without inventing a run."""
    status = status if isinstance(status, Mapping) else {}
    robot = status.get("robot")
    robot = robot if isinstance(robot, Mapping) else {}
    health = status.get("health")
    health = health if isinstance(health, Mapping) else {}
    report = deepcopy(dict(report)) if isinstance(report, Mapping) else None
    fresh_robot = health.get("fresh") is True

    def result(state, headline, reason, next_action):
        return {"state": state, "headline": headline, "reason": reason,
                "next_action": next_action, "report": report}

    if fresh_robot and robot.get("busy") is True:
        process_name = robot.get("process_name")
        activity = robot.get("activity")
        if isinstance(process_name, str) and process_name.strip():
            detail = f"The robot reports an active {process_name} process."
        elif isinstance(activity, str) and activity in {"demo", "rl", "zeroing", "stopping", "driving"}:
            detail = f"The robot reports an active {activity} process."
        else:
            detail = "The robot reports an active control process."
        if isinstance(robot.get("detail"), str) and robot["detail"].strip():
            detail += " " + robot["detail"].strip()
        return result("running", "A robot control process is active", detail,
                      "Let the current process finish and review its result before starting another test.")

    if report is not None:
        if report.get("stale") is not False:
            return result("unknown", "Execution report is stale",
                          "The last progress report has expired; current runner activity is unknown.",
                          "Refresh the runner’s progress report to identify the current work or blocker.")
        state = report.get("state")
        summary = report.get("summary")
        next_action = report.get("next_action")
        if not isinstance(state, str) or state not in {"preparing", "blocked", "running", "idle"} or not isinstance(summary, str) or not summary.strip() or not isinstance(next_action, str) or not next_action.strip():
            return result("unknown", "Execution report needs verification",
                          "The runner’s latest report is incomplete or invalid.",
                          "Publish a current progress report with the work, blocker, and next action.")
        if state == "running":
            observation = "Fresh robot readings show no active control process." if fresh_robot else "Live robot activity has not been verified."
            return result("unknown", "Reported run needs verification",
                          f"The runner reports: {summary} {observation}",
                          "Check the runner and its robot connection before starting another test.")
        if not fresh_robot and state == "idle":
            return result("unknown", "Runner reports idle — robot activity unverified",
                          f"{summary} Live robot activity has not been verified.", next_action)
        headlines = {
            "preparing": "Preparing the next test",
            "blocked": "Idle — execution blocked" if fresh_robot else "Execution blocked — robot activity unverified",
            "idle": "Idle — progress reported",
        }
        return result(state, headlines[state], summary, next_action)

    waiting = sum(
        1 for item in experiments or ()
        if isinstance(item, Mapping) and item.get("status") == "waiting_for_operator"
    )
    if waiting:
        noun = "plan" if waiting == 1 else "plans"
        reason = f"There are {waiting} saved physical-test {noun}. They are not started automatically by the website; the serialized guarded Codex runner may advance them, and no runner has reported current work on them."
        if not fresh_robot:
            reason = "Live robot activity has not been verified. " + reason
        return result("idle" if fresh_robot else "unknown",
                      "Idle — no runner progress reported" if fresh_robot else "Execution status unknown — no runner progress reported",
                      reason,
                      "Have the runner inspect the oldest plan and report what it is preparing, running, or concretely blocked on.")
    return result("idle" if fresh_robot else "unknown",
                  "Idle — no runner progress reported" if fresh_robot else "Execution status unknown",
                  "No active control process or current runner progress has been reported.",
                  "Publish the current work or next test in a runner progress report.")
