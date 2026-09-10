"""The loop. Read top to bottom; it is the whole design."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from . import planner, robot, runner
from .builder import BuilderThread
from .config import Settings
from .store import Store, now_iso


@dataclass
class Counters:
    started_at: str = ""
    unreachable: int = 0
    empty_plans: int = 0
    planned_while_waiting: bool = False
    last_run_id: Optional[str] = None
    notes: list = field(default_factory=list)


def stop_reason(settings: Settings, store: Store, c: Counters) -> Optional[str]:
    failed = store.consecutive_failed_runs(since=c.started_at)
    if failed >= settings.max_consecutive_failed_runs:
        return f"{failed} failed runs in a row"
    if c.unreachable >= settings.max_consecutive_unreachable:
        return f"robot unreachable {c.unreachable} times in a row"
    if c.empty_plans >= settings.max_consecutive_empty_plans:
        return f"planner returned nothing {c.empty_plans} times in a row with an empty queue"
    spent = store.spend_last_24h()
    if spent >= settings.daily_spend_cap_usd:
        return f"spent ${spent:.2f} in 24 h, cap ${settings.daily_spend_cap_usd:.0f}"
    return None


def run_once(settings: Settings, store: Store, plan: Dict[str, Any], log=print) -> Dict[str, Any]:
    """Health read, run, record. Returns the stored run row."""
    run_id = store.start_run(plan["id"])
    try:
        fb = robot.health(settings.robot_url, settings.health_budget_s)
    except robot.RobotUnreachable as exc:
        store.finish_run(run_id, status="unreachable", exit_code=None, run_dir=None,
                         summary=None, log_tail=str(exc))
        store.set_plan_status(plan["id"], "queued", f"robot unreachable: {exc}")
        return store.run(run_id)
    except robot.RobotNotReady as exc:
        store.finish_run(run_id, status="failed", exit_code=None, run_dir=None,
                         summary=None, log_tail=f"robot not ready: {exc}")
        store.set_plan_status(plan["id"], "queued", f"robot not ready: {exc}")
        return store.run(run_id)
    log(f"robot ok: {fb.get('live')}/18 servos, roll {fb.get('roll_deg')} pitch {fb.get('pitch_deg')}")
    log(f"sync: {runner.sync_checkout(settings)}")
    log(f"run {plan['protocol']} ({plan['title']})")
    result = runner.run_protocol(settings, plan["protocol"], run_id, force=bool(plan.get("force")))
    store.finish_run(run_id, status=result.status, exit_code=result.exit_code,
                     run_dir=str(result.run_dir) if result.run_dir else None,
                     summary=result.summary, log_tail=result.log_tail)
    store.set_plan_status(plan["id"], "done" if result.status == "ok" else "failed",
                          f"exit {result.exit_code}, {result.motion_s:.0f} s")
    log(f"run {result.status} (exit {result.exit_code}) in {result.motion_s:.0f} s")
    return store.run(run_id)


def main_loop(settings: Settings, store: Store, *, log=print, sleep=time.sleep,
              max_iterations: Optional[int] = None) -> str:
    settings.runs_dir.mkdir(parents=True, exist_ok=True)
    builder = BuilderThread(settings, store)
    c = Counters(started_at=now_iso())
    released = store.release_stuck_builds()
    store.add_event("note", "loop started" + (f"; {released} interrupted build(s) requeued" if released else ""))
    iterations = 0
    while max_iterations is None or iterations < max_iterations:
        iterations += 1
        if settings.pause_file.exists():
            log("paused (PAUSE file present)")
            sleep(settings.idle_sleep_s)
            continue
        reason = stop_reason(settings, store, c)
        if reason:
            store.add_event("stop", reason)
            log(f"STOP: {reason}")
            return reason
        started = builder.maybe_start()
        if started:
            log(f"builder started for plan {started}")
        plan = store.next_runnable()
        if plan is None:
            # A queue of nothing but builds must not leave the robot idle for
            # the length of a build: ask the planner once for something that
            # exists on disk, then wait.
            if builder.busy() and c.planned_while_waiting:
                log("waiting on builder")
                sleep(settings.idle_sleep_s)
                continue
            c.planned_while_waiting = builder.busy()
            last = store.runs(limit=1)
            report = planner.plan(settings, store, last[0] if last else None,
                                  last_run_id=last[0]["id"] if last else None)
            log(f"planner: {report}")
            if report.get("added", 0) == 0:
                c.empty_plans += 1
                sleep(settings.idle_sleep_s)
            else:
                c.empty_plans = 0
            continue
        if runner.protocol_needs_stand(settings, plan["protocol"]):
            store.set_plan_status(plan["id"], "skipped", "protocol needs a stand; robot is on the floor")
            log(f"skip {plan['protocol']}: needs a stand")
            continue
        run = run_once(settings, store, plan, log=log)
        c.planned_while_waiting = False
        if run["status"] == "unreachable":
            c.unreachable += 1
            sleep(settings.idle_sleep_s)
            continue
        c.unreachable = 0
        # Every run gets its paragraph and the queue gets refreshed while the
        # result is fresh. One call, about a dollar, two minutes max.
        report = planner.plan(settings, store, run, last_run_id=run["id"])
        log(f"planner: {report}")
        c.empty_plans = 0 if (report.get("added", 0) or store.next_runnable()) else c.empty_plans + 1
    return "iteration limit"
