"""Nominal mesh frame regression: lateral pad offset is not pitch-axis tilt."""
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

mujoco = pytest.importorskip("mujoco")

from hexapod_core.joint_frame import robot_abs_rad_to_mujoco_rel_rad
from rl_move.sim.cart_foot_decode import CartFootDecoder
from rl_move.sim.servo_model import build_model

CENTER = np.tile(np.deg2rad([0, 20, 100]), 6)
BOX = np.array([0.06, 0.035, 0.04])


@pytest.fixture(autouse=True)
def nominal_mesh_family(monkeypatch):
    # conftest's primitive override takes precedence over cfg.
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")


@pytest.fixture
def nominal_decoder():
    model = build_model(source="mesh_mjx")
    return model, CartFootDecoder(model, CENTER, BOX)


def test_nominal_fk_matches_actual_mesh_at_numerical_precision(nominal_decoder):
    model, decoder = nominal_decoder
    assert decoder.verify_fk(model, n=200, seed=0) < 1e-11


def test_ik_round_trip_uses_actual_mujoco_foot_positions(nominal_decoder):
    model, decoder = nominal_decoder
    data = mujoco.MjData(model)
    mujoco.mj_resetData(model, data)
    qadr = model.jnt_qposadr[decoder._jids]
    rng = np.random.default_rng(91)
    for _ in range(100):
        q = CENTER + rng.uniform(-1, 1, 18) * np.tile(
            np.deg2rad([7, 5, 7]), 6)
        data.qpos[qadr] = robot_abs_rad_to_mujoco_rel_rad(q)
        mujoco.mj_kinematics(model, data)
        # Targets come from MuJoCo, not the decoder's own approximate FK.
        feet = np.stack([
            decoder._R[leg] @ (data.site_xpos[sid] - decoder._org[leg])
            for leg, sid in enumerate(decoder._sids)])
        action = ((feet - decoder.center_p) / BOX).reshape(18)
        assert np.max(np.abs(action)) < 1.0
        np.testing.assert_allclose(decoder.decode(action), q, atol=1e-10, rtol=0)


def test_zero_action_stance_and_default_off_joint_targets(nominal_decoder):
    from rl_move.config import load_config
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = load_config()
    cfg.setdefault("env", {})["model_source"] = "mesh_mjx"
    cfg.setdefault("goal", {}).update({
        "joint_action_bias_hip_deg": 40.0,
        "joint_action_bias_knee_deg": 35.0,
        "joint_action_box_yaw_deg": 15.0,
        "joint_action_box_hip_deg": 20.0,
        "joint_action_box_knee_deg": 25.0,
    })
    from copy import deepcopy
    zero_cfg = deepcopy(cfg)
    zero_cfg["goal"].update({f"walk_cart_foot_box_{axis}_m": 0.0
                             for axis in "xyz"})
    absent = SimHexapodJointWalkEnv(cfg=cfg, randomize=False, seed=0)
    off = SimHexapodJointWalkEnv(cfg=zero_cfg, randomize=False, seed=0)
    try:
        assert absent._model_source == off._model_source == "mesh_mjx"
        _, decoder = nominal_decoder
        np.testing.assert_allclose(decoder.decode(np.zeros(18)),
                                   absent._act_to_q(np.zeros(18))[0],
                                   atol=1e-12, rtol=0)
        for action in np.random.default_rng(92).uniform(-1, 1, (30, 18)):
            np.testing.assert_array_equal(absent._act_to_q(action)[0],
                                          off._act_to_q(action)[0])
    finally:
        absent.close()
        off.close()


def test_parallel_pitch_yaw_axes_remain_rejected(nominal_decoder):
    model, decoder = nominal_decoder
    model.jnt_axis[decoder._jids[1]] = model.jnt_axis[decoder._jids[0]]
    with pytest.raises(ValueError, match="pitch axis parallel to yaw axis"):
        CartFootDecoder(model, CENTER, BOX)
