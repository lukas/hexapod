"""Smoother-walk training knobs (2026-09-20).

Covers three opt-in, default-off additions:
  ITEM 2  reward.k_action_accel  — Δ²action (joint-acceleration) smoothness
          penalty in ``compute_reward``.
  ITEM 4  sensing.attitude_alpha — config-driven complementary-filter gyro
          trust, threaded into the deployed RobotStateEstimator and the sim
          training obs filter.

All three assert the DEFAULT stays bit-exact (adds exactly 0.0 / reproduces
alpha=0.98) so existing training and deployed policies are unchanged.
No mujoco needed — kept out of the "slow" set on purpose.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from rl_move.env import compute_reward
from rl_move.robot_state import N_JOINTS, RobotState, RobotStateEstimator

_RL_MOVE = Path(__file__).resolve().parents[1]


def _state() -> RobotState:
    return RobotState(
        timestamp=0.0,
        joint_position=np.zeros(N_JOINTS),
        joint_velocity=np.zeros(N_JOINTS),
        imu_roll=0.03,
        imu_pitch=-0.02,
        imu_yaw=0.0,
        imu_gyro=np.array([0.1, -0.05, 0.0]),
        imu_accel=np.array([0.0, 0.0, 9.80665]),
        commanded_position=np.zeros(N_JOINTS),
        servo_current=np.full(N_JOINTS, 0.2),
    )


# --- ITEM 2: Δ²action smoothness penalty -----------------------------------

def test_action_accel_default_off_is_bit_exact():
    """Default cfg (no k_action_accel) adds exactly 0.0 regardless of whether
    a caller threads prev_prev_action — proves the new plumbing is a no-op."""
    st = _state()
    a = np.array([0.4, -0.3, 0.1, 0.0, 0.2, -0.1])
    p = np.array([0.1, 0.0, 0.0, 0.0, 0.0, 0.0])
    pp = np.array([0.9, -0.9, 0.5, 0.2, -0.2, 0.3])

    r_no_pp, parts_no_pp = compute_reward({}, st, a, p)
    r_with_pp, parts_with_pp = compute_reward({}, st, a, p, prev_prev_action=pp)

    assert parts_no_pp["reward_action_accel"] == 0.0
    assert parts_with_pp["reward_action_accel"] == 0.0
    # Identical scalar reward with or without the threaded prev_prev_action.
    assert r_with_pp == r_no_pp


def test_action_accel_penalty_value_and_sign():
    """When on, the term is exactly -k * sum((a - 2p + pp)^2) and lowers the
    scalar reward by that amount vs the off case."""
    st = _state()
    a = np.array([0.4, -0.3, 0.1, 0.0, 0.2, -0.1])
    p = np.array([0.1, 0.0, 0.0, 0.0, 0.0, 0.0])
    pp = np.array([0.9, -0.9, 0.5, 0.2, -0.2, 0.3])
    k = 0.05
    cfg = {"reward": {"k_action_accel": k}}

    d2a = a - 2.0 * p + pp
    expected = -k * float(np.sum(d2a ** 2))

    r_on, parts_on = compute_reward(cfg, st, a, p, prev_prev_action=pp)
    r_off, _ = compute_reward({}, st, a, p, prev_prev_action=pp)

    assert parts_on["reward_action_accel"] == expected
    assert parts_on["reward_action_accel"] < 0.0
    # The whole difference between on/off is exactly the new term.
    assert r_on - r_off == expected


def test_action_accel_needs_prev_prev_action():
    """Knob on but no prev_prev_action threaded → guarded to 0.0 (a caller
    that hasn't been updated cannot accidentally get a wrong penalty)."""
    st = _state()
    a = np.ones(6)
    p = np.zeros(6)
    cfg = {"reward": {"k_action_accel": 0.05}}
    _, parts = compute_reward(cfg, st, a, p, prev_prev_action=None)
    assert parts["reward_action_accel"] == 0.0


# --- ITEM 4: config-driven attitude alpha ----------------------------------

def test_attitude_alpha_default_is_bit_exact():
    est = RobotStateEstimator(bus=object(), cfg={})
    assert est._att.alpha == 0.98


def test_attitude_alpha_flows_from_cfg():
    est = RobotStateEstimator(
        bus=object(), cfg={"sensing": {"attitude_alpha": 0.995}})
    assert est._att.alpha == 0.995


def test_sim_env_attitude_filter_reads_the_same_cfg_key():
    """The sim training obs filter (sim_env) must use the config knob, not a
    hardcoded 0.98 — otherwise the alpha change would reach deploy but not
    training. Source-level so the check stays out of the slow mujoco set."""
    src = (_RL_MOVE / "sim" / "sim_env.py").read_text()
    assert '"attitude_alpha"' in src
    assert "alpha = self._attitude_alpha" in src
    # The old hardcoded value must be gone from the inline filter.
    assert "alpha = 0.98" not in src
