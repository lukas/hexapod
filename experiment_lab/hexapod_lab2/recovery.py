"""When a run trips on a joint, let the robot free itself before trying again.

The robot already contains the recovery moves; the lab only orders them:

  1. POST /api/zero {"pose":"sit"}   collision-aware safe-zero glide back to
                                     belly-down, legs straight out. Limps
                                     itself on any stall or surprise force.
  2. POST /api/untrap {"force":true} the 20 %-torque fold that collapses
                                     whatever is propping the chassis on a
                                     folded knee. Forced because the robot's
                                     own detector only classifies a tip of
                                     12° or more, and a knee pinned under a
                                     level body (the 2026-09-10 jam) sits at
                                     0–5°. Safe by construction: at 20 %
                                     torque a stalled servo cannot heat.
  3. POST /api/zero {"pose":"sit"}   once more after the fold.

Each rung runs exactly once with a 30 s settle between rungs. The robot's
docstring says untrap is "never retried, torque never escalated"; the lab
does not override that. If the ladder fails the loop pauses and texts.

Proven live 2026-09-10 2:31 PM: rung 1 alone freed a knee at 120° pinned
under the body after three runs had tripped on it.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Callable, Dict, Optional
from urllib.request import Request, urlopen

from .config import Settings

JAM_PATTERN = re.compile(
    r"joint \d+( \(ID \d+\))? (overcurrent|tracking error|off by|missed)|start pose did not verify|bus write failed",
    re.I,
)
SETTLE_S = 30.0
MOVE_TIMEOUT_S = 150.0
KNEE_JOINTS = (2, 5, 8, 11, 14, 17)


def looks_like_jam(log_tail: str) -> bool:
    return bool(JAM_PATTERN.search(log_tail or ""))


def _post(url: str, body: Dict[str, Any]) -> Dict[str, Any]:
    req = Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _get(url: str) -> Dict[str, Any]:
    with urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode())


def wait_for_idle(robot_url: str, *, get=_get, sleep=time.sleep, timeout_s: float = MOVE_TIMEOUT_S) -> str:
    """Poll until the robot's demo worker stops; return its final status text."""
    deadline = time.monotonic() + timeout_s
    status = ""
    while time.monotonic() < deadline:
        demo = (get(f"{robot_url}/api/rl/state").get("pose") or {}).get("demo") or {}
        status = str(demo.get("status") or "")
        if not demo.get("running"):
            return status
        sleep(3)
    return status or "timeout"


def at_rest(fb: Dict[str, Any], *, knee_tol_deg: float = 20.0, tilt_deg: float = 8.0) -> bool:
    joints = fb.get("joints") or []
    if len(joints) < 18 or not fb.get("ok"):
        return False
    knees_ok = all(abs(float(joints[i].get("deg") or 0)) <= knee_tol_deg for i in KNEE_JOINTS)
    tilt_ok = max(abs(float(fb.get("roll_deg") or 0)), abs(float(fb.get("pitch_deg") or 0))) <= tilt_deg
    return knees_ok and tilt_ok


def recover(settings: Settings, *, log: Callable[[str], None] = print, post=_post, get=_get,
            sleep=time.sleep) -> Dict[str, Any]:
    """Run the ladder. Returns {"ok": bool, "rungs": [...], "final": status}."""
    url = settings.robot_url.rstrip("/")
    rungs = [("zero", "/api/zero", {"pose": "sit"}),
             ("untrap", "/api/untrap", {"force": True}),
             ("zero", "/api/zero", {"pose": "sit"})]
    report: Dict[str, Any] = {"ok": False, "rungs": [], "final": ""}
    for i, (name, path, body) in enumerate(rungs):
        if i:
            sleep(SETTLE_S)
        try:
            accepted = post(f"{url}{path}", body)
            status = wait_for_idle(url, get=get, sleep=sleep) if accepted.get("ok") else str(accepted.get("error"))
            fb = get(f"{url}/api/feedback")
        except Exception as exc:  # noqa: BLE001 - robot unreachable mid-recovery is a failed rung
            status, fb = f"{type(exc).__name__}: {exc}", {}
        ok = at_rest(fb) and not status.lower().startswith("error")
        report["rungs"].append({"rung": name, "status": status[:200], "ok": ok})
        log(f"recovery {name}: {'ok' if ok else 'not yet'} — {status[:120]}")
        if ok:
            report["ok"], report["final"] = True, status
            return report
    report["final"] = report["rungs"][-1]["status"] if report["rungs"] else ""
    return report
