"""Walk-mode velocity/progress INCOME and direction telemetry, moved out of SimHexapodJointWalkEnv._post_step.

Every function here is one contiguous block of the walk-mode pricing stack
moved mechanically: ``env`` is the env instance (the former ``self``), the
remaining parameters are the block's live inputs and the return values its
live outputs, so the call site in ``_post_step`` is a single assignment.
Bodies are byte-identical to the original apart from ``self`` -> ``env``
and re-indentation; the header comments travelled with the code.
"""
from __future__ import annotations

import math

import numpy as np

from rl_move.config import cfg_get
from .walk_task import (
    WALK_CMD_MODE_IDS, WALK_DIRECTION_MIN_SPEED_M_S, _add_walk_direction_info,
)


def direction_telemetry(env,
                        along, cmd_cross, goal, info, k_cmd_track, s_ref, v):
    _add_walk_direction_info(
        info, float(v[0]), float(v[1]),
        float(goal.vx_ref), float(goal.vy_ref),
        min_speed_m_s=WALK_DIRECTION_MIN_SPEED_M_S)
    # Raw commanded-direction speed telemetry (08-15, operator
    # directive fb_20260815T114414: judge command-following by
    # RAW SIGNED m/s along the requested direction, never by
    # clipped gate factors or total speed; SIMPLIFIED by
    # fb_20260815T115650: NO per-heading bin keys in training —
    # uniform [-pi,pi] heading sampling + the signed average
    # already zeroes out command-ignorant motion, and fixed
    # 8/12-direction panels belong in held-out EVAL only). cfg
    # goal.walk_cmd_metrics=1; default 0 = no new info keys,
    # legacy info dict bit-exact. Emitted ONLY on
    # active-command ticks (s_ref > 1e-3), so the trainers'
    # info-scalar means are per-ACTIVE-tick by construction.
    if (s_ref > 1e-3 and float(cfg_get(
            env.cfg, "goal", "walk_cmd_metrics",
            default=0.0)) == 1.0):
        ux, uy = goal.vx_ref / s_ref, goal.vy_ref / s_ref
        info["v_along_cmd_m_s"] = float(along)
        info["v_cross_abs_m_s"] = (
            cmd_cross if k_cmd_track > 0.0 else
            abs(float(ux * v[1] - uy * v[0])))
        info["cmd_speed_m_s"] = s_ref
        info["wrong_way"] = 1.0 if along < 0.0 else 0.0
        info["walk_cmd_mode_id"] = WALK_CMD_MODE_IDS.get(
            getattr(env._goal_traj, "cmd_mode", "legacy"), 0)
        # Walk-direction telemetry (operator directive
        # fb_20260815T192912): angular error in DEGREES between
        # the achieved planar velocity and the commanded
        # direction. Direction is undefined near zero speed, so
        # ticks are VALID only when actual speed >= 5 mm/s;
        # walk_dir_valid is emitted on every active tick (its
        # mean = valid fraction) while the deg key is emitted
        # only on valid ticks (its mean = error over valid
        # ticks). Same walk_cmd_metrics gate as above: the
        # default (0) keeps the legacy info dict bit-exact.
        spd = float(np.hypot(*v))
        dir_valid = spd >= 5e-3
        info["walk_dir_valid"] = 1.0 if dir_valid else 0.0
        if dir_valid:
            cosang = max(-1.0, min(1.0, float(along) / spd))
            info["walk_direction_err_deg"] = math.degrees(
                math.acos(cosang))
    if env._walk_bucket is not None:
        info["walk_bucket"] = env._walk_bucket
