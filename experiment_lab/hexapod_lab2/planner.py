"""Two minutes, one question: what should the robot do next, and why?"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import claude_cli
from .config import Settings
from .runner import list_protocols, protocol_exists, protocol_needs_stand
from .store import Store

# Builds cost $1-2 and 5-10 minutes each and run one at a time; past this
# many pending, more proposals are just a backlog.
MAX_BUILDING = 3

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "learned": {
            "type": "string",
            "description": "One paragraph on the most recent run: what it showed, with numbers, and what that changes. Empty if there was no run.",
        },
        "plans": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "why": {"type": "string", "description": "Two sentences: the question this answers and how it moves the goal."},
                    "kind": {"type": "string", "enum": ["existing", "needs_code", "needs_fix"]},
                    "protocol": {"type": "string", "description": "Protocol file name without .json when kind is existing."},
                    "build_spec": {"type": "string", "description": "needs_code: exactly what protocol file to create and how, under 120 words. needs_fix: the diagnosis (which file/constant/behaviour, with the evidence), the smallest change that unblocks a run, and which existing protocol proves it; under 150 words."},
                    "force": {"type": "boolean", "description": "True only for whole-body protocols that need the runner's --force."},
                    "needs_robot": {"type": "boolean", "description": "needs_fix only: true if the engineer must move the robot, ssh in, flash firmware or deploy to diagnose or verify. The loop stops running while it holds the robot (up to 30 min)."},
                    "intent": {"type": "string", "enum": ["test", "explore"], "description": "test: the why states what result would count as success. explore: run it to look and learn; the run is recorded as explored, not passed or failed."},
                },
                "required": ["title", "why", "kind"],
            },
        },
    },
    "required": ["learned", "plans"],
}


def _local(value: Any) -> str:
    """UTC ISO -> the operator's clock, so the planner talks in local time."""
    try:
        when = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return str(value)[:16]
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone().strftime("%b %-d %-I:%M %p")


