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

import math

import numpy as np

from rl_move.config import cfg_get
from .walk_task import (walk_legduty_ratio_charge, walk_legslip_ratio_charge)


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


def leg_duty_ratio_charge(env, info, s_ref):
    # Per-LEG duty-RATIO reward CHARGE (reward.walk_leg_duty_
    # ratio_charge, 2026-09-08 -- design rationale on
    # walk_legduty_ratio_tick/_charge above, near
    # walk_legduty_term_tick). Deliberately ADDITIVE, not
    # multiplicative: never touches r_walk/r_prog/r_cmd_track,
    # so it cannot be "simply outbid" by a fatter income term
    # the way every walk_duty_gate-class *_factor could be
    # (each of their own closures named this as the failure
    # shape); no episode cutoff, so there is nothing to pay
    # off as an ambient one-time cost either (the termination
    # class's own closure signature). Uses the PREVIOUS tick's
    # EMA (one-tick lag, same convention as every other gate in
    # this file); this tick's contacts update the EMA in the
    # bookkeeping block below for NEXT tick's price. Grace: no
    # charge until walk_leg_duty_ratio_grace_s worth of ticks
    # have updated the EMA (the EMA has no natural "window
    # full" signal, so a plain tick counter stands in for the
    # window-must-fill grace every other gate uses). Default
    # 0 = off: no charge, no info keys, legacy bit-exact. cfg:
    # reward.walk_leg_duty_ratio_charge (0.0),
    # reward.walk_leg_duty_ratio_target (0.30, the calibrated
    # passing-population's own p10 worst-leg ratio),
    # reward.walk_leg_duty_ratio_grace_s (3.0).
    g_ratio = float(cfg_get(env.cfg, "reward",
                            "walk_leg_duty_ratio_charge",
                            default=0.0))
    # Optional swing-count floor (2026-09-08, see the
    # walk_legduty_ratio_charge docstring): read here
    # (unconditionally, not nested under the grace check
    # below) so both this pricing block AND the per-foot
    # swing-event loop further down can see it this same
    # tick. Default 0.0 = off, bit-exact legacy (no state
    # tracked, no info keys, same as g_ratio itself when 0).
    g_ratio_swingfloor = float(cfg_get(
        env.cfg, "reward",
        "walk_leg_duty_ratio_swing_min_count", default=0.0))
    r_ratio = 0.0
    if g_ratio > 0.0 and s_ref > 1e-3:
        ratio_grace_s = float(cfg_get(
            env.cfg, "reward", "walk_leg_duty_ratio_grace_s",
            default=3.0))
        if env._legduty_ratio_ticks * env.dt >= ratio_grace_s:
            ratio_target = float(cfg_get(
                env.cfg, "reward", "walk_leg_duty_ratio_target",
                default=0.30))
            ratio_swing_counts = None
            if g_ratio_swingfloor > 0.0:
                ratio_swing_win = max(1, int(round(float(cfg_get(
                    env.cfg, "reward",
                    "walk_leg_duty_ratio_swing_window_s",
                    default=4.0)) / env.dt)))
                if len(env._legduty_ratio_swing_hist) \
                        >= ratio_swing_win:
                    ratio_swing_counts = np.sum(
                        env._legduty_ratio_swing_hist, axis=0)
            ratio_agg = str(cfg_get(
                env.cfg, "reward", "walk_leg_duty_ratio_agg",
                default="min"))
            worst_shortfall, _ratios = walk_legduty_ratio_charge(
                env._legduty_ratio_ema, ratio_target,
                swing_counts=ratio_swing_counts,
                swing_min_count=g_ratio_swingfloor,
                agg=ratio_agg)
            r_ratio = -g_ratio * worst_shortfall
            info["walk_leg_duty_ratio_shortfall"] = worst_shortfall
            info["reward_walk_leg_duty_ratio"] = r_ratio
    return g_ratio, g_ratio_swingfloor, r_ratio


