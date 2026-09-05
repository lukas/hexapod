"""Command arrows shared by every interactive MuJoCo render path.

The policy command is expressed in the robot body frame (``+x`` forward,
``+y`` left).  The helpers below rotate it into the world frame and add
decorative-only geoms to an existing MuJoCo scene:

* a green arrow on the ground for planar joystick motion;
* an amber curved arrow on the ground for a yaw command; and
* a blue vertical arrow beside the robot while rising or lowering.

The geoms live only in ``MjvScene`` and therefore cannot collide with or
otherwise affect the simulation.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np


LINEAR_EPS_MPS = 1e-3
TURN_EPS_RAD_S = 1e-3
HEIGHT_EPS_M = 1e-3
GROUND_Z_M = 0.018

_LINEAR_RGBA = (0.10, 0.95, 0.20, 1.0)
_TURN_RGBA = (1.00, 0.55, 0.05, 1.0)
_HEIGHT_RGBA = (0.10, 0.65, 1.00, 1.0)
_RISE_MODES = {"rise", "recover", "stand", "standup", "up"}
_LOWER_MODES = {"lower", "fold", "sit", "down"}


@dataclass(frozen=True)
class CommandCue:
    """The command channels that have a visual meaning."""

    mode: str = ""
    vx: float = 0.0
    vy: float = 0.0
    wz: float = 0.0


@dataclass(frozen=True)
class IndicatorSegment:
    """One decorative MuJoCo connector geom."""

    kind: str
    start: np.ndarray
    end: np.ndarray
    width: float
    rgba: tuple[float, float, float, float]


def _finite_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return 0.0
    return out if math.isfinite(out) else 0.0


def _value_at(value: Any, step: int) -> float | None:
    """Read either a scalar live target or an array trajectory channel."""
    if value is None:
        return None
    try:
        arr = np.asarray(value)
        if arr.ndim == 0:
            return _finite_float(arr.item())
        flat = arr.reshape(-1)
        if not len(flat):
            return None
        i = min(max(int(step), 0), len(flat) - 1)
        return _finite_float(flat[i])
    except (TypeError, ValueError):
        return None


def command_cue_from_env(env: Any, *, mode: str | None = None) -> CommandCue:
    """Extract the command currently shown to an environment's policy.

    Regular training trajectories store command arrays.  The web/player
    trajectory stores scalar joystick targets, so both representations are
    accepted.  ``_current_goal`` is the fallback for custom trajectory types.
    """
    traj = getattr(env, "_goal_traj", None)
    step = int(getattr(env, "_step_i", 0))
    resolved_mode = str(
        mode if mode is not None else getattr(traj, "mode", "")
    ).strip().lower()

    goal = None

    def ref(traj_name: str, goal_name: str) -> float:
        nonlocal goal
        value = _value_at(getattr(traj, traj_name, None), step)
        if value is not None:
            return value
        if goal is None:
            current_goal = getattr(env, "_current_goal", None)
            goal = current_goal() if callable(current_goal) else False
        return _finite_float(getattr(goal, goal_name, 0.0)) if goal else 0.0

    # Interactive stance-policy controls do not change the task mode.  While
    # their published height reference is ramping toward the requested target,
    # derive the same rise/lower cue from that signed delta.
    if resolved_mode not in _RISE_MODES | _LOWER_MODES:
        target = getattr(getattr(traj, "goal", None), "height_ref", None)
        published = getattr(getattr(traj, "_pub", None), "height_ref", None)
        if target is not None and published is not None:
            dh = _finite_float(target) - _finite_float(published)
            if dh > HEIGHT_EPS_M:
                resolved_mode = "rise"
            elif dh < -HEIGHT_EPS_M:
                resolved_mode = "lower"

    return CommandCue(
        mode=resolved_mode,
        vx=ref("vx", "vx_ref"),
        vy=ref("vy", "vy_ref"),
        wz=ref("wz", "wz_ref"),
    )


def indicator_segments(data: Any, chassis_bid: int,
                       cue: CommandCue) -> list[IndicatorSegment]:
    """Build world-frame connector segments for ``cue`` without MuJoCo IO."""
    chassis = np.asarray(data.xpos[chassis_bid], dtype=float)
    rot = np.asarray(data.xmat[chassis_bid], dtype=float).reshape(3, 3)
    out: list[IndicatorSegment] = []

    cmd_body = np.array([cue.vx, cue.vy, 0.0], dtype=float)
    cmd_speed = float(np.linalg.norm(cmd_body[:2]))
    if cmd_speed > LINEAR_EPS_MPS:
        direction = rot @ (cmd_body / cmd_speed)
        direction[2] = 0.0
        norm = float(np.linalg.norm(direction[:2]))
        if norm > 1e-9:
            direction /= norm
            length = 0.16 + 0.10 * min(cmd_speed / 0.10, 1.0)
            start = np.array(
                [chassis[0], chassis[1], GROUND_Z_M], dtype=float
            ) + direction * 0.13
            end = start + direction * length
            out.append(IndicatorSegment(
                "arrow", start, end, 0.014, _LINEAR_RGBA
            ))

    if abs(cue.wz) > TURN_EPS_RAD_S:
        # A long arc is recognizable as rotation from any camera angle.  Its
        # tangent follows +CCW for positive wz and -CW for negative wz.
        yaw = math.atan2(float(rot[1, 0]), float(rot[0, 0]))
        turn_sign = 1.0 if cue.wz > 0.0 else -1.0
        span = 1.5 * math.pi
        start_angle = yaw - turn_sign * 0.75 * math.pi
        angles = start_angle + turn_sign * np.linspace(0.0, span, 15)
        points = [
            np.array([
                chassis[0] + 0.25 * math.cos(float(a)),
                chassis[1] + 0.25 * math.sin(float(a)),
                GROUND_Z_M,
            ], dtype=float)
            for a in angles
        ]
        for i, (start, end) in enumerate(zip(points, points[1:])):
            last = i == len(points) - 2
            out.append(IndicatorSegment(
                "arrow" if last else "capsule",
                start,
                end,
                0.012 if last else 0.005,
                _TURN_RGBA,
            ))

    vertical = (1 if cue.mode in _RISE_MODES
                else -1 if cue.mode in _LOWER_MODES else 0)
    if vertical:
        # Put the height arrow just outside the right-front footprint so it is
        # visible without covering the robot.  The anchor rotates with it.
        side = rot @ np.array([0.14, -0.23, 0.0], dtype=float)
        xy = chassis[:2] + side[:2]
        low = np.array([xy[0], xy[1], 0.025], dtype=float)
        high = np.array([xy[0], xy[1], 0.22], dtype=float)
        out.append(IndicatorSegment(
            "arrow",
            low if vertical > 0 else high,
            high if vertical > 0 else low,
            0.014,
            _HEIGHT_RGBA,
        ))

    return out


def draw_command_indicator(mujoco_mod: Any, scene: Any, data: Any,
                           chassis_bid: int, cue: CommandCue,
                           *, clear: bool = False) -> int:
    """Append command geoms to ``scene`` and return the number added."""
    if scene is None:
        return 0
    if clear:
        scene.ngeom = 0

    type_for = {
        "arrow": mujoco_mod.mjtGeom.mjGEOM_ARROW,
        "capsule": mujoco_mod.mjtGeom.mjGEOM_CAPSULE,
    }
    added = 0
    for segment in indicator_segments(data, chassis_bid, cue):
        if scene.ngeom >= scene.maxgeom:
            break
        geom_type = type_for[segment.kind]
        geom = scene.geoms[scene.ngeom]
        mujoco_mod.mjv_initGeom(
            geom,
            geom_type,
            np.zeros(3, dtype=np.float64),
            np.zeros(3, dtype=np.float64),
            np.eye(3, dtype=np.float64).reshape(-1),
            np.asarray(segment.rgba, dtype=np.float32),
        )
        mujoco_mod.mjv_connector(
            geom,
            geom_type,
            float(segment.width),
            np.asarray(segment.start, dtype=np.float64),
            np.asarray(segment.end, dtype=np.float64),
        )
        geom.category = mujoco_mod.mjtCatBit.mjCAT_DECOR
        scene.ngeom += 1
        added += 1
    return added


def draw_env_command_indicator(env: Any, scene: Any, *,
                               mode: str | None = None,
                               clear: bool = False) -> int:
    """Convenience bridge used by off-screen and passive viewers."""
    return draw_command_indicator(
        env._mujoco,
        scene,
        env.data,
        env._chassis_bid,
        command_cue_from_env(env, mode=mode),
        clear=clear,
    )
