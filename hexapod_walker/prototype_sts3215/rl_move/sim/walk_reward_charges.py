"""Walk-mode reward CHARGES, moved out of SimHexapodJointWalkEnv._post_step.

Every function here is one contiguous block of the walk-mode pricing stack
moved mechanically: ``env`` is the env instance (the former ``self``), the
remaining parameters are the block's live inputs and the return values its
live outputs, so the call site in ``_post_step`` is a single assignment.
Bodies are byte-identical to the original apart from ``self`` -> ``env``
and re-indentation; the header comments travelled with the code.
"""
from __future__ import annotations

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
