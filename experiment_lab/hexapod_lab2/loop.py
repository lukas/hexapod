"""The loop. Read top to bottom; it is the whole design."""
from __future__ import annotations

import math
import os
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from . import alerts, commands, deploy, eyes, planner, recentre, recovery, robot, runner, zero_check
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
    cap = settings.current_cap()
    if spent >= cap:
        return f"spent ${spent:.2f} in 24 h, cap ${cap:.0f}"
    return None


CAMERA_MEASURED_PREFIXES = ("whole_body", "champion_stand", "tripod", "walk")


def camera_measured(protocol: str) -> bool:
    """Protocols whose result is read off the camera: worth starting in frame.
    Single-leg belly ladders are not; standing the robot up for them is wear
    for nothing (hexapod 2's clamp snapped after six re-steps in six minutes)."""
    return (protocol or "").lower().startswith(CAMERA_MEASURED_PREFIXES)


def walk_intent(doc: Optional[dict]) -> Optional[str]:
    """One phrase for the eyes: what the first leg of a walk protocol will do."""
    from . import walk
    legs = walk.legs_of(doc or {})
    if not legs:
        return None
    leg = legs[0]
    if leg.speed < 1.0 and leg.omega:
        return f"turn in place for about {leg.seconds:.0f} s"
    dist_cm = leg.speed * leg.seconds / 10.0
    if abs(leg.vx) >= abs(leg.vy):
        way = "forward" if leg.vx > 0 else "backward"
    else:
        way = "to its right" if leg.vy > 0 else "to its left"
    back = " and then back" if len(legs) > 1 and legs[1].name.endswith("_back") else ""
    return f"walk about {dist_cm:.0f} cm {way}{back}"


def pixel_of(settings: Settings, run_dir: Path):
    """Where the chassis tag sits in the frame (fractions), or None."""
    from . import walk as walk_mod
    try:
        return walk_mod.Session(settings, run_dir, log=lambda m: None).pixel()
    except Exception:  # noqa: BLE001 - no camera is "not visible"
        return None


def recentre_distance_cm(frac, frame_width_cm: float = 120.0) -> float:
    """Rough distance to the middle for the eyes; the top camera sees about 1.2 m across."""
    return recentre.distance_frac(frac) * frame_width_cm


def recentre_before(settings: Settings, run_dir: Path, *, walk: bool, log=print) -> Optional[Dict[str, Any]]:
    """Recentre if the chassis tag is far from the middle; sit again unless a walk follows."""
    from . import walk as walk_mod
    s = walk_mod.Session(settings, run_dir, log=log)
    frac = s.pixel()
    if frac is None:
        log("recentre: chassis tag not in any camera; running where it is")
        return {"moved": False, "done": False, "reason": "tag not visible", "start": None, "end": None, "seconds": 0.0}
    if not recentre.needs_recentre(frac):
        return None
    rc = recentre.recentre(s, budget_s=settings.recentre_budget_s)
    log(f"recentre: {rc['reason']} ({rc['start']} -> {rc['end']})")
    if rc["moved"] and not walk:
        s.sit(wait=True)
    return rc