def leg_swing_rate_gate(env,
                        info, lift, r_cmd_track, r_prog, r_walk, s_ref,
                        support_gate):
    # Per-leg swing-RATE income gate (09-05, closing two prior
    # anti-park exploits together after both were confirmed
    # gameable end-to-end, 6/6 and 9/9 FAIL respectively --
    # see CURRENT_TRUTHS.md 09-05 ~13:1x..~19:2x): score = MIN
    # over commanded support legs of clip(count of qualifying
    # real swings completed in the trailing
    # swing_gate_window_s of COMMANDED ticks / swing_gate_
    # min_count, 0, 1). A qualifying swing uses the IDENTICAL
    # stride-filtered definition walk_gait_gate already uses
    # (liftoff -> >=2 ticks airborne -> touchdown with XY
    # stride >= gait_gate_stride_mm) -- a high-frequency
    # contact-chatter "swing" that never displaces the foot
    # never counts, which is what closes walk_duty_gate's
    # freeze/vibrate exploit (a planted or vibrating leg racks
    # up contact-DUTY trivially but completes zero qualifying
    # SWINGS). Requiring a MINIMUM COUNT within the window
    # (not a recency-decay score that only asks "how long
    # since the last one") is what closes walk_gait_gate's
    # rare-token-dodge exploit (that gate's own g_score reads
    # 1.0 off a single swing anywhere in window+fade seconds;
    # this gate needs >=swing_gate_min_count of them inside
    # ONE window, so a leg stepping once every several seconds
    # cannot clear a >=2/window bar the way it cleared a
    # >=1/(window+fade) recency floor). MIN, not mean, per the
    # same lesson every prior anti-sacrifice gate in this file
    # learned: a fractional discount is simply paid, so any
    # one support leg failing the bar collapses transport
    # income to the (1-g) floor. Episode-start grace: scores
    # 1.0 until the window is full (mirrors walk_duty_gate/
    # walk_gait_gate). Penalties are never shrunk. Default 0 =
    # off, no state, no info keys, legacy bit-exact. cfg:
    # reward.walk_swing_gate in [0,1],
    # reward.swing_gate_window_s (4.0),
    # reward.swing_gate_min_count (2.0) -- reuses
    # reward.gait_gate_stride_mm for the qualifying-swing
    # stride filter (same physical definition, one knob).
    g_swing = float(cfg_get(env.cfg, "reward",
                            "walk_swing_gate", default=0.0))
    if g_swing > 0.0 and s_ref > 1e-3:
        n_swin = max(1, int(round(float(cfg_get(
            env.cfg, "reward", "swing_gate_window_s",
            default=4.0)) / env.dt)))
        sw_min_count = max(1.0, float(cfg_get(
            env.cfg, "reward", "swing_gate_min_count",
            default=2.0)))
        sw_score = 1.0
        if len(env._swing_gate_hist) >= n_swin:
            counts = np.sum(env._swing_gate_hist, axis=0)
            for f in range(6):
                if f in lift:
                    continue
                sw_score = min(
                    sw_score,
                    min(float(counts[f]) / sw_min_count, 1.0))
        swg_factor = (1.0 - g_swing) + g_swing * sw_score
        r_walk *= swg_factor
        support_gate *= swg_factor
        if r_prog > 0.0:
            r_prog *= swg_factor
        if r_cmd_track > 0.0:
            r_cmd_track *= swg_factor
        info["walk_swing_gate_min"] = sw_score
        info["walk_swing_gate_factor"] = swg_factor
    return g_swing, r_cmd_track, r_prog, r_walk, support_gate


