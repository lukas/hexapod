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
