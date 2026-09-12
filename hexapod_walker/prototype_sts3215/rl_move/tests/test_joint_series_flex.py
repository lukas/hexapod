"""Mechanics tests for the isolated post-encoder series-flex topology."""
from __future__ import annotations

import math
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


mujoco = pytest.importorskip("mujoco")

from rl_move.sim import joint_series_flex as JSF
from rl_move.sim.servo_model import (
    MESH_MJX_XML,
    joint_qpos_addrs,
    joint_qvel_addrs,
    position_actuator_ids,
)


@pytest.fixture(autouse=True)
def _pin_model_family(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")


def _joint_table(**overrides):
    table = {}
    for index, name in enumerate(JSF.ACTIVE_JOINT_NAMES):
        values = {
            "stiffness_nm_rad": 20.0 + index,
            "damping_nms_rad": 0.1 + index * 0.01,
            "frictionloss_nm": index * 0.001,
            "springref_deg": 0.0,
            "range_deg": [-6.0, 6.0],
        }
        values.update(overrides)
        table[name] = values
    return table


def _cfg(*, legs=range(6), axes=JSF.AXES, joints=None):
    return {
        "joint_series_flex": {
            "enabled": 1,
            "legs": list(legs),
            "axes": list(axes),
            "joints": _joint_table() if joints is None else joints,
        }
    }


def test_checked_in_probe_is_explicit_and_default_safe():
    path = Path(JSF.__file__).with_name("joint_series_flex_probe.json")
    blob = json.loads(path.read_text())
    spec = JSF.from_cfg({
        "joint_series_flex": {
            **blob["joint_series_flex"],
            "enabled": 1,
        }
    })

    assert spec is not None
    assert spec.selected_joint_names == tuple(
        name for name in JSF.ACTIVE_JOINT_NAMES if not name.endswith("_yaw"))
    assert spec.params("L0_pitch").stiffness_nm_rad == 180.0
    assert spec.params("L0_knee").stiffness_nm_rad == 120.0
    assert "not a calibrated" in blob["purpose"]


def _base_spec():
    return mujoco.MjSpec.from_string(MESH_MJX_XML.read_text())


def _flex_model(*, legs=range(6), axes=JSF.AXES):
    spec = JSF.from_cfg(_cfg(legs=legs, axes=axes))
    assert spec is not None
    return JSF.apply_to_mjspec(_base_spec(), spec).compile(), spec


def _output_body_name(active_name: str) -> str:
    leg, axis = active_name.split("_", 1)
    return {
        "yaw": leg + "_yaw",
        "pitch": leg + "_femur",
        "knee": leg + "_tibia",
    }[axis]


def test_config_is_default_off_and_requires_explicit_complete_table():
    assert JSF.from_cfg({}) is None
    assert JSF.from_cfg({"joint_series_flex": {"enabled": 0}}) is None
    with pytest.raises(ValueError, match="requires joint_series_flex.legs"):
        JSF.from_cfg({"joint_series_flex": {"enabled": 1}})

    joints = _joint_table()
    joints.pop("L5_knee")
    with pytest.raises(ValueError, match="exactly the 18.*L5_knee"):
        JSF.from_cfg(_cfg(joints=joints))

    joints = _joint_table()
    joints["L0_pitch"]["stiffnes_nm_rad"] = 1.0
    with pytest.raises(ValueError, match="unknown.*stiffnes_nm_rad"):
        JSF.from_cfg(_cfg(joints=joints))


def test_config_selection_is_canonical_and_values_are_per_joint():
    spec = JSF.from_cfg(_cfg(legs=[4, 1], axes=["knee", "pitch"]))
    assert spec is not None
    assert spec.legs == (1, 4)
    assert spec.axes == ("pitch", "knee")
    assert spec.selected_joint_names == (
        "L1_pitch", "L1_knee", "L4_pitch", "L4_knee")
    assert len(spec.entries) == 18
    assert spec.params("L4_knee").stiffness_nm_rad == 34.0

    with pytest.raises(ValueError, match="unique indices"):
        JSF.from_cfg(_cfg(legs=[4, 4]))
    with pytest.raises(ValueError, match="selected from"):
        JSF.from_cfg(_cfg(axes=["hip"]))
    with pytest.raises(ValueError, match="stiffness_nm_rad must be > 0"):
        JSF.from_cfg(_cfg(joints=_joint_table(stiffness_nm_rad=0.0)))


def test_full_rewrite_preserves_action_contract_inertia_and_keyframes():
    base_spec = _base_spec()
    base = base_spec.compile()
    # apply_to_mjspec serializes canonical MJCF, whose decimal formatting is
    # the correct rigid reference for comparing the rewritten model.
    canonical = mujoco.MjSpec.from_string(base_spec.to_xml()).compile()
    model, spec = _flex_model()
    addrs = JSF.addresses(model, expected=spec)
    assert addrs is not None

    assert (model.nq, model.nv, model.nu) == (
        base.nq + 18, base.nv + 18, base.nu)
    assert len(position_actuator_ids(model)) == 18
    assert joint_qpos_addrs(model).shape == (18,)
    assert joint_qvel_addrs(model).shape == (18,)
    assert model.body_mass.sum() == pytest.approx(
        canonical.body_mass.sum(), abs=2e-12)

    for active_name in JSF.ACTIVE_JOINT_NAMES:
        active_jid = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_JOINT, active_name)
        flex_jid = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_JOINT,
            active_name + "_series_flex")
        carrier_bid = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_BODY,
            active_name + "_encoder_carrier")
        output_bid = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_BODY,
            _output_body_name(active_name))
        assert model.jnt_bodyid[active_jid] == carrier_bid
        assert model.jnt_bodyid[flex_jid] == output_bid
        assert model.body_parentid[output_bid] == carrier_bid
        assert model.jnt_axis[flex_jid] == pytest.approx(
            model.jnt_axis[active_jid])
        params = spec.params(active_name)
        flex_dof = int(model.jnt_dofadr[flex_jid])
        flex_qpos = int(model.jnt_qposadr[flex_jid])
        assert model.jnt_stiffness[flex_jid] == pytest.approx(
            params.stiffness_nm_rad)
        assert model.dof_damping[flex_dof] == pytest.approx(
            params.damping_nms_rad)
        assert model.dof_frictionloss[flex_dof] == pytest.approx(
            params.frictionloss_nm)
        assert model.qpos_spring[flex_qpos] == pytest.approx(
            math.radians(params.springref_deg))
        assert model.jnt_range[flex_jid] == pytest.approx(
            np.radians(params.range_deg))

        base_bid = mujoco.mj_name2id(
            canonical, mujoco.mjtObj.mjOBJ_BODY,
            _output_body_name(active_name))
        assert (model.body_mass[carrier_bid] + model.body_mass[output_bid]
                == pytest.approx(canonical.body_mass[base_bid], rel=1e-12))
        assert (model.body_inertia[carrier_bid] + model.body_inertia[output_bid]
                == pytest.approx(canonical.body_inertia[base_bid], rel=1e-12))

    # Actuator transmissions still name the upstream, encoder-side joints.
    actuator_ids = position_actuator_ids(model)
    assert model.actuator_trnid[actuator_ids, 0] == pytest.approx(
        [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
         for name in JSF.ACTIVE_JOINT_NAMES])
    assert not set(model.actuator_trnid[actuator_ids, 0]) & set(
        addrs.flex_joint_ids)

    for key_name in ("plant", "stance"):
        old_key = mujoco.mj_name2id(
            base, mujoco.mjtObj.mjOBJ_KEY, key_name)
        new_key = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_KEY, key_name)
        assert model.key_qpos[new_key, joint_qpos_addrs(model)] \
            == pytest.approx(base.key_qpos[old_key, joint_qpos_addrs(base)])
        assert model.key_qpos[new_key, list(addrs.flex_qpos_addrs)] \
            == pytest.approx(0.0)

    # With hidden deflection zero, restructuring the tree must not move any
    # original collision or visual geometry.
    old_data = mujoco.MjData(base)
    new_data = mujoco.MjData(model)
    old_key = mujoco.mj_name2id(
        base, mujoco.mjtObj.mjOBJ_KEY, "plant")
    new_key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "plant")
    mujoco.mj_resetDataKeyframe(base, old_data, old_key)
    mujoco.mj_resetDataKeyframe(model, new_data, new_key)
    mujoco.mj_forward(base, old_data)
    mujoco.mj_forward(model, new_data)
    for old_gid in range(base.ngeom):
        name = mujoco.mj_id2name(
            base, mujoco.mjtObj.mjOBJ_GEOM, old_gid)
        if name is None:
            continue
        new_gid = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_GEOM, name)
        assert new_data.geom_xpos[new_gid] == pytest.approx(
            old_data.geom_xpos[old_gid], abs=5e-7)
        assert new_data.geom_xmat[new_gid] == pytest.approx(
            old_data.geom_xmat[old_gid], abs=5e-7)


