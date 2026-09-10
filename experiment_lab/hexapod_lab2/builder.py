"""One tool-using subagent per needs_code plan, in its own worktree, 30 minutes max."""
from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from . import claude_cli
from .config import Settings
from .gitlock import GIT_LOCK
from .runner import protocol_exists, sync_checkout
from .store import Store

BUILD_SCHEMA = {
    "type": "object",
    "properties": {
        "built": {"type": "boolean"},
        "protocol": {"type": "string", "description": "Protocol file name without .json that is now on origin/main."},
        "summary": {"type": "string", "description": "Under 80 words: what was created and how it was checked."},
    },
    "required": ["built", "summary"],
}


def _prompt(settings: Settings, plan: Dict[str, Any]) -> str:
    return f"""You are building one sysid protocol file for a cheap 18-servo hexapod so the lab loop can run it. Hard limits: 30 minutes wall clock, ${settings.builder_max_usd:.0f}. Work only inside this checkout.

PLAN: {plan['title']}
WHY: {plan['why']}
BUILD SPEC: {plan['build_spec']}

How:
1. Look at hexapod_walker/prototype_sts3215/sysid/protocols/ for the closest existing protocol and hexapod_walker/prototype_sts3215/sysid/generate_leg_variant.py (--leg N remaps a protocol to another leg). Reuse; do not invent new motion shapes unless the spec asks.
2. Create the file. Validate it with a dry run, which moves nothing:
   cd hexapod_walker/prototype_sts3215 && ../../.venv/bin/python -m sysid.run_hw --protocol sysid/protocols/<name>.json
3. If the dry run passes, commit only that file (plus generator changes if you had to make them) and push to origin main:
   git add <files> && git commit -m "Add <name> sysid protocol" && git push origin HEAD:main
4. Report built=true with the protocol name.

Do not add safety checks, preflight steps, audits or tests. Do not touch anything outside sysid/. Do not run the robot (never pass --go). If the spec does not make sense or would need new motion you cannot validate, report built=false and say why in one sentence."""


def _prepare_worktree(settings: Settings, plan_id: str, *, subdir: str = "build") -> Path:
    wt = settings.data_dir / subdir / plan_id / "worktree"
    with GIT_LOCK:
        if wt.exists():
            subprocess.run(["git", "-C", str(settings.checkout), "worktree", "remove", "--force", str(wt)],
                           capture_output=True, text=True)
        wt.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "-C", str(settings.checkout), "fetch", "-q", "origin", "main"],
                       check=True, capture_output=True, text=True, timeout=120)
        subprocess.run(["git", "-C", str(settings.checkout), "worktree", "add", "--detach", str(wt), "origin/main"],
                       check=True, capture_output=True, text=True, timeout=120)
    # The dry run needs the repo venv; a worktree does not have one. Share it.
    venv = wt / ".venv"
    if not venv.exists():
        venv.symlink_to(settings.checkout / ".venv")
    return wt


def _cleanup_worktree(settings: Settings, wt: Path) -> None:
    with GIT_LOCK:
        subprocess.run(["git", "-C", str(settings.checkout), "worktree", "remove", "--force", str(wt)],
                       capture_output=True, text=True)


def build_plan(settings: Settings, store: Store, plan: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous build of one plan. Flips it to queued/existing on success."""
    pid = plan["id"]
    log_path = settings.data_dir / "build" / pid / "builder.log"
    try:
        wt = _prepare_worktree(settings, pid)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        msg = f"worktree failed: {getattr(exc, 'stderr', '') or exc}"[:300]
        store.set_plan_status(pid, "failed", msg)
        store.add_event("builder", f"{plan['title']}: {msg}")
        return {"ok": False, "error": msg}
    res = claude_cli.build(settings.claude_bin, _prompt(settings, plan), BUILD_SCHEMA,
                           workdir=wt, model=settings.builder_model,
                           max_usd=settings.builder_max_usd, timeout_s=settings.builder_budget_s,
                           log_path=log_path)
    if res.cost_usd:
        store.add_spend("builder", res.cost_usd, plan["title"])
    _cleanup_worktree(settings, wt)
    if not res.ok:
        store.set_plan_status(pid, "failed", f"builder: {res.error}"[:300])
        store.add_event("builder", f"{plan['title']}: builder failed: {res.error}"[:400])
        return {"ok": False, "error": res.error, "cost_usd": res.cost_usd}
    out = res.output or {}
    protocol = str(out.get("protocol") or "").strip().removesuffix(".json")
    summary = " ".join(str(out.get("summary") or "").split())[:400]
    sync_checkout(settings)
    if out.get("built") and protocol and protocol_exists(settings, protocol):
        store.mark_built(pid, protocol)
        store.add_event("builder", f"{plan['title']}: built {protocol}. {summary}")
        return {"ok": True, "protocol": protocol, "cost_usd": res.cost_usd}
    reason = summary or "builder reported built=false"
    if out.get("built") and protocol:
        reason = f"builder says it pushed {protocol} but it is not on origin/main after pull. {summary}"
    store.set_plan_status(pid, "failed", reason[:300])
    store.add_event("builder", f"{plan['title']}: not built. {reason}"[:400])
    return {"ok": False, "error": reason, "cost_usd": res.cost_usd}


class BuilderThread:
    """At most one build at a time, off the main loop."""

    def __init__(self, settings: Settings, store: Store):
        self.settings, self.store = settings, store
        self._thread: Optional[threading.Thread] = None
        self.current: Optional[str] = None

    def busy(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def maybe_start(self) -> Optional[str]:
        """One code job at a time. Fixes (needs_fix) go ahead of builds: a fix
        unblocks runs that are already queued, a build only adds one."""
        if self.busy():
            return None
        pending = [p for p in self.store.building_plans() if p.get("status_note") != "builder running"]
        if not pending:
            return None
        fixes = [p for p in pending if p.get("kind") == "needs_fix"]
        plan = (fixes or pending)[-1]  # oldest first (plans() is newest-first)
        self.store.set_plan_status(plan["id"], "building", "builder running")
        self.current = plan["id"]
        # A sqlite3 connection is not shareable across threads; the build
        # thread opens its own handle on the same database.
        thread_store = Store(self.store.path)
        if plan.get("kind") == "needs_fix":
            from .engineer import fix_plan
            target, name = fix_plan, f"engineer-{plan['id']}"
        else:
            target, name = build_plan, f"builder-{plan['id']}"
        self._thread = threading.Thread(target=target, args=(self.settings, thread_store, plan),
                                        name=name, daemon=True)
        self._thread.start()
        return plan["id"]