def leg_duty_gate(env,
                  info, lift, r_cmd_track, r_prog, r_walk, s_ref, support_gate):
    # Per-leg contact-DUTY income gate (09-05 dig-in
    # headset-base-s0c1-acq1: LEGPARK confirmed family-wide,
    # not gSDE-specific — 1/3 plain-Gaussian heading seeds
    # hardened a marginal leg into a chronic duty-0.03-0.07
    # paddle over 40M while reward rose and speed stayed
    # flat). The two prior anti-park levers each had one
    # right half: walk_gait_gate collapses income (right
    # STRUCTURE — charges are simply outbid, quadwalk3/5 +
    # the idleterm/k_park FAIL pair) but scores a completion
    # window that a rare token swing resets (gamed 2/2,
    # sde-s1/s2-c3gg, gate_factor pinned 0.98-0.99 while the
    # harness flagged a duty-0.0 leg); k_park prices duty
    # (right SIGNAL, the harness's own sacrifice metric) but
    # as a flat charge. This gate combines the proven
    # halves: score = MIN over support legs of
    # clip(trailing-window contact duty / duty_gate_floor,
    # 0, 1); healthy tripod duty ~0.4-0.6 scores 1.0, the
    # harness bar is 0.10, floor 0.15 adds margin. A token
    # touch cannot dodge it (one contact tick moves a 3 s
    # window mean ~1/300); a parked or paddling leg drags
    # ALL transport income to the (1-g) floor within
    # ~duty_gate_window_s. MIN not mean (fractional
    # discounts are simply paid). Gates only once the window
    # is full (episode-start grace, mirrors k_park); history
    # appends in the contact block below, so previous-tick
    # state prices this tick (same one-tick lag as
    # walk_gait_gate). Penalties are never shrunk. Default
    # 0 = off: no state, no info keys, legacy bit-exact.
    # cfg: reward.walk_duty_gate in [0,1],
    # reward.duty_gate_window_s (3.0),
    # reward.duty_gate_floor (0.15).
    g_duty = float(cfg_get(env.cfg, "reward",
                           "walk_duty_gate", default=0.0))
    if g_duty > 0.0 and s_ref > 1e-3:
        n_dwin = max(1, int(round(float(cfg_get(
            env.cfg, "reward", "duty_gate_window_s",
            default=3.0)) / env.dt)))
        d_score = 1.0
        if len(env._dgate_hist) >= n_dwin:
            d_floor = float(cfg_get(env.cfg, "reward",
                                    "duty_gate_floor",
                                    default=0.15))
            duty = np.mean(env._dgate_hist, axis=0)
            for f in range(6):
                if f in lift:
                    continue
                d_score = min(
                    d_score,
                    min(float(duty[f]) / d_floor, 1.0))
        dg_factor = (1.0 - g_duty) + g_duty * d_score
        r_walk *= dg_factor
        support_gate *= dg_factor
        if r_prog > 0.0:
            r_prog *= dg_factor
        if r_cmd_track > 0.0:
            r_cmd_track *= dg_factor
        info["walk_duty_min"] = d_score
        info["walk_duty_gate_factor"] = dg_factor
    return g_duty, r_cmd_track, r_prog, r_walk, support_gate


