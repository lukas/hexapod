"""The engineer: fix a blocker in code, on a branch, inside a box.

A `needs_fix` plan carries a diagnosis and a change. One tool-using Claude
gets a worktree of origin/main, the diagnosis, the wide-camera stills of the
run that failed, and thirty minutes. It commits to a branch `lab2/fix-<id>`
and pushes that branch, never main. The loop then applies a merge gate
(scope, size, forbidden paths) before fast-forwarding main, syncing the
runner checkout, flagging a robot deploy if linux_control changed, and
queueing the verification protocol the engineer named. Anything the gate
refuses stays on its branch for a human, and the operator gets one text.

Rules the engineer is given, verbatim in the prompt: no --go, no robot
POSTs (the loop owns the robot), no firmware, no edits to the lab itself,
smallest change that unblocks a run, and if the job is bigger than the
box, do the piece that unblocks and list the rest as followups.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import claude_cli
from .builder import _cleanup_worktree, _prepare_worktree
from .config import Settings
from .gitlock import GIT_LOCK
from .store import Store

FIX_SCHEMA = {
    "type": "object",
    "properties": {
        "fixed": {"type": "boolean"},
        "summary": {"type": "string", "description": "Under 100 words: the diagnosis you confirmed, what you changed, how you checked it."},
        "verify_protocol": {"type": "string", "description": "Existing protocol (no .json) the loop should run next to prove the fix."},
        "touched_robot_side": {"type": "boolean", "description": "True if anything under linux_control/ changed."},
        "deployed": {"type": "boolean", "description": "True if you already deployed/flashed the robot yourself."},
        "followups": {"type": "array", "maxItems": 3, "items": {"type": "object", "properties": {
            "title": {"type": "string"}, "why": {"type": "string"}, "fix_spec": {"type": "string"}},
            "required": ["title", "why", "fix_spec"]}},
    },
    "required": ["fixed", "summary"],
}


def branch_name(plan_id: str) -> str:
    return f"lab2/fix-{plan_id}"


def _robot_rules(settings: Settings, plan: Dict[str, Any]) -> str:
    if plan.get("needs_robot"):
        return f"""YOU HOLD THE ROBOT for this job; the loop runs nothing until you finish. You may:
- read it and move it over HTTP at {settings.robot_url} (GET /api/feedback, /api/rl/state, /api/status; POST /api/zero {{"pose":"sit"}}, /api/standup, /api/untrap; the sysid runner with --go),
- ssh in: `ssh {settings.robot_ssh}` (tree at /home/arduino/hexapod_sts, service hexapod-web, journal via `journalctl -u hexapod-web -n 200`),
- deploy: `HEXAPOD_SSH={settings.robot_ssh} HEXAPOD_HOST={settings.robot_url} ./deploy_ssh.sh` from linux_control/,
- flash bridge firmware: `firmware/flash_feetech_bridge.sh {settings.robot_ssh}` (then restart hexapod-web),
- look: wide camera `{settings.wide_frame_url}`, tag camera `{settings.vision_frame_url}` (curl them to files and read them).
It is a cheap robot with its own in-loop trips (current, temperature, tilt, tracking, servo loss); those are the safety system, do not add pre-run rituals. Leave it belly-down, limp and healthy (18/18 servos, tilt under 8 deg) when you finish: POST /api/zero {{"pose":"sit"}} is the way. Report deployed=true if you pushed code or firmware to the robot yourself."""
    return f"""NEVER move the robot: no `--go`, no POST to the robot, no deploy, no ssh. The loop owns the robot; it will deploy linux_control changes between runs and run your `verify_protocol` next. Dry runs (`python -m sysid.run_hw --protocol ...` without --go) and unit tests are fine."""


def _prompt(settings: Settings, plan: Dict[str, Any], branch: str, stills: List[Path]) -> str:
    still_lines = "\n".join(f"- {p}" for p in stills[:6]) or "- none available"
    return f"""You are fixing one blocker in a cheap 18-servo hexapod's code so the lab loop can keep running experiments. Hard limits: 30 minutes wall clock, ${settings.engineer_max_usd:.0f}. Work only inside this checkout, on branch `{branch}` (already checked out).

PLAN: {plan['title']}
WHY: {plan['why']}
DIAGNOSIS AND CHANGE (from the planner): {plan['build_spec']}

Wide-camera stills from the run that failed (look at them; they are files you can read):
{still_lines}

