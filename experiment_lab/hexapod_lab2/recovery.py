"""When a run trips on a joint, let the robot free itself before trying again.

The robot already contains the recovery moves; the lab only orders them:

  0. POST /api/standup {"mode":"step","direction":"down"} if the robot is
                                     standing (median hip > 5, knee > 12,
                                     tilt < 20): step down first. The zero
                                     blend below straightens loaded legs and
                                     drops a standing chassis onto its belly
                                     (nine times on hexapod 2, 2026-09-11).
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
from pathlib import Path
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


def trip_line(log_tail: str) -> str:
    """The runner's own error sentence, not whatever line happened to be last
    (the dataset path is printed after the error)."""
    m = re.search(r"runner: ok=False error=([^\n]+)", log_tail or "")
    if m:
        return m.group(1).strip()[:200]
    m = JAM_PATTERN.search(log_tail or "")
    if m:
        line = (log_tail or "")[max(0, m.start() - 40):m.end() + 120].splitlines()
        return (line[0] if len(line) == 1 else next((l for l in line if m.group(0) in l), line[0])).strip()[:200]
    lines = (log_tail or "").strip().splitlines()
    return lines[-1][-160:] if lines else "joint trip"


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


def _fetch_bytes(url: str) -> bytes:
    with urlopen(url, timeout=10) as resp:
        return resp.read()


def pose_digest(fb: Dict[str, Any]) -> Dict[str, Any]:
    """The part of a feedback snapshot a reader (or the planner) needs."""
    joints = fb.get("joints") or []
    if len(joints) < 18:
        return {"ok": False}
    deg = [round(float(j.get("deg") or 0), 1) for j in joints]
    return {
        "ok": bool(fb.get("ok")),
        "roll_deg": fb.get("roll_deg"), "pitch_deg": fb.get("pitch_deg"),
        "knees_deg": [deg[i] for i in KNEE_JOINTS],
        "hips_deg": [deg[i] for i in (1, 4, 7, 10, 13, 16)],
        "yaws_deg": [deg[i] for i in (0, 3, 6, 9, 12, 15)],
        "peak_current_a": max(float(j.get("cur_a") or 0) for j in joints),
        "max_temp_c": max(float(j.get("temp_c") or 0) for j in joints),
    }


class Recorder:
    """Writes what a recovery saw into a run folder: feedback JSON and a
    camera still at each step. Every recovery is an unplanned experiment
    and gets kept like one."""

    def __init__(self, run_dir: Optional[Path], frame_url: str, *, get=_get, fetch=_fetch_bytes):
        self.run_dir, self.frame_url, self.get, self.fetch = run_dir, frame_url, get, fetch

    def snapshot(self, robot_url: str, tag: str) -> Dict[str, Any]:
        try:
            fb = self.get(f"{robot_url}/api/feedback")
        except Exception as exc:  # noqa: BLE001
            fb = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        if self.run_dir is not None:
            self.run_dir.mkdir(parents=True, exist_ok=True)
            (self.run_dir / f"{tag}_feedback.json").write_text(json.dumps(fb, indent=1))
            try:
                (self.run_dir / f"{tag}.jpg").write_bytes(self.fetch(self.frame_url))
            except Exception:  # noqa: BLE001 - a missing still is not a failed recovery
                pass
        return fb


def upright(fb: Optional[Dict[str, Any]], *, hip_deg: float = 5.0, knee_deg: float = 12.0,
            tilt_deg: float = 20.0) -> bool:
    """The demos classifier's shape gate, read from /api/feedback: a robot with its
    hips and knees bent and the body level is standing on its legs."""
    joints = (fb or {}).get("joints") or []
    if len(joints) != 18:
        return False
    try:
        hips = sorted(float(joints[j]["deg"]) for j in range(1, 18, 3))
        knees = sorted(float(joints[j]["deg"]) for j in range(2, 18, 3))
        roll, pitch = float(fb.get("roll_deg") or 0.0), float(fb.get("pitch_deg") or 0.0)
    except (KeyError, TypeError, ValueError):
        return False
    med = lambda v: 0.5 * (v[2] + v[3])  # noqa: E731
    return med(hips) > hip_deg and med(knees) > knee_deg and (roll ** 2 + pitch ** 2) ** 0.5 < tilt_deg


def at_rest(fb: Dict[str, Any], *, knee_tol_deg: float = 20.0, tilt_deg: float = 8.0) -> bool:
    joints = fb.get("joints") or []
    if len(joints) < 18 or not fb.get("ok"):
        return False
    knees_ok = all(abs(float(joints[i].get("deg") or 0)) <= knee_tol_deg for i in KNEE_JOINTS)
    tilt_ok = max(abs(float(fb.get("roll_deg") or 0)), abs(float(fb.get("pitch_deg") or 0))) <= tilt_deg
    return knees_ok and tilt_ok


def recover(settings: Settings, *, log: Callable[[str], None] = print, post=_post, get=_get,
            sleep=time.sleep, run_dir: Optional[Path] = None, fetch=_fetch_bytes) -> Dict[str, Any]:
    """Run the ladder and record it. Returns {"ok", "rungs", "final", "before", "after"}."""
    url = settings.robot_url.rstrip("/")
    rec = Recorder(run_dir, settings.vision_frame_url, get=get, fetch=fetch)
    rungs = [("zero", "/api/zero", {"pose": "sit"}),
             ("untrap", "/api/untrap", {"force": True}),
             ("zero", "/api/zero", {"pose": "sit"})]
    before = rec.snapshot(url, "00_before")
    if upright(before):
        # Standing: step down before anything straightens a loaded leg.
        rungs.insert(0, ("step_down", "/api/standup", {"mode": "step", "direction": "down"}))
        log("recovery: robot is standing; stepping down before the zero blend")
    report: Dict[str, Any] = {"ok": False, "rungs": [], "final": "",
                              "before": pose_digest(before), "after": None}
    for i, (name, path, body) in enumerate(rungs):
        if i:
            sleep(SETTLE_S)
        started = time.monotonic()
        try:
            accepted = post(f"{url}{path}", body)
            status = wait_for_idle(url, get=get, sleep=sleep) if accepted.get("ok") else str(accepted.get("error"))
        except Exception as exc:  # noqa: BLE001 - robot unreachable mid-recovery is a failed rung
            status = f"{type(exc).__name__}: {exc}"
        fb = rec.snapshot(url, f"{i + 1:02d}_after_{name}")
        ok = at_rest(fb) and not status.lower().startswith("error")
        report["rungs"].append({"rung": name, "request": body, "status": status[:200], "ok": ok,
                                "seconds": round(time.monotonic() - started, 1), "pose": pose_digest(fb)})
        log(f"recovery {name}: {'ok' if ok else 'not yet'} — {status[:120]}")
        if ok:
            report["ok"], report["final"], report["after"] = True, status, pose_digest(fb)
            return report
    report["final"] = report["rungs"][-1]["status"] if report["rungs"] else ""
    report["after"] = report["rungs"][-1]["pose"] if report["rungs"] else None
    return report