def test_selector_installs_only_l4_load_bearing_pitch_and_knee():
    base = _base_spec().compile()
    model, spec = _flex_model(legs=[4], axes=["pitch", "knee"])
    addrs = JSF.addresses(model, expected=spec)
    assert addrs is not None
    assert addrs.joint_names == ("L4_pitch", "L4_knee")
    assert (model.nq, model.nv, model.nu) == (
        base.nq + 2, base.nv + 2, base.nu)
    assert mujoco.mj_name2id(
        model, mujoco.mjtObj.mjOBJ_BODY,
        "L4_yaw_encoder_carrier") == -1

    all_spec = JSF.from_cfg(_cfg())
    assert all_spec is not None
    with pytest.raises(ValueError, match="selection does not match"):
        JSF.addresses(model, expected=all_spec)


def test_l4_hip_and_knee_loads_pass_through_true_series_coordinates():
    model, spec = _flex_model(legs=[4], axes=["pitch", "knee"])
    addrs = JSF.addresses(model, expected=spec)
    assert addrs is not None
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)

    pad_bid = mujoco.mj_name2id(
        model, mujoco.mjtObj.mjOBJ_BODY, "L4_pad")
    jacp = np.zeros((3, model.nv))
    jacr = np.zeros((3, model.nv))
    mujoco.mj_jacBody(model, data, jacp, jacr, pad_bid)
    wrench = np.array([0.7, -1.1, 1.9, 0.2, 0.4, -0.3])

    for active_name in ("L4_pitch", "L4_knee"):
        active_jid = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_JOINT, active_name)
        flex_jid = mujoco.mj_name2id(
            model, mujoco.mjtObj.mjOBJ_JOINT,
            active_name + "_series_flex")
        active_dof = int(model.jnt_dofadr[active_jid])
        flex_dof = int(model.jnt_dofadr[flex_jid])
        # Identical screw axes mean a downstream foot wrench reflects the
        # same generalized torque to encoder and spring coordinates.
        assert jacp[:, active_dof] == pytest.approx(jacp[:, flex_dof])
        assert jacr[:, active_dof] == pytest.approx(jacr[:, flex_dof])
        active_tau = np.r_[jacp[:, active_dof], jacr[:, active_dof]] @ wrench
        flex_tau = np.r_[jacp[:, flex_dof], jacr[:, flex_dof]] @ wrench
        assert active_tau == pytest.approx(flex_tau)
        assert abs(active_tau) > 1e-3

    data.qpos[list(addrs.flex_qpos_addrs)] = np.radians([2.0, -3.0])
    mujoco.mj_forward(model, data)
    for jid, qaddr, daddr in zip(
            addrs.flex_joint_ids, addrs.flex_qpos_addrs,
            addrs.flex_dof_addrs):
        expected_tau = -model.jnt_stiffness[jid] * data.qpos[qaddr]
        assert data.qfrc_passive[daddr] == pytest.approx(expected_tau)