Rules:
- Smallest change that unblocks a run. If the real fix is bigger than this box, make the piece that unblocks and list the rest under `followups` (each a self-contained fix_spec); the loop queues them.
- Only edit under `{settings.fix_scope}` (firmware included). Never `experiment_lab/` (the lab itself), never this prompt's rules. The merge gate rejects anything else and the whole branch is left unmerged.
- Stay under {settings.max_fix_lines} changed lines total.
- {_robot_rules(settings, plan)}
- Run the unit tests for the module you touched (`../../.venv/bin/python -m pytest <test file> -q` from hexapod_walker/prototype_sts3215/linux_control or sysid). Do not add new safety checks, pre-run gates or audits; loosen or fix, do not add ceremony.
- Commit with a message that states the diagnosis, then: `git push origin HEAD:{branch}`.
- Report fixed=true only if you pushed and the tests you ran pass. Name an existing protocol that will exercise the fix as `verify_protocol`."""


def gate(settings: Settings, diff_stat: str, changed_files: List[str]) -> Optional[str]:
    """None if the diff may merge; otherwise the reason it may not."""
    if not changed_files:
        return "no changes on the branch"
    for f in changed_files:
        if not f.startswith(settings.fix_scope):
            return f"touches {f}, outside {settings.fix_scope}"
        for bad in settings.fix_forbidden:
            if f.startswith(bad):
                return f"touches forbidden path {f}"
    m = re.search(r"(\d+) insertion", diff_stat)
    d = re.search(r"(\d+) deletion", diff_stat)
    lines = (int(m.group(1)) if m else 0) + (int(d.group(1)) if d else 0)
    if lines > settings.max_fix_lines:
        return f"{lines} changed lines, limit {settings.max_fix_lines}"
    return None


def _git(settings: Settings, *args: str, timeout: float = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(settings.checkout), *args], capture_output=True, text=True, timeout=timeout)


def merge_branch(settings: Settings, branch: str) -> Dict[str, Any]:
    """Fetch the engineer's branch, gate it, fast-forward main. Returns a report."""
    with GIT_LOCK:
        fetched = _git(settings, "fetch", "-q", "origin", "main", branch)
        if fetched.returncode:
            return {"merged": False, "reason": f"fetch failed: {fetched.stderr.strip()[:200]}"}
        files = _git(settings, "diff", "--name-only", f"origin/main...origin/{branch}").stdout.split()
        stat = _git(settings, "diff", "--shortstat", f"origin/main...origin/{branch}").stdout.strip()
        reason = gate(settings, stat, files)
        if reason:
            return {"merged": False, "reason": reason, "files": files, "stat": stat}
        # Fast-forward main on the remote; if main moved under us the push is
        # rejected and the branch stays for a human rather than us rebasing code
        # we did not write.
        pushed = _git(settings, "push", "-q", "origin", f"origin/{branch}:main")
        if pushed.returncode:
            return {"merged": False, "reason": f"main moved; not fast-forward: {pushed.stderr.strip()[:200]}",
                    "files": files, "stat": stat}
        _git(settings, "fetch", "-q", "origin", "main")
        _git(settings, "merge", "-q", "--ff-only", "origin/main")
        return {"merged": True, "files": files, "stat": stat,
                "robot_side": any("/linux_control/" in f for f in files)}