def _trim(text: Any, limit: int) -> str:
    flat = " ".join(str(text or "").split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def _run_digest(run: Optional[Dict[str, Any]]) -> str:
    if not run:
        return "No run yet."
    parts = [f"plan: {run.get('title')}", f"protocol: {run.get('protocol')}",
             f"status: {run.get('status')} (exit {run.get('exit_code')})"]
    summary = run.get("summary_json")
    if summary:
        try:
            doc = json.loads(summary)
            parts.append("runner_summary: " + _trim(json.dumps(doc, sort_keys=True), 1500))
        except ValueError:
            pass
    tail = str(run.get("log_tail") or "")
    if tail:
        parts.append("runner log tail:\n" + tail[-1200:])
    try:
        seen = json.loads(summary or "{}").get("seen") if summary else None
    except ValueError:
        seen = None
    if seen:
        parts.append("what the wide camera showed:\n" + str(seen)[:900])
    return "\n".join(parts)


def build_prompt(settings: Settings, store: Store, last_run: Optional[Dict[str, Any]]) -> str:
    protocols = list_protocols(settings)
    # Nearly every reviewed protocol (all the belly-rest and radial-shear
    # single-leg replays included) is a trajectory replay, so the tag says
    # that and nothing more; "whole body" would steer the planner away from
    # the cheapest runs.
    force_note = ("Protocols marked [traj] are trajectory replays; the loop passes the runner's --force for them automatically. Read the description for the physical setup (belly-rest ones need no stand)."
                  if settings.allow_force else
                  "Trajectory protocols (marked [traj]) cannot run in this loop right now; do not queue them.")
    proto_lines = "\n".join(
        f"- {p['name']}{' [traj]' if p['whole_body'] else ''}"
        f"{' [NEEDS STAND: not runnable]' if p['needs_stand'] else ''}: {_trim(p['description'], 160)}"
        for p in protocols)
    learnings = store.learnings(limit=8)
    learn_lines = "\n".join(f"- {_local(l['created_at'])}: {_trim(l['text'], 700)}" for l in learnings) or "- none yet"
    queue = store.plans(["queued", "building"])
    queue_lines = "\n".join(f"- [{p['status']}] {p['title']} ({p['protocol'] or p['kind']})" for p in queue) or "- empty"
    building = sum(1 for p in queue if p["status"] == "building")
    runnable = sum(1 for p in queue if p["status"] == "queued")
    queue_note = ""
    if building >= MAX_BUILDING:
        queue_note += f"\n{building} code jobs are already pending; new needs_code plans will be dropped (needs_fix still accepted), so prefer existing protocols."
    if runnable == 0:
        queue_note += "\nNothing runnable is queued: the robot is idle until you name at least one existing protocol worth running now."
    recent = store.runs(limit=6)
    recent_lines = "\n".join(
        f"- {_local(r['started_at'])} {r['protocol']}: {r['status']}" for r in recent) or "- none"
    return f"""You plan the next physical experiments for a cheap 18-servo hexapod. You have two minutes and no tools. Times below are the operator's local clock; use that clock, never UTC, when you mention a time.

GOAL: {settings.goal}

PHYSICAL SETUP: the robot sits on the floor on its own legs. There is no stand and nobody will suspend it or move it between runs. Protocols marked [NEEDS STAND] were written for a suspended robot and must not be queued; the loop rejects them. Anything "supported-chassis", "belly-rest" or "on the ground" is fine.

STEP BACK FIRST. Before proposing anything, ask: what do we actually not know that blocks smooth walking, and what is the cheapest run that answers it? Do not propose runs that repeat what the learnings already say. Do not propose safety checks, preflight rituals, audits or verification steps: the robot has its own in-loop trips (current, temperature, load, tilt, servo loss) and the runner enforces them. If the queue already has good plans, return zero new plans.

AVAILABLE PROTOCOLS (the runner executes these as-is; kind=existing):
{proto_lines}
{force_note}

If the right next experiment needs a protocol that does not exist, return kind=needs_code with a build_spec: a builder agent with repository access will create the file. Prefer remapping an existing protocol to another leg (there is `sysid/generate_leg_variant.py --leg N`) over inventing new motion.

If runs are failing for a reason that lives in CODE rather than in the protocol (a runner constant, a gate that rejects the robot's measured behaviour, a robot-side bug), return kind=needs_fix with a build_spec that states the diagnosis and the smallest change. An engineer agent gets a 30-minute box, a branch, and the failed run's camera stills; the loop merges it through a scope/size gate, deploys robot-side code between runs, and runs the protocol you name to verify. Set needs_robot=true when the fix has to touch the robot itself (ssh, firmware, moving it to reproduce); the loop hands the robot over exclusively for that job. Prefer needs_robot=false when a code read and unit tests suffice. Do not work around a code blocker by writing protocols that dodge it; ask for the fix. If the fix is bigger than 30 minutes, ask for the piece that unblocks a run; the engineer lists the rest as followups.

WHAT WE HAVE LEARNED (newest first):
{learn_lines}

RECENT RUNS:
{recent_lines}

CURRENT QUEUE:
{queue_lines}{queue_note}

MOST RECENT RUN, IN FULL:
{_run_digest(last_run)}

Write `learned` as one plain paragraph about that most recent run: the measured result with numbers, and what it means for the goal. If the run failed, say what failed and whether it is worth retrying. Then give at most three plans, each with a title, a two-sentence why, and either an existing protocol name or a build_spec. Cheapest informative run first.

Not every experiment is a pass/fail test. When a plan is there to look and learn (map a behaviour, sweep a parameter, see what the robot does), set intent=explore: the run is recorded as `explored`, not as a success or failure, and your `learned` paragraph is its result. Use intent=test only when the why states what result would count as success. A run marked failed means the robot or the code did not do what was asked, never that the answer was disappointing."""


def validate_plans(settings: Settings, plans: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not isinstance(plans, list):
        return out
    for raw in plans:
        if len(out) >= 3:
            break
        if not isinstance(raw, dict):
            continue
        title = _trim(raw.get("title"), 120)
        why = _trim(raw.get("why"), 600)
        if not title or not why:
            continue
        kind = raw.get("kind")
        protocol = str(raw.get("protocol") or "").strip().removesuffix(".json")
        force = bool(raw.get("force"))
        intent = "explore" if raw.get("intent") == "explore" else "test"
        if kind == "existing":
            if not protocol or not re.fullmatch(r"[A-Za-z0-9_.-]+", protocol):
                continue
            if protocol_exists(settings, protocol) and protocol_needs_stand(settings, protocol):
                continue
            if not protocol_exists(settings, protocol):
                # The model named a file that is not on disk: that is a build.
                kind, spec = "needs_code", f"Create sysid/protocols/{protocol}.json. {why}"
                out.append({"title": title, "why": why, "kind": kind, "protocol": None,
                            "build_spec": spec, "force": force, "intent": intent})
                continue
            if force and not settings.allow_force:
                continue
            out.append({"title": title, "why": why, "kind": "existing", "protocol": protocol,
                        "build_spec": None, "force": force, "intent": intent})
        elif kind in ("needs_code", "needs_fix"):
            spec = _trim(raw.get("build_spec"), 1200)
            if not spec:
                continue
            out.append({"title": title, "why": why, "kind": kind, "protocol": None,
                        "build_spec": spec, "force": force, "intent": intent,
                        "needs_robot": bool(raw.get("needs_robot")) and kind == "needs_fix"})
    return out


def plan(settings: Settings, store: Store, last_run: Optional[Dict[str, Any]],
         *, last_run_id: Optional[str] = None) -> Dict[str, Any]:
    """Call the planner once; record spend, learning and plans. Returns a report."""
    prompt = build_prompt(settings, store, last_run)
    res = claude_cli.oneshot(settings.claude_bin, prompt, PLAN_SCHEMA,
                             model=settings.planner_model, max_usd=settings.planner_max_usd,
                             timeout_s=settings.planner_budget_s)
    if res.cost_usd:
        store.add_spend("planner", res.cost_usd, "plan")
    if not res.ok:
        store.add_event("note", f"planner failed: {res.error}")
        return {"ok": False, "error": res.error, "added": 0, "cost_usd": res.cost_usd}
    learned = _trim(res.output.get("learned"), 2000)
    if learned and last_run:
        store.add_learning(learned, run_id=last_run_id)
    added = 0
    building = len(store.building_plans())
    for p in validate_plans(settings, res.output.get("plans")):
        if p["kind"] in ("needs_code", "needs_fix"):
            if building >= MAX_BUILDING and p["kind"] == "needs_code":
                continue
            building += 1
        store.add_plan(title=p["title"], why=p["why"], kind=p["kind"], protocol=p["protocol"],
                       build_spec=p["build_spec"], force=p["force"], needs_robot=p.get("needs_robot", False),
                       intent=p.get("intent", "test"))
        added += 1
    return {"ok": True, "added": added, "learned": learned, "cost_usd": res.cost_usd}