def gait_gate(env,
              info, lift, r_cmd_track, r_prog, r_walk, s_ref, support_gate):
    # All-support-legs gait gate (08-13, quad track; the
    # STRUCTURAL close of the leg-sacrifice loophole after
    # cw-quadwalk1-5 measured pricing exhausted for BOTH cheat
    # families: fronts-down paid a -575/ep lift-contact charge
    # (~40% of return) and kept walking on six (quadwalk3);
    # mid-leg-park ignored a 6x k_park_duty reprice outright
    # (quadwalk5). Additive charges are payable fines, and the
    # anchor gate's fraction spans LOADED feet only — a leg
    # parked in the AIR silently drops out of its denominator.
    # Same lesson as the prog/anchor/loadslip gates: make the
    # cheat worth less BY CONSTRUCTION. Velocity income
    # (kernel + positive progress; quadwalk's clear/plant
    # income in _quad_income rides the same factor) is
    # multiplied by the MIN over commanded SUPPORT legs of a
    # per-leg "recently completed a real swing" score: 1.0 if
    # the leg finished a liftoff -> >=2-ticks-airborne ->
    # touchdown swing with XY stride >= gait_gate_stride_mm
    # within the trailing gait_gate_window_s of COMMANDED
    # ticks, fading linearly to 0 over gait_gate_fade_s after
    # that (a fade, not a hard zero — the holdstill1
    # zero-gradient lesson). MIN, not mean: quadwalk3/5
    # measured that any fractional discount is simply paid;
    # sacrificing ANY subset of support legs must collapse
    # transport income to the (1-g) floor. Episode start
    # counts as "just stepped" (window+fade of commanded
    # grace); lift legs are exempt (they must NOT step);
    # penalties are never shrunk. Default 0 = off, legacy
    # bit-exact. cfg: reward.walk_gait_gate in [0,1],
    # reward.gait_gate_window_s (2.0), gait_gate_fade_s (2.0),
    # gait_gate_stride_mm (10.0).
    g_gait = float(cfg_get(env.cfg, "reward",
                           "walk_gait_gate", default=0.0))
    env._gait_gate_qfactor = 1.0
    if g_gait > 0.0 and s_ref > 1e-3:
        env._gait_cmd_tick += 1
        n_gwin = max(1, int(round(float(cfg_get(
            env.cfg, "reward", "gait_gate_window_s",
            default=2.0)) / env.dt)))
        n_gfade = int(round(float(cfg_get(
            env.cfg, "reward", "gait_gate_fade_s",
            default=2.0)) / env.dt))
        g_score = 1.0
        for f in range(6):
            if f in lift:
                continue
            since = env._gait_cmd_tick - env._gait_last_step[f]
            if since <= n_gwin:
                sc = 1.0
            elif n_gfade > 0:
                sc = max(1.0 - (since - n_gwin) / n_gfade, 0.0)
            else:
                sc = 0.0
            g_score = min(g_score, sc)
        gt_factor = (1.0 - g_gait) + g_gait * g_score
        r_walk *= gt_factor
        support_gate *= gt_factor
        if r_prog > 0.0:
            r_prog *= gt_factor
        if r_cmd_track > 0.0:
            r_cmd_track *= gt_factor
        env._gait_gate_qfactor = gt_factor
        info["walk_gait_min"] = g_score
        info["walk_gait_gate_factor"] = gt_factor
    return g_gait, r_cmd_track, r_prog, r_walk, support_gate


def height_gate(env, goal, info, r_prog, r_walk, s_ref, support_gate):
    # Height-keeping income gate (2026-08-10, hardware finding
    # rl_docs/HARDWARE.md "sag": deployed walk policies migrate
    # to a crouch 54-70 mm below the spawn stance — measured on
    # the bench, knees track commands so it is COMMANDED posture,
    # not slip. The base stack's quadratic height charge
    # (env.py k_height) is ~0.36/tick at 60 mm while walk income
    # is ~3/tick, so the crouch simply outbids it. Gate the
    # income instead: multiply kernel + positive progress by a
    # Gaussian on the body's height error vs the episode ref
    # (z0-anchored, same as env.py h_err). Factor 1 at ref
    # height, 0.61 at one sigma (30 mm default), 0.14 at two;
    # symmetric so stilting up is never a strategy either.
    # Never shrinks a penalty; metric exports whenever a
    # velocity is commanded, the modifier only when enabled;
    # default 0 = off, legacy exact. cfg:
    # reward.walk_height_gate in [0,1],
    # reward.walk_height_sigma_mm.
    g_hgt = float(cfg_get(env.cfg, "reward",
                          "walk_height_gate", default=0.0))
    if s_ref > 1e-3:
        h_err_m = (float(env.data.xpos[env._chassis_bid, 2])
                   - env._z0) - goal.height_ref
        sig_m = float(cfg_get(env.cfg, "reward",
                              "walk_height_sigma_mm",
                              default=30.0)) / 1000.0
        h_gauss = math.exp(
            -0.5 * (h_err_m / max(sig_m, 1e-6)) ** 2)
        info["walk_height_factor"] = h_gauss
        if g_hgt > 0.0:
            hgt_factor = (1.0 - g_hgt) + g_hgt * h_gauss
            r_walk *= hgt_factor
            support_gate *= hgt_factor
            if r_prog > 0.0:
                r_prog *= hgt_factor
    return r_prog, r_walk, support_gate


