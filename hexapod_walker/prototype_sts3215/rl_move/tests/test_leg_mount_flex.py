"""Mechanics-only tests for the opt-in six-DOF leg-mount flex rewrite."""
from __future__ import annotations

import math
from copy import deepcopy

import numpy as np
import pytest


mujoco = pytest.importorskip("mujoco")

from rl_move.sim import leg_mount_flex as LMF
from rl_move.sim.servo_model import (
    MESH_MJX_XML,
    joint_qpos_addrs,
    joint_qvel_addrs,
    position_actuator_ids,
)


def _cfg(**overrides):
    section = {
        "enabled": 1,
        "stiffness_nm_rad": 20.0,
        "damping_nms_rad": 0.5,
        "frictionloss_nm": 0.0,
        "springref_deg": 0.0,
        "range_deg": [-15.0, 15.0],
    }
    section.update(overrides)
    return {"leg_mount_flex": section}


def _base_spec():
    return mujoco.MjSpec.from_string(MESH_MJX_XML.read_text())


def _flex_model(spec: LMF.LegMountFlexSpec | None = None):
    spec = spec or LMF.from_cfg(_cfg())
    return LMF.apply_to_mjspec(_base_spec(), spec).compile()


def test_config_is_default_off_and_enabled_values_are_explicit():
    assert LMF.from_cfg({}) is None
    assert LMF.from_cfg({"leg_mount_flex": {"enabled": 0}}) is None
    with pytest.raises(ValueError, match="stiffness_nm_rad"):
        LMF.from_cfg({"leg_mount_flex": {"enabled": 1}})
    with pytest.raises(ValueError, match="exactly 0 or 1"):
        LMF.from_cfg({"leg_mount_flex": {"enabled": 0.5}})


def test_config_broadcasts_scalars_and_accepts_per_leg_values():
    spec = LMF.from_cfg(_cfg(
        stiffness_nm_rad=[10, 11, 12, 13, 14, 15],
        damping_nms_rad=[0, 1, 2, 3, 4, 5],
        frictionloss_nm=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
        springref_deg=[-2, -1, 0, 1, 2, 3],
        range_deg=[[-10, 10], [-11, 12], [-12, 13],
                   [-13, 14], [-14, 15], [-15, 16]],
    ))
    assert spec is not None
    assert spec.stiffness_nm_rad == (10, 11, 12, 13, 14, 15)
    assert spec.damping_nms_rad == (0, 1, 2, 3, 4, 5)
    assert spec.springref_deg == (-2, -1, 0, 1, 2, 3)
    assert spec.range_deg[5] == (-15, 16)

    broadcast = LMF.from_cfg(_cfg(range_deg=12.0))
    assert broadcast is not None
    assert broadcast.stiffness_nm_rad == (20.0,) * 6
    assert broadcast.range_deg == ((-12.0, 12.0),) * 6


@pytest.mark.parametrize("key,value,match", [
    ("stiffness_nm_rad", 0.0, "stiffness"),
    ("damping_nms_rad", -0.1, "damping"),
    ("frictionloss_nm", -0.1, "frictionloss"),
    ("range_deg", [0.0, 10.0], "contain 0"),
    ("springref_deg", 20.0, "outside range"),
])
def test_config_rejects_nonphysical_values(key, value, match):
    with pytest.raises(ValueError, match=match):
        LMF.from_cfg(_cfg(**{key: value}))


def test_rewrite_preserves_mass_actuators_and_keyframe_joint_semantics():
    base = _base_spec().compile()
    base_mass = base.body_mass.copy()
    base_inertia = base.body_inertia.copy()
    base_keys = {}
    for key_name in ("plant", "stance"):
        kid = mujoco.mj_name2id(base, mujoco.mjtObj.mjOBJ_KEY, key_name)
        base_keys[key_name] = base.key_qpos[kid, joint_qpos_addrs(base)].copy()

    spec = LMF.from_cfg(_cfg(
        stiffness_nm_rad=[10, 11, 12, 13, 14, 15],
        damping_nms_rad=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        frictionloss_nm=[0.01, 0.02, 0.03, 0.04, 0.05, 0.06],
        springref_deg=[-2, -1, 0, 1, 2, 3],
        range_deg=[[-10, 10], [-11, 12], [-12, 13],
                   [-13, 14], [-14, 15], [-15, 16]],
    ))
    model = _flex_model(spec)

    assert (model.nq, model.nv, model.nu) == (base.nq + 6, base.nv + 6,
                                               base.nu)
    assert np.array_equal(model.body_mass, base_mass)
    assert np.array_equal(model.body_inertia, base_inertia)
    assert joint_qpos_addrs(model).shape == (18,)
    assert joint_qvel_addrs(model).shape == (18,)
    assert position_actuator_ids(model).shape == (18,)

    addrs = LMF.addresses(model)
    assert addrs is not None
    for leg, (jid, qadr, dadr) in enumerate(zip(
            addrs.joint_ids, addrs.qpos_addrs, addrs.dof_addrs)):
        assert np.array_equal(model.jnt_axis[jid], [0.0, 1.0, 0.0])
        assert model.jnt_stiffness[jid] == pytest.approx(10.0 + leg)
        assert model.dof_damping[dadr] == pytest.approx(0.1 * (leg + 1))
        assert model.dof_frictionloss[dadr] == pytest.approx(0.01 * (leg + 1))
        assert model.dof_armature[dadr] == 0.0
        assert model.qpos_spring[qadr] == pytest.approx(
            math.radians(-2 + leg))
        assert model.jnt_range[jid] == pytest.approx(
            np.radians(spec.range_deg[leg]))

    # Adding a joint inside every yaw body interleaves qpos addresses.  The
    # named active joints must nevertheless retain the original key poses,
    # and the hidden flex coordinate must start at geometry-zero (not at its
    # potentially nonzero spring preload reference).
    for key_name in ("plant", "stance"):
        kid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, key_name)
        assert model.key_qpos[kid, joint_qpos_addrs(model)] == pytest.approx(
            base_keys[key_name])
        assert model.key_qpos[kid, addrs.qpos_addrs] == pytest.approx(0.0)


