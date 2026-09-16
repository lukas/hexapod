"""Walk-mode reward CHARGES, moved out of SimHexapodJointWalkEnv._post_step.

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


def idle_travel_floor_charge(env, along, info, reward, s_ref):
    # Anti-park TRAVEL FLOOR charge (operator order 2026-08-21,
    # from-scratch anti-slip walking): every prior from-scratch
    # gait arm collapsed into freeze or march-in-place, and a
    # slip-per-metre objective is meaningless at ~zero travel.
    # This charges, per second of COMMANDED motion, the
    # shortfall of the body's smoothed along-command speed below
    # reward.walk_idle_speed_m_s: r -= k * clip((floor - ema)/
    # floor, 0, 1) * dt. A parked or marching-in-place body pays
    # the full k per second; a body creeping at half the floor
    # pays half; anything travelling at or above the floor pays
    # nothing, and there is no upper bound to hit (this is a
    # FLOOR, not a speed band). The EMA (reward.walk_idle_tau_s,
    # default 1 s) is what makes it smooth and gradient-bearing:
    # a real gait's per-tick along speed oscillates through zero
    # every stride and must not be charged for that. Added AFTER
    # the income gates so no gate can shrink it. Default 0 =
    # off, legacy bit-exact (no new info keys, no state use).
    # cfg: reward.k_walk_idle_charge, reward.walk_idle_speed_m_s,
    # reward.walk_idle_tau_s.
    k_idle = float(cfg_get(env.cfg, "reward",
                           "k_walk_idle_charge", default=0.0)) \
        * env._walk_charge_scale()
    if k_idle > 0.0 and s_ref > 1e-3:
        tau = max(float(cfg_get(env.cfg, "reward",
                                "walk_idle_tau_s", default=1.0)),
                  env.dt)
        env._walk_idle_ema += (env.dt / tau) * (
            float(along) - env._walk_idle_ema)
        floor_v = max(float(cfg_get(
            env.cfg, "reward", "walk_idle_speed_m_s",
            default=0.03)), 1e-6)
        shortfall = min(max(
            (floor_v - env._walk_idle_ema) / floor_v, 0.0), 1.0)
        r_idle = -k_idle * shortfall * env.dt
        reward = float(reward) + r_idle
        info["walk_along_ema_m_s"] = env._walk_idle_ema
        info["walk_idle_shortfall"] = shortfall
        info["reward_walk_idle"] = r_idle
    return reward


def move_current_charge(env, info, reward, s_ref):
    # Commanded-WALK (translating-tick) actuator-current charge
    # (2026-08-25, gaitgate-scratch1/tf64-mesh-acq1 dig-in): the
    # mesh model family (+66% mass vs the legacy primitive
    # calibration) makes a rigid partial-tripod HOLD the
    # cheapest way to satisfy walk income under this reward
    # stack -- 3 legs lock permanently planted (duty_cycle
    # ~1.0) while the other 3 are held aloft, concentrating
    # stance load until the shared safety current trip
    # (>2.5 A sustained 0.8 s through a 0.1 s LPF) fires
    # (over_current, not topple). This is the WALKING-tick
    # analog of k_walk_stop_current above (same mechanism:
    # price sustained per-servo current above a headroom
    # threshold, quadratically, every commanded-translating
    # tick) -- confirmed NECESSARY because reward.walk_gait_gate
    # (the min-across-legs step-completion gate, the other
    # tried anti-sacrifice lever) does not fix this: a policy
    # can satisfy a rolling swing-completion window with rare
    # token swings while spending most ticks in the same rigid
    # lock, so it is gameable and, measured directly
    # (gaitgate-scratch1 vs its ungated parent), made the
    # held-out fall rate WORSE (39/48 vs 12/48), not better.
    # Threshold (2.2 A) is set
    # ABOVE the stop-tick threshold (1.5 A) and below the trip
    # (2.5 A) deliberately: honest six-leg cycling legitimately
    # draws current in brief per-leg stance-loading spikes
    # (the scripted teacher itself touches up to 2.627 A on
    # 29% of ticks but with max per-servo DWELL 0.32 s) -- a
    # per-tick quadratic-over-threshold charge already prices
    # DURATION correctly with no extra state (an episode-long
    # lock pays every tick; a 0.32 s honest spike pays for
    # 0.32 s), so 2.2 A leaves brief honest spikes cheap while
    # a sustained near-trip hold accumulates a large charge.
    # Commanded-translating ticks only (s_ref > 1e-3, the
    # mirror-image scope of the stop charge above); added
    # AFTER the income gates (gait-gate rule). Default 0 = off,
    # legacy bit-exact (no new info keys, no behavior change
    # for any existing recipe that doesn't set this cfg).
    # cfg: reward.k_walk_move_current.
    k_movecur = float(cfg_get(env.cfg, "reward",
                              "k_walk_move_current", default=0.0))
    if k_movecur > 0.0 and s_ref > 1e-3:
        cur_mv = getattr(env._state, "servo_current", None)
        if cur_mv is not None:
            thr_mv = 2.2
            cap_mv = 4.0
            over_mv = np.maximum(
                np.abs(np.asarray(cur_mv, dtype=float)) - thr_mv,
                0.0)
            r_movecur = -k_movecur * min(
                float(np.sum(over_mv ** 2)), cap_mv)
            reward = float(reward) + r_movecur
            info["walk_move_current_max_a"] = float(
                np.max(np.abs(cur_mv)))
            info["reward_walk_move_current"] = r_movecur
    return reward


def stop_charges(env, goal, info, reward, s_ref, v):
    # Commanded-STOP speed charge (2026-08-24, joyfullcurr6
    # dig-in): during commanded-stop segments NOTHING in this
    # stack prices residual body speed except the shallow
    # Gaussian kernel (stillness 2.0/tick vs a 0.04 m/s creep's
    # 1.45/tick, +0.55/tick margin) — every other walk term
    # (prog gate, course, park-duty, step/drag, idle) is guarded
    # by s_ref > 1e-3 and pays/charges NOTHING on stop ticks.
    # The V6 ladder's cert bar (mean stop-tick speed <= 0.015
    # m/s) therefore had no matching reward optimum, and the
    # 40M joyfullcurr6 run converged to a ~0.04 m/s creep that
    # failed the b1 stop cert ~79 rounds in a row while reward
    # sat converged. This charges, on stop ticks only (s_ref ~
    # 0 and NOT a commanded turn-in-place — that motion is the
    # command), the instantaneous body speed against the
    # 0.015 m/s cert bar: r -= k * min(speed/scale, cap).
    # Stillness pays 0,
    # the observed creep pays ~2.7k/tick, walking through a
    # stop pays the cap — so true stillness is the optimum by
    # construction, matching the cert exactly. Added AFTER the
    # income gates so no gate can shrink it. NOT part of the
    # walk_charge_ramp trio (that ramp loosens charges that
    # make refusal falsely cheap; this one prices obedience to
    # an explicit stop command and must never loosen). Default
    # 0 = off, legacy bit-exact (no new info keys).
    # cfg: reward.k_walk_stop_charge, reward.walk_stop_grace_s.
    k_stopc = float(cfg_get(env.cfg, "reward",
                            "k_walk_stop_charge", default=0.0))
    # Read the stop-CURRENT gain here too: both stop charges
    # share the _walk_stop_cmd_s grace timer, so the timer must
    # tick whenever EITHER is armed (k_stopcur=0 default keeps
    # the guard identical to the pre-current-charge code).
    k_stopcur = float(cfg_get(env.cfg, "reward",
                              "k_walk_stop_current", default=0.0))
    if k_stopc > 0.0 or k_stopcur > 0.0:
        # Elapsed time since the current stop segment began
        # (reset the instant translation is commanded again).
        # Tracked whenever the charge is active at all so the
        # ramp below is correct from the very first stop tick,
        # independent of the turn-in-place exemption.
        if s_ref > 1e-3:
            env._walk_stop_cmd_s = 0.0
        else:
            env._walk_stop_cmd_s += env.dt
    if (k_stopc > 0.0 and s_ref <= 1e-3
            and not (env._yaw_cmd
                     and abs(float(getattr(goal, "wz_ref", 0.0)
                                   or 0.0)) > 1e-3)):
        scale_sc = 0.015
        cap_sc = 4.0
        # Settle-grace (2026-08-24, joyfullcurr7 dig-in): the
        # plain charge above priced the UNAVOIDABLE physical
        # deceleration transient right after a stop command as
        # harshly as sustained creep, and joyfullcurr7 (k=1.0,
        # no grace) measured the consequence directly — every
        # fall in its held-out joygate session was an
        # over_current safety trip, not roll/tilt: the policy
        # was braking hard enough to spike actuator current.
        # grace_s > 0 linearly ramps the charge's MULTIPLIER
        # from 0 at the instant a stop begins to 1.0 at
        # grace_s seconds in (then holds at 1.0) so the
        # transient pays little/nothing while SUSTAINED creep
        # past the grace window still pays the full charge —
        # the actual cert-bar violation. Default 0 = off,
        # bit-exact (grace_mult stays exactly 1.0, identical
        # to the pre-grace formula).
        grace_s = float(cfg_get(env.cfg, "reward",
                                "walk_stop_grace_s", default=0.0))
        grace_mult = 1.0
        if grace_s > 1e-6:
            grace_mult = min(max(
                env._walk_stop_cmd_s / grace_s, 0.0), 1.0)
        sp_sc = float(np.hypot(float(v[0]), float(v[1])))
        r_stopc = -k_stopc * grace_mult * min(sp_sc / scale_sc,
                                               cap_sc)
        reward = float(reward) + r_stopc
        info["walk_stop_speed_m_s"] = sp_sc
        info["reward_walk_stop"] = r_stopc
        info["walk_stop_grace_mult"] = grace_mult
    # Commanded-STOP actuator-current charge (2026-08-24,
    # joyfullcurr8 dig-in): joyfullcurr7 (stop-speed charge,
    # no grace) and joyfullcurr8 (+0.4s grace ramp) BOTH ended
    # with 100% of held-out joygate falls = over_current; the
    # grace ramp moved slip/dir_err but over_current not at
    # all. Root cause: the SafetyLayer trips on servo current
    # > 2.5 A SUSTAINED for 0.8 s through a ~0.1 s low-pass
    # (safety.py / sim_env._read_state) -- that is not a
    # braking transient, it is a sustained isometric fight
    # (stiff position targets pressing against contact) held
    # through the stop stance. NOTHING in the stack prices
    # that fight on stop ticks (k_current_hot is global and
    # OFF in this lineage), so speed-based stop pricing pushes
    # the policy INTO it: braking/freezing hard is the
    # cheapest way to zero the speed charge. This charges, on
    # stop ticks only (same s_ref/turn-in-place scoping as the
    # speed charge above), per-servo current quadratically
    # above a headroom threshold (default 1.5 A = 1.0 A under
    # the trip): r -= k * grace_mult * min(sum(max(|I|-thr,0)^2),
    # cap). A settled deadband stance draws ~0 A (sim_env
    # firmware dead-zone), so RELAXED stillness pays nothing
    # -- the optimum is stop-without-fighting, exactly what
    # the joygate demands. Level charge, not current-rate: the
    # trip fires on sustained level, and the 0.1 s LPF already
    # erases spikes a rate term would price. Shares
    # walk_stop_grace_s (same timer) so the unavoidable
    # braking current of the first grace window pays little.
    # Added AFTER the income gates (gait-gate rule). Default
    # 0 = off, legacy bit-exact (no new info keys).
    # cfg: reward.k_walk_stop_current (+ shared walk_stop_grace_s).
    if (k_stopcur > 0.0 and s_ref <= 1e-3
            and not (env._yaw_cmd
                     and abs(float(getattr(goal, "wz_ref", 0.0)
                                   or 0.0)) > 1e-3)):
        cur_sc = getattr(env._state, "servo_current", None)
        if cur_sc is not None:
            thr_cur = 1.5
            cap_cur = 4.0
            grace_s_cur = float(cfg_get(env.cfg, "reward",
                                        "walk_stop_grace_s",
                                        default=0.0))
            gm_cur = 1.0
            if grace_s_cur > 1e-6:
                gm_cur = min(max(
                    env._walk_stop_cmd_s / grace_s_cur, 0.0), 1.0)
            over_cur = np.maximum(
                np.abs(np.asarray(cur_sc, dtype=float)) - thr_cur,
                0.0)
            r_stopcur = -k_stopcur * gm_cur * min(
                float(np.sum(over_cur ** 2)), cap_cur)
            reward = float(reward) + r_stopcur
            info["walk_stop_current_max_a"] = float(
                np.max(np.abs(cur_sc)))
            info["reward_walk_stop_current"] = r_stopcur
    return reward
