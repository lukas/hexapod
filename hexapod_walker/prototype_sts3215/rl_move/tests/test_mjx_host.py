"""Host-side (no torch/jax needed) checks for mjx_host.prepare_shared_model.

Focused on 2026-09-08's ``foot_geom_radius`` threading: the shared MJX/
warp-training model must apply the SAME diagnostic foot-sphere-radius
override the C eval env applies (``sim_env.set_foot_geom_radius``), or a
training launch dosing ``env.foot_geom_radius_m`` would silently train on
the default geometry while only eval saw the dosed one — a train/eval
physics mismatch. Default (0.0) must stay bit-exact.
"""
import mujoco
import numpy as np
import pytest

from rl_move.sim.mjx_host import (foot_geom_radius_from_cfg,
                                   prepare_shared_model)
from rl_move.sim.servo_model import SimServoParams


def _params():
    return SimServoParams.defaults()


def test_foot_geom_radius_from_cfg_default_and_override():
    assert foot_geom_radius_from_cfg({}) == 0.0
    assert foot_geom_radius_from_cfg(
        {"env": {"foot_geom_radius_m": 0.012}}) == 0.012


def test_prepare_shared_model_foot_geom_radius_default_off_bit_exact():
    base = prepare_shared_model(_params(), iterations=10, ls_iterations=10)
    off = prepare_shared_model(_params(), iterations=10, ls_iterations=10,
                               foot_geom_radius=0.0)
    assert np.array_equal(base.geom_size, off.geom_size)


def test_prepare_shared_model_foot_geom_radius_dosed():
    base = prepare_shared_model(_params(), iterations=10, ls_iterations=10)
    dosed = prepare_shared_model(_params(), iterations=10, ls_iterations=10,
                                 foot_geom_radius=0.012)
    foot0 = mujoco.mj_name2id(dosed, mujoco.mjtObj.mjOBJ_GEOM, "L0_foot")
    assert dosed.geom_size[foot0, 0] == pytest.approx(0.012)
    assert base.geom_size[foot0, 0] != pytest.approx(0.012)
    # Only the foot geoms move; everything else (incl. friction) is
    # untouched by this lever.
    foot_ids = [mujoco.mj_name2id(dosed, mujoco.mjtObj.mjOBJ_GEOM,
                                   f"L{i}_foot") for i in range(6)]
    other = np.ones(base.geom_size.shape[0], dtype=bool)
    other[foot_ids] = False
    assert np.array_equal(dosed.geom_size[other], base.geom_size[other])
    assert np.array_equal(dosed.geom_friction, base.geom_friction)
