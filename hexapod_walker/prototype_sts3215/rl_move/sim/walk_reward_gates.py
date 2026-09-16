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
from .walk_task import (walk_legslip_ratio_charge)


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


def leg_swinggap_charge(env, info, s_ref):
    # Per-LEG swing-GAP reward CHARGE (reward.walk_leg_swing_
    # gap_charge, 2026-09-08 -- the "duration-since-last-swing
    # PATTERN price" concrete lead named by the loadslip-
    # ratio-charge closure (this cycle's own CURRENT_TRUTHS/
    # STATUS.md entry): both the duty-ratio charge (contact-
    # TIME based) and the loadslip charge (velocity based)
    # price a STATE a dragging/planted leg can satisfy without
    # ever completing a real step (duty recovers by holding
    # longer, slip recovers by holding stiller -- both closed
    # 2-4/2-4 seeds with 0-1/4 held-out groups clearing
    # efficacy). This charges the PATTERN directly: seconds
    # elapsed since this leg's last qualifying swing (the
    # IDENTICAL stride-filtered liftoff->airborne->touchdown-
    # with-real-XY-stride event walk_gait_gate/walk_swing_gate/
    # the duty-ratio swing-floor add-on already detect via
    # their own `*_flags` arrays below -- same physical
    # definition, own flag array/state so this dose sweeps
    # standalone). A leg cannot reduce this charge by planting
    # harder or sliding less; only by actually swinging.
    # Additive (never multiplies r_walk/r_prog/r_cmd_track),
    # no episode cutoff, one-tick lag -- same shape as every
    # other per-leg charge in this file. CAPPED FROM THE START
    # (reward.walk_leg_swing_gap_cap_s, default 4.0): unlike
    # the loadslip charge's initial uncapped design (whose own
    # isolation canary drove an orders-of-magnitude reward
    # collapse before the excess-cap retrofit), a duration-
    # since-last-swing signal is exactly as unbounded (a leg
    # could go the whole episode without swinging) so this
    # mechanism ships pre-capped per the 08-21 "encode the
    # lesson in the mechanism" practice. Default 0.0 = off, no
    # state read beyond the always-present `_swing_gap_s`
    # counter (itself inert -- 0 charge -- while off), legacy
    # bit-exact. cfg: reward.walk_leg_swing_gap_charge (0.0),
    # reward.walk_leg_swing_gap_grace_s (3.0, seconds of gap
    # tolerated before it counts -- a leg mid-stance for a
    # normal stride period is not yet "stuck"),
    # reward.walk_leg_swing_gap_cap_s (4.0).
    g_swinggap = float(cfg_get(env.cfg, "reward",
                               "walk_leg_swing_gap_charge",
                               default=0.0))
    r_gap = 0.0
    if g_swinggap > 0.0 and s_ref > 1e-3:
        gap_grace_s = float(cfg_get(
            env.cfg, "reward", "walk_leg_swing_gap_grace_s",
            default=3.0))
        worst_gap = max(env._swing_gap_s)
        excess = max(0.0, worst_gap - gap_grace_s)
        gap_cap_s = float(cfg_get(
            env.cfg, "reward", "walk_leg_swing_gap_cap_s",
            default=4.0))
        priced_gap = (min(excess, gap_cap_s)
                      if gap_cap_s > 0.0 else excess)
        r_gap = -g_swinggap * priced_gap
        info["walk_leg_swing_gap_worst_s"] = worst_gap
        info["reward_walk_leg_swing_gap"] = r_gap
    return g_swinggap, r_gap


def leg_loadslip_ratio_charge(env, info, s_ref):
    # Per-LEG load-SLIP reward CHARGE (reward.walk_leg_
    # loadslip_ratio_charge, 2026-09-08 -- design rationale on
    # walk_legslip_ratio_tick/_charge above, near
    # walk_legduty_ratio_tick/_charge). Same additive/no-
    # cutoff/one-tick-lag shape as the duty-ratio charge
    # (this tick's per-foot tangent-slip measurements update
    # the EMA in the bookkeeping block below for NEXT tick's
    # price). Grace: no charge until walk_leg_loadslip_ratio_
    # grace_s worth of ticks have updated the EMA. Default
    # 0 = off: no charge, no info keys, legacy bit-exact,
    # independent of every other slip/duty mechanism's state.
    # cfg: reward.walk_leg_loadslip_ratio_charge (0.0),
    # reward.walk_leg_loadslip_ratio_target (1.5, assume-and-
    # go -- see the function-level comment above),
    # reward.walk_leg_loadslip_ratio_grace_s (3.0),
    # reward.walk_leg_loadslip_ratio_tau_s (1.0),
    # reward.walk_leg_loadslip_ratio_excess_cap (0.0 = OFF,
    # 2026-09-08 -- the isolation canaries `cw-walkscratch-
    # crutchoff-{s0,s1}-widen8-loadslip-target6-alone` (CANARY
    # FAIL - MECHANISM both seeds) found this charge's own
    # reward-quarters collapse GETS WORSE, not better, once the
    # walk_leg_duty_ratio_charge confound is removed -- unlike
    # duty-ratio's shortfall (naturally bounded at `target`,
    # <=0.30 by construction), this charge's `worst_excess` =
    # max(0, max(ratio)-target) has NO upper bound: a leg
    # transiently sliding many multiples of its peers' rate
    # (a real, if rare, tail event under DR/faults/pushes) can
    # spike the per-tick charge arbitrarily far past its
    # "typical" 0.02-0.03 telemetry reading, and PPO's return
    # normalization/advantage estimation can be dominated by a
    # handful of such outlier ticks regardless of the charge's
    # overall weight (already shown: 10x/3x weight cuts barely
    # moved the collapse magnitude in the earlier w15/w45
    # dose-bracket, both CLOSED FAIL). Capping `worst_excess`
    # at this value (if >0) directly bounds the per-tick charge
    # to `-charge*cap` regardless of how extreme the tail event
    # is, isolating "price the typical excess" from "let one
    # bad tick dominate the whole return" -- untested, next
    # concrete lever named by the isolation closure. Default
    # 0.0 = no cap (legacy/current behavior), bit-exact.
    g_lsratio = float(cfg_get(env.cfg, "reward",
                              "walk_leg_loadslip_ratio_charge",
                              default=0.0))
    r_lsratio = 0.0
    if g_lsratio > 0.0 and s_ref > 1e-3:
        lsratio_grace_s = float(cfg_get(
            env.cfg, "reward", "walk_leg_loadslip_ratio_grace_s",
            default=3.0))
        if env._legslip_ratio_ticks * env.dt >= lsratio_grace_s:
            lsratio_target = float(cfg_get(
                env.cfg, "reward", "walk_leg_loadslip_ratio_target",
                default=1.5))
            worst_excess, _ls_ratios = walk_legslip_ratio_charge(
                env._legslip_ratio_ema, lsratio_target)
            lsratio_cap = float(cfg_get(
                env.cfg, "reward",
                "walk_leg_loadslip_ratio_excess_cap", default=0.0))
            priced_excess = (min(worst_excess, lsratio_cap)
                              if lsratio_cap > 0.0 else worst_excess)
            r_lsratio = -g_lsratio * priced_excess
            info["walk_leg_loadslip_ratio_excess"] = worst_excess
            info["reward_walk_leg_loadslip_ratio"] = r_lsratio
    return g_lsratio, r_lsratio
