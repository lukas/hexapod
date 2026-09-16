"""Walk-mode INCOME GATES and per-leg gait charges, moved out of
SimHexapodJointWalkEnv._post_step.

Every function here is one contiguous block of the walk-mode pricing stack
moved mechanically: ``env`` is the env instance (the former ``self``), the
remaining parameters are the block's live inputs and the return values its
live outputs, so the call site in ``_post_step`` is a single assignment.
Bodies are byte-identical to the original apart from ``self`` -> ``env``
and re-indentation; the header comments travelled with the code.
"""
from __future__ import annotations

from rl_move.config import cfg_get


def kernel_progress_gate(env, along, info, r_walk, s_ref):
    # Progress-gated kernel income (cycle 20, cw-walk-kgate;
    # cfg reward.walk_kernel_prog_gate in [0,1], default 0=off):
    # multiply the velocity-error kernel by
    # clip(along/s_ref, 0, 1). Root cause: at commands
    # 0.02-0.06 m/s the ABSOLUTE-error kernel pays a parked
    # robot (v=0) 0.97-1.85/tick (up to 93% of peak income), so
    # the tripod park stays a paid basin (return +519 vs +1220
    # walking) that k_park_duty merely discounts. Gating income
    # on achieved progress makes the park earn ~0 kernel income
    # by construction while perfect tracking is unchanged
    # (factor 1); overspeed unaffected (clip at 1). Walk-mode
    # only by construction (this block).
    # Support-quality product for the windowed course INCOME
    # term below (fb_20260829T142239_63c818 item 5: positive
    # walk income must be gated by support quality). Collects
    # the SAME blended factors the run's own configured support
    # gates (anchor / loadslip / height / gait) already apply
    # to kernel income — a belly shuffle, skate or flag-leg
    # gait earns course income at the same discount its kernel
    # income takes, by construction, with zero new tuning.
    # Deliberately EXCLUDES the per-tick prog/yaw kernels: the
    # windowed term measures progress itself over gait-scale
    # windows, and a per-tick progress factor would re-import
    # exactly the instantaneous-velocity sensitivity the
    # directive forbids.
    support_gate = 1.0
    g_kernel = float(cfg_get(env.cfg, "reward",
                             "walk_kernel_prog_gate",
                             default=0.0))
    if g_kernel > 0.0 and s_ref > 1e-3:
        factor = min(max(along / s_ref, 0.0), 1.0)
        r_walk *= (1.0 - g_kernel) + g_kernel * factor
        info["walk_prog_factor"] = factor
    return r_walk, support_gate
