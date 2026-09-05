"""CPU-only regression checks for faithful multi-rate sensor/write replay."""
import copy
import json
import math

import numpy as np
import pytest

from rl_move.attitude import ComplementaryAttitude, G0
from rl_move.robot_state import JointVelocityFilter, RobotState
from rl_move.sim.deployed_transport import Cadence, DeployedTransport


def raw(t):
    return RobotState(
        timestamp=t, joint_position=np.full(18, t),
        joint_velocity=np.full(18, 999.), imu_roll=999., imu_pitch=999.,
        imu_yaw=0, imu_gyro=np.array([.2, -.1, .3]),
        imu_accel=np.array([0., 0., G0]), commanded_position=np.zeros(18),
        servo_current=np.full(18, 2.), dt=.01)


def test_100_policy_50_write_10_snapshot_counts_and_hold():
    replay = DeployedTransport({}, 100)
    snapshots = []
    writes = []
    for i in range(100):
        t = i / 100
        state = replay.acquire(raw(t))
        if state.timing["snapshot_fresh"]:
            snapshots.append(i)
        if replay.write.due(t):
            writes.append(i)
        assert state.timestamp == pytest.approx((i // 10) / 10)
        assert state.joint_position[0] == state.timestamp
        assert state.timing["full_feedback"] == (i % 10 == 0)
    assert snapshots == list(range(0, 100, 10))
    assert writes == list(range(0, 100, 2))


def test_exact_shared_filters_run_only_on_acquired_frame():
    replay = DeployedTransport({}, 100)
    qd = JointVelocityFilter(alpha=.3)
    att = ComplementaryAttitude(alpha=.98)
    for i in range(31):
        frame = raw(i / 100)
        observed = replay.acquire(frame)
        if i % 10 == 0:
            expected_qd = qd.update(frame.joint_position, frame.timestamp)
            expected_att = att.update(tuple(frame.imu_accel / G0),
                                      tuple(frame.imu_gyro), .1 if i else 0)
        np.testing.assert_array_equal(observed.joint_velocity, expected_qd)
        assert observed.imu_roll == pytest.approx(expected_att.roll)
        assert observed.imu_pitch == pytest.approx(expected_att.pitch)
    assert observed.joint_velocity[0] == pytest.approx(.657)


def test_health_mask_preserves_cached_telemetry_but_not_trip_counts():
    replay = DeployedTransport({}, 100)
    fresh = replay.acquire(raw(0))
    held = replay.acquire(raw(.01))
    assert replay.safety_state(fresh).servo_current is not None
    assert replay.safety_state(held).servo_current is None
    assert held.servo_current is not None
    assert held.timing["feedback_sample_seq"] == fresh.timing["feedback_sample_seq"]


def test_measured_intervals_jitter_reproducible_and_no_catchup_burst():
    a = Cadence(10, intervals_ms=[80, 120], jitter_ms=3, seed=4)
    b = Cadence(10, intervals_ms=[80, 120], jitter_ms=3, seed=4)
    aa = [i for i in range(100) if a.due(i / 100)]
    bb = [i for i in range(100) if b.due(i / 100)]
    assert aa == bb
    assert len(set(np.diff(aa))) > 1
    a.due(10)
    assert not a.due(10)
    assert a.skipped > 0


@pytest.mark.parametrize("cfg", [
    {"snapshot_hz": 0}, {"snapshot_hz": 101},
    {"snapshot_intervals_ms": [0]}, {"snapshot_jitter_ms": 100},
    {"velocity_alpha": math.nan},
    {"snapsho_hz": 10}, {"velocity_max_jump_rad": -1},
])
def test_invalid_contract_fails_loudly(cfg):
    with pytest.raises(ValueError):
        DeployedTransport(cfg, 100)


def test_reset_restarts_filters_and_cadences():
    replay = DeployedTransport({}, 100)
    replay.acquire(raw(0))
    replay.acquire(raw(.1))
    replay.reset()
    state = replay.acquire(raw(20))
    np.testing.assert_array_equal(state.joint_velocity, np.zeros(18))
    assert replay.snapshot.events == 1


def test_disabled_config_is_bit_exact_cpu_rollout():
    pytest.importorskip("mujoco")
    from rl_move.config import load_config
    from rl_move.sim.sim_env import SimHexapodBalanceEnv
    cfg = load_config()
    cfg.setdefault("control", {})["hz"] = 100
    cfg.setdefault("env", {})["model_source"] = "primitive"
    off = copy.deepcopy(cfg)
    off["transport"] = {"enabled": False, "snapshot_hz": -1}
    envs = [SimHexapodBalanceEnv(cfg=c, seed=3, episode_seconds=.2)
            for c in (cfg, off)]
    try:
        resets = [env.reset(seed=3) for env in envs]
        np.testing.assert_array_equal(resets[0][0], resets[1][0])
        for _ in range(10):
            results = [env.step(np.zeros(env.n_act)) for env in envs]
            np.testing.assert_array_equal(results[0][0], results[1][0])
            np.testing.assert_array_equal(envs[0].data.qpos, envs[1].data.qpos)
            assert results[0][1:4] == results[1][1:4]
            assert "transport" not in results[0][4]
    finally:
        for env in envs:
            env.close()


def test_reconstruction_preserves_known_export_contract():
    from rl_move.sim.eval_deployed_transport import reconstructed_config
    meta = dict(training_hz=100, model_source="mesh", walk_obs_body_vel=2,
                walk_phase_obs=1, phase_hz=1.333333,
                walk_speed_min_m_s=.08, walk_speed_max_m_s=.08,
                safety={"max_delta_q_deg": .375})
    cfg = reconstructed_config(meta)
    assert cfg["control"]["hz"] == 100
    assert cfg["goal"]["walk_obs_body_vel"] == 2
    assert cfg["bus"]["write_speed"] == 400
    assert cfg["bus"]["write_acc"] == 20
    assert "servo_vel_max_counts_s" not in cfg["bus"]
    assert cfg["safety"]["max_delta_q_deg"] == .375


def test_frozen_actor_uses_hardware_forward_pass(tmp_path):
    from rl_move.sim.eval_deployed_transport import FrozenActor
    path = tmp_path / "actor.json"
    path.write_text(json.dumps({
        "meta": {"joint_frame": "robot_abs",
                 "joint_contract": "robot_abs_tibia_v2"},
        "W1": [[1., 0.], [0., 1.]], "b1": [0., 0.],
        "W2": [[1., 0.], [0., 1.]], "b2": [0., 0.],
        "Wout": [[1., 0.]] * 18, "bout": [0.] * 18,
    }))
    actor = FrozenActor(path)
    out, _ = actor.predict(np.array([.5, -.2]))
    np.testing.assert_allclose(out, np.full(18, np.tanh(np.tanh(.5))))
    with pytest.raises(ValueError):
        actor.predict(np.zeros(2), deterministic=False)


def test_mjx_refuses_transport_before_building_any_model():
    from rl_move.sim.mjx_host import make_shim_class
    class NeverBuild:
        def __init__(self, **kwargs):
            raise AssertionError("should refuse transport before constructing")
    with pytest.raises(ValueError, match="CPU-only"):
        make_shim_class(NeverBuild)(None, cfg={"transport": {"enabled": True}})
