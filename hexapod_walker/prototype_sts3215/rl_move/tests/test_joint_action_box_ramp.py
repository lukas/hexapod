"""goal.joint_action_box_ramp_steps -- trainer-driven action-box
width ramp.

09-23, standwalk extplant82-actionbox PARTIAL triage: the fixed
action box DOES extend the settled stance (172mm tucked -> 201mm) but
walk quality regresses hard and every stochastic walk episode trips
over_current -- reads as fighting a too-tight band at max effort
while still learning the gait. The gate's own PARTIAL branch names
the fix: "widen the box gradually (curriculum) rather than the fixed
band". This mirrors the existing bus.profile_ramp_steps / reward.
drag_stance_allow_ramp_steps trainer-driven pattern exactly: the
TRAINER anneals the box HALF-WIDTH from a wide (default = the full
hardware half-range per axis, i.e. no-op) start down to the cfg
TARGET box_{yaw,hip,knee}_deg over that many global env steps, via
apply_action_box_ramp_frac.

Contract under test:
  - default (key absent/0) is bit-exact OFF: no ramp state, apply
    raises;
  - armed but no box target -> fails closed at construction (nothing
    to ramp toward);
  - ARMED env CONSTRUCTS at the TARGET box (eval_checkpoint / play /
    periodic C evals judge the full target band without any
    broadcast) -- same contract as the profile ramp;
  - frac 0 -> wide start (default = hardware half-range, box is a
    no-op), 0.5 -> midpoint, >=1 -> target, clamped;
  - the box CENTER never moves, only the width;
  - custom start-width keys override the default wide-open start.
"""
from __future__ import annotations

import numpy as np
import pytest


pytest.importorskip("mujoco")

from walk_env_helpers import _make_walk_env, SLIPWALK_OVERRIDES

BOX_OVERRIDES = {
    ("goal", "joint_action_bias_hip_deg"): 40.0,
    ("goal", "joint_action_bias_knee_deg"): 15.0,
    ("goal", "joint_action_box_yaw_deg"): 11.0,
    ("goal", "joint_action_box_hip_deg"): 20.0,
    ("goal", "joint_action_box_knee_deg"): 23.0,
}

RAMP_OVERRIDES = {**BOX_OVERRIDES,
                   ("goal", "joint_action_box_ramp_steps"): 2_000_000}


def test_default_off_bit_exact_and_apply_raises():
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **BOX_OVERRIDES})
    assert env._joint_action_box_ramp is None
    with pytest.raises(RuntimeError, match="not armed"):
        env.apply_action_box_ramp_frac(0.5)
    env.close()


def test_ramp_without_active_box_fails_closed():
    ov = {**SLIPWALK_OVERRIDES,
          ("goal", "joint_action_box_ramp_steps"): 2_000_000}
    with pytest.raises(ValueError, match="needs an active action box"):
        _make_walk_env(0, ov)


def test_armed_env_constructs_at_target_box():
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **RAMP_OVERRIDES})
    assert env._joint_action_box_ramp is not None
    box_deg = np.degrees(env._joint_action_box_rad).reshape(6, 3)[0]
    assert box_deg[0] == pytest.approx(11.0)
    assert box_deg[1] == pytest.approx(20.0)
    assert box_deg[2] == pytest.approx(23.0)
    env.close()


def test_frac_endpoints_midpoint_and_clamp_default_wide_start():
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **RAMP_OVERRIDES})
    v0 = env.apply_action_box_ramp_frac(0.0)
    # Default start = full hardware half-range per axis (yaw (35,35)
    # half=35, hip (-80,40) half=60, knee (-20,150) half=85) -- a
    # no-op box (axis_lo/hi already clip there).
    assert v0["box_yaw_deg"] == pytest.approx(35.0)
    assert v0["box_hip_deg"] == pytest.approx(60.0)
    assert v0["box_knee_deg"] == pytest.approx(85.0)

    vm = env.apply_action_box_ramp_frac(0.5)
    assert vm["box_yaw_deg"] == pytest.approx((35.0 + 11.0) / 2)
    assert vm["box_hip_deg"] == pytest.approx((60.0 + 20.0) / 2)
    assert vm["box_knee_deg"] == pytest.approx((85.0 + 23.0) / 2)

    v1 = env.apply_action_box_ramp_frac(1.0)
    assert v1["box_hip_deg"] == pytest.approx(20.0)
    assert v1["box_knee_deg"] == pytest.approx(23.0)

    assert env.apply_action_box_ramp_frac(7.0)["frac"] == 1.0
    assert env.apply_action_box_ramp_frac(-3.0)["frac"] == 0.0
    env.close()


def test_custom_start_keys():
    env = _make_walk_env(0, {
        **SLIPWALK_OVERRIDES, **RAMP_OVERRIDES,
        ("goal", "joint_action_box_ramp_start_hip_deg"): 40.0,
        ("goal", "joint_action_box_ramp_start_knee_deg"): 50.0,
    })
    v0 = env.apply_action_box_ramp_frac(0.0)
    assert v0["box_hip_deg"] == pytest.approx(40.0)
    assert v0["box_knee_deg"] == pytest.approx(50.0)
    env.close()


def test_center_never_moves_across_the_ramp():
    """Only the width ramps -- a=0 always lands on the same bias-
    shifted stance center regardless of frac."""
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **RAMP_OVERRIDES})
    zero = np.zeros(env.n_act)
    q_before = env._act_to_q(zero)[0].copy()
    env.apply_action_box_ramp_frac(0.3)
    q_mid = env._act_to_q(zero)[0].copy()
    env.apply_action_box_ramp_frac(1.0)
    q_after = env._act_to_q(zero)[0].copy()
    assert np.allclose(q_before, q_mid, atol=1e-9)
    assert np.allclose(q_before, q_after, atol=1e-9)
    env.close()


def test_bounds_shrink_as_frac_increases():
    """Any fixed action's excursion from center shrinks monotonically
    as frac moves from 0 (wide) to 1 (target, tighter)."""
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **RAMP_OVERRIDES})
    a = np.ones(env.n_act)
    center = env._joint_action_box_center
    q0 = env.apply_action_box_ramp_frac(0.0)
    d0 = np.abs(env._act_to_q(a)[0] - center).max()
    env.apply_action_box_ramp_frac(0.5)
    d5 = np.abs(env._act_to_q(a)[0] - center).max()
    env.apply_action_box_ramp_frac(1.0)
    d1 = np.abs(env._act_to_q(a)[0] - center).max()
    assert d0 > d5 > d1 - 1e-9
    env.close()


def test_motor_contract_unaffected():
    """The box ramp is a joint_task-side mechanism; it must not touch
    motor_contract (that's the profile ramp's own reporting)."""
    from rl_move.config import load_config
    from rl_move.sim.servo_model import motor_contract
    cfg = load_config()
    for (sec, leaf), val in RAMP_OVERRIDES.items():
        cfg.setdefault(sec, {})[leaf] = val
    c = motor_contract(cfg)
    assert "goal.joint_action_box_ramp_steps" not in c
