"""``safety.lower_joint_limit_terminate_s`` (2026-10-01, walkcurr
over_current L1-hip false-positive follow-up): LOWER-mode-only
termination keyed on (near own mechanical hinge limit) AND
(qvel-static), the SAME conjunction
``eval_lifecycle_handoff_rlonly.trip_summary()`` already uses post-hoc
to classify CORROBORATED_STALL vs RAIL_MOVING -- reused here as a live
per-tick check instead of a force/duty proxy. Default OFF (bit-exact;
no existing config sets this key). See
``rl_docs/tracks/walkcurr/STATUS.md`` Next 1 for why the force-based
``hold_min_load_apply_lower`` alternative was closed instead (false-
fires on ~100% of ALL lower episodes, healthy or not).

Same hand-built ``mode_seq`` rise->lower harness as
``test_hold_minload_apply_lower.py`` (not imported -- kept
self-contained per RESEARCH_RULES "Tests")."""
from __future__ import annotations

import numpy as np

from rl_move.config import load_config
from rl_move.sim.walk_task import SimHexapodJointWalkEnv


def _make_env(seed=0, *, episode_seconds=20.0, extra_cfg=None):
    cfg = load_config()
    g = cfg.setdefault("goal", {})
    g["mode_seq"] = 1.0
    for k, v in (extra_cfg or {}).items():
        sect, name = k.split(".", 1)
        cfg.setdefault(sect, {})[name] = v
    return SimHexapodJointWalkEnv(cfg, seed=seed,
                                  episode_seconds=episode_seconds)


def _drive_lower_segment(env, *, switch_s=5.0, episode_seconds=20.0,
                         action=None):
    dt = env.dt
    tk = lambda s: int(round(s / dt))  # noqa: E731
    env.reset()
    env._seq_plan = [
        {"mode": "rise", "tick": 0, "blend": 0},
        {"mode": "lower", "tick": tk(switch_s), "blend": 0},
    ]
    env._seq_idx = 0
    env._seq_seg_end = tk(switch_s)
    rng = np.random.default_rng(1)
    reasons = []
    for _ in range(int(episode_seconds / dt) - 1):
        a = (action if action is not None
             else rng.uniform(-0.05, 0.05, env.action_space.shape[0]))
        _, _, term, _trunc, info = env.step(a)
        reasons.append(info.get("termination_reason"))
        if term:
            break
    return reasons, tk(switch_s)


def test_lower_joint_limit_defaults_off_bit_exact():
    """Key unset: even with an absurdly generous margin/stall band
    that would catch almost any joint, the termination must never
    fire (legacy behavior, zero new state read)."""
    env = _make_env(extra_cfg={
        "safety.lower_joint_limit_margin_rad": 10.0,
        "safety.lower_joint_limit_stall_qvel": 10.0,
        "safety.lower_joint_limit_grace_s": 0.1,
    })
    reasons, _switch_tick = _drive_lower_segment(
        env, action=np.zeros(18))  # near-zero action -> near-zero qvel
    assert "lower_joint_limit" not in reasons
    env.close()


def test_lower_joint_limit_fires_when_enabled_and_static_near_limit():
    """Generous margin/stall band + a HOLD (zero-delta) action during
    lower should read every joint as both 'near its own limit' is NOT
    guaranteed, but 'static' certainly is -- so with a generous enough
    margin (10 rad, i.e. always true) the termination must fire once
    enabled, no earlier than its own grace window."""
    env = _make_env(extra_cfg={
        "safety.lower_joint_limit_terminate_s": 0.2,
        "safety.lower_joint_limit_grace_s": 0.3,
        "safety.lower_joint_limit_margin_rad": 10.0,
        "safety.lower_joint_limit_stall_qvel": 10.0,
    })
    reasons, switch_tick = _drive_lower_segment(env, action=np.zeros(18))
    fire_tick = next((i for i, r in enumerate(reasons)
                      if r == "lower_joint_limit"), None)
    assert fire_tick is not None, (
        "expected lower_joint_limit to fire during the lower segment "
        "once enabled with a generous margin/stall band")
    dt = env.dt
    assert fire_tick >= switch_tick + int(round(0.3 / dt)) - 1, (
        f"fired at tick {fire_tick}, lower segment started at "
        f"{switch_tick} -- grace window not honored")
    env.close()


def test_lower_joint_limit_does_not_fire_during_rise_phase():
    """Same generous settings, but must not fire during the EARLIER
    rise segment (mode gate must stay lower-only)."""
    env = _make_env(extra_cfg={
        "safety.lower_joint_limit_terminate_s": 0.2,
        "safety.lower_joint_limit_grace_s": 0.3,
        "safety.lower_joint_limit_margin_rad": 10.0,
        "safety.lower_joint_limit_stall_qvel": 10.0,
    })
    reasons, switch_tick = _drive_lower_segment(
        env, switch_s=5.0, action=np.zeros(18))
    pre_switch_reasons = reasons[:switch_tick]
    assert "lower_joint_limit" not in pre_switch_reasons
    env.close()


def test_lower_joint_limit_does_not_fire_when_moving_even_near_limit():
    """Generous margin (near-limit always true) but a TIGHT stall_qvel
    (near-zero) combined with a large-amplitude oscillating action
    (genuine joint velocity) must NOT fire -- the qvel-static half of
    the conjunction must gate independently of the margin half (this
    is the exact RAIL_MOVING case the force-based alternative could
    not distinguish)."""
    env = _make_env(extra_cfg={
        "safety.lower_joint_limit_terminate_s": 0.2,
        "safety.lower_joint_limit_grace_s": 0.1,
        "safety.lower_joint_limit_margin_rad": 10.0,
        "safety.lower_joint_limit_stall_qvel": 1e-6,
    })
    dt = env.dt
    rng = np.random.default_rng(2)

    def oscillating_action(_env):
        return rng.choice([-1.0, 1.0]) * np.full(18, 0.3)

    env.reset()
    env._seq_plan = [
        {"mode": "rise", "tick": 0, "blend": 0},
        {"mode": "lower", "tick": int(round(5.0 / dt)), "blend": 0},
    ]
    env._seq_idx = 0
    env._seq_seg_end = int(round(5.0 / dt))
    reasons = []
    for _ in range(int(20.0 / dt) - 1):
        _, _, term, _trunc, info = env.step(oscillating_action(env))
        reasons.append(info.get("termination_reason"))
        if term:
            break
    assert "lower_joint_limit" not in reasons
    env.close()
