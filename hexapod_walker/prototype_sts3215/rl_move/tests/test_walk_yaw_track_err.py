"""reward.k_yaw_track_err — direct signed-match tracking-error charge
on turn ticks (walkcurr STATUS Next item (a), 09-28).

Context: the closed stillretune{0,10,25}-canary2m sweep zeroed
reward.k_yaw_still across its whole range and STILL reproduced the
identical frozen-body shape, ruling out "the still-charge dominates"
as the explanation on its own. The remaining named half of item (a)
is untried: the k_yaw_prog ratio kernel is exactly ZERO (not
negative) at wz=0, so "do nothing" is reward-NEUTRAL, not
reward-dominated, on a turn tick -- a risk-averse policy weighing
that neutral income against term_penalty fall risk has no reward
pressure to prefer a small real attempt over freezing. This charge
makes wz=0 strictly WORSE than any point closer to the command, with
a maximum (0) only at exact tracking, independent of k_yaw_still/
k_yaw_prog. Default 0.0 = off, bit-exact legacy.

Contract under test (mechanics only, per RESEARCH_RULES "Tests" --
no rollout-ranking/trained-behavior assertion):
  - default (key absent/0) is bit-exact off: no info key, no reward
    delta;
  - exact tracking (wz == wz_ref) charges exactly 0;
  - wz == 0 on a live turn tick charges exactly -k (the full,
    unclipped charge at the command magnitude);
  - wrong-direction wz (same magnitude, opposite sign) charges 4x the
    wz==0 charge (quadratic in normalized error);
  - the charge clips at 3x normalized error (bounded, no blowup on a
    fall/collision transient);
  - off the turn-in-place condition (wz_ref == 0, hold ticks), no
    charge fires regardless of achieved wz.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.walk_task import SimHexapodJointWalkEnv
from rl_move.sim.joint_task import q_rad_to_action


def _turn_env(k=0.0, seed=0):
    cfg = load_config()
    goal = cfg.setdefault("goal", {})
    goal["walk_yaw_cmd"] = 1
    goal["walk_yaw_max_rad_s"] = 0.3
    goal["walk_yaw_zero_frac"] = 0.0
    goal["walk_turn_in_place_frac"] = 1.0
    goal["walk_gait_start_frac"] = 0.0
    goal["walk_cmd_hold_s"] = 0.0
    goal["walk_cmd_ramp_s"] = 0.0
    rw = cfg.setdefault("reward", {})
    if k:
        rw["k_yaw_track_err"] = k
    env = SimHexapodJointWalkEnv(cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 0.0)
    g.p_walk = 1.0
    env.reset()
    return env


def _hold_action(env):
    return q_rad_to_action(env._cmd.copy())


def _advance_to_turn_tick(env, max_ticks=100):
    a = _hold_action(env)
    for _ in range(max_ticks):
        goal = env._current_goal()
        if abs(float(goal.wz_ref)) > 1e-3 and abs(
                float(np.hypot(goal.vx_ref, goal.vy_ref))) <= 1e-3:
            return
        env.step(a)
    raise AssertionError("never reached a live turn-in-place tick")


def test_default_off_no_info_key_and_bit_exact():
    env = _turn_env(k=0.0)
    _advance_to_turn_tick(env)
    _, _, _, _, info = env.step(_hold_action(env))
    assert "reward_yaw_track_err" not in info
    env.close()


def test_exact_tracking_charges_zero():
    env = _turn_env(k=10.0)
    _advance_to_turn_tick(env)
    goal = env._current_goal()
    env._body_wz = lambda: float(goal.wz_ref)
    _, _, _, _, info = env.step(_hold_action(env))
    assert info["reward_yaw_track_err"] == pytest.approx(0.0, abs=1e-9)
    env.close()


def test_frozen_wz_charges_full_k():
    env = _turn_env(k=10.0)
    _advance_to_turn_tick(env)
    env._body_wz = lambda: 0.0  # frozen body: full normalized error 1.0
    _, _, _, _, info = env.step(_hold_action(env))
    assert info["reward_yaw_track_err"] == pytest.approx(-10.0)
    env.close()


def test_wrong_direction_charges_4x_frozen():
    env = _turn_env(k=10.0)
    _advance_to_turn_tick(env)
    goal = env._current_goal()
    env._body_wz = lambda: -float(goal.wz_ref)  # opposite sign, |err|=2x
    _, _, _, _, info = env.step(_hold_action(env))
    assert info["reward_yaw_track_err"] == pytest.approx(-40.0)
    env.close()


def test_charge_clips_at_3x_normalized_error():
    env = _turn_env(k=10.0)
    _advance_to_turn_tick(env)
    goal = env._current_goal()
    # a huge overshoot: normalized error far past the 3x clip
    env._body_wz = lambda: -10.0 * float(goal.wz_ref)
    _, _, _, _, info = env.step(_hold_action(env))
    assert info["reward_yaw_track_err"] == pytest.approx(-90.0)
    env.close()


def test_hold_tick_never_charged():
    cfg = load_config()
    goal = cfg.setdefault("goal", {})
    goal["walk_yaw_cmd"] = 1
    rw = cfg.setdefault("reward", {})
    rw["k_yaw_track_err"] = 10.0
    env = SimHexapodJointWalkEnv(cfg, seed=0)
    g = env._goal_gen
    for m in ("lean", "track", "unload", "raise", "rise", "lower"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 0.0)
    g.p_hold = 1.0
    g.p_walk = 0.0
    env.reset()
    env._body_wz = lambda: 0.0
    _, _, _, _, info = env.step(_hold_action(env))
    assert info.get("reward_yaw_track_err", 0.0) == 0.0
    env.close()
