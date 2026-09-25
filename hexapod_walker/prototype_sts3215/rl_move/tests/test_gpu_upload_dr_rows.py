"""Per-world (GPU) DR upload carries what the CPU reset path applies.

Two regressions found reviewing the cw-adapt50hz wide-DR campaign
(2026-09-25):

1. ``mjx_host.ModelDrScratch.rows_for`` never called
   ``EpisodeRandomization.apply_asym_to_model``, so ``dr.leg_torque_scale``
   (and the struct overlay's per-leg torque) was a silent no-op on every
   ``--impl warp`` run: the uploaded ``actuator_forcerange`` rows carried
   only the global ``torque_scale``.
2. ``RandRanges.zero_drift_cmd_frame`` defaulted to 0 (legacy: the zero
   bias corrupts encoder reads only, "a residual hardware never shows"),
   so ``dr.joint_zero_bias_deg`` never displaced a foot physically unless
   a recipe set the key. It now defaults to the physical frame mode.
"""
from __future__ import annotations

import dataclasses
import types

import mujoco
import numpy as np

from rl_move.sim import mjx_host
from rl_move.sim.domain_rand import DomainRandomizer, RandRanges
from rl_move.sim.mjx_backend import MODEL_DR_FIELDS
from rl_move.sim.servo_model import (
    SimServoParams, apply_params_to_model, build_model)


def _healthy_model():
    params = SimServoParams.load()
    model = build_model()
    apply_params_to_model(model, params)
    return model, params


def _env_stub(model, ep):
    cb = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "chassis")
    return types.SimpleNamespace(
        _ep_rand=ep, _chassis_bid=cb if cb >= 0 else 1,
        _apply_struct_compliance_to_model=lambda m: None)


def _upload_rows(ep):
    model, params = _healthy_model()
    scratch = mjx_host.ModelDrScratch(model, params)
    return model, scratch.rows_for(_env_stub(model, ep))


def test_leg_torque_scale_reaches_uploaded_forcerange_rows():
    rr = RandRanges()
    rr.leg_torque_scale = (0.5, 0.5)
    ep = DomainRandomizer(rr, scale=1.0).sample(np.random.default_rng(0))
    ep = dataclasses.replace(ep, torque_scale=1.0)   # isolate the per-leg term
    assert np.allclose(ep.leg_torque_scale, 0.5)
    base, rows = _upload_rows(ep)
    assert "actuator_forcerange" in MODEL_DR_FIELDS
    fr0 = np.asarray(base.actuator_forcerange)
    fr = rows["actuator_forcerange"]
    nz = np.abs(fr0) > 0
    assert nz.any()
    ratio = np.abs(fr[nz]) / np.abs(fr0[nz])
    assert np.allclose(ratio, 0.5), ratio


def test_uploaded_rows_match_cpu_reset_order_with_asym_and_fault():
    rr = RandRanges()
    rr.leg_torque_scale = (0.7, 1.1)
    ep = DomainRandomizer(rr, scale=1.0).sample(np.random.default_rng(3))
    assert np.any(ep.leg_torque_scale != 1.0)
    base, rows = _upload_rows(ep)
    # What sim_env.reset does on its private model, in the same order.
    m2 = build_model()
    params = SimServoParams.load()
    apply_params_to_model(m2, params, kp_scale=ep.kp_scale,
                          kv_scale=ep.kv_scale, torque_scale=ep.torque_scale)
    ep.apply_fault_to_model(m2)
    ep.apply_asym_to_model(m2)
    assert np.allclose(rows["actuator_forcerange"], m2.actuator_forcerange)
    # and per-leg: legs with different draws get different ranges
    per_leg = [np.abs(rows["actuator_forcerange"][3 * leg]).max()
               for leg in range(6)]
    assert len({round(v, 9) for v in per_leg}) > 1


def test_unit_leg_torque_scale_leaves_upload_bit_exact():
    rr = RandRanges()
    assert tuple(rr.leg_torque_scale) == (1.0, 1.0)
    ep = DomainRandomizer(rr, scale=1.0).sample(np.random.default_rng(0))
    base, rows = _upload_rows(ep)
    m2 = build_model()
    params = SimServoParams.load()
    apply_params_to_model(m2, params, kp_scale=ep.kp_scale,
                          kv_scale=ep.kv_scale, torque_scale=ep.torque_scale)
    ep.apply_fault_to_model(m2)
    assert np.array_equal(rows["actuator_forcerange"], m2.actuator_forcerange)


def test_zero_drift_frame_mode_is_the_default():
    rr = RandRanges()
    assert float(rr.zero_drift_cmd_frame) == 1.0
    ep = DomainRandomizer(rr, scale=1.0).sample(np.random.default_rng(0))
    assert ep.zero_drift_cmd_frame is True
    # scaled() keeps the flag (it is a mechanism switch, not a range)
    assert float(rr.scaled(0.0).zero_drift_cmd_frame) == 1.0
    # legacy mode is still reachable explicitly
    rr.zero_drift_cmd_frame = 0.0
    ep0 = DomainRandomizer(rr, scale=1.0).sample(np.random.default_rng(0))
    assert ep0.zero_drift_cmd_frame is False
    # and flipping the flag does not move any other draw (no rng use)
    assert np.array_equal(ep0.joint_zero_bias_rad, ep.joint_zero_bias_rad)
    assert ep0.mass_scale == ep.mass_scale