def loaded_slip_gate(env,
                     along, info, r_prog, r_walk, reward, s_ref, support_gate):
    # Loaded-slip income gate (operator ruling 2026-08-09
    # WALK-SLIP; the structural fix for the cadence-reset
    # exploit). The anchor gate's per-touchdown allowance is an
    # accounting identity the policy exploited (free slip =
    # cadence x tol; c1 +23% stances, tol5 paid the gate).
    # This gate multiplies velocity income (kernel + positive
    # progress) by a factor of the EPISODE-ACCUMULATED loaded
    # slip per meter of along-command body progress — the same
    # quantity the eval harness scores — which no touchdown can
    # reset: factor = clip((ls_max - ratio)/(ls_max - ls_ok),
    # 0, 1); ratio = slip_m / max(progress_m, ls_floor_m).
    # Slip accumulates while a foot was in contact on the prior
    # tick (harness definition, no deadband); progress banks
    # max(along,0)*dt; both only while a velocity is commanded.
    # Never shrinks a penalty; zero-slip gait factor 1; default
    # 0 = off, legacy exact. cfg: reward.walk_loadslip_gate in
    # [0,1], reward.loadslip_ok, reward.loadslip_max,
    # reward.loadslip_floor_m.
    g_ls = float(cfg_get(env.cfg, "reward",
                         "walk_loadslip_gate", default=0.0))
    # Measurement always runs while a velocity is commanded
    # (operator 08-10: loadslip_ratio was invisible in W&B for
    # every run that didn't enable the gate — the METRIC must
    # not be coupled to the reward MODIFIER). The gate itself
    # still only scales income when walk_loadslip_gate > 0.
    if s_ref > 1e-3:
        step_slip_m = 0.0
        for f in range(6):
            adr = env._touch_adr[f]
            on = (adr >= 0 and
                  float(env.data.sensordata[adr]) > 0.5)
            xy = env.data.xpos[env._pad_bids[f], :2]
            if env._ls_prev_on[f] \
                    and env._ls_prev_xy[f] is not None:
                d_ls = float(np.linalg.norm(
                    xy - env._ls_prev_xy[f]))
                env._ls_slip_m += d_ls
                step_slip_m += d_ls
            env._ls_prev_xy[f] = xy.copy()
            env._ls_prev_on[f] = on
        env._ls_prog_m += max(along, 0.0) * env.dt
        floor_m = float(cfg_get(env.cfg, "reward",
                                "loadslip_floor_m",
                                default=0.05))
        ls_ok = float(cfg_get(env.cfg, "reward",
                              "loadslip_ok", default=0.75))
        ls_max = float(cfg_get(env.cfg, "reward",
                               "loadslip_max", default=1.50))
        # Windowed (EMA) loaded-slip ratio (walkcurr item(4)
        # follow-up, 2026-09-06). The cumulative ratio above
        # averages slip_m/prog_m over the WHOLE episode, so
        # late-episode behavior is diluted by every earlier
        # tick — the item(4) `loadslip-c1` canary showed
        # exactly this shape (env/walk_loadslip_ratio noisy,
        # no clean downtrend, at a bank-proven dose) and its
        # own FAIL verdict named "a windowed rather than
        # episode-cumulative slip ratio" as the next lever
        # (rl_docs/tracks/walkcurr/STATUS.md, 09-06 ~19:1x).
        # cfg: reward.walk_loadslip_window_s (seconds, default
        # 0.0 = OFF, bit-exact legacy cumulative ratio below
        # unchanged — step_slip_m/step_prog_m above are
        # computed either way but only READ when this is on).
        # When > 0, slip and progress are tracked as
        # exponential-moving-average RATES with that time
        # constant (same alpha=dt/tau pattern as
        # reward.walk_kernel_vel_ema) and the ratio is
        # recomputed from the CURRENT window only, so a policy
        # is priced on recent slip, not diluted by an
        # early-episode transient or a long clean stretch.
        # reward.loadslip_floor_m_s (default 0.01 m/s) is the
        # windowed floor — a SEPARATE knob from the
        # cumulative-mode loadslip_floor_m (meters) since the
        # EMA operates on rates, not accumulated distance.
        window_s = float(cfg_get(env.cfg, "reward",
                                 "walk_loadslip_window_s",
                                 default=0.0))
        if window_s > 0.0:
            a_ls = env.dt / max(window_s, env.dt)
            env._ls_slip_ema += a_ls * (
                (step_slip_m / max(env.dt, 1e-9))
                - env._ls_slip_ema)
            env._ls_prog_ema += a_ls * (
                max(along, 0.0) - env._ls_prog_ema)
            floor_m_s = float(cfg_get(env.cfg, "reward",
                                      "loadslip_floor_m_s",
                                      default=0.01))
            ratio = env._ls_slip_ema / max(
                env._ls_prog_ema, floor_m_s)
        else:
            ratio = env._ls_slip_m / max(env._ls_prog_m, floor_m)
        factor = min(max(
            (ls_max - ratio) / max(ls_max - ls_ok, 1e-6),
            0.0), 1.0)
        info["walk_loadslip_ratio"] = ratio
        info["walk_loadslip_factor"] = factor
        if window_s > 0.0:
            info["walk_loadslip_ratio_cumulative"] = (
                env._ls_slip_m / max(env._ls_prog_m, floor_m))
        if g_ls > 0.0:
            ls_factor = (1.0 - g_ls) + g_ls * factor
            r_walk *= ls_factor
            support_gate *= ls_factor
            if r_prog > 0.0:
                r_prog *= ls_factor
        # Direct loaded-slip excess penalty (operator order
        # fb_20260820T075230_4a90c6, fast anti-skate V5): the
        # loadslip GATE can only zero income — a skating
        # policy that also collects non-velocity reward is
        # "complained about", never charged. This term charges
        # the EPISODE-ACCUMULATED loaded-slip ratio's excess
        # over loadslip_ok per second while a velocity is
        # commanded: r -= k * max(ratio - loadslip_ok, 0) * dt
        # (2026-08-20 ~08:5x realign, q_20260820T0830Z: the
        # authored desktop commit 2cb2a7b7 scales by env.dt
        # like every other per-second reward charge in this
        # file, e.g. c_time above — the controller
        # reconstruction had dropped the dt factor, which
        # would have made this term ~1/dt = 25x too strong
        # for the intended k=6.0 dose the moment any dose ever
        # reaches PPO; fixed before any training exercises it,
        # both canaries died at the B0 precert before this
        # term ever ran). Same ratio the gate and the eval
        # harness score (no touchdown resets it); a policy
        # that keeps skating keeps paying every tick, one that
        # walks clean pays nothing. Additive penalty — never
        # shrunk by income gates. Default 0 = off, bit-exact
        # legacy (no new info keys). cfg: reward.k_loadslip_excess.
        # NOT scaled by the walk-charge ramp below (walkcurr
        # bank finding, 2026-08-23,
        # test_walkcurr_chargeramp_min_ranking_holds): the
        # ramp exists to lower DISCOVERY FRICTION (park/idle/
        # heading charges that make refusing-to-move look
        # falsely safe), never the anti-skate/anti-fall floor.
        # Scaling k_loadslip_excess by the same shared
        # min_frac (0.15) made 'skate' (+130.6) and the swing-
        # farming 'shuffle' twin (+227.9) BOTH beat every
        # wrong-way/standing behavior at the ramp's minimum —
        # exactly the "high-slip/skate/fall is the floor"
        # invariant the track rule (STATUS.md, operator 08-23)
        # forbids trading away, and precisely the window
        # (early, high-exploration training) where a
        # from-scratch policy is most likely to find and lock
        # onto it. loadslip stays at its full bank-proven dose
        # at every ramp frac; only k_walk_heading/
        # k_walk_idle_charge/k_park_duty (discovery friction,
        # bank-proven safe to loosen — see the same test file)
        # ramp.
        k_lse = float(cfg_get(env.cfg, "reward",
                              "k_loadslip_excess",
                              default=0.0))
        # walkcurr loadslip-BOOTSTRAP (08-23, fwd4 dig-in
        # follow-up; see the __init__ block + apply_loadslip_
        # bootstrap_frac): scales this charge only, only while
        # reward.walk_loadslip_bootstrap_steps is armed; 1.0
        # (no-op, bit-exact) otherwise.
        k_lse *= env._loadslip_excess_scale()
        if k_lse > 0.0:
            r_lse = -k_lse * max(ratio - ls_ok, 0.0) * env.dt
            reward += r_lse
            info["reward_loadslip_excess"] = r_lse
    return r_prog, r_walk, reward, support_gate


