"""Tests for the optional FK-based height-error observation channel
(``obs.height_err_sense``, see ``rl_move/env.py::build_obs`` /
``height_err_sense_obs_dim``).

2026-09-17 walkcurr `lower` floor (14/14 reward-pricing/batch-
composition/termination-timing mechanism arms closed on the identical
partial-descend-then-freeze absorbing state, see
rl_docs/tracks/walkcurr/STATUS.md): every closed lever changed how the
OUTCOME is priced; none gave the policy a direct measurement of its
own height error to react to mid-descent. This channel is that
measurement, computed via the same stance-inferring FK estimator
``rl_move.estimator.estimate_body_height_m`` already validates for
velocity (``obs.walk_obs_body_vel=3``) -- hardware-realistic (encoders
+ IMU only), default OFF and bit-exact when off, per RESEARCH_RULES.
"""
from __future__ import annotations

import numpy as np

from rl_move.env import (GOAL_DIM, TaskGoal, build_obs,
                          height_err_sense_obs_dim)
from rl_move.estimator import estimate_body_height_m
from rl_move.robot_state import N_JOINTS, RobotState


def _standing_q() -> np.ndarray:
    # A plausible non-degenerate standing pose (hip/knee bent, yaw ~0)
    # repeated across all 6 legs -- degenerate all-zero q collapses
    # the FK stance-height estimate to 0, which would not exercise the
    # scaling/subtraction math below.
    leg = np.array([0.0, 0.2, 1.76])
    return np.tile(leg, 6)


def _state(q=None, roll=0.0, pitch=0.0) -> RobotState:
    q = _standing_q() if q is None else q
    return RobotState(
        timestamp=0.0,
        joint_position=q,
        joint_velocity=np.zeros(N_JOINTS),
        imu_roll=roll, imu_pitch=pitch, imu_yaw=0.0,
        imu_gyro=np.zeros(3),
        imu_accel=np.zeros(3),
        commanded_position=np.zeros(N_JOINTS),
    )


def test_height_err_sense_obs_dim_default_off():
    assert height_err_sense_obs_dim({}) == 0
    assert height_err_sense_obs_dim({"obs": {"height_err_sense": 0.0}}) == 0


def test_height_err_sense_obs_dim_on():
    assert height_err_sense_obs_dim({"obs": {"height_err_sense": 1.0}}) == 1


def test_build_obs_default_off_width_unchanged_and_bit_exact():
    q_nom = _standing_q()
    prev_action = np.zeros(6)
    st = _state(q=q_nom)
    obs_off = build_obs({}, st, q_nom, prev_action)
    obs_explicit_off = build_obs(
        {"obs": {"height_err_sense": 0.0}}, st, q_nom, prev_action)
    assert obs_off.shape == (18 + 18 + 2 + 3 + 6,)
    np.testing.assert_array_equal(obs_off, obs_explicit_off)


def test_build_obs_on_appends_one_scalar_at_the_end():
    q_nom = _standing_q()
    prev_action = np.zeros(6)
    st = _state(q=q_nom)
    cfg = {"obs": {"height_err_sense": 1.0}}
    obs_on = build_obs(cfg, st, q_nom, prev_action)
    obs_off = build_obs({}, st, q_nom, prev_action)
    assert obs_on.shape[0] == obs_off.shape[0] + 1
    np.testing.assert_allclose(obs_on[:obs_off.shape[0]], obs_off)


def test_build_obs_on_reads_zero_at_nominal_pose_no_goal():
    # state == q_nom, no goal -> h_now == h_nom -> error 0.
    q_nom = _standing_q()
    prev_action = np.zeros(6)
    st = _state(q=q_nom)
    cfg = {"obs": {"height_err_sense": 1.0}}
    obs_on = build_obs(cfg, st, q_nom, prev_action)
    assert abs(float(obs_on[-1])) < 1e-6


def test_build_obs_on_tracks_a_real_height_change():
    # Bend the knees further (larger knee angle) to lower the body;
    # the estimator should read a nonzero, correctly-signed change --
    # not just echo zero regardless of pose.
    q_nom = _standing_q()
    q_low = q_nom.copy()
    q_low[2::3] += 0.3  # every 3rd joint is the knee in this layout
    prev_action = np.zeros(6)
    st = _state(q=q_low)
    cfg = {"obs": {"height_err_sense": 1.0}}
    obs_on = build_obs(cfg, st, q_nom, prev_action)
    h_now = estimate_body_height_m(q_low, 0.0, 0.0)
    h_nom = estimate_body_height_m(q_nom, 0.0, 0.0)
    assert abs(h_now - h_nom) > 1e-4
    expected = (h_now - h_nom) / 0.05
    np.testing.assert_allclose(float(obs_on[-1]), expected, atol=1e-5)


def test_build_obs_on_nets_out_against_goal_height_ref():
    # If the goal's height_ref exactly matches the real height change,
    # the observed error should read ~0 (policy is on-target).
    q_nom = _standing_q()
    q_low = q_nom.copy()
    q_low[2::3] += 0.3
    prev_action = np.zeros(6)
    st = _state(q=q_low)
    cfg = {"obs": {"height_err_sense": 1.0}}
    h_now = estimate_body_height_m(q_low, 0.0, 0.0)
    h_nom = estimate_body_height_m(q_nom, 0.0, 0.0)
    goal = TaskGoal(height_ref=(h_now - h_nom))
    obs_on = build_obs(cfg, st, q_nom, prev_action, goal=goal)
    assert abs(float(obs_on[-1])) < 1e-5


def test_build_obs_on_with_goal_appends_after_goal():
    q_nom = _standing_q()
    prev_action = np.zeros(6)
    st = _state(q=q_nom)
    cfg = {"obs": {"height_err_sense": 1.0}}
    goal = TaskGoal(roll_ref=0.1)
    obs = build_obs(cfg, st, q_nom, prev_action, goal=goal)
    assert obs.shape[0] == 18 + 18 + 2 + 3 + 6 + GOAL_DIM + 1


# ---------------------------------------------------------------------------
# Real-env integration: SimHexapodJointGoalEnv is the walkcurr rise/hold/
# lower task class this mechanism actually targets. Confirms
# observation_space width matches build_obs's real output in both states
# and stays default-off bit-exact.
# ---------------------------------------------------------------------------

def test_joint_goal_env_height_err_sense_default_off_bit_exact():
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


def test_joint_goal_env_height_err_sense_on_widens_obs_by_one():
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
    cfg_on.setdefault("obs", {})["height_err_sense"] = 1.0
    env_on = SimHexapodJointGoalEnv(params=SimServoParams.load(),
                                     cfg=cfg_on, randomize=False,
                                     episode_seconds=2.0, seed=0)
    obs_on, _ = env_on.reset()
    assert obs_on.shape == env_on.observation_space.shape
    assert obs_on.shape[0] == n_off + 1
    a = q_rad_to_action(env_on._cmd.copy())
    obs2, r, term, trunc, info = env_on.step(a)
    assert obs2.shape[0] == n_off + 1
    assert np.isfinite(obs2[-1])
    env_on.close()
