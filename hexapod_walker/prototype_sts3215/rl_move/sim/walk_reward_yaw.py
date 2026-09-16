"""Walk-mode YAW reward terms, moved out of SimHexapodJointWalkEnv._post_step.

Every function here is one contiguous block of the walk-mode pricing stack
moved mechanically: ``env`` is the env instance (the former ``self``), the
remaining parameters are the block's live inputs and the return values its
live outputs, so the call site in ``_post_step`` is a single assignment.
Bodies are byte-identical to the original apart from ``self`` -> ``env``
and re-indentation; the header comments travelled with the code.
"""
from __future__ import annotations

import numpy as np

from rl_move.config import cfg_get


def hip_yaw_margin_charge(env, info, reward):
    # Hip-yaw limit-margin charge (2026-08-19; operator order
    # fb_20260818T152717 lineage — the direction-switch tangle).
    # probe_dirswitch_tangle measured the tangle PRECURSOR:
    # after abrupt command switches the walker rides hip-yaw
    # joints within ~2 deg of (and into) the hard stop for
    # 1-9% of ticks (yaw_sat_frac 0.013-0.093, margin min to
    # -0.65 deg), while rot60 sector crossings were exonerated.
    # Three exposure/schedule/blend levers (steer1-hard20m1,
    # steer2-hard20m1-r1, steer2-blend1) moved the symptom
    # without curing it, so this prices the precursor
    # directly: per tick, each leg whose hip-yaw sits within
    # reward.yaw_margin_allow_deg of either hard limit pays
    # k_yaw_margin scaled linearly by depth into the band
    # (margin >= allow -> 0, margin <= 0 [pressed into the
    # stop] -> full k). WALK-mode block only; charged on every
    # walk tick regardless of the commanded speed (saturation
    # during a stop dwell is the same tangle precursor). The
    # honest tall gait rides ~10-20+ deg of margin and pays
    # ~0 by construction (semantics bank). Reads only
    # data.qpos + model constants, so C env and MJX FakeData
    # backends price identically. Default 0.0 = off, block
    # skipped, bit-exact legacy.
    k_yawm = float(cfg_get(env.cfg, "reward", "k_yaw_margin",
                           default=0.0))
    if k_yawm > 0.0:
        jr = getattr(env, "_yaw_margin_jrng", None)
        if jr is None:
            jr = []
            for leg in range(6):
                j = env.model.joint(f"L{leg}_yaw")
                jr.append((int(np.asarray(j.qposadr).item()),
                           float(np.degrees(j.range[0])),
                           float(np.degrees(j.range[1]))))
            env._yaw_margin_jrng = jr
        allow_deg = float(cfg_get(env.cfg, "reward",
                                  "yaw_margin_allow_deg",
                                  default=3.0))
        r_yawm = 0.0
        for adr, lo, hi in jr:
            q = float(np.degrees(env.data.qpos[adr]))
            margin = min(q - lo, hi - q)
            if margin < allow_deg:
                depth = 1.0 - max(margin, 0.0) / allow_deg
                r_yawm -= k_yawm * depth
        if r_yawm:
            reward += r_yawm
        info["reward_yaw_margin"] = r_yawm
    return reward
