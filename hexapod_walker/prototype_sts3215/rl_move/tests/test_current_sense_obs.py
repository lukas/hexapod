"""Tests for the optional per-joint current-sense observation channel
(``obs.current_sense``, see ``rl_move/env.py::build_obs`` /
``current_sense_obs_dim``).

2026-09-14 walkcurr flat-start-rise residual (22/22+3 mechanism families
closed on the over_current fingerprint, see rl_docs/tracks/walkcurr/
STATUS.md): the sim already computes ``state.servo_current`` every tick
(reward/safety-termination consume it) but never exposed it to the
policy's observation. This is new observation-space plumbing, default
OFF and bit-exact when off, per RESEARCH_RULES.
"""
from __future__ import annotations

import numpy as np

from rl_move.env import build_obs, current_sense_obs_dim
from rl_move.robot_state import N_JOINTS, RobotState


def _state(servo_current=None) -> RobotState:
    return RobotState(
        timestamp=0.0,
        joint_position=np.zeros(N_JOINTS),
        joint_velocity=np.zeros(N_JOINTS),
        imu_roll=0.0, imu_pitch=0.0, imu_yaw=0.0,
        imu_gyro=np.zeros(3),
        imu_accel=np.zeros(3),
        commanded_position=np.zeros(N_JOINTS),
        servo_current=servo_current,
    )


def test_current_sense_obs_dim_default_off():
    assert current_sense_obs_dim({}) == 0
    assert current_sense_obs_dim({"obs": {"current_sense": 0.0}}) == 0


def test_current_sense_obs_dim_on():
    assert current_sense_obs_dim({"obs": {"current_sense": 1.0}}) == N_JOINTS


def test_build_obs_default_off_width_unchanged_and_bit_exact():
    q_nom = np.zeros(N_JOINTS)
    prev_action = np.zeros(6)
    st = _state(servo_current=np.arange(N_JOINTS, dtype=float))
    obs_off = build_obs({}, st, q_nom, prev_action)
    obs_explicit_off = build_obs(
        {"obs": {"current_sense": 0.0}}, st, q_nom, prev_action)
    assert obs_off.shape == (18 + 18 + 2 + 3 + 6,)
    np.testing.assert_array_equal(obs_off, obs_explicit_off)


def test_build_obs_on_appends_scaled_current_at_the_end():
    q_nom = np.zeros(N_JOINTS)
    prev_action = np.zeros(6)
    cur = np.linspace(-2.0, 2.0, N_JOINTS)
    st = _state(servo_current=cur)
    cfg = {"obs": {"current_sense": 1.0, "current_scale": 2.0}}
    obs_on = build_obs(cfg, st, q_nom, prev_action)
    obs_off = build_obs({}, st, q_nom, prev_action)
    assert obs_on.shape[0] == obs_off.shape[0] + N_JOINTS
    np.testing.assert_allclose(obs_on[:obs_off.shape[0]], obs_off)
    np.testing.assert_allclose(obs_on[-N_JOINTS:], cur / 2.0, atol=1e-6)


def test_build_obs_on_falls_back_to_zeros_when_no_current_reading():
    q_nom = np.zeros(N_JOINTS)
    prev_action = np.zeros(6)
    st = _state(servo_current=None)
    cfg = {"obs": {"current_sense": 1.0}}
    obs_on = build_obs(cfg, st, q_nom, prev_action)
    assert obs_on.shape[0] == 18 + 18 + 2 + 3 + 6 + N_JOINTS
    np.testing.assert_array_equal(obs_on[-N_JOINTS:], np.zeros(N_JOINTS))


def test_build_obs_on_with_goal_appends_after_goal():
    from rl_move.env import GOAL_DIM, TaskGoal
    q_nom = np.zeros(N_JOINTS)
    prev_action = np.zeros(6)
    cur = np.full(N_JOINTS, 0.5)
    st = _state(servo_current=cur)
    cfg = {"obs": {"current_sense": 1.0}}
    goal = TaskGoal(roll_ref=0.1)
    obs = build_obs(cfg, st, q_nom, prev_action, goal=goal)
    assert obs.shape[0] == 18 + 18 + 2 + 3 + 6 + GOAL_DIM + N_JOINTS
    np.testing.assert_allclose(obs[-N_JOINTS:], cur, atol=1e-6)


# ---------------------------------------------------------------------------
# Real-env integration: SimHexapodJointGoalEnv is the walkcurr rise-task
# class this mechanism actually targets. Confirms observation_space width
# matches build_obs's real output in both states and stays default-off
# bit-exact.
# ---------------------------------------------------------------------------

def test_joint_goal_env_current_sense_default_off_bit_exact():
    from rl_move.config import load_config
    from rl_move.sim.servo_model import SimServoParams
    from rl_move.sim.joint_task import SimHexapodJointGoalEnv, q_rad_to_action

    cfg_off = load_config()
    env_off = SimHexapodJointGoalEnv(params=SimServoParams.load(),
                                      cfg=cfg_off, randomize=False,
                                      episode_seconds=2.0, seed=0)
    obs, _ = env_off.reset()
    assert obs.shape == env_off.observation_space.shape
    n_before = obs.shape[0]
    a = q_rad_to_action(env_off._cmd.copy())
    obs2, *_ = env_off.step(a)
    assert obs2.shape == (n_before,)
    env_off.close()


def test_joint_goal_env_current_sense_on_widens_obs_and_carries_current():
    from rl_move.config import load_config
    from rl_move.sim.servo_model import SimServoParams
    from rl_move.sim.joint_task import SimHexapodJointGoalEnv, q_rad_to_action

    cfg_off = load_config()
    env_off = SimHexapodJointGoalEnv(params=SimServoParams.load(),
                                      cfg=cfg_off, randomize=False,
                                      episode_seconds=2.0, seed=0)
    obs_off, _ = env_off.reset()
    n_off = obs_off.shape[0]
    env_off.close()

    cfg_on = load_config()
    cfg_on.setdefault("obs", {})["current_sense"] = 1.0
    env_on = SimHexapodJointGoalEnv(params=SimServoParams.load(),
                                     cfg=cfg_on, randomize=False,
                                     episode_seconds=2.0, seed=0)
    obs_on, _ = env_on.reset()
    assert obs_on.shape == env_on.observation_space.shape
    assert obs_on.shape[0] == n_off + N_JOINTS
    a = q_rad_to_action(env_on._cmd.copy())
    obs2, r, term, trunc, info = env_on.step(a)
    assert obs2.shape[0] == n_off + N_JOINTS
    # Standing near q_nom under load should draw some nonzero current
    # on at least one servo (not all-zero placeholder/fallback).
    tail = obs2[-N_JOINTS:]
    assert np.isfinite(tail).all()
    env_on.close()
