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
