"""Double-check a zero pose that might only look like zero to the encoders.

The operator (2026-09-11): "if the robot is supposedly in zero pose and it
looks wildly off double check what's going on". The runner's own start-pose
check reads encoders on the servo output shafts, so a horn whose screws have
slipped passes it. The camera cannot be fooled: hexapod-zero-check (in the
tracker) re-derives each leg's azimuth from its lid tags in the top camera
and compares it with the installed layout.

Four outcomes, and only one of them holds the loop:

  agree             encoders at zero, camera agrees: run.
  camera_disagrees  encoders at zero, camera says a leg points elsewhere:
                    slipped horn or wrong logical zero. Hold, keep the frame,
                    say which leg. The one place the lab refuses rather than
                    corrects.
  not_at_zero       encoders are not at zero, so the lid check means nothing
                    yet; the runner glides to its start pose anyway. Noted.
  blind             the camera could not measure (no frame, no plane, tracker
                    error). Run, and say the check was blind.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlsplit

from .config import Settings

ENCODER_ZERO_TOL_DEG = 8.0


def encoders(fb: Optional[Dict[str, Any]], *, tol_deg: float = ENCODER_ZERO_TOL_DEG) -> Dict[str, Any]:
    """Are the 18 encoders within tol of the logical zero pose?"""
    joints = (fb or {}).get("joints") or []
    degs = [float(j["deg"]) for j in joints if isinstance(j, dict) and j.get("deg") is not None]
    if len(degs) != 18:
        return {"at_zero": False, "known": False, "worst_deg": None, "worst_joint": None}
    worst = max(range(18), key=lambda j: abs(degs[j]))
    return {"at_zero": abs(degs[worst]) <= tol_deg, "known": True,
            "worst_deg": round(degs[worst], 1), "worst_joint": worst}


def camera(settings: Settings, out_dir: Optional[Path], *, run: Callable = subprocess.run,
           top_camera: Optional[int] = None) -> Dict[str, Any]:
    """Run hexapod-zero-check once; its JSON, or {"error": ...}."""
    u = urlsplit(settings.wide_frame_url)
    top = settings.top_camera if top_camera is None else top_camera
    cmd = ["uv", "run", "hexapod-zero-check", "--json", "--top-camera", str(top),
           "--camera-url", f"{u.scheme}://{u.netloc}"]
    if out_dir is not None:
        cmd += ["--out", str(out_dir)]
    try:
        proc = run(cmd, cwd=str(settings.tracker_checkout), capture_output=True, text=True,
                   timeout=settings.zero_check_budget_s)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"hexapod-zero-check took longer than {settings.zero_check_budget_s:.0f} s"}
    except OSError as exc:
        return {"ok": False, "error": f"could not start hexapod-zero-check: {exc}"}
    line = (proc.stdout or "").strip().splitlines()
    try:
        doc = json.loads(line[-1]) if line else {}
    except ValueError:
        doc = {}
    if not isinstance(doc, dict) or not doc:
        return {"ok": False, "error": f"hexapod-zero-check exit {proc.returncode}: {(proc.stderr or proc.stdout or '')[-300:]}"}
    return doc


_real_camera = camera   # tests replace ``camera``; this keeps the subprocess wrapper reachable


def double_check(settings: Settings, fb: Optional[Dict[str, Any]], out_dir: Optional[Path], *,
                 run: Callable = subprocess.run, log: Callable[[str], None] = print) -> Dict[str, Any]:
    """The 2x2 of encoders and camera. Returns {"verdict", "text", "legs_off", "frame", "camera", "encoders"}."""
    enc = encoders(fb)
    out: Dict[str, Any] = {"encoders": enc, "legs_off": [], "frame": None, "camera": None}
    if not enc["known"]:
        out.update(verdict="blind", text="feedback did not return 18 joints; zero check skipped")
        log("zero check: " + out["text"])
        return out
    if not enc["at_zero"]:
        out.update(verdict="not_at_zero",
                   text=f"encoders not at zero (joint {enc['worst_joint']} at {enc['worst_deg']:+.1f} deg); "
                        f"lid check skipped, the runner glides to its start pose")
        log("zero check: " + out["text"])
        return out
    cam = camera(settings, out_dir, run=run)
    out["camera"] = {k: cam.get(k) for k in ("ok", "off", "unseen", "error", "warning", "summary", "chassis_tag_seen")}
    out["frame"] = cam.get("frame")
    legs = cam.get("legs") or {}
    if cam.get("error") or not legs:
        out.update(verdict="blind", text=f"camera could not check the zero pose: {cam.get('error') or 'no legs seen'}")
    elif cam.get("off"):
        out["legs_off"] = [int(l) for l in cam["off"]]
        detail = "; ".join(f"leg {l}: camera {legs[str(l)]['azimuth_deg']} deg, layout {legs[str(l)]['expected_deg']} deg "
                           f"({legs[str(l)]['residual_deg']:+.0f})" for l in out["legs_off"] if str(l) in legs)
        out.update(verdict="camera_disagrees",
                   text=f"encoders say zero but the camera says leg{'s' if len(out['legs_off']) > 1 else ''} "
                        f"{out['legs_off']} point elsewhere: {detail}. Slipped horn or wrong logical zero; not moving it.")
    else:
        unseen = cam.get("unseen") or []
        out.update(verdict="agree", text="encoders at zero and the camera agrees with the layout"
                   + (f" (legs {unseen} not seen)" if unseen else ""))
    log("zero check: " + out["text"])
    return out
