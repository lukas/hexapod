"""Tests for the optional height-RATE observation channel
(``obs.height_vel_sense``, see ``rl_move/env.py::build_obs`` /
``height_vel_sense_obs_dim``) and its stateful estimator
(``rl_move.estimator.HeightRateEstimator``).

2026-09-17 walkcurr `lower` floor (15/15 reward-pricing/batch-
composition/termination-timing/position-observation mechanism classes
closed on the identical partial-descend-then-freeze absorbing state,
see STATUS.md 2026-09-17 ~06:3x / CURRENT_TRUTHS.md same timestamp):
``obs.height_err_sense`` (the POSITION half of the observation-space
axis) alone did not break the freeze on either seed. This channel is
the RATE half of that same axis -- a stateful finite-difference-and-
filter of the same FK height read, hardware-realistic (encoders + IMU
only), default OFF and bit-exact when off, per RESEARCH_RULES.
"""
from __future__ import annotations

import numpy as np

from rl_move.env import (GOAL_DIM, TaskGoal, build_obs,
                          height_vel_sense_obs_dim)
from rl_move.estimator import HeightRateEstimator, estimate_body_height_m
from rl_move.robot_state import N_JOINTS, RobotState


def _standing_q() -> np.ndarray:
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


# ---------------------------------------------------------------------------
# HeightRateEstimator (estimator.py)
# ---------------------------------------------------------------------------

def test_height_rate_estimator_first_tick_returns_zero():
    est = HeightRateEstimator(dt=0.04)
    q = _standing_q()
    assert est.update(q, 0.0, 0.0) == 0.0


def test_height_rate_estimator_zero_when_stationary():
    est = HeightRateEstimator(dt=0.04)
    q = _standing_q()
    est.update(q, 0.0, 0.0)
    for _ in range(5):
        v = est.update(q, 0.0, 0.0)
    assert abs(v) < 1e-9


def test_height_rate_estimator_signed_and_scaled_for_a_real_descent():
    # Lower the body at a known rate by moving the knee angle linearly
    # tick-to-tick; the filtered rate should converge to a NEGATIVE
    # (descending) value once the one-pole filter settles.
    dt = 0.04
    est = HeightRateEstimator(dt=dt, alpha=1.0)  # alpha=1 -> no lag
    q0 = _standing_q()
    h0 = estimate_body_height_m(q0, 0.0, 0.0)
    q1 = q0.copy()
    q1[2::3] += 0.05  # bend knees further -> lower the body
    h1 = estimate_body_height_m(q1, 0.0, 0.0)
    assert h1 < h0  # sanity: this pose really is lower
    est.update(q0, 0.0, 0.0)
    v = est.update(q1, 0.0, 0.0)
    expected = (h1 - h0) / dt
    np.testing.assert_allclose(v, expected, atol=1e-9)


def test_height_rate_estimator_reset_forgets_previous_frame():
    est = HeightRateEstimator(dt=0.04)
    q0 = _standing_q()
    q1 = q0.copy()
    q1[2::3] += 0.05
    est.update(q0, 0.0, 0.0)
    est.update(q1, 0.0, 0.0)
    est.reset()
    # First tick after reset has no previous frame -> 0.0 again, not a
    # spurious jump computed against the pre-reset frame.
    assert est.update(q1, 0.0, 0.0) == 0.0


# ---------------------------------------------------------------------------
# build_obs / height_vel_sense_obs_dim (env.py) -- pure/stateless: the
# caller supplies the already-estimated height_vel_mps.
# ---------------------------------------------------------------------------

def test_height_vel_sense_obs_dim_default_off():
    assert height_vel_sense_obs_dim({}) == 0
    assert height_vel_sense_obs_dim({"obs": {"height_vel_sense": 0.0}}) == 0


def test_height_vel_sense_obs_dim_on():
    assert height_vel_sense_obs_dim({"obs": {"height_vel_sense": 1.0}}) == 1


