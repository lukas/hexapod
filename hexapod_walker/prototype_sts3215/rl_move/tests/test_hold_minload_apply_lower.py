"""``safety.hold_min_load_apply_lower`` (2026-10-01, walkcurr
over_current L1-hip root-cause follow-up): extends the EXISTING
hold-mode min-foot-load termination to also cover ``lower`` mode,
default OFF (bit-exact legacy -- no existing lower-role config sets
this key). See ``rl_docs/tracks/walkcurr/
lowerrole_overcurrent_qpos_limit_2026-10-01/SUMMARY.md`` for the
root-cause evidence (L1 hip pinned past its own hinge limit while
that leg sits airborne the whole episode -- a permanently "sacrificed"
leg during descent that the lower-role recipe's own already-configured
``hold_min_load_terminate_*`` keys never fire on, purely because this
mode gate excluded ``lower``).

Same ``mode_seq`` hand-plan harness as
``test_mode_seq_grace_windows.py``'s own hold-switch test (not
imported -- kept self-contained per RESEARCH_RULES "Tests")."""
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


def _drive_lower_segment(env, *, switch_s=5.0, episode_seconds=20.0):
    """Hand-build rise(0..switch_s)->lower(switch_s..end) mode_seq plan
    (same trick as test_mode_seq_grace_windows.py) and drive it with
    small random actions, returning the per-tick termination_reason
    list and the tick index ``lower`` starts at."""
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
        _, _, term, _trunc, info = env.step(
            rng.uniform(-0.05, 0.05, env.action_space.shape[0]))
        reasons.append(info.get("termination_reason"))
        if term:
            break
    return reasons, tk(switch_s)


def test_hold_min_load_apply_lower_defaults_off_bit_exact():
    """Default (key unset): min-load floor set impossibly high so
    EVERY foot reads "low" -- if the gate still excluded `lower` mode
    correctly, hold_min_load must NEVER fire across a full lower
    segment (the pre-existing, unmodified behavior)."""
    env = _make_env(extra_cfg={
        "safety.hold_min_load_terminate_s": 0.5,
        "safety.hold_min_load_terminate_grace_s": 0.5,
        "safety.hold_min_load_terminate_n": 100.0,
    })
    reasons, _switch_tick = _drive_lower_segment(env)
    assert "hold_min_load" not in reasons
    env.close()


def test_hold_min_load_apply_lower_fires_when_enabled():
    """Same floor/grace, but `hold_min_load_apply_lower=1`: the
    termination MUST fire during the `lower` segment, no earlier than
    its own grace window after the rise->lower switch."""
    env = _make_env(extra_cfg={
        "safety.hold_min_load_terminate_s": 0.5,
        "safety.hold_min_load_terminate_grace_s": 0.5,
        "safety.hold_min_load_terminate_n": 100.0,
        "safety.hold_min_load_apply_lower": 1.0,
    })
    reasons, switch_tick = _drive_lower_segment(env)
    fire_tick = next((i for i, r in enumerate(reasons)
                      if r == "hold_min_load"), None)
    assert fire_tick is not None, (
        "expected hold_min_load to fire during the lower segment "
        "once apply_lower=1")
    dt = env.dt
    assert fire_tick >= switch_tick + int(round(0.5 / dt)) - 1, (
        f"fired at tick {fire_tick}, lower segment started at "
        f"{switch_tick} -- grace window not honored")
    env.close()


def test_hold_min_load_apply_lower_does_not_fire_during_rise_phase():
    """With apply_lower=1 but the floor set high, the termination must
    still not fire during the EARLIER rise segment (the gate adds
    `lower`, it must not accidentally widen to `rise` too)."""
    env = _make_env(extra_cfg={
        "safety.hold_min_load_terminate_s": 0.5,
        "safety.hold_min_load_terminate_grace_s": 0.5,
        "safety.hold_min_load_terminate_n": 100.0,
        "safety.hold_min_load_apply_lower": 1.0,
    })
    reasons, switch_tick = _drive_lower_segment(env, switch_s=5.0)
    pre_switch_reasons = reasons[:switch_tick]
    assert "hold_min_load" not in pre_switch_reasons
    env.close()