def anchored_stance_gate(env, info, r_prog, r_walk, s_ref, support_gate):
    # Anchored-stance income gate (cycle 30; the dense-
    # decomposition rung's stance-no-slip component, implemented
    # as INCOME GATING per operator 0-c.2 / step0 "worth less by
    # construction" — additive charging of slip is refuted 2x
    # (kernel-gating c24, effort c29) and a timing reference is
    # refuted (phase prior c30: agreement locked 0.93, slip
    # unmoved). A foot is ANCHORED while loaded and within
    # reward.anchor_tol_mm (default 10 mm) of its own touchdown
    # point; velocity income (kernel + positive progress) is
    # multiplied by the anchored fraction of loaded feet.
    # Paddling (all six feet creeping ~24 mm per stance) collects
    # ~0.53-0.70 of income at tol=10 (measured, controller scale
    # audit 2026-08-09); an anchored gait collects ~1.0. Negative
    # progress (moving against command) is NOT gated - the gate
    # must never shrink a penalty. Zero loaded feet => factor
    # (1-g): ballistic ticks earn no anchored income. Walk-mode
    # only by construction (this block); default OFF = legacy
    # exact. cfg: reward.walk_anchor_gate in [0,1],
    # reward.anchor_tol_mm.
    g_anchor = float(cfg_get(env.cfg, "reward",
                             "walk_anchor_gate", default=0.0))
    if g_anchor > 0.0 and s_ref > 1e-3:
        tol_m = float(cfg_get(env.cfg, "reward",
                              "anchor_tol_mm",
                              default=10.0)) / 1000.0
        loaded = 0
        anchored = 0
        for f in range(6):
            adr = env._touch_adr[f]
            on = (adr >= 0 and
                  float(env.data.sensordata[adr]) > 0.5)
            xy = env.data.xpos[env._pad_bids[f], :2]
            if on and not env._anchor_prev_on[f]:
                env._anchor_xy[f] = xy.copy()
            elif not on:
                env._anchor_xy[f] = None
            env._anchor_prev_on[f] = on
            if on and env._anchor_xy[f] is not None:
                loaded += 1
                if float(np.linalg.norm(
                        xy - env._anchor_xy[f])) <= tol_m:
                    anchored += 1
        frac = (anchored / loaded) if loaded > 0 else 0.0
        a_factor = (1.0 - g_anchor) + g_anchor * frac
        r_walk *= a_factor
        support_gate *= a_factor
        if r_prog > 0.0:
            r_prog *= a_factor
        info["walk_anchor_frac"] = frac
    return r_prog, r_walk, support_gate