def run_once(settings: Settings, store: Store, plan: Dict[str, Any], log=print,
             sleep_fn=time.sleep) -> Dict[str, Any]:
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
    walk_doc = runner.walk_document(settings, plan["protocol"])
    about_to = walk_intent(walk_doc) if walk_doc else None
    obstacle: Optional[str] = None
    run_dir = settings.runs_dir / run_id
    # A recentre is a move too: if one is coming, the look is told about it.
    recentre_pending = False
    if settings.recentre and (walk_doc is not None or camera_measured(plan["protocol"])):
        frac = pixel_of(settings, run_dir)
        recentre_pending = recentre.needs_recentre(frac)
        if recentre_pending:
            towards = f"walk about {recentre_distance_cm(frac):.0f} cm toward the middle of this picture first"
            about_to = f"{towards}, then {about_to}" if about_to else towards
    if settings.look_before_moving:
        # The one look before motion: can the eyes see the robot, and does
        # it look ready? Telemetry cannot tell that a leg is off and someone
        # is holding it. A no leaves the plan queued and holds the loop. For
        # a walk the same look is asked what sits in the robot's way.
        flat = zero_check.encoders(fb)["at_zero"] and math.hypot(float(fb.get("roll_deg") or 0), float(fb.get("pitch_deg") or 0)) < 8.0
        ready, saw, cost = eyes.ready_to_move(settings, about_to=about_to, pose_known=flat)
        if cost:
            store.add_spend("eyes", cost, run_id)
        store.add_event("look", f"{'ready' if ready else 'NOT READY'}: {saw[:400]}")
        log(f"look: {saw[:160]}")
        if not ready:
            # The same resting robot got YES and NO a minute apart on 2026-09-11.
            # One more look, a few seconds later, before holding the whole loop;
            # two independent noes are a hold, one is a wobble.
            sleep_fn(8.0)
            ready, saw2, cost2 = eyes.ready_to_move(settings, about_to=about_to, pose_known=flat)
            if cost2:
                store.add_spend("eyes", cost2, run_id)
            store.add_event("look", f"second look {'ready' if ready else 'NOT READY'}: {saw2[:400]}")
            log(f"second look: {saw2[:160]}")
            saw = saw2 if ready else f"{saw[:200]} / again: {saw2[:200]}"
        if not ready:
            store.finish_run(run_id, status="held", exit_code=None, run_dir=None,
                             summary={"look": saw[:400]}, log_tail=f"not moved; eyes: {saw}")
            store.set_plan_status(plan["id"], "queued", f"eyes: {saw[:120]}")
            return store.run(run_id)
        obstacle = eyes.obstacle_in(saw) if about_to else None
        if obstacle:
            store.add_event("look", f"obstacle near the robot: {obstacle[:200]}")
    zc: Optional[Dict[str, Any]] = None
    if settings.zero_check and runner.walk_document(settings, plan["protocol"]) is None:
        # Protocols other than walks start from the zero pose. The encoders
        # cannot see a slipped horn; the camera can. This holds only when the
        # encoders say zero and the camera says a leg points elsewhere.
        zc = zero_check.double_check(settings, fb, run_dir / "zero_check", log=log)
        store.add_event("zero_check", f"{zc['verdict']}: {zc['text'][:300]}")
        if zc["verdict"] == "camera_disagrees":
            store.finish_run(run_id, status="held", exit_code=None, run_dir=str(run_dir),
                             summary={"zero_check": zc}, log_tail=f"not moved; zero check: {zc['text']}")
            store.set_plan_status(plan["id"], "queued", f"zero check: {zc['text'][:120]}")
            settings.pause_file.write_text(f"paused: {zc['text']}\n")
            store.add_event("needs_hand", f"zero pose looks wrong on camera: {zc['text'][:300]}")
            alerts.text(store, "zero_check", f"legs {zc['legs_off']} do not point where the layout says zero is while "
                                             f"the encoders read zero (slipped horn?). Paused; frame on run {run_id}.")
            return store.run(run_id)
    rc: Optional[Dict[str, Any]] = None
    if recentre_pending and obstacle:
        # Something is in the way of the move to the middle: run where it is.
        rc = {"moved": False, "done": False, "reason": f"not moved, the look saw {obstacle[:120]} in the way",
              "start": None, "end": None, "seconds": 0.0}
        store.add_event("recentre", rc["reason"][:300])
        log("recentre: " + rc["reason"])
    elif settings.recentre and (walk_doc is not None or camera_measured(plan["protocol"])):
        # Where the camera is the measurement, start in the middle of its frame.
        rc = recentre_before(settings, run_dir, walk=walk_doc is not None, log=log)
        if rc is not None:
            store.add_event("recentre", f"{'moved' if rc['moved'] else 'left'}: {rc['reason'][:200]}")
    log(f"sync: {runner.sync_checkout(settings)}")
    log(f"run {plan['protocol']} ({plan['title']})")
    with eyes.WideCapture(settings.wide_frame_url, run_dir / "wide"):
        extra = {"obstacle": obstacle} if obstacle else {}
        result = runner.run_protocol(settings, plan["protocol"], run_id, force=bool(plan.get("force")), **extra)
    # ok/failed say whether the robot did what the protocol asked. A plan whose
    # intent is to explore has no pass/fail on top of that: a run that completed
    # is "explored", and what it showed goes in the planner's learned paragraph.
    status = "explored" if (result.status == "ok" and plan.get("intent") == "explore") else result.status
    summary = dict(result.summary or {})
    if zc is not None:
        summary["zero_check"] = {k: zc.get(k) for k in ("verdict", "text", "legs_off", "frame")}
    if rc is not None:
        summary["recentre_before"] = {k: rc.get(k) for k in ("moved", "done", "reason", "start", "end", "seconds")}
    store.finish_run(run_id, status=status, exit_code=result.exit_code,
                     run_dir=str(result.run_dir or run_dir),
                     summary=summary or None, log_tail=result.log_tail)
    store.set_plan_status(plan["id"], "done" if status in ("ok", "explored") else "failed",
                          f"exit {result.exit_code}, {result.motion_s:.0f} s")
    log(f"run {status} (exit {result.exit_code}) in {result.motion_s:.0f} s")
    tail = (result.log_tail or "").strip().splitlines()
    eyes.see_run(settings, store, run_id,
                 f"protocol {plan['protocol']}: {plan['why'][:300]}\nresult: {result.status}, exit {result.exit_code}\n"
                 f"last runner lines: {' | '.join(tail[-3:])}", log=log)
    return store.run(run_id)


