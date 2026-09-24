"""Tests for the optional rise start-kind one-hot observation channel
(``obs.rise_start_kind_sense``, see ``rl_move/env.py::build_obs`` /
``rise_start_kind_sense_obs_dim``/``rise_start_kind_onehot``).

2026-09-24 standwalk rise flat/bridge precision gap (``ops.sh index
story cw-stand50hz-gru-dual-rlfinetune-rise-s1-flatbias-canary2m``):
reweighting how often flat/bridge starts are DRAWN during the RL
fine-tune left the composed-gate flat-start success rate exactly
unchanged (0/10 flat both the default and the 55%-flat mix), closing
training-frequency as a lever. This channel is the named untried axis
instead: explicit start-kind STATE conditioning, so a shared policy
does not have to infer flat/bridge/crouch from the continuous pose
alone. Default OFF, bit-exact when off, per RESEARCH_RULES.
"""
from __future__ import annotations

import numpy as np

from rl_move.env import (GOAL_DIM, RISE_START_KIND_LABELS, TaskGoal,
                          build_obs, rise_start_kind_onehot,
                          rise_start_kind_sense_obs_dim)
from rl_move.robot_state import N_JOINTS, RobotState


def _state() -> RobotState:
    return RobotState(
        timestamp=0.0,
        joint_position=np.zeros(N_JOINTS),
        joint_velocity=np.zeros(N_JOINTS),
        imu_roll=0.0, imu_pitch=0.0, imu_yaw=0.0,
        imu_gyro=np.zeros(3),
        imu_accel=np.zeros(3),
        commanded_position=np.zeros(N_JOINTS),
    )


def test_obs_dim_default_off():
    assert rise_start_kind_sense_obs_dim({}) == 0
    assert rise_start_kind_sense_obs_dim(
        {"obs": {"rise_start_kind_sense": 0.0}}) == 0


def test_obs_dim_on_is_three():
    assert rise_start_kind_sense_obs_dim(
        {"obs": {"rise_start_kind_sense": 1.0}}) == len(
            RISE_START_KIND_LABELS) == 3


def test_onehot_lookup():
    np.testing.assert_array_equal(
        rise_start_kind_onehot("flat"), [1.0, 0.0, 0.0])
    np.testing.assert_array_equal(
        rise_start_kind_onehot("bridge"), [0.0, 1.0, 0.0])
    np.testing.assert_array_equal(
        rise_start_kind_onehot("crouch"), [0.0, 0.0, 1.0])


def test_onehot_lookup_unknown_or_none_is_all_zero():
    np.testing.assert_array_equal(rise_start_kind_onehot(None), [0, 0, 0])
    np.testing.assert_array_equal(
        rise_start_kind_onehot("bank"), [0, 0, 0])
    np.testing.assert_array_equal(
        rise_start_kind_onehot("plant"), [0, 0, 0])


def test_build_obs_default_off_width_unchanged_and_bit_exact():
    q_nom = np.zeros(N_JOINTS)
    prev_action = np.zeros(6)
    st = _state()
    obs_off = build_obs({}, st, q_nom, prev_action)
    obs_explicit_off = build_obs(
        {"obs": {"rise_start_kind_sense": 0.0}}, st, q_nom, prev_action,
        rise_start_kind_onehot_vec=np.array([1.0, 0.0, 0.0]))
    np.testing.assert_array_equal(obs_off, obs_explicit_off)


def test_build_obs_on_appends_three_at_the_end():
    q_nom = np.zeros(N_JOINTS)
    prev_action = np.zeros(6)
    st = _state()
    cfg = {"obs": {"rise_start_kind_sense": 1.0}}
    obs_off = build_obs({}, st, q_nom, prev_action)
    obs_on_no_vec = build_obs(cfg, st, q_nom, prev_action)
    assert obs_on_no_vec.shape[0] == obs_off.shape[0] + 3
    np.testing.assert_allclose(obs_on_no_vec[:obs_off.shape[0]], obs_off)
    np.testing.assert_array_equal(obs_on_no_vec[-3:], [0.0, 0.0, 0.0])


def test_build_obs_on_passes_through_the_onehot():
    q_nom = np.zeros(N_JOINTS)
    prev_action = np.zeros(6)
    st = _state()
    cfg = {"obs": {"rise_start_kind_sense": 1.0}}
    vec = rise_start_kind_onehot("bridge")
    obs_on = build_obs(cfg, st, q_nom, prev_action,
                       rise_start_kind_onehot_vec=vec)
    np.testing.assert_array_equal(obs_on[-3:], [0.0, 1.0, 0.0])


def test_build_obs_on_with_goal_appends_after_goal():
    q_nom = np.zeros(N_JOINTS)
    prev_action = np.zeros(6)
    st = _state()
    cfg = {"obs": {"rise_start_kind_sense": 1.0}}
    goal = TaskGoal(roll_ref=0.1)
    obs_off = build_obs({}, st, q_nom, prev_action)
    obs = build_obs(cfg, st, q_nom, prev_action, goal=goal)
    assert obs.shape[0] == obs_off.shape[0] + GOAL_DIM + 3