def fix_plan(settings: Settings, store: Store, plan: Dict[str, Any]) -> Dict[str, Any]:
    pid = plan["id"]
    branch = branch_name(pid)
    log_path = settings.data_dir / "fix" / pid / "engineer.log"
    try:
        wt = _prepare_worktree(settings, pid, subdir="fix")
        with GIT_LOCK:
            subprocess.run(["git", "-C", str(wt), "checkout", "-q", "-B", branch], check=True,
                           capture_output=True, text=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        msg = f"worktree failed: {getattr(exc, 'stderr', '') or exc}"[:300]
        store.set_plan_status(pid, "failed", msg)
        store.add_event("engineer", f"{plan['title']}: {msg}")
        return {"ok": False, "error": msg}
    stills = _stills_for(store, plan)
    res = claude_cli.build(settings.claude_bin, _prompt(settings, plan, branch, stills), FIX_SCHEMA,
                           workdir=wt, model=settings.builder_model, max_usd=settings.engineer_max_usd,
                           timeout_s=settings.engineer_budget_s, log_path=log_path)
    if res.cost_usd:
        store.add_spend("engineer", res.cost_usd, plan["title"])
    _cleanup_worktree(settings, wt)
    if plan.get("needs_robot"):
        _release_robot(settings, store, plan)
    if not res.ok:
        store.set_plan_status(pid, "failed", f"engineer: {res.error}"[:300])
        store.add_event("engineer", f"{plan['title']}: engineer failed: {res.error}"[:400])
        return {"ok": False, "error": res.error, "cost_usd": res.cost_usd}
    out = res.output or {}
    summary = " ".join(str(out.get("summary") or "").split())[:500]
    if not out.get("fixed"):
        store.set_plan_status(pid, "failed", f"engineer reported not fixed: {summary}"[:300])
        store.add_event("engineer", f"{plan['title']}: not fixed. {summary}"[:400])
        return {"ok": False, "error": summary, "cost_usd": res.cost_usd}
    merged = merge_branch(settings, branch)
    if not merged.get("merged"):
        note = f"left on {branch} for review: {merged.get('reason')}"
        store.set_plan_status(pid, "failed", note[:300])
        store.add_event("engineer", f"{plan['title']}: {note}. {summary}"[:400])
        from . import alerts
        alerts.text(store, f"fix-{pid}", f"engineer's fix for '{plan['title']}' was not merged ({merged.get('reason')}). "
                                         f"Branch {branch} is on GitHub for you to look at.")
        return {"ok": False, "error": note, "cost_usd": res.cost_usd, **merged}
    if (merged.get("robot_side") or out.get("touched_robot_side")) and not out.get("deployed"):
        settings.deploy_flag.write_text(f"{branch}: {summary}\n")
    verify = str(out.get("verify_protocol") or "").strip().removesuffix(".json")
    from .runner import protocol_exists
    if verify and protocol_exists(settings, verify):
        store.add_plan(title=f"Verify fix: {plan['title'][:60]}", why=f"Engineer changed {', '.join(merged.get('files', [])[:3])}: {summary}",
                       kind="existing", protocol=verify, build_spec=None, source="engineer", robot=plan.get("robot") or "hexapod1")
    queued = 0
    for f in out.get("followups") or []:
        if isinstance(f, dict) and f.get("title") and f.get("fix_spec"):
            store.add_plan(title=str(f["title"])[:120], why=str(f.get("why") or "")[:600], kind="needs_fix",
                           protocol=None, build_spec=str(f["fix_spec"])[:1200], source="engineer",
                           robot=plan.get("robot") or "hexapod1")
            queued += 1
    store.set_plan_status(pid, "done", f"merged {merged.get('stat', '')}; verify {verify or 'none'}; {queued} followups")
    store.add_event("engineer", f"{plan['title']}: merged ({merged.get('stat', '')}). {summary}"[:400])
    return {"ok": True, "cost_usd": res.cost_usd, "verify": verify, "followups": queued, **merged}


def _release_robot(settings: Settings, store: Store, plan: Dict[str, Any]) -> None:
    """The engineer is done with the robot: make sure it is healthy and at rest
    before the loop takes it back; run the recovery ladder if it is not."""
    from . import recovery, robot
    settings.robot_held.unlink(missing_ok=True)
    try:
        fb = robot.health(settings.robot_url, 20.0)
        if recovery.at_rest(fb):
            store.add_event("engineer", f"{plan['title']}: robot released healthy and at rest")
            return
        note = "robot released but not at rest"
    except Exception as exc:  # noqa: BLE001
        note = f"robot released unhealthy: {exc}"
    store.add_event("engineer", f"{plan['title']}: {note}; running recovery")
    rep = recovery.recover(settings, log=lambda m: None)
    store.add_event("recovery", ("recovered after engineer: " if rep["ok"] else "FAILED after engineer: ")
                    + "; ".join(f"{r['rung']}={r['status'][:60]}" for r in rep["rungs"]))
    if not rep["ok"]:
        from . import alerts
        settings.pause_file.write_text("paused: robot not healthy after engineer job\n")
        alerts.text(store, "needs_hand", f"after the engineer job '{plan['title'][:60]}' the robot is not at rest and "
                                         f"recovery failed. Paused; check it, then reply resume.")


def _stills_for(store: Store, plan: Dict[str, Any]) -> List[Path]:
    """Wide-camera stills from the most recent failed run, for the engineer to look at."""
    for r in store.runs(limit=10):
        if r["status"] == "failed" and r.get("run_dir"):
            wide = Path(r["run_dir"]) / "wide"
            if wide.exists():
                frames = sorted(wide.glob("*.jpg"))
                return frames[-4:] + frames[:2]
    return []
