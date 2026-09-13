"""dr.foot_friction_scale / dr.leg_torque_scale / dr.struct_dr_prob
trainer-side structured hard-region DR (2026-09-13 speed sim-to-real
order, item (b) of docs/DR_JOINT_PANEL_2026-09-13.md's Next list).

Contract under test (RESEARCH_RULES "Tests": fast, mechanics-only):
- default OFF is bit-exact: the legacy rng stream is unchanged (golden
  values captured from the pre-change code) and the apply paths are
  byte-level no-ops on the model;
- guarded draws: enabling one axis never shifts the base draws;
- struct overlay: fires at the configured probability, sets a mode,
  forces frame-coupled zero bias, stays inside the panel dose menu;
- model application: per-foot friction doses exactly the foot geoms
  (+ floor cap, max-combine rule) and per-leg torque scales exactly
  that leg's actuator forcerange rows — both fields in
  mjx_backend.MODEL_DR_FIELDS (per-world upload guarantee);
- scaled(): ranges shrink toward nominal, probability follows the
  curriculum, dose menu does not.
"""
import dataclasses

import numpy as np
import pytest

from rl_move.sim.domain_rand import (
    DEG2RAD, STRUCT_ZERO_BIAS_DEG, DomainRandomizer, EpisodeRandomization,
    N_LEGS, RandRanges)
from rl_move.sim.mjx_backend import MODEL_DR_FIELDS
from rl_move.sim.servo_model import (
    N_JOINTS, SimServoParams, _act_id, apply_params_to_model, build_model,
    joint_names)


def _fresh_model():
    model = build_model()
    apply_params_to_model(model, SimServoParams.load())
    return model


def _neutral_ep(**kw) -> EpisodeRandomization:
    base = DomainRandomizer(scale=0.0).sample(np.random.default_rng(0))
    return dataclasses.replace(base, **kw)


# ------------------------------------------------------------- default off

def test_default_off_rng_stream_bit_exact_golden():
    # Golden values captured from the pre-change sampler (2026-09-13,
    # this cycle, seeds 7/12345, scale 1.0): any drift here means the
    # default path consumed a different rng stream.
    s = DomainRandomizer(RandRanges(), scale=1.0).sample(
        np.random.default_rng(7))
    assert round(s.mass_scale, 12) == 1.07390100843
    assert round(float(s.kp_scale[0]), 12) == 0.838681637573
    assert round(s.torque_scale, 12) == 0.930935026978
    assert round(float(s.joint_zero_bias_rad[17]), 12) == -0.009549621966
    assert round(float(s.imu_pos_m[2]), 12) == 0.001528723308
    assert round(s.cmd_drop_prob, 12) == 0.034184218667
    s2 = DomainRandomizer(RandRanges(), scale=1.0).sample(
        np.random.default_rng(12345))
    assert round(s2.mass_scale, 12) == 0.939975961347
    assert round(s2.cmd_drop_prob, 12) == 0.016671889835
    for s_ in (s, s2):
        assert s_.struct_dr_mode == ""
        assert np.all(s_.foot_friction_scale == 1.0)
        assert np.all(s_.leg_torque_scale == 1.0)


def test_enabling_new_axes_never_shifts_base_draws():
    # Guarded draws happen AFTER every base field: base fields must be
    # identical between off and on for the same seed.
    off = DomainRandomizer(RandRanges(), scale=1.0).sample(
        np.random.default_rng(11))
    on = DomainRandomizer(RandRanges(
        foot_friction_scale=(0.5, 1.1), leg_torque_scale=(0.6, 1.05)),
        scale=1.0).sample(np.random.default_rng(11))
    assert on.mass_scale == off.mass_scale
    assert np.array_equal(on.start_offset_rad, off.start_offset_rad)
    assert np.array_equal(on.imu_mount_rot, off.imu_mount_rot)
    assert on.ext_push_peak_n == off.ext_push_peak_n
    assert np.all(on.foot_friction_scale >= 0.5)
    assert np.any(on.foot_friction_scale != 1.0)
    # struct overlay REPLACES model-error fields by design, but fields
    # outside the overlay (start pose, IMU mount) keep the base draw.
    on2 = DomainRandomizer(RandRanges(struct_dr_prob=1.0),
                           scale=1.0).sample(np.random.default_rng(11))
    assert np.array_equal(on2.start_offset_rad, off.start_offset_rad)
    assert np.array_equal(on2.imu_mount_rot, off.imu_mount_rot)
    assert np.array_equal(on2.imu_pos_m, off.imu_pos_m)
    assert on2.struct_dr_mode in ("correlated", "asymmetric")