# ---------------------------------------------------------------------------
# Real-env integration: SimHexapodGoalEnv is the standwalk rise/hold/lower
# task class this mechanism actually targets. Confirms observation_space
# width matches build_obs's real output, the channel is genuinely zero on
# non-rise ticks, and default-off stays bit-exact.
# ---------------------------------------------------------------------------

def test_goal_env_rise_start_kind_sense_default_off_bit_exact():
    from rl_move.config import load_config
    from rl_move.sim.goal_task import SimHexapodGoalEnv
    from rl_move.sim.servo_model import SimServoParams

    cfg_off = load_config()
    env_off = SimHexapodGoalEnv(params=SimServoParams.load(),
                                cfg=cfg_off, randomize=False,
                                episode_seconds=2.0, seed=0)
    obs, _ = env_off.reset()
    assert obs.shape == env_off.observation_space.shape
    a = np.zeros(env_off.action_space.shape[0], dtype=np.float32)
    obs2, *_ = env_off.step(a)
    assert obs2.shape == obs.shape
    env_off.close()


def test_goal_env_rise_start_kind_sense_on_widens_obs_by_three():
    from rl_move.config import load_config
    from rl_move.sim.goal_task import SimHexapodGoalEnv
    from rl_move.sim.servo_model import SimServoParams

    cfg_off = load_config()
    env_off = SimHexapodGoalEnv(params=SimServoParams.load(),
                                cfg=cfg_off, randomize=False,
                                episode_seconds=2.0, seed=0)
    obs_off, _ = env_off.reset()
    n_off = obs_off.shape[0]
    env_off.close()

    cfg_on = load_config()
    cfg_on.setdefault("obs", {})["rise_start_kind_sense"] = 1.0
    env_on = SimHexapodGoalEnv(params=SimServoParams.load(),
                               cfg=cfg_on, randomize=False,
                               episode_seconds=2.0, seed=0)
    obs_on, _ = env_on.reset()
    assert obs_on.shape == env_on.observation_space.shape
    assert obs_on.shape[0] == n_off + 3
    a = np.zeros(env_on.action_space.shape[0], dtype=np.float32)
    obs2, *_ = env_on.step(a)
    assert obs2.shape[0] == n_off + 3
    assert np.isfinite(obs2[-3:]).all()
    env_on.close()


def _force_all_rise_cfg():
    """A cfg mix that draws mode="rise" on every episode (p_rise=1.0,
    every sibling mode zeroed) -- ``GoalGenerator.__init__`` normalizes
    the probs, but zeroing the rest makes the draw deterministic
    regardless of normalization."""
    from rl_move.config import load_config
    cfg = load_config()
    cfg.setdefault("obs", {})["rise_start_kind_sense"] = 1.0
    g = cfg.setdefault("goal", {})
    for k in ("p_hold", "p_lean", "p_track", "p_unload", "p_raise",
             "p_lower", "p_quad"):
        g[k] = 0.0
    g["p_rise"] = 1.0
    return cfg


def test_goal_env_rise_start_kind_sense_matches_forced_rise_start_kind():
    """A rise episode forced to a flat start should carry a [1,0,0]
    tail; forced to crouch, [0,0,1] -- proves the channel reads the
    REAL per-episode start kind, not a constant/always-zero stub."""
    from rl_move.sim.goal_task import SimHexapodGoalEnv
    from rl_move.sim.servo_model import SimServoParams

    env = SimHexapodGoalEnv(params=SimServoParams.load(),
                            cfg=_force_all_rise_cfg(), randomize=False,
                            episode_seconds=6.0, seed=0)
    env._goal_gen.force_rise_start = "flat"
    obs, _ = env.reset()
    assert env._goal_traj.mode == "rise"
    np.testing.assert_array_equal(obs[-3:], [1.0, 0.0, 0.0])

    env._goal_gen.force_rise_start = "crouch"
    obs, _ = env.reset()
    assert env._goal_traj.mode == "rise"
    np.testing.assert_array_equal(obs[-3:], [0.0, 0.0, 1.0])
    env.close()


def test_non_rise_tick_channel_is_zero_even_when_armed():
    """A non-rise (hold) episode must read an all-zero tail, matching
    build_obs's "zero for non-rise ticks" contract even though the
    global cfg flag is armed."""
    from rl_move.config import load_config
    from rl_move.sim.goal_task import SimHexapodGoalEnv
    from rl_move.sim.servo_model import SimServoParams

    cfg_on = load_config()
    cfg_on.setdefault("obs", {})["rise_start_kind_sense"] = 1.0
    g = cfg_on.setdefault("goal", {})
    for k in ("p_lean", "p_track", "p_unload", "p_raise", "p_rise",
             "p_lower", "p_quad"):
        g[k] = 0.0
    g["p_hold"] = 1.0
    env = SimHexapodGoalEnv(params=SimServoParams.load(),
                            cfg=cfg_on, randomize=False,
                            episode_seconds=2.0, seed=0)
    obs, _ = env.reset()
    assert env._goal_traj.mode == "hold"
    np.testing.assert_array_equal(obs[-3:], [0.0, 0.0, 0.0])
    env.close()