def test_rewrite_is_noop_when_off_and_rejects_partial_or_double_install():
    rigid_spec = _base_spec()
    assert LMF.apply_to_mjspec(rigid_spec, None) is rigid_spec
    rigid = rigid_spec.compile()
    assert LMF.addresses(rigid, required=False) is None
    with pytest.raises(ValueError, match="no leg mount flex"):
        LMF.addresses(rigid)

    flex_spec = LMF.apply_to_mjspec(_base_spec(), LMF.from_cfg(_cfg()))
    with pytest.raises(ValueError, match="already exists"):
        LMF.apply_to_mjspec(flex_spec, LMF.from_cfg(_cfg()))

    partial = _base_spec()
    partial.body("L0_yaw").add_joint(
        name=LMF.JOINT_NAMES[0], type=mujoco.mjtJoint.mjJNT_HINGE,
        axis=[0, 1, 0], stiffness=10.0, limited=False)
    with pytest.raises(ValueError, match="incomplete"):
        LMF.addresses(partial.compile(), required=False)


def test_diagnostics_reports_hidden_state_without_changing_contract():
    model = _flex_model()
    data = mujoco.MjData(model)
    addrs = LMF.addresses(model)
    assert addrs is not None
    data.qpos[list(addrs.qpos_addrs)] = np.radians([1, -2, 3, -4, 5, -6])
    data.qvel[list(addrs.dof_addrs)] = np.radians([6, -5, 4, -3, 2, -1])
    mujoco.mj_forward(model, data)

    out = LMF.diagnostics(model, data)
    assert out["enabled"] is True
    assert out["angle_deg"] == pytest.approx([1, -2, 3, -4, 5, -6])
    assert out["velocity_deg_s"] == pytest.approx([6, -5, 4, -3, 2, -1])
    assert out["spring_torque_nm"][0] == pytest.approx(
        -20.0 * math.radians(1.0))
    assert out["max_abs_angle_deg"] == pytest.approx(6.0)
    rigid = _base_spec().compile()
    assert LMF.diagnostics(rigid, mujoco.MjData(rigid)) == {"enabled": False}


def test_diagnostics_supports_mjx_host_data_without_passive_force_field():
    from types import SimpleNamespace

    model = _flex_model()
    data = mujoco.MjData(model)
    host_data = SimpleNamespace(qpos=data.qpos.copy(), qvel=data.qvel.copy())

    out = LMF.diagnostics(model, host_data)

    assert out["enabled"] is True
    assert out["passive_force_nm"] is None
    assert len(out["spring_torque_nm"]) == 6


def test_mjx_accepts_the_augmented_topology():
    pytest.importorskip("jax")
    mjx = pytest.importorskip("mujoco.mjx")
    model = _flex_model()
    device_model = mjx.put_model(model)
    assert (device_model.nq, device_model.nv) == (model.nq, model.nv)
    assert device_model.jnt_stiffness.shape == model.jnt_stiffness.shape


def test_private_env_wires_hidden_flex_without_policy_shape_change(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")
    from rl_move.config import load_config
    from rl_move.sim.sim_env import SimHexapodBalanceEnv

    cfg = deepcopy(load_config())
    cfg["struct_comp"]["enabled"] = 0
    cfg["leg_mount_flex"] = _cfg()["leg_mount_flex"]
    env = SimHexapodBalanceEnv(
        cfg=cfg, randomize=False, episode_seconds=0.1)

    obs, info = env.reset(seed=0)

    assert env.model.nq == 31
    assert env.model.nv == 30
    assert env.action_space.shape == (6,)
    assert obs.shape == (47,)
    assert info["leg_mount_flex"]["enabled"] is True


def test_env_refuses_double_counted_static_and_dynamic_compliance(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")
    from rl_move.config import load_config
    from rl_move.sim.sim_env import SimHexapodBalanceEnv

    cfg = deepcopy(load_config())
    cfg["struct_comp"]["enabled"] = 1
    cfg["leg_mount_flex"] = _cfg()["leg_mount_flex"]

    with pytest.raises(ValueError, match="cannot both be enabled"):
        SimHexapodBalanceEnv(cfg=cfg, randomize=False, episode_seconds=0.1)