def record_recovery(settings: Settings, store: Store, plan: Dict[str, Any], trip: str,
                    *, log=print, sleep=time.sleep, recover=None) -> Dict[str, Any]:
    """Run the recovery ladder as a recorded, unplanned experiment."""
    pid = store.add_plan(
        title=f"Recovery after {plan['protocol']}",
        why=(f"{plan['protocol']} tripped: {trip}. Unplanned: which of the robot's own escape "
             f"moves (safe-zero, low-torque untrap) frees it from this pose, and at what cost?"),
        kind="existing", protocol=None, build_spec=None, source="loop", robot=plan.get("robot") or "hexapod1",
        status="running")
    rid = store.start_run(pid)
    run_dir = settings.runs_dir / rid
    with eyes.WideCapture(settings.wide_frame_url, run_dir / "wide"):
        rep = (recover or recovery.recover)(settings, log=log, sleep=sleep, run_dir=run_dir)
    lines = [f"trip: {trip}", f"before: {rep.get('before')}"]
    lines += [f"{r['rung']} ({r['seconds']} s): {r['status']} -> {'free' if r['ok'] else 'still stuck'}" for r in rep["rungs"]]
    lines.append(f"after: {rep.get('after')}")
    store.finish_run(rid, status="ok" if rep["ok"] else "failed", exit_code=None, run_dir=str(run_dir),
                     summary={"recovery": True, "after_protocol": plan["protocol"], "trip": trip, **rep},
                     log_tail="\n".join(lines))
    store.set_plan_status(pid, "done" if rep["ok"] else "failed",
                          f"freed by {next((r['rung'] for r in rep['rungs'] if r['ok']), 'nothing')}")
    store.add_event("recovery", ("recovered: " if rep["ok"] else "FAILED: ")
                    + "; ".join(f"{r['rung']}={r['status'][:60]}" for r in rep["rungs"]))
    eyes.see_run(settings, store, rid, f"recovery after {plan['protocol']} tripped ({trip}); rungs: "
                 + "; ".join(f"{r['rung']}={r['status'][:60]}" for r in rep["rungs"]), log=log)
    return store.run(rid)