def test_build_obs_default_off_width_unchanged_and_bit_exact():
    q_nom = _standing_q()
    prev_action = np.zeros(6)
    st = _state(q=q_nom)
    obs_off = build_obs({}, st, q_nom, prev_action, height_vel_mps=3.0)
    obs_explicit_off = build_obs(
        {"obs": {"height_vel_sense": 0.0}}, st, q_nom, prev_action,
        height_vel_mps=3.0)
    assert obs_off.shape == (18 + 18 + 2 + 3 + 6,)
    # A nonzero height_vel_mps must have NO effect at all when the
    # channel is off (default-off bit-exactness even if a caller
    # sloppily passes a nonzero value).
    np.testing.assert_array_equal(obs_off, obs_explicit_off)


def test_build_obs_on_appends_one_scalar_at_the_end():
    q_nom = _standing_q()
    prev_action = np.zeros(6)
    st = _state(q=q_nom)
    cfg = {"obs": {"height_vel_sense": 1.0}}
    obs_on = build_obs(cfg, st, q_nom, prev_action, height_vel_mps=0.02)
    obs_off = build_obs({}, st, q_nom, prev_action)
    assert obs_on.shape[0] == obs_off.shape[0] + 1
    np.testing.assert_allclose(obs_on[:obs_off.shape[0]], obs_off)


def test_build_obs_on_scales_the_supplied_rate():
    q_nom = _standing_q()
    prev_action = np.zeros(6)
    st = _state(q=q_nom)
    cfg = {"obs": {"height_vel_sense": 1.0, "height_vel_scale": 0.02}}
    obs_on = build_obs(cfg, st, q_nom, prev_action, height_vel_mps=0.01)
    np.testing.assert_allclose(float(obs_on[-1]), 0.5, atol=1e-6)


def test_build_obs_on_default_zero_rate_reads_zero():
    q_nom = _standing_q()
    prev_action = np.zeros(6)
    st = _state(q=q_nom)
    cfg = {"obs": {"height_vel_sense": 1.0}}
    obs_on = build_obs(cfg, st, q_nom, prev_action)
    assert abs(float(obs_on[-1])) < 1e-9


def test_build_obs_on_stacks_after_height_err_sense():
    q_nom = _standing_q()
    prev_action = np.zeros(6)
    st = _state(q=q_nom)
    cfg = {"obs": {"height_err_sense": 1.0, "height_vel_sense": 1.0}}
    obs = build_obs(cfg, st, q_nom, prev_action, height_vel_mps=0.02)
    obs_err_only = build_obs(
        {"obs": {"height_err_sense": 1.0}}, st, q_nom, prev_action)
    assert obs.shape[0] == obs_err_only.shape[0] + 1
    np.testing.assert_allclose(obs[:-1], obs_err_only)


def test_build_obs_on_with_goal_appends_after_goal():
    q_nom = _standing_q()
    prev_action = np.zeros(6)
    st = _state(q=q_nom)
    cfg = {"obs": {"height_vel_sense": 1.0}}
    goal = TaskGoal(roll_ref=0.1)
    obs = build_obs(cfg, st, q_nom, prev_action, goal=goal,
                    height_vel_mps=0.01)
    assert obs.shape[0] == 18 + 18 + 2 + 3 + 6 + GOAL_DIM + 1


# ---------------------------------------------------------------------------
# Real-env integration: SimHexapodJointGoalEnv is the walkcurr rise/hold/
# lower task class this mechanism targets. Confirms observation_space
# width matches build_obs's real output, stays default-off bit-exact,
# and the per-episode estimator actually resets across episodes/pool
# restores (mjx_host.SNAP_ATTRS).
# ---------------------------------------------------------------------------

def test_joint_goal_env_height_vel_sense_default_off_bit_exact():
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


def test_joint_goal_env_height_vel_sense_on_widens_obs_by_one():
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
    cfg_on.setdefault("obs", {})["height_vel_sense"] = 1.0
    env_on = SimHexapodJointGoalEnv(params=SimServoParams.load(),
                                     cfg=cfg_on, randomize=False,
                                     episode_seconds=2.0, seed=0)
    obs_on, _ = env_on.reset()
    assert obs_on.shape == env_on.observation_space.shape
    assert obs_on.shape[0] == n_off + 1
    # First tick after reset: no previous FK frame yet -> rate reads 0.
    assert obs_on[-1] == 0.0
    a = q_rad_to_action(env_on._cmd.copy())
    obs2, r, term, trunc, info = env_on.step(a)
    assert obs2.shape[0] == n_off + 1
    assert np.isfinite(obs2[-1])
    env_on.close()


