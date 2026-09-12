"""Walk the robot toward the middle of the camera's frame.

The operator (2026-09-11): "look at the robot, if it's helpful move it to the
center ... try to recenter at the end". On hexapod 2 the runs that lost their
measurement were the ones that walked out of frame or under the camera; the
grid session's fix was a goto-centre before every straight run. This is that,
for whichever camera decodes the chassis tag, closed loop on the tag's pixel
position and without any floor calibration:

1. If the tag is within FAR_FRAC of the middle there is nothing to do.
2. Stand, push straight forward for PROBE_S, and read which way the tag moved
   in the image: that is the body's +x in pixels.
3. Aim at the middle: command vx/vy in the body frame from the pixel error
   rotated into body axes, re-measure every STEP_S, re-learn the heading and
   the camera's handedness from each push, stop when within CENTRE_TOL_FRAC.
4. Any guard the walk runner would honour (tag lost, frame edge, tilt, servo
   trip, robot silent) stops the push, and the stop command always goes out.

Nothing here holds the loop: if it cannot recentre it says why and the run
goes ahead where the robot is.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

from .walk import FEEDBACK_LOST_S, J_HZ, SETTLE_S, TILT_ABORT_DEG, Leg, Session

CENTRE_TOL_FRAC = 0.10     # this close to the middle counts as centred
FAR_FRAC = 0.25            # further than this from the middle is worth fixing
PROBE_S = 6.0              # one forward push to learn where the body points in the image
STEP_S = 6.0               # re-measure and re-aim this often
SPEED_MM_S = 30.0
MIN_MOVE_PX = 12.0         # less than this and a push taught us nothing
Vec = Tuple[float, float]


def distance_frac(frac: Optional[Vec]) -> float:
    return math.hypot(frac[0] - 0.5, frac[1] - 0.5) if frac else 0.0


def needs_recentre(frac: Optional[Vec]) -> bool:
    return frac is not None and distance_frac(frac) > FAR_FRAC


def _rot(v: Vec, deg: float) -> Vec:
    """Rotate an image vector (x right, y down) by deg; positive is clockwise as seen in the picture."""
    a = math.radians(deg)
    return (v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a))


def _unit(v: Vec) -> Vec:
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n) if n else (0.0, 0.0)


def aim(err_px: Vec, fwd: Vec, chirality: float) -> Tuple[float, float]:
    """Body-frame vx (forward) and vy (right) that move the tag along err_px.

    ``fwd`` is body +x in image pixels; body +y (the robot's right, clockwise
    from forward seen from above) is fwd turned 90 deg clockwise in a picture
    taken from above, or counter-clockwise if the camera image is mirrored
    (chirality -1), which the pushes detect."""
    right = _rot(fwd, 90.0 * chirality)
    e = _unit(err_px)
    vx = SPEED_MM_S * (e[0] * fwd[0] + e[1] * fwd[1])
    vy = SPEED_MM_S * (e[0] * right[0] + e[1] * right[1])
    return round(vx, 1), round(vy, 1)


def drive(s: Session, leg: Leg, seconds: float) -> Optional[str]:
    """Stream one command for ``seconds``; the reason if a guard stopped it early. Always sends stop."""
    t0 = s.clock()
    next_tick, last_pose_at, last_fb_at, last_fb_ok = t0, -1e9, -1e9, t0
    reason: Optional[str] = None
    last_dist: Optional[float] = None
    try:
        while s.clock() - t0 < seconds:
            now = s.clock()
            if now >= next_tick:
                try:
                    r = s.post(f"{s.robot}/cmd", raw=leg.command().encode())
                    if isinstance(r, str) and "refused" in r.lower():
                        return f"gait refused: {r[:80]}"
                except Exception as exc:  # noqa: BLE001
                    if now - last_fb_ok > FEEDBACK_LOST_S:
                        return f"robot not answering: {exc}"
                next_tick += 1.0 / J_HZ
            if now - last_pose_at >= 0.2:
                last_pose_at = now
                frac = s.pixel()
                if frac is None:
                    return "tag lost"
                dist = distance_frac(frac)
                # Near the edge and getting further from the middle: stop. Near the
                # edge but coming back in is exactly what a recentre push does.
                if s.near_edge(frac) and last_dist is not None and dist > last_dist + 1e-4:
                    return "frame edge"
                last_dist = dist
            if now - last_fb_at >= 0.3:
                last_fb_at = now
                fb = s.feedback()
                if fb is None:
                    if now - last_fb_ok > FEEDBACK_LOST_S:
                        return "robot feedback silent"
                else:
                    last_fb_ok = now
                    roll, pitch = fb.get("roll_deg"), fb.get("pitch_deg")
                    if roll is not None and pitch is not None and math.hypot(float(roll), float(pitch)) > TILT_ABORT_DEG:
                        return f"tilt {math.hypot(float(roll), float(pitch)):.0f} deg"
                    if (fb.get("servo") or {}).get("tripped"):
                        return "servo tripped"
            s.sleep(0.01)
    finally:
        s.stop(leg)
    return reason


def recentre(s: Session, *, budget_s: float = 90.0, gait: int = 1, label: str = "recentre") -> Dict[str, Any]:
    """Bring the chassis tag toward the middle of the frame. Leaves the robot standing."""
    out: Dict[str, Any] = {"moved": False, "done": False, "reason": "", "start": None, "end": None,
                           "seconds": 0.0, "pushes": 0, "heading_px": None, "chirality": 1}
    frac = s.pixel()
    out["start"] = [round(v, 3) for v in frac] if frac else None
    if frac is None:
        out["reason"] = "tag not visible"
        return out
    if not needs_recentre(frac):
        out.update(done=True, reason=f"already near the middle ({distance_frac(frac):.2f} of the frame off centre)")
        return out
    if not s.stand():
        out["reason"] = "could not stand: " + "; ".join(s.notes[-2:])
        return out
    t0 = s.clock()
    fwd: Optional[Vec] = None
    chir = 1.0
    probe_sign = 1.0            # the probe pushes forward; backward if forward met the frame edge
    edge_stops = 0
    while s.clock() - t0 < budget_s:
        frac = s.pixel()
        if frac is None:
            out["reason"] = "tag lost"
            break
        if distance_frac(frac) <= CENTRE_TOL_FRAC:
            out.update(done=True, reason="centred")
            break
        w, h = s.frame_size or (1280, 720)
        err = ((0.5 - frac[0]) * w, (0.5 - frac[1]) * h)          # tag -> middle, pixels
        remaining = budget_s - (s.clock() - t0)
        if fwd is None:
            leg = Leg(f"{label}_probe", probe_sign * SPEED_MM_S, 0.0, 0.0, min(PROBE_S, remaining), gait)
        else:
            vx, vy = aim(err, fwd, chir)
            leg = Leg(label, vx, vy, 0.0, min(STEP_S, remaining), gait)
        before = frac
        stop = drive(s, leg, leg.seconds)
        out["pushes"] += 1
        out["moved"] = True
        s.sleep(SETTLE_S)
        if stop and stop != "frame edge":
            out["reason"] = stop
            break
        if stop == "frame edge":
            edge_stops += 1
            if fwd is None and probe_sign > 0:
                # Forward took it toward the edge: the way in is the other way. One more probe.
                probe_sign = -1.0
                s.notes.append(f"{label}: forward probe met the frame edge; probing backward")
                continue
            if edge_stops >= 2:
                out["reason"] = stop
                break
        else:
            edge_stops = 0
        after = s.pixel()
        if after is None:
            out["reason"] = "tag lost"
            break
        d = ((after[0] - before[0]) * w, (after[1] - before[1]) * h)
        if math.hypot(*d) < MIN_MOVE_PX:
            if fwd is None:
                out["reason"] = "robot did not move on the probe"
                break
            continue
        cmd_deg = math.degrees(math.atan2(leg.vy, leg.vx))       # commanded direction, clockwise from body +x
        if fwd is not None and abs(leg.vy) > 5.0:
            # Which handedness explains the push better? The predicted image direction of the
            # command is body +x turned by cmd_deg clockwise (chirality +1) or counter-clockwise (-1).
            du = _unit(d)
            fit = {c: sum(a * b for a, b in zip(_rot(fwd, c * cmd_deg), du)) for c in (1.0, -1.0)}
            if fit[-chir] > fit[chir] + 0.2:
                chir = -chir
                s.notes.append(f"{label}: camera image looks mirrored; using the other handedness")
        fwd = _rot(_unit(d), -chir * cmd_deg)
    else:
        out["reason"] = f"budget of {budget_s:.0f} s used"
    end = s.pixel()
    out["end"] = [round(v, 3) for v in end] if end else None
    out["seconds"] = round(s.clock() - t0, 1)
    out["heading_px"] = [round(v, 3) for v in fwd] if fwd else None
    out["chirality"] = int(chir)
    if out["done"] and out["moved"]:
        out["reason"] = f"centred after {out['pushes']} pushes"
    return out
