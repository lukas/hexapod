from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import numpy as np

from hexapod_core.joint_frame import (
    FRAME_ROBOT_ABS,
    JOINT_CONTRACT,
    mujoco_rel_rad_to_robot_abs_rad,
    require_checkpoint_joint_contract,
    require_robot_abs_joint_frame,
    robot_abs_rad_to_mujoco_rel_rad,
)
from rl_move.robot_state import RobotState

ROOT = Path(__file__).resolve().parents[2]
LINUX = ROOT / "linux_control"
if str(LINUX) not in sys.path:
    sys.path.insert(0, str(LINUX))

import rl_policy  # noqa: E402


def _pose_rad() -> np.ndarray:
    q = np.zeros(18)
    for leg in range(6):
        q[3 * leg + 0] = 0.01 * leg
        q[3 * leg + 1] = 0.2 + 0.01 * leg
        q[3 * leg + 2] = 0.55 + 0.02 * leg
    return q


def test_robot_abs_mujoco_rel_roundtrip():
    q_abs = _pose_rad()
    q_rel = robot_abs_rad_to_mujoco_rel_rad(q_abs)
    for leg in range(6):
        hip = 3 * leg + 1
        knee = 3 * leg + 2
        assert q_rel[knee] == q_abs[knee] - q_abs[hip]
    np.testing.assert_allclose(mujoco_rel_rad_to_robot_abs_rad(q_rel),
                               q_abs)


def test_hardware_walk_20_80_is_mujoco_20_60_not_20_80():
    """Regression for physical-parity replays accidentally using the legacy
    MuJoCo +20/+80-relative policy plant (= +20/+100 absolute)."""
    q_abs_deg = np.asarray([0.0, 20.0, 80.0] * 6)
    q_rel_deg = np.degrees(robot_abs_rad_to_mujoco_rel_rad(
        np.radians(q_abs_deg)
    ))
    np.testing.assert_allclose(q_rel_deg, [0.0, 20.0, 60.0] * 6,
                               atol=1e-9)
    np.testing.assert_allclose(
        np.degrees(mujoco_rel_rad_to_robot_abs_rad(np.radians(q_rel_deg))),
        q_abs_deg,
        atol=1e-9,
    )


def test_joint_policy_surface_is_robot_abs_while_mujoco_stays_private():
    from rl_move.sim.joint_task import (
        SimHexapodJointGoalEnv, action_to_q_rad, q_rad_to_action,
    )
    from rl_move.sim.sim_env import _default_plant_deg

    q_abs = np.radians(np.asarray([0.0, 20.0, 80.0] * 6))
    np.testing.assert_allclose(
        action_to_q_rad(q_rad_to_action(q_abs)), q_abs, atol=1e-12)
    env = SimHexapodJointGoalEnv.__new__(SimHexapodJointGoalEnv)
    q_mujoco = env._logical_to_mujoco_q(q_abs)
    np.testing.assert_allclose(np.degrees(q_mujoco),
                               [0.0, 20.0, 60.0] * 6, atol=1e-9)
    np.testing.assert_allclose(env._mujoco_to_logical_q(q_mujoco),
                               q_abs, atol=1e-12)
    np.testing.assert_allclose(_default_plant_deg(),
                               [0.0, 20.0, 80.0] * 6, atol=1e-9)


def test_policy_artifacts_must_declare_robot_abs():
    assert require_robot_abs_joint_frame(
        {"joint_frame": "robot_abs",
         "joint_contract": JOINT_CONTRACT}) == FRAME_ROBOT_ABS
    for meta in ({}, {"joint_frame": "robot_abs"},
                 {"joint_frame": "model_rel",
                  "joint_contract": JOINT_CONTRACT}):
        with np.testing.assert_raises(ValueError):
            require_robot_abs_joint_frame(meta)


def test_checkpoint_requires_both_frame_and_contract(tmp_path):
    def checkpoint(name: str, data: dict) -> Path:
        path = tmp_path / name
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("data", json.dumps(data))
        return path

    valid = checkpoint("valid.zip", {
        "joint_frame": FRAME_ROBOT_ABS,
        "joint_contract": JOINT_CONTRACT,
    })
    assert require_checkpoint_joint_contract(valid) == JOINT_CONTRACT
    for i, meta in enumerate((
        {"joint_contract": JOINT_CONTRACT},
        {"joint_frame": FRAME_ROBOT_ABS},
        {"joint_frame": "model_rel", "joint_contract": JOINT_CONTRACT},
    )):
        with np.testing.assert_raises(ValueError):
            require_checkpoint_joint_contract(checkpoint(f"bad{i}.zip", meta))


def test_robot_runner_state_view_is_never_reinterpreted():
    q_abs = _pose_rad()
    state = RobotState(
        timestamp=1.0,
        joint_position=q_abs,
        joint_velocity=q_abs * 0.1,
        imu_roll=0.0,
        imu_pitch=0.0,
        imu_yaw=0.0,
        imu_gyro=np.zeros(3),
        imu_accel=np.zeros(3),
        commanded_position=q_abs + 0.01,
    )
    view = rl_policy._state_for_policy_frame(state, FRAME_ROBOT_ABS)
    assert view is state
    with np.testing.assert_raises(ValueError):
        rl_policy._state_for_policy_frame(state, "model_rel")


def test_plant_pose_is_stamped_and_unstamped_file_is_rejected(
        tmp_path, monkeypatch):
    from motor_setup import feetech_bus

    path = tmp_path / "plant_pose.json"
    monkeypatch.setattr(feetech_bus, "PLANT_PATH_CANDIDATES", (path,))
    path.write_text(json.dumps({"hip_deg": 20.0, "knee_deg": 80.0}))
    assert feetech_bus.load_plant_pose()["learned"] is False

    saved = feetech_bus.save_plant_pose(20.0, 80.0)
    raw = json.loads(saved.read_text())
    assert raw["joint_frame"] == FRAME_ROBOT_ABS
    assert raw["joint_contract"] == JOINT_CONTRACT
    loaded = feetech_bus.load_plant_pose()
    assert loaded["learned"] is True
    assert loaded["joint_frame"] == FRAME_ROBOT_ABS
    assert loaded["joint_contract"] == JOINT_CONTRACT
