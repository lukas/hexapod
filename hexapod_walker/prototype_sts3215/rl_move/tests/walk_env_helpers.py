"""Shared walk-env construction helpers for the joint-action tests.

Extracted 2026-09-08 from the retired MDP_PREFLIGHT bank
(test_task_semantics.py) so its fast mechanics tests could keep running.
Test-support code only; not a test module (no test_ prefix).
"""
from __future__ import annotations

from rl_move.config import cfg_get, load_config
from rl_move.sim.servo_model import SimServoParams

WALK_OVERRIDES = {
    ("reward", "k_step_event"): 1.0,
    ("reward", "k_drag_loaded"): 10.0,
    ("reward", "k_park_duty"): 1.0,
    ("reward", "walk_kernel_prog_gate"): 1.0,
    ("reward", "walk_anchor_gate"): 1.0,
    ("reward", "anchor_tol_mm"): 10.0,
    ("goal", "walk_speed_min_m_s"): 0.05,
    ("goal", "walk_speed_max_m_s"): 0.06,
}

def _make_walk_env(seed: int, overrides: dict | None = None,
                   episode_seconds: float = 15.0):
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv

    cfg = load_config()
    for (sec, leaf), val in (overrides or WALK_OVERRIDES).items():
        cfg.setdefault(sec, {})[leaf] = val
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(None), randomize=False,
        dr_scale=0.0, episode_seconds=episode_seconds, seed=seed, cfg=cfg)
    gen = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(gen, f"p_{m}"):
            setattr(gen, f"p_{m}", 1.0 if m == "walk" else 0.0)
    return env

SLIPWALK_CMD_VX = 0.05

SLIPWALK_OVERRIDES = {
    # reward.term_penalty (08-22, cw-amp-m2-freeprog-{noamp,style05}
    # dig-in): the anti-suicide term. Under this stack WITHOUT it, a
    # scripted topple-in-1s netted +19/ep — the best-paying behavior
    # in the whole bank short of real walking (park -243, stall -143,
    # skate -1023) — because death exits before the freeprog/idle/
    # loadslip charges accrue, and both freeprog 2M arms duly learned
    # suicide in q4 (tilt terminations 59->132 / 90->241 at constant
    # std). Sized 400 > the worst-case discounted cost of staying
    # alive (-3.1/tick x (1-0.99^375)/0.01 ~= -295), so dying never
    # out-bids surviving in PPO's own view. Bit-exact for behaviors
    # that survive to truncation (the charge fires on term only).
    ("reward", "term_penalty"): 400.0,
    ("reward", "k_step_event"): 1.0,
    ("reward", "k_park_duty"): 2.0,
    ("reward", "k_walk_freeprog"): 3.0,
    ("reward", "walk_freeprog_cap_m_s"): 0.05,
    ("reward", "walk_loadslip_gate"): 0.0,
    ("reward", "loadslip_ok"): 1.5,
    ("reward", "k_loadslip_excess"): 6.0,
    ("reward", "walk_gait_gate"): 1.0,
    ("reward", "k_walk_idle_charge"): 20.0,
    ("reward", "walk_idle_speed_m_s"): 0.02,
    ("reward", "walk_idle_tau_s"): 1.0,
    ("goal", "walk_speed_min_m_s"): SLIPWALK_CMD_VX,
    ("goal", "walk_speed_max_m_s"): SLIPWALK_CMD_VX,
    ("goal", "walk_heading_max_rad"): 0.0,
}