def test_diagnostics_separates_encoder_flex_and_output_angles():
    model, spec = _flex_model(legs=[4], axes=["pitch", "knee"])
    addrs = JSF.addresses(model, expected=spec)
    assert addrs is not None
    data = mujoco.MjData(model)
    data.qpos[list(addrs.active_qpos_addrs)] = np.radians([10.0, 20.0])
    data.qpos[list(addrs.flex_qpos_addrs)] = np.radians([2.0, -3.0])
    data.qvel[list(addrs.flex_dof_addrs)] = np.radians([4.0, -5.0])
    mujoco.mj_forward(model, data)

    out = JSF.diagnostics(model, data)
    assert out["joint_names"] == ["L4_pitch", "L4_knee"]
    assert out["encoder_angle_deg"] == pytest.approx([10.0, 20.0])
    assert out["flex_angle_deg"] == pytest.approx([2.0, -3.0])
    assert out["output_angle_deg"] == pytest.approx([12.0, 17.0])
    assert out["flex_velocity_deg_s"] == pytest.approx([4.0, -5.0])
    assert out["max_abs_flex_deg"] == pytest.approx(3.0)

    host_data = SimpleNamespace(
        qpos=data.qpos.copy(), qvel=data.qvel.copy())
    assert JSF.diagnostics(model, host_data)["passive_force_nm"] is None
    rigid = _base_spec().compile()
    assert JSF.diagnostics(rigid, mujoco.MjData(rigid)) == {"enabled": False}


