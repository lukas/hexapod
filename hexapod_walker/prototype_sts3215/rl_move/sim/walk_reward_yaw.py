"""Walk-mode YAW reward terms, moved out of SimHexapodJointWalkEnv._post_step.

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


def turn_in_place_kernel_gate_and_freeze(env, goal, info, r_walk, s_ref):
    # Achieved-yaw kernel gate for turn-in-place ticks (08-11,
    # cw-omni-mirror1-r1 freeze exploit; cfg
    # reward.walk_kernel_yaw_gate in [0,1], default 0=off).
    # Root cause (probe-confirmed): on yaw-commanded ticks with
    # NO linear command (s_ref ~ 0, wz_ref != 0) the linear
    # kernel above pays a FROZEN robot full income — v_lin = 0
    # matches ref exactly and walk_kernel_prog_gate never
    # engages (it requires s_ref > 1e-3). With turn-in-place
    # episodes at 30% of training, a park banked ~1130/ep, more
    # than the mid-training policy earned by walking (500-860)
    # — so PPO parked and the 40M run collapsed. Fix: on those
    # ticks multiply the linear kernel by achieved-yaw fraction
    # clip(wz/wz_ref, 0, 1) — the exact prog-gate analog.
    # Freeze/wrong-direction earns ~0 by construction; perfect
    # turning unchanged (factor 1); genuine stop segments
    # (s_ref ~ 0 AND wz_ref ~ 0) stay paid — standing there IS
    # the commanded behavior. Walk-mode only by construction.
    g_ykernel = float(cfg_get(env.cfg, "reward",
                              "walk_kernel_yaw_gate",
                              default=0.0))
    if (g_ykernel > 0.0 and env._yaw_cmd and s_ref <= 1e-3
            and abs(goal.wz_ref) > 1e-3):
        wz_k = env._body_wz()
        factor = min(max(wz_k / goal.wz_ref, 0.0), 1.0)
        r_walk *= (1.0 - g_ykernel) + g_ykernel * factor
        info["walk_yaw_kernel_factor"] = factor
    # Explicit minimum-motion tie-break CHARGE for turn-in-
    # place ticks (09-11, `term_penalty_ramp{0,100}-canary2m`
    # FAIL-MECHANISM pair; the escalation both that pair's own
    # gate and the parent `turnramp-cont6m`/`canary2m` verdicts
    # named as the next and last remaining single-lever
    # mechanism after FOUR prior canaries -- yawprice3x
    # (price), turnramp (dose), turnramp-cont6m (budget),
    # termramp{0,100} (risk-curriculum ramp) -- all reproduced
    # the identical static splayed freeze-crouch. Root cause:
    # the kernel gates immediately above
    # (walk_kernel_yaw_gate/walk_yaw_kernel_gate) already make
    # a frozen body earn ~0 income on these ticks, but ~0 is
    # only REWARD-NEUTRAL, and PPO is comparing it against a
    # real -400 term_penalty risk if a clumsy turn attempt
    # trips over_current/tilt -- a risk-averse policy's optimal
    # response to "0 income, 0 risk" beating "~0 income,
    # nonzero risk" is exactly the observed freeze. No income
    # fix on the reward side can repair a risk-side asymmetry,
    # which is why all four income/price/budget/ramp levers
    # failed identically. This charges freeze directly instead
    # of pricing income: on turn-in-place ticks (s_ref ~ 0,
    # wz_ref != 0 -- the IDENTICAL gating condition as
    # walk_kernel_yaw_gate/walk_yaw_kernel_gate above) with
    # achieved |wz| below reward.walk_turn_freeze_wz_thresh
    # rad/s (default 0.05, well under any commanded
    # goal.walk_yaw_max_rad_s in this recipe and above gyro
    # noise), charge a flat -reward.walk_turn_freeze_charge
    # per tick. Additive (never multiplies r_walk/r_prog/
    # r_cmd_track, matching every other per-tick charge in
    # this file) and STATELESS (instantaneous wz vs a fixed
    # threshold -- no EMA, no MJX_SNAPSHOT_EXTRA plumbing
    # needed). Makes freeze strictly reward-NEGATIVE relative
    # to any attempted motion above the noise floor, on top of
    # (not instead of) the existing achieved-yaw kernel gates;
    # an honestly-turning gait's wz oscillates well above
    # 0.05 rad/s and pays nothing extra, only a genuinely
    # still body is charged. Default 0.0 = off, bit-exact
    # legacy (no state read, no info key written). See
    # test_walk_turn_freeze_charge.py.
    g_freeze = float(cfg_get(env.cfg, "reward",
                             "walk_turn_freeze_charge",
                             default=0.0))
    r_freeze = 0.0
    if (g_freeze > 0.0 and env._yaw_cmd and s_ref <= 1e-3
            and abs(goal.wz_ref) > 1e-3):
        wz_freeze_thresh = float(cfg_get(
            env.cfg, "reward", "walk_turn_freeze_wz_thresh",
            default=0.05))
        wz_freeze_now = env._body_wz()
        info["walk_turn_freeze_wz"] = wz_freeze_now
        if abs(wz_freeze_now) < wz_freeze_thresh:
            r_freeze = -g_freeze
        info["reward_walk_turn_freeze"] = r_freeze
    # Turn-in-place tick flag (09-11, escalation after FIVE
    # single-lever reward-side fixes on the turn-in-place
    # freeze all failed identically -- yawprice3x (price),
    # turnramp (dose), turnramp-cont6m (budget), termramp{0,100}
    # (risk-curriculum ramp), walk_turn_freeze_charge (direct
    # charge, this cycle's freezecharge{,5,10}-canary2m triple,
    # all three CANARY FAIL-MECHANISM: same static splayed
    # freeze-crouch on video regardless of dose). Every one of
    # those levers moves the SAME per-tick task-reward ledger
    # PPO's value function already prices identically to the
    # `term_penalty` risk it's weighed against -- the standing
    # gate's own next-named class is a mechanism ORTHOGONAL to
    # that ledger: a state-novelty (RND) exploration bonus
    # gated onto these exact ticks (rnd_vec.RNDVecWrapper's new
    # `info_gate_key`), which pays for visiting new states
    # regardless of task outcome and decays as a pose is
    # repeatedly revisited -- unlike a fixed charge/price, it
    # cannot be "outbid" by a fixed term_penalty at high
    # magnitude the way the charge dose sweep just was. This
    # flag is the READ-ONLY hook that lets the vec-env-level
    # RND wrapper see which ticks are live turn-in-place
    # (identical gating condition as the kernel gates/freeze
    # charge above: s_ref ~ 0, wz_ref != 0, walk_yaw_cmd=1) --
    # it carries no reward of its own and is written whenever
    # walk_yaw_cmd=1 (an already-opt-in new-lineage flag), so
    # every pre-09-11 lineage (walk_yaw_cmd=0) never sees this
    # key at all. See test_walk_turn_freeze_charge.py.
    if env._yaw_cmd:
        info["walk_turn_in_place_tick"] = (
            1.0 if (s_ref <= 1e-3 and abs(goal.wz_ref) > 1e-3)
            else 0.0)
    return r_walk, r_freeze


def anti_drift_yaw_pricing(env, goal, info, reward):
    # Anti-drift yaw pricing (operator, 08-10). Price
    # ESCALATION on the symmetric kernel is CLOSED (yawcmd1 /
    # yawgate1 / yawgate2: the structural ~+0.09 rad/s left
    # drift survives any kernel weight — near wz_ref=0 the
    # Gaussian's gradient at the drift point is tiny, and on
    # turn segments the kernel never goes NEGATIVE for
    # wrong-direction rotation). Two different mechanisms,
    # both default 0 = byte-identical legacy:
    #  - reward.k_yaw_prog: SIGNED rotation income, the
    #    k_walk_prog analog for turn segments: pay
    #    k * clip(wz/wz_ref, -1.5, 1.25) — constant gradient
    #    toward the commanded direction and genuinely negative
    #    when rotating against it.
    #  - reward.k_yaw_still: quadratic drift charge on
    #    heading-hold segments (wz_ref == 0): -k * wz^2. At
    #    the measured drift (0.09 rad/s) k=50 costs ~0.4/tick
    #    (real money vs the ~2/tick kernel); gyro-noise-level
    #    wz stays ~free by the square law.
    if env._yaw_cmd:
        k_yp = float(cfg_get(env.cfg, "reward", "k_yaw_prog",
                             default=0.0))
        k_ys = float(cfg_get(env.cfg, "reward", "k_yaw_still",
                             default=0.0))
        if k_yp > 0.0 or k_ys > 0.0:
            wz_now = env._body_wz()
            if k_yp > 0.0 and abs(goal.wz_ref) > 1e-3:
                # OVER-SPIN FARM FIX (08-23 income audit,
                # probe_walk_income yawcmd0 stack): the legacy
                # clip's +1.25 headroom makes OVER-rotation
                # strictly dominant — the gradient points to
                # ratio 1.25, not 1.0, and the eroded acq1-r2
                # policy measurably farmed it (yaw_progress
                # ratio 1.78, yaw_prog income +14% over the
                # accurate champion; also explains yawprice3x
                # getting WORSE with 3x income). cfg
                # reward.yaw_prog_overshoot_decay > 0 makes
                # income PEAK at ratio 1.0 and decay linearly
                # past it (never below 0 on the overshoot
                # side, so gyro noise is not punished);
                # default 0.0 = bit-exact legacy clip.
                # DC-vs-AC (same defect class as the 08-11
                # yaw_still fix): pricing the INSTANTANEOUS wz
                # pays the smooth fast spinner and fines the
                # honest gait's zero-mean stride oscillation
                # (measured 08-23: a 0.95-ratio tracker earned
                # NEGATIVE yaw_prog while a 2.0-ratio spinner
                # earned +). cfg reward.yaw_prog_avg_s = EMA
                # time constant (s) for the wz used in the
                # ratio; default 0 = legacy instantaneous.
                # Per-episode EMA state rides
                # MJX_SNAPSHOT_EXTRA like _yaw_still_ema.
                tau_p = float(cfg_get(env.cfg, "reward",
                                      "yaw_prog_avg_s",
                                      default=0.0))
                if tau_p > 0.0:
                    a_ema = min(env.dt / tau_p, 1.0)
                    env._yaw_prog_ema += a_ema * (
                        wz_now - env._yaw_prog_ema)
                    wz_p = env._yaw_prog_ema
                    info["yaw_prog_wz_avg"] = wz_p
                else:
                    wz_p = wz_now
                ratio = wz_p / goal.wz_ref
                decay = float(cfg_get(
                    env.cfg, "reward",
                    "yaw_prog_overshoot_decay", default=0.0))
                if decay > 0.0 and ratio > 1.0:
                    val = max(1.0 - decay * (ratio - 1.0), 0.0)
                else:
                    val = min(max(ratio, -1.5), 1.25)
                r_yp = k_yp * val
                reward = float(reward) + r_yp
                info["reward_yaw_prog"] = r_yp
            if k_ys > 0.0 and abs(goal.wz_ref) <= 1e-3:
                # DC-drift charge, not oscillation tax (08-11,
                # probe_walk_income latent-defect fix). The
                # instantaneous -k*wz^2 charged the honest
                # gait's zero-mean stride oscillation
                # (wz_rms ~ 0.044) about -73/ep while a frozen
                # body paid ~0 — the charge taxed exactly the
                # wrong policy. The drift being priced is DC
                # (a fixed ~+0.09 rad/s offset); the gait's
                # oscillation is zero-mean AC. Charging the
                # EMA of wz separates them: the oscillation
                # averages toward 0, the drift keeps its full
                # offset. cfg reward.yaw_still_avg_s = EMA time
                # constant in seconds, default 0 = legacy
                # instantaneous (byte-identical). Per-episode
                # EMA state rides MJX_SNAPSHOT_EXTRA
                # (pool-restore lesson, commit 65edba7).
                tau = float(cfg_get(env.cfg, "reward",
                                    "yaw_still_avg_s",
                                    default=0.0))
                if tau > 0.0:
                    a_ema = min(env.dt / tau, 1.0)
                    env._yaw_still_ema += a_ema * (
                        wz_now - env._yaw_still_ema)
                    wz_chg = env._yaw_still_ema
                    info["yaw_still_wz_avg"] = wz_chg
                else:
                    wz_chg = wz_now
                r_ys = -k_ys * wz_chg * wz_chg
                reward = float(reward) + r_ys
                info["reward_yaw_still"] = r_ys
    return reward


def yaw_rate_kernel(env, along, goal, info, reward, s_ref):
    # Yaw-rate tracking kernel (goal.walk_yaw_cmd lineage only;
    # reward.k_walk_yaw default 0 = off). Paid in EVERY walk
    # tick, including wz_ref = 0 — heading-hold earns income, so
    # the free ~+10 deg/20 s drift of the yaw-blind lineage is
    # finally priced. NOT gated on s_ref: a stop segment with
    # wz_ref != 0 is a commanded turn in place and must pay.
    k_yaw = float(cfg_get(env.cfg, "reward", "k_walk_yaw",
                          default=0.0))
    if env._yaw_cmd and k_yaw > 0.0:
        wz = env._body_wz()
        sig_w = 0.15
        # Stride-EMA yaw kernel (08-23, hold/forward income-
        # dominance audit, probe_walk_income yawcmd0 stack): the
        # SAME sway-tax defect the walk_kernel_vel_ema fix
        # (phasedir7/7b/8) repaired for the linear-velocity
        # kernel exists here too, unfixed — a genuine full-stop
        # hold command pins wz near 0 with almost no variance
        # (nothing is moving), while an honest walking/turning
        # gait's body yaw-rate oscillates stride-to-stride around
        # its achieved mean even when perfectly on-command, so
        # the INSTANTANEOUS Gaussian never sits at its peak for
        # real motion the way it does for standing still.
        # Measured (probe_walk_income, ypfix1 checkpoint, full
        # 15s pinned segments): reward_walk_yaw hold=374 vs
        # forward=203 vs tip_left/right=132/147 — a real
        # richness gap on TOP of the k_yaw_prog/k_yaw_still
        # progress bonuses those segments already collect, part
        # of the measured hold/forward income dominance
        # (q_20260823T0240Z item b) that eroded turn+push
        # tracking under extra budget (tipfrac05-acq1). Fix
        # mirrors walk_kernel_vel_ema exactly in scope: ONLY the
        # kernel's err term is smoothed; the g_yaw/g_hold
        # achieved-rotation/achieved-progress gates below and
        # k_yaw_prog/k_yaw_still still use the RAW instantaneous
        # wz (those are correctness gates on real behavior, not
        # a shaping kernel, and must not be desensitized).
        # cfg reward.walk_kernel_yaw_ema > 0 turns it on; default
        # 0.0 = bit-exact legacy (raw wz, unchanged). Update is
        # unconditional while the flag is on (matches
        # walk_kernel_vel_ema's stop-segments-included
        # convention: the EMA lags any transition by ~tau for
        # every candidate behavior equally, so it cannot be
        # gamed by timing a segment boundary).
        if float(cfg_get(env.cfg, "reward", "walk_kernel_yaw_ema",
                         default=0.0)) > 0.0:
            tau_kw = max(float(cfg_get(
                env.cfg, "reward", "walk_kernel_yaw_tau_s",
                default=0.75)), env.dt)
            a_kw = env.dt / tau_kw
            env._walk_kernel_wz_ema += a_kw * (
                wz - env._walk_kernel_wz_ema)
            wz_kernel = env._walk_kernel_wz_ema
            info["walk_kernel_wz_ema"] = wz_kernel
        else:
            wz_kernel = wz
        yaw_err = wz - goal.wz_ref
        yaw_err_kernel = wz_kernel - goal.wz_ref
        r_yaw = k_yaw * math.exp(
            -(yaw_err_kernel ** 2) / (2.0 * sig_w ** 2))
        # Yaw income gated on ACHIEVED rotation (cw-walk-yawcmd1
        # dig-in, 08-10: with sigma 0.15 the ungated kernel pays
        # a command-ignoring policy exp(-.5*(0.135/0.15)^2)=0.67
        # of max income every tick — both yawcmd1 seeds learned
        # exactly that: command-invariant ~+0.09 rad/s drift,
        # turn |wz_err| med 0.24 vs gate 0.10. This was the
        # pre-registered WISHLIST item-3 risk; fix is the
        # walk_kernel_prog_gate analog: on turn segments
        # multiply yaw income by clip(wz/wz_ref, 0, 1) —
        # parked/wrong-direction earns ~0 by construction,
        # perfect tracking unchanged, over-rotation clipped
        # (the Gaussian already prices overshoot). Hold
        # segments (wz_ref=0) have no fraction-of-zero, so this
        # gate skips them — but see walk_yaw_hold_prog_gate
        # below (08-11): ungated hold income turned out to be a
        # stillness subsidy, priced by linear progress instead.
        # cfg reward.walk_yaw_kernel_gate in [0,1], default
        # 0=off (byte-identical to pre-change behavior).
        g_yaw = float(cfg_get(env.cfg, "reward",
                              "walk_yaw_kernel_gate",
                              default=0.0))
        if g_yaw > 0.0 and abs(goal.wz_ref) > 1e-3:
            factor = min(max(wz / goal.wz_ref, 0.0), 1.0)
            r_yaw *= (1.0 - g_yaw) + g_yaw * factor
            info["walk_yaw_gate_factor"] = factor
        # Heading-hold yaw income gated on achieved LINEAR
        # progress (08-11, probe_walk_income latent-defect fix).
        # Root cause (probe, mirror2 stack): on linear-command
        # ticks (s_ref > 0, wz_ref = 0) the "hold segments stay
        # ungated" branch above pays a MOTIONLESS body full
        # heading-hold income — wz = 0 matches the zero yaw ref
        # exactly — 373-375/ep to freeze, sacrifice and paddle
        # alike, the single largest channel in the turn stack,
        # while the honest gait's natural wz oscillation earns
        # slightly less AND pays k_yaw_still. Net: the yaw stack
        # taxed honest walking ~-100/ep RELATIVE to stillness.
        # Fix is the walk_kernel_yaw_gate mirror image: on those
        # ticks multiply yaw income by achieved-progress
        # fraction clip(along/s_ref, 0, 1). A freeze earns ~0
        # heading-hold income by construction; a tracking walker
        # keeps it all. Genuine stop segments (s_ref ~ 0 AND
        # wz_ref ~ 0) stay paid — standing still with no body
        # spin IS the commanded behavior there. cfg
        # reward.walk_yaw_hold_prog_gate in [0,1], default
        # 0 = off (byte-identical legacy).
        g_hold = float(cfg_get(env.cfg, "reward",
                               "walk_yaw_hold_prog_gate",
                               default=0.0))
        if (g_hold > 0.0 and abs(goal.wz_ref) <= 1e-3
                and s_ref > 1e-3):
            factor = min(max(along / s_ref, 0.0), 1.0)
            r_yaw *= (1.0 - g_hold) + g_hold * factor
            info["walk_yaw_hold_factor"] = factor
        # COMBINED-TICK BOOST (09-03, standwalk item-2
        # branch-(b)-v2, "a combined-tick-targeted course/yaw
        # reward term" — the remaining fallback after
        # bc_anchor_walk_combined_skip/bc_anchor_teacher_
        # omega_boost both REFUTED 4/4 canary cells). The
        # family's own ledger cfg already trains with
        # k_walk_yaw=1.0 applied to EVERY walk tick (cap29-
        # stdwalklo-hi and every downstream canary), so a GATE
        # that zeroed this income outside combined ticks would
        # remove supervision from the already-working pure-
        # turn behavior (probe_turn_authority: wz~0.18-0.23
        # rad/s on a 0.25 rad/s pure-turn command) instead of
        # adding to the known-degraded combined-tick behavior
        # (sim_env.py's `_bc_combined_early` comment: the
        # scripted teacher itself retains only ~33% of its
        # pure-turn wz authority once a forward speed is
        # commanded simultaneously). A multiplicative BOOST,
        # not a gate, is the surgical lever: only combined
        # ticks get their existing k_walk_yaw income scaled
        # up, so the yaw kernel's gradient can compete with
        # the anchor's own degraded pull specifically there,
        # while every other walk tick (pure-turn, straight,
        # hold) is bit-exact unchanged. cfg reward.walk_yaw_
        # combined_boost, default 1.0 = identity (bit-exact
        # no-op), matching every other *_boost knob in this
        # file (train.bc_anchor_teacher_omega_boost). See
        # test_task_semantics.py test_walk_yaw_combined_boost_*.
        _yaw_combined_boost = float(cfg_get(
            env.cfg, "reward", "walk_yaw_combined_boost",
            default=1.0))
        if _yaw_combined_boost != 1.0:
            _combined_tick = (s_ref > 1e-3
                              and abs(goal.wz_ref) > 1e-3)
            if _combined_tick:
                r_yaw *= _yaw_combined_boost
            info["walk_yaw_combined_tick"] = float(_combined_tick)
        reward = float(reward) + r_yaw
        info["reward_walk_yaw"] = r_yaw
        info["walk_yaw_err"] = abs(yaw_err)
        info["walk_wz"] = wz
    return reward


def yaw_offset_kernel(env, goal, info, reward):
    """Task-space TURN-OFFSET reward (walkcurr Next item; design
    sketched track STATUS.md 2026-09-25 ~13:5x, built 2026-09-26 after
    the rate-based tip_frac==0 "walk+curve specialist" composition
    route CLOSED 0/2 seeds on the SAME eased-cap contract:
    `cw-walkyaw50hz-rlonly-scratch-sac-{s0,s1}-easedterm-tipfrac0-
    acq1`, both FAIL on sacrificed legs / prog / wrong-way). Every
    closed rate-based mechanism above (`yaw_rate_kernel`,
    `anti_drift_yaw_pricing`, ...) prices a continuous commanded
    yaw-RATE every tick — either pinned at exactly 0 (heading-hold) or
    a nonzero band with an instant flip at resample boundaries — so
    the policy must simultaneously hold near-zero rate AND spin at a
    commanded rate within the SAME continuous-control episode, with no
    notion of "the turn is done." This function instead prices the
    REMAINING error between a discrete target relative-heading OFFSET
    (drawn once per episode/segment in walk_task._sample_walk from
    goal.walk_yaw_offset_set) and the cumulative body rotation actually
    achieved since the command was issued (env._yaw_offset_achieved,
    integrated from env._body_wz() every tick — avoids any atan2
    wraparound since offsets stay well under one full turn). A
    0-degree offset now settles the SAME position-error kernel at 0 as
    every other offset, removing the bang-bang rate/zero dichotomy the
    closed mechanism could never resolve.

    Two additive, independently-gated terms, both default 0.0 = off,
    bit-exact legacy (goal.walk_yaw_offset_set unset -> env._yaw_
    offset_cmd False -> this function returns reward unchanged, no
    info keys, no state mutation):
      - reward.k_walk_yaw_offset: Gaussian kernel on the remaining
        error (width reward.walk_yaw_offset_sigma_rad) — shapes the
        approach, same family as every other kernel in this file.
      - reward.k_walk_yaw_offset_hold: flat per-tick bonus paid only
        while |remaining error| <= reward.walk_yaw_offset_tol_rad —
        the settle/hold analog of walk_yaw_hold_prog_gate/k_yaw_still,
        rewarding STAYING at the target rather than merely passing
        through it.

    Runs on every walk tick this lineage trains with (not gated on
    s_ref: the linear command is forced to zero whenever _sample_walk
    draws this mode, so s_ref is already ~0 on those ticks). Episodes
    where the frac draw did not fire keep yaw_offset_ref at its
    default 0.0 — i.e. "hold whatever heading you started at," a
    sensible degenerate case, not a separate exclusion flag.
    See test_walk_yaw_offset.py.
    """
    if not getattr(env, "_yaw_offset_cmd", False):
        return reward
    target = float(getattr(goal, "yaw_offset_ref", 0.0))
    env._yaw_offset_achieved += env._body_wz() * env.dt
    err = target - env._yaw_offset_achieved
    info["walk_yaw_offset_target"] = target
    info["walk_yaw_offset_achieved"] = env._yaw_offset_achieved
    info["walk_yaw_offset_err"] = err
    k_kernel = float(cfg_get(env.cfg, "reward", "k_walk_yaw_offset",
                             default=0.0))
    if k_kernel > 0.0:
        sigma = max(float(cfg_get(
            env.cfg, "reward", "walk_yaw_offset_sigma_rad",
            default=0.35)), 1e-6)
        r_off = k_kernel * math.exp(-(err ** 2) / (2.0 * sigma ** 2))
        reward = float(reward) + r_off
        info["reward_walk_yaw_offset"] = r_off
    k_hold = float(cfg_get(env.cfg, "reward", "k_walk_yaw_offset_hold",
                           default=0.0))
    if k_hold > 0.0:
        tol = float(cfg_get(env.cfg, "reward",
                            "walk_yaw_offset_tol_rad", default=0.07))
        if abs(err) <= tol:
            reward = float(reward) + k_hold
            info["reward_walk_yaw_offset_hold"] = k_hold
    return reward


def turn_kernel_neutral(env, goal, info, r_prog, r_walk, s_ref):
    # Turn-kernel-neutral: strip the BASE velocity-tracking
    # kernel's stand-still subsidy on genuine turn-in-place
    # ticks (09-13, walkyaw tip1/retry1/obspad triple-FAIL
    # root-cause read). All three prior levers on this exact
    # `cw-walkyaw50hz-rlonly-scratch` family (warm-start from
    # a CLEAN rl_only forward walker = obspad, scratch-init =
    # retry1, scratch-init+100%-turn-only-exposure = tip1) and
    # the six reward/exploration-side levers closed earlier on
    # the sibling dualbc/standwalk turn-freeze problem (price,
    # dose, budget, risk-curriculum ramp, direct freeze charge,
    # 4 RND variants) all left `r_walk` (this file's `K_WALK`
    # Gaussian kernel keyed on `err = |v - (vx_ref, vy_ref)|`,
    # computed unconditionally in walk mode, `sigma_v` narrow
    # at 0.05 m/s) COMPLETELY UNTOUCHED and un-gated — none of
    # those levers ever targeted the BASE locomotion kernel,
    # only the yaw-specific terms (`k_walk_yaw`/kernel-gate/
    # hold-prog-gate/`k_yaw_prog`/`k_yaw_still`) or exploration/
    # init/exposure. On a genuine turn-in-place tick (`vx_ref
    # = vy_ref = 0`, the walk_turn_in_place_tick condition
    # below), `err` is minimized (== 0, `r_walk` at its K_WALK=
    # 2.0 MAX) by the body staying perfectly STILL — a reward
    # roughly 2x the yaw stack's own k_walk_yaw=1.0 max, paid
    # unconditionally every tick, requiring zero skill,
    # zero risk, matching probe evidence: `env/walk_vel_err`
    # FALLS and `env/walk_speed` FALLS across training (tip1
    # s1: 0.078->0.060, 0.126->0.105) while `env/walk_wz` stays
    # pinned at noise-floor the whole run -- the policy is
    # measurably learning to move LESS, not more, under a
    # supposedly turn-only command. This does not repair the
    # separately-diagnosed risk-side asymmetry (a fall during
    # a turn attempt still truncates the episode) but removes
    # the one confirmed, previously-untested, actively-PAID
    # incentive to do nothing at all. cfg reward.
    # walk_turn_kernel_neutral in [0,1], default 0.0 = off,
    # bit-exact legacy (no info key, no reward delta). At 1.0,
    # r_walk (and the already-zero r_prog on these ticks) is
    # fully suppressed ONLY on genuine turn-in-place ticks
    # (identical gating condition as walk_turn_freeze_charge/
    # walk_turn_in_place_tick above); every other tick
    # (forward, combined, hold) is untouched. See
    # test_walk_turn_kernel_neutral.py.
    g_turn_neutral = float(cfg_get(
        env.cfg, "reward", "walk_turn_kernel_neutral",
        default=0.0))
    if (g_turn_neutral > 0.0 and env._yaw_cmd
            and s_ref <= 1e-3 and abs(goal.wz_ref) > 1e-3):
        _tn_factor = 1.0 - min(max(g_turn_neutral, 0.0), 1.0)
        r_walk *= _tn_factor
        r_prog *= _tn_factor
        info["walk_turn_kernel_neutral_factor"] = _tn_factor
    return r_prog, r_walk
