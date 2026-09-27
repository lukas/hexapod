"""Measured mechanical stops of the real legs -- the joint envelope every commanded
pose has to respect, in ONE place (2026-09-27).

The servo limits in ``motor_setup.feetech_bus.AXIS_LIMITS_DEG`` (hip -80..40, knee
hinge -20..150) are what the ENCODER can express; the leg stops earlier: on hexapod2
the femur meets the top chassis near hip -55 and the knee hinge stalls near 126-136
(measured 2026-09-22 during the reversed STEP, 2026-09-27 as an over_load trip of the
teacher-free RL walker at hinge 135.6 deg / 2.6 A).  Commanding past a stop is a fight
against plastic (8.2 A summed on 09-22), and in the sim it is a range the MJCF model
(knee range 2.62 rad = 150 deg) happily allows -- so a policy trained without this
envelope learns to use it and stalls on the robot.

Frames: hip is the same in every frame; the knee stop is a HINGE angle (tibia relative
to femur).  ``clip_robot_abs`` takes/returns robot_abs poses (absolute tibia), the
contract everything above the servo boundary speaks, and converts internally.

Consumers: rl_move.safety.SafetyLayer (sim training AND the robot runtime -- the one
pathway), linux_control/api/standup.py (fold caps for the STEP frames).
"""
from __future__ import annotations

import math

# hostname -> (hip min deg, knee hinge max deg).  Tightest known robot is the default
# for anyone who does not know which robot they will run on (a policy has to fit all).
MEASURED_STOPS: dict[str, tuple[float, float]] = {
    "hexapod2": (-52.0, 125.0),
}
DEFAULT_HIP_MIN_DEG, DEFAULT_KNEE_HINGE_MAX_DEG = MEASURED_STOPS["hexapod2"]
# The servo's own expressible range (feetech_bus.AXIS_LIMITS_DEG) -- the legacy caps.
SERVO_HIP_MIN_DEG, SERVO_KNEE_HINGE_MIN_DEG, SERVO_KNEE_HINGE_MAX_DEG = -80.0, -20.0, 150.0


def stops_for(host: str | None) -> tuple[float, float]:
    """(hip min deg, knee hinge max deg) for a robot hostname; robots without a
    measurement keep the servo range (their frames were baked against it)."""
    key = (host or "").split(".")[0]
    return MEASURED_STOPS.get(key, (SERVO_HIP_MIN_DEG, SERVO_KNEE_HINGE_MAX_DEG))


def tightest(*pairs: tuple[float, float] | None) -> tuple[float, float]:
    """Combine envelopes: the highest hip minimum and the lowest knee hinge maximum win."""
    hip_min, hinge_max = SERVO_HIP_MIN_DEG, SERVO_KNEE_HINGE_MAX_DEG
    for p in pairs:
        if p is None:
            continue
        hip_min = max(hip_min, float(p[0]))
        hinge_max = min(hinge_max, float(p[1]))
    return hip_min, hinge_max


def clip_robot_abs(q, hip_min_deg: float, knee_hinge_max_deg: float, *,
                   knee_hinge_min_deg: float = SERVO_KNEE_HINGE_MIN_DEG,
                   radians: bool = False):
    """Clip an 18-vector robot_abs pose ([yaw, hip, knee_abs] x 6) to the envelope:
    hip >= hip_min, knee hinge (= knee_abs - hip) within [hinge_min, hinge_max].
    Works on lists or numpy arrays; returns the same kind.  ``radians`` selects the unit
    of both q and the result (the limits are always degrees)."""
    import numpy as np
    arr = np.array(q, dtype=float)
    scale = math.pi / 180.0 if radians else 1.0
    hip_min = hip_min_deg * scale
    h_lo, h_hi = knee_hinge_min_deg * scale, knee_hinge_max_deg * scale
    hips = np.maximum(arr[1::3], hip_min)
    hinge = np.clip(arr[2::3] - hips, h_lo, h_hi)
    arr[1::3] = hips
    arr[2::3] = hips + hinge
    return arr if isinstance(q, np.ndarray) else arr.tolist()