# ---------------------------------------------------------------------------
# Hardware env (rl_move.env.HexapodBalanceEnv) wiring: the docstring/
# hypothesis claim is "computable identically on real hardware from
# encoders + IMU alone" -- confirm the board-side _obs() actually feeds a
# live HeightRateEstimator (not silently 0.0 forever like an unwired
# channel would), same contract as the sim twin.
# ---------------------------------------------------------------------------

def _hw_env(height_vel_sense: float) -> "object":
    from rl_move.env import HexapodBalanceEnv
    env = HexapodBalanceEnv(
        object(),
        cfg={
            "control": {"hz": 25},
            "sensing": {"full_feedback_hz": 10},
            "safety": {"over_current_trip_s": 2.0},
            "bus": {"enable_motion": False},
            "obs": {"height_vel_sense": height_vel_sense},
        },
        log=False,
    )
    return env


def test_hardware_env_default_off_height_vel_est_stays_none():
    env = _hw_env(0.0)
    assert env._height_vel_est is None
    obs = env._obs(_state())
    obs_bare = build_obs(env.cfg, _state(), env._q_nom, env._prev_action,
                         tilt_ref=env._tilt_ref0)
    np.testing.assert_array_equal(obs, obs_bare)


def test_hardware_env_on_creates_estimator_only_after_reset():
    # __init__ alone must not create it (reset() owns the per-episode
    # lifecycle, same as the sim twin's _reset_finalize) -- the estimator
    # here needs an explicit "episode start" the constructor doesn't have.
    env = _hw_env(1.0)
    assert env._height_vel_est is None


def test_hardware_env_obs_tracks_a_real_height_change_once_wired():
    from rl_move.estimator import HeightRateEstimator
    env = _hw_env(1.0)
    env._height_vel_est = HeightRateEstimator(dt=env.dt)
    q0 = _state().joint_position
    obs0 = env._obs(_state(q0))  # first tick: no previous frame -> 0
    assert obs0[-1] == 0.0
    q1 = q0.copy()
    q1[2::3] += 0.05
    st1 = RobotState(
        timestamp=0.0, joint_position=q1, joint_velocity=np.zeros(N_JOINTS),
        imu_roll=0.0, imu_pitch=0.0, imu_yaw=0.0, imu_gyro=np.zeros(3),
        imu_accel=np.zeros(3), commanded_position=np.zeros(N_JOINTS))
    obs1 = env._obs(st1)
    assert obs1[-1] != 0.0  # a real pose change now reads a nonzero rate


def test_height_vel_sense_state_rides_mjx_snap_attrs():
    # Pool-restore lesson (commit-65edba7 bug class, see mjx_host.py's
    # own SNAP_ATTRS comment): any new per-episode attr set in
    # reset/_read_state and read across ticks MUST ride SNAP_ATTRS or a
    # pool-restored episode silently inherits another episode's
    # estimator state.
    from rl_move.sim.mjx_host import SNAP_ATTRS
    assert "_height_vel_est" in SNAP_ATTRS
    assert "_height_vel_mps" in SNAP_ATTRS


def test_joint_goal_env_height_vel_sense_estimator_resets_on_reset():
    from rl_move.config import load_config
    from rl_move.sim.servo_model import SimServoParams
    from rl_move.sim.joint_task import SimHexapodJointGoalEnv, q_rad_to_action

    cfg_on = load_config()
    cfg_on.setdefault("obs", {})["height_vel_sense"] = 1.0
    env = SimHexapodJointGoalEnv(params=SimServoParams.load(),
                                 cfg=cfg_on, randomize=False,
                                 episode_seconds=2.0, seed=0)
    env.reset()
    a = q_rad_to_action(env._cmd.copy())
    for _ in range(3):
        env.step(a)
    # A fresh reset must forget the previous episode's FK frame (first
    # post-reset tick reads exactly 0.0, not a value differenced
    # against the stale last frame of the prior episode -- the exact
    # bug class mjx_host.SNAP_ATTRS exists to catch on pool restores).
    obs, _ = env.reset()
    assert obs[-1] == 0.0
    env.close()