def test_apply_paths_noop_at_neutral():
    model = _fresh_model()
    before = {f: getattr(model, f).copy()
              for f in ("geom_friction", "actuator_forcerange")}
    ep = _neutral_ep()
    ep.apply_asym_to_model(model)
    assert np.array_equal(model.actuator_forcerange,
                          before["actuator_forcerange"])
    model2 = _fresh_model()
    ep.apply_to_model(model2, chassis_bid=1)  # neutral scale-0 episode
    # foot-friction block must not fire at all-ones (byte-equal rows).
    import mujoco
    foot_gids = [mujoco.mj_name2id(model2, mujoco.mjtObj.mjOBJ_GEOM,
                                   f"L{i}_foot") for i in range(N_LEGS)]
    assert np.array_equal(model2.geom_friction[foot_gids],
                          before["geom_friction"][foot_gids])


# --------------------------------------------------------------- struct

def test_struct_overlay_fires_and_stays_in_bounds():
    rng = np.random.default_rng(3)
    dr = DomainRandomizer(RandRanges(struct_dr_prob=1.0), scale=1.0)
    modes = set()
    for _ in range(24):
        ep = dr.sample(rng)
        assert ep.struct_dr_mode in ("correlated", "asymmetric")
        modes.add(ep.struct_dr_mode)
        assert ep.zero_drift_cmd_frame is True or ep.zero_drift_cmd_frame == 1
        assert np.all(np.abs(ep.joint_zero_bias_rad)
                      <= STRUCT_ZERO_BIAS_DEG * DEG2RAD + 1e-12)
        assert np.all(ep.foot_friction_scale <= 1.10 + 1e-12)
        assert np.all(ep.foot_friction_scale >= 0.50 - 1e-12)
        assert np.all(ep.leg_torque_scale <= 1.05 + 1e-12)
        assert np.all(ep.leg_torque_scale >= 0.60 - 1e-12)
        assert ep.kp_scale.shape == (N_JOINTS,)
        assert 0.0 <= ep.cmd_drop_prob <= 0.08
    assert modes == {"correlated", "asymmetric"}


def test_struct_prob_zero_never_fires():
    rng = np.random.default_rng(5)
    dr = DomainRandomizer(RandRanges(struct_dr_prob=0.0), scale=1.0)
    assert all(dr.sample(rng).struct_dr_mode == "" for _ in range(16))


# ------------------------------------------------------------- model edits

def test_foot_friction_doses_feet_and_caps_floor():
    import mujoco
    model = _fresh_model()
    ffs = np.array([0.5, 1.0, 1.0, 1.0, 1.0, 1.0])
    foot_gids = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM,
                                   f"L{i}_foot") for i in range(N_LEGS)]
    floor_gid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "floor")
    base_foot = model.geom_friction[foot_gids, 0].copy()
    ep = _neutral_ep(foot_friction_scale=ffs)
    ep.apply_to_model(model, chassis_bid=1)
    assert model.geom_friction[foot_gids[0], 0] == pytest.approx(
        0.5 * base_foot[0])
    for k in range(1, N_LEGS):
        assert model.geom_friction[foot_gids[k], 0] == pytest.approx(
            base_foot[k])
    # floor capped to the min dosed foot (max-combine rule).
    assert model.geom_friction[floor_gid, 0] == pytest.approx(
        min(0.5 * base_foot[0],
            float(model.geom_friction[floor_gid, 0])))
    assert model.geom_friction[floor_gid, 0] <= 0.5 * base_foot[0] + 1e-12
    assert "geom_friction" in MODEL_DR_FIELDS


def test_leg_torque_scales_exactly_that_legs_actuators():
    model = _fresh_model()
    before = model.actuator_forcerange.copy()
    lts = np.ones(N_LEGS)
    lts[2] = 0.6
    ep = _neutral_ep(leg_torque_scale=lts)
    ep.apply_asym_to_model(model)
    names = joint_names()
    touched = set()
    for j in (6, 7, 8):  # leg 2 joints
        for suffix in ("", "_d"):
            a = _act_id(model, names[j] + suffix)
            touched.add(a)
            assert np.allclose(model.actuator_forcerange[a],
                               0.6 * before[a])
    for a in range(model.nu):
        if a not in touched:
            assert np.array_equal(model.actuator_forcerange[a], before[a])
    assert "actuator_forcerange" in MODEL_DR_FIELDS


# ---------------------------------------------------------------- scaled()

def test_scaled_forwards_new_fields():
    r = RandRanges(foot_friction_scale=(0.5, 1.1),
                   leg_torque_scale=(0.6, 1.05), struct_dr_prob=0.6)
    half = r.scaled(0.5)
    assert half.struct_dr_prob == pytest.approx(0.3)
    assert half.foot_friction_scale == pytest.approx((0.75, 1.05))
    assert half.leg_torque_scale == pytest.approx((0.8, 1.025))
    zero = r.scaled(0.0)
    assert zero.struct_dr_prob == 0.0
    assert zero.foot_friction_scale == pytest.approx((1.0, 1.0))
    # scaled(0) neutral ranges must ALSO be treated as off (guarded draw).
    ep = DomainRandomizer(r, scale=0.0).sample(np.random.default_rng(1))
    assert np.all(ep.foot_friction_scale == 1.0)
    assert ep.struct_dr_mode == ""
