"""One health read with a hard wall clock. This is the whole preflight."""
from __future__ import annotations

import json
import time
from typing import Any, Dict
from urllib.request import urlopen


class RobotUnreachable(Exception):
    pass


class RobotNotReady(Exception):
    pass


def health(robot_url: str, budget_s: float = 10.0, *, max_temp_c: float = 60.0,
           max_tilt_deg: float = 25.0) -> Dict[str, Any]:
    """Return /api/feedback if the robot can move, else raise.

    Ten seconds is the operator's rule. The in-loop trips do the protecting;
    this only stops us launching a runner at a robot that is off, has a servo
    missing, is already hot, or has fallen over.
    """
    started = time.monotonic()
    try:
        with urlopen(f"{robot_url.rstrip('/')}/api/feedback", timeout=budget_s) as resp:
            fb = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - any transport failure is "unreachable"
        raise RobotUnreachable(f"{type(exc).__name__}: {exc}") from exc
    return assess(fb, elapsed_s=time.monotonic() - started, budget_s=budget_s,
                  max_temp_c=max_temp_c, max_tilt_deg=max_tilt_deg)


def assess(fb: Dict[str, Any], *, elapsed_s: float, budget_s: float,
           max_temp_c: float = 60.0, max_tilt_deg: float = 25.0) -> Dict[str, Any]:
    if elapsed_s > budget_s:
        raise RobotUnreachable(f"feedback took {elapsed_s:.1f} s, budget {budget_s:.0f} s")
    if not fb.get("ok"):
        raise RobotNotReady(f"feedback not ok: {fb.get('error') or fb}")
    live = int(fb.get("live") or 0)
    if live < 18:
        raise RobotNotReady(f"{live}/18 servos live")
    joints = fb.get("joints") or []
    temps = [float(j.get("temp_c") or 0) for j in joints if isinstance(j, dict)]
    if temps and max(temps) > max_temp_c:
        raise RobotNotReady(f"servo at {max(temps):.0f} C, limit {max_temp_c:.0f} C")
    roll = abs(float(fb.get("roll_deg") or 0))
    pitch = abs(float(fb.get("pitch_deg") or 0))
    if max(roll, pitch) > max_tilt_deg:
        raise RobotNotReady(f"tilt roll {roll:.0f} pitch {pitch:.0f} deg, limit {max_tilt_deg:.0f}")
    return fb