def test_noop_double_install_and_mjx_conversion():
    source = _base_spec()
    assert JSF.apply_to_mjspec(source, None) is source
    assert JSF.addresses(source.compile(), required=False) is None

    spec = JSF.from_cfg(_cfg(legs=[4], axes=["pitch", "knee"]))
    assert spec is not None
    installed = JSF.apply_to_mjspec(source, spec)
    with pytest.raises(ValueError, match="already or partially installed"):
        JSF.apply_to_mjspec(installed, spec)

    pytest.importorskip("jax")
    mjx = pytest.importorskip("mujoco.mjx")
    model = installed.compile()
    device_model = mjx.put_model(model)
    assert (device_model.nq, device_model.nv, device_model.nu) == (
        model.nq, model.nv, model.nu)
    assert device_model.jnt_stiffness.shape == model.jnt_stiffness.shape


def test_build_model_private_env_and_shared_mjx_host_wiring(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")
    from rl_move.config import load_config
    from rl_move.sim.mjx_host import prepare_shared_model
    from rl_move.sim.servo_model import SimServoParams, build_model
    from rl_move.sim.sim_env import SimHexapodBalanceEnv

    cfg = deepcopy(load_config())
    cfg["struct_comp"]["enabled"] = 0
    cfg["leg_mount_flex"]["enabled"] = 0
    cfg["joint_series_flex"] = _cfg(
        legs=[4], axes=["pitch", "knee"])["joint_series_flex"]
    spec = JSF.from_cfg(cfg)
    assert spec is not None

    direct = build_model(source="mesh_mjx", joint_series_flex=spec)
    direct_addrs = JSF.addresses(direct, expected=spec)
    assert direct_addrs is not None
    assert direct_addrs.joint_names == ("L4_pitch", "L4_knee")

    private = SimHexapodBalanceEnv(
        cfg=cfg, randomize=False, episode_seconds=0.1)
    obs, info = private.reset(seed=0)
    obs2, *_ = private.step(np.zeros(6))
    assert obs.shape == obs2.shape == (47,)
    assert private.action_space.shape == (6,)
    assert info["joint_series_flex"]["joint_names"] \
        == ["L4_pitch", "L4_knee"]
    private.close()

    shared = prepare_shared_model(
        SimServoParams.defaults(), iterations=10, ls_iterations=10,
        cfg=cfg)
    shared_env = SimHexapodBalanceEnv(
        cfg=cfg, model=shared, randomize=False, episode_seconds=0.1)
    shared_obs, shared_info = shared_env.reset(seed=0)
    assert shared_obs.shape == (47,)
    assert shared_info["joint_series_flex"]["enabled"] is True
    shared_env.close()


def test_runtime_rejects_every_compliance_double_count(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")
    from rl_move.config import load_config
    from rl_move.sim.leg_mount_flex import from_cfg as mount_from_cfg
    from rl_move.sim.servo_model import build_model
    from rl_move.sim.sim_env import SimHexapodBalanceEnv

    base = deepcopy(load_config())
    base["joint_series_flex"] = _cfg(
        legs=[4], axes=["pitch", "knee"])["joint_series_flex"]
    with pytest.raises(ValueError, match="cannot both be enabled"):
        SimHexapodBalanceEnv(
            cfg=base, randomize=False, episode_seconds=0.1)

    base["struct_comp"]["enabled"] = 0
    base["leg_mount_flex"] = {
        "enabled": 1,
        "stiffness_nm_rad": 20.0,
        "damping_nms_rad": 0.5,
        "frictionloss_nm": 0.0,
        "springref_deg": 0.0,
        "range_deg": [-6.0, 6.0],
    }
    with pytest.raises(ValueError, match="cannot both be enabled"):
        SimHexapodBalanceEnv(
            cfg=base, randomize=False, episode_seconds=0.1)

    series_spec = JSF.from_cfg(base)
    mount_spec = mount_from_cfg(base)
    with pytest.raises(ValueError, match="mutually exclusive"):
        build_model(source="mesh_mjx", leg_mount_flex=mount_spec,
                    joint_series_flex=series_spec)


def test_legacy_rise_full_state_remaps_by_named_encoder_addresses(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")
    from rl_move.config import load_config
    from rl_move.sim.sim_env import SimHexapodBalanceEnv

    cfg = deepcopy(load_config())
    cfg["struct_comp"]["enabled"] = 0
    cfg["leg_mount_flex"]["enabled"] = 0
    cfg["joint_series_flex"] = _cfg(
        legs=[4], axes=["pitch", "knee"])["joint_series_flex"]
    env = SimHexapodBalanceEnv(
        cfg=cfg, randomize=False, episode_seconds=0.1)

    rigid_qpos = np.zeros(25)
    rigid_qpos[2] = 0.16
    rigid_qpos[3] = 1.0
    rigid_qpos[7:25] = np.linspace(-0.2, 0.2, 18)
    rigid_qvel = np.linspace(-0.3, 0.3, 24)
    env._exact_start_pending = (rigid_qpos.copy(), rigid_qvel.copy())
    env._settle = lambda *args, **kwargs: None

    obs, _ = env.reset(seed=0)

    assert obs.shape == (47,)
    assert env.model.nq == 27 and env.model.nv == 26
    assert env.data.qpos[env._qadr] == pytest.approx(rigid_qpos[7:25])
    assert env.data.qvel[env._vadr] == pytest.approx(rigid_qvel[6:24])
    addrs = JSF.addresses(env.model)
    assert addrs is not None
    assert env.data.qpos[list(addrs.flex_qpos_addrs)] \
        == pytest.approx(env.model.qpos0[list(addrs.flex_qpos_addrs)])
    assert env.data.qvel[list(addrs.flex_dof_addrs)] == pytest.approx(0.0)
    env.close()


def test_replay_records_series_deflection_without_changing_servo_shape(
        monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")
    from rl_move.sim.replay_trace import _ReplaySim, analyze
    from rl_move.sim.servo_model import SimServoParams

    spec = JSF.from_cfg(_cfg(legs=[4], axes=["pitch", "knee"]))
    assert spec is not None
    q0 = np.tile([0.0, 20.0, 80.0], 6)
    n = 25
    trace = {
        "q": np.tile(q0, (n, 1)),
        "cmd": np.tile(q0, (n, 1)),
        "t": np.arange(n, dtype=float) * 0.04,
        "roll": np.zeros(n),
        "pitch": np.zeros(n),
        "ref_roll": 0.0,
        "ref_pitch": 0.0,
        "gyro_x": np.zeros(n),
        "gyro_y": np.zeros(n),
        "current_a": np.full((n, 18), np.nan),
    }

    result = _ReplaySim(
        SimServoParams.load(), model_source="mesh_mjx",
        joint_series_flex=spec).replay(trace, settle_s=0.0)
    metrics = analyze(trace, result)

    assert result["q"].shape == (n, 18)
    assert result["series_flex_deg"].shape == (n, 18)
    assert metrics["sim_max_series_flex_deg"] >= 0.0


def test_link_length_randomization_targets_series_carrier_offsets():
    from rl_move.sim.domain_rand import DomainRandomizer
    from rl_move.sim.servo_model import build_model

    spec = JSF.from_cfg(_cfg(legs=[4], axes=["pitch", "knee"]))
    assert spec is not None
    model = build_model(source="mesh_mjx", joint_series_flex=spec)
    pitch_carrier = mujoco.mj_name2id(
        model, mujoco.mjtObj.mjOBJ_BODY, "L4_pitch_encoder_carrier")
    knee_carrier = mujoco.mj_name2id(
        model, mujoco.mjtObj.mjOBJ_BODY, "L4_knee_encoder_carrier")
    femur_output = mujoco.mj_name2id(
        model, mujoco.mjtObj.mjOBJ_BODY, "L4_femur")
    tibia_output = mujoco.mj_name2id(
        model, mujoco.mjtObj.mjOBJ_BODY, "L4_tibia")
    pitch_x = float(model.body_pos[pitch_carrier, 0])
    knee_x = float(model.body_pos[knee_carrier, 0])
    assert model.body_pos[femur_output, 0] == 0.0
    assert model.body_pos[tibia_output, 0] == 0.0

    episode = DomainRandomizer(scale=0.0).sample(
        np.random.default_rng(0))
    episode.link_scale[:] = 1.0
    episode.link_scale[4] = [1.1, 0.9, 1.0]
    chassis = mujoco.mj_name2id(
        model, mujoco.mjtObj.mjOBJ_BODY, "chassis")
    episode.apply_to_model(model, chassis_bid=chassis)

    assert model.body_pos[pitch_carrier, 0] == pytest.approx(1.1 * pitch_x)
    assert model.body_pos[knee_carrier, 0] == pytest.approx(0.9 * knee_x)
    assert model.body_pos[femur_output, 0] == 0.0
    assert model.body_pos[tibia_output, 0] == 0.0