def main_loop(settings: Settings, store: Store, *, log=print, sleep=time.sleep,
              max_iterations: Optional[int] = None, inbox: Optional[commands.Inbox] = None) -> str:
    settings.runs_dir.mkdir(parents=True, exist_ok=True)
    builder = BuilderThread(settings, store)
    c = Counters(started_at=now_iso())
    released = store.release_stuck_builds()
    store.add_event("note", "loop started" + (f"; {released} interrupted build(s) requeued" if released else ""))
    if inbox is None:
        inbox = commands.Inbox(recipient=os.getenv("HEXAPOD_LAB2_ALERT_RECIPIENT", "").strip())

    def fresh_start() -> None:
        # A resume (by text, by CLI, or by deleting PAUSE) is a fresh three
        # strikes; whatever stopped us has been looked at.
        c.started_at, c.unreachable, c.empty_plans = now_iso(), 0, 0

    iterations = 0
    was_paused = False
    while max_iterations is None or iterations < max_iterations:
        iterations += 1
        commands.poll_and_apply(settings, store, inbox, on_resume=fresh_start, log=log)
        if settings.pause_file.exists():
            was_paused = True
            log("paused (PAUSE file present)")
            sleep(settings.idle_sleep_s)
            continue
        if was_paused:
            was_paused = False
            fresh_start()
            store.add_event("note", "resumed")
        reason = stop_reason(settings, store, c)
        if reason:
            # Stop means pause, not exit: the process stays up so a text
            # reply ("resume", "raise cap 100") can get it going again.
            store.add_event("stop", reason)
            log(f"STOP: {reason}")
            settings.pause_file.write_text(f"stopped: {reason}\n")
            alerts.text(store, "stop", f"stopped: {reason}. {commands.HELP}")
            continue
        dep = deploy.deploy_if_needed(settings, store, log=log)
        if dep.get("deployed"):
            log("deployed robot-side code")
        started = builder.maybe_start()
        if started:
            log(f"code job started for plan {started}")
        if settings.robot_held.exists():
            log(f"engineer holds the robot ({settings.robot_held.read_text().strip()[:60]})")
            sleep(settings.idle_sleep_s)
            continue
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
        run = run_once(settings, store, plan, log=log, sleep_fn=sleep)
        c.planned_while_waiting = False
        if run["status"] == "unreachable":
            c.unreachable += 1
            sleep(settings.idle_sleep_s)
            continue
        c.unreachable = 0
        if run["status"] == "held":
            saw = (run.get("log_tail") or "").replace("not moved; eyes: ", "", 1)
            settings.pause_file.write_text(f"paused: not moving, the camera look said: {saw[:200]}\n")
            store.add_event("needs_hand", f"held before {plan['protocol']}: {saw[:300]}")
            alerts.text(store, "not_ready",
                        f"not moving. Looked at the camera before {plan['protocol']} and it said: "
                        f"{saw[:220]} Paused; reply resume when the robot is ready.")
            continue
        if run["status"] == "failed" and recovery.looks_like_jam(run.get("log_tail") or ""):
            # A tripped joint usually means a leg ended up somewhere the next
            # glide cannot start from. Let the robot free itself before the
            # next run instead of spending three strikes finding that out,
            # and keep the whole episode as an experiment of its own: which
            # escape freed which pose is exactly the data a better escape
            # would be designed from.
            trip = recovery.trip_line(run.get("log_tail") or "")
            log("run tripped on a joint; running recovery ladder")
            sleep(recovery.SETTLE_S)
            run = record_recovery(settings, store, plan, trip, log=log, sleep=sleep)
            if run["status"] != "ok":
                settings.pause_file.write_text("paused: recovery failed, robot needs a hand\n")
                store.add_event("needs_hand", f"recovery failed after {plan['protocol']}: {trip}")
                alerts.text(store, "needs_hand",
                            f"robot needs a hand. {plan['protocol']} tripped ({trip[-120:]}) "
                            f"and safe-zero/untrap could not free it. Paused; free the leg, then reply resume.")
        # Every run gets its paragraph and the queue gets refreshed while the
        # result is fresh. One call, about a dollar, two minutes max.
        report = planner.plan(settings, store, run, last_run_id=run["id"])
        log(f"planner: {report}")
        c.empty_plans = 0 if (report.get("added", 0) or store.next_runnable()) else c.empty_plans + 1
    return "iteration limit"
