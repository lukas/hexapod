"""Frozen observation contract for dependency-light deployed policies.

The simulator appends walk features in this order after the common
68-wide joint-goal observation:

``[vx_ref, vy_ref, vx_meas, vy_meas] / 0.15``
``[sin(phase), cos(phase)]`` (phase lineages)
``[wz_ref / 0.5]`` (yaw-command lineages)
``mode_onehot[6]`` (dual-GRU unified lineage)
``fault_health[18]`` (AMP fault lineage)

Width 74 is AMBIGUOUS by count alone (rl_move/np_policy.py
``_phase_meta_errors``): the "phase-walk" family (a real advancing gait
clock, ``goal.walk_phase_obs=1``) and the walkcurr turn-and-hold family
(``goal.walk_yaw_offset_frac=1``, a static per-episode
``[target, remaining-error]`` pair, never a clock) both land on
68+4+2=74. An explicit ``yaw_offset_cmd=True`` call opts a width-74 tail
OUT of the phase-clock contract and into
``[yaw_offset_target, yaw_offset_remaining] / (pi/2)`` instead (mirrors
``rl_move/sim/walk_task.py``'s ``_yaw_offset_cmd`` block / the reward's
``walk_reward_yaw.yaw_offset_kernel``); the two are mutually exclusive at
this width, never both appended (that would make width 76).

Keeping this small numpy-only module separate from the hardware loop makes
the layout directly unit-testable against ``walk_task.py``.  Robot runners
must call :func:`walk_observation_tail`; open-coded width branches are not a
supported extension point.
"""
from __future__ import annotations

import math

import numpy as np

from .np_policy import MODE_ONEHOT_ORDER

N_JOINTS = 18
WALK_VEL_SCALE = 0.15
WALK_YAW_SCALE = 0.5
YAW_OFFSET_SCALE = math.pi / 2   # rad (90 deg); matches walk_task.py
WALK_OBS_DIMS = (72, 74, 75, 81, 93)
WALK_PHASE_OBS_DIMS = (74, 75, 81, 93)
WALK_YAW_OBS_DIMS = (75, 81, 93)
WALK_MODE_OBS_DIMS = (81,)
WALK_FAULT_OBS_DIMS = (93,)
WALK_YAW_OFFSET_OBS_DIM = 74   # the only width the offset contract defines
BASE_GOAL_OBS_DIM = 68


def policy_mode_onehot(mode: str) -> np.ndarray:
    """Return the frozen six-wide family one-hot used during training."""
    try:
        index = MODE_ONEHOT_ORDER.index(str(mode))
    except ValueError as exc:
        raise ValueError(
            f"unsupported deployed policy mode {mode!r}; expected one of "
            f"{MODE_ONEHOT_ORDER}") from exc
    result = np.zeros(len(MODE_ONEHOT_ORDER), dtype=np.float32)
    result[index] = 1.0
    return result


def walk_observation_tail(obs_dim: int, vx_ref: float, vy_ref: float,
                          phase: float, wz_ref: float = 0.0, *,
                          mode: str = "walk",
                          fault_health=None,
                          yaw_offset_cmd: bool = False,
                          yaw_offset_target: float = 0.0,
                          yaw_offset_remaining: float = 0.0) -> np.ndarray:
    """Build the exact post-68 observation tail for one policy tick.

    ``yaw_offset_cmd=True`` (only defined at ``WALK_YAW_OFFSET_OBS_DIM``,
    i.e. 74) swaps the width-74 tail from ``[sin(phase), cos(phase)]`` to
    ``[yaw_offset_target, yaw_offset_remaining] / YAW_OFFSET_SCALE`` (both
    rad) -- default False is bit-exact unchanged behavior.
    """
    obs_dim = int(obs_dim)
    if obs_dim not in WALK_OBS_DIMS:
        raise ValueError(
            f"unsupported deployed walk obs_dim {obs_dim}; "
            f"expected one of {WALK_OBS_DIMS}")
    if yaw_offset_cmd and obs_dim != WALK_YAW_OFFSET_OBS_DIM:
        raise ValueError(
            "yaw_offset_cmd is only defined at obs_dim "
            f"{WALK_YAW_OFFSET_OBS_DIM} (got {obs_dim})")
    tail = [
        vx_ref / WALK_VEL_SCALE,
        vy_ref / WALK_VEL_SCALE,
        # goal.walk_obs_body_vel=2 deployment contract: measured := ref.
        vx_ref / WALK_VEL_SCALE,
        vy_ref / WALK_VEL_SCALE,
    ]
    if yaw_offset_cmd:
        tail.extend([yaw_offset_target / YAW_OFFSET_SCALE,
                     yaw_offset_remaining / YAW_OFFSET_SCALE])
    elif obs_dim in WALK_PHASE_OBS_DIMS:
        tail.extend([math.sin(phase), math.cos(phase)])
    if obs_dim in WALK_YAW_OBS_DIMS:
        tail.append(wz_ref / WALK_YAW_SCALE)
    if obs_dim in WALK_MODE_OBS_DIMS:
        tail.extend(policy_mode_onehot(mode))
    if obs_dim in WALK_FAULT_OBS_DIMS:
        health = (np.ones(N_JOINTS, dtype=np.float32)
                  if fault_health is None
                  else np.asarray(fault_health, dtype=np.float32))
        if health.shape != (N_JOINTS,) or not np.all(np.isfinite(health)):
            raise ValueError("fault_health must contain 18 finite values")
        tail.extend(health)
    result = np.asarray(tail, dtype=np.float32)
    expected = obs_dim - BASE_GOAL_OBS_DIM
    if result.shape != (expected,):
        raise AssertionError(
            f"obs-{obs_dim} tail width {result.shape[0]} != {expected}")
    return result


def phase_clock_runs(obs_dim: int, vx_ref: float, vy_ref: float,
                     wz_ref: float = 0.0, *,
                     phase_run_on_yaw: bool = False,
                     yaw_offset_cmd: bool = False) -> bool:
    """Mirror ``goal.walk_phase_run_on_yaw`` clock gating.

    ``yaw_offset_cmd=True`` never has a clock (the width-74 turn-and-hold
    contract has no ``[sin, cos]`` tail at all -- see
    :func:`walk_observation_tail`), regardless of vx/vy/wz.
    """
    if yaw_offset_cmd:
        return False
    if int(obs_dim) not in WALK_PHASE_OBS_DIMS:
        return False
    if math.hypot(vx_ref, vy_ref) > 1e-3:
        return True
    return bool(phase_run_on_yaw) and abs(wz_ref) > 1e-3


def supports_yaw_command(obs_dim: int) -> bool:
    return int(obs_dim) in WALK_YAW_OBS_DIMS


def supports_yaw_offset_command(obs_dim: int) -> bool:
    """Whether this width can carry the turn-and-hold offset contract.

    Callers must still gate on the export's own ``meta.walk_yaw_offset_cmd``
    flag (width 74 is ambiguous -- see module docstring); this only says
    the width is *capable*, not that a given checkpoint uses it.
    """
    return int(obs_dim) == WALK_YAW_OFFSET_OBS_DIM


def supports_mode_command(obs_dim: int) -> bool:
    return int(obs_dim) in WALK_MODE_OBS_DIMS
