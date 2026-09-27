"""Per-axis actuator set pinned (2026-09-27 servo-profile refit).

sim_model.json: the 2026-09-21 reality-gap refit (knee kp 250, vel ceiling
tied to the write profile) with latency restored to the 2026-08-07 bench
values and deadband 0.15/0.15/0.25 -- the 09-21 yaw/hip latency 130/125 ms
double-counted the 400/20 profile ramp (replay fit of the robot's own
command streams, ~/.hexapod/analysis/servo_fit). The pre-refit air fit
stays selectable with bus.servo_params=air; the 09-21 file is kept as
sim_model_20260921_refit.json. This pins the values and the selection
wiring so a later edit that silently reverts them is caught.
"""
from __future__ import annotations

import pytest

from rl_move.sim.servo_model import (
    AIR_MODEL_PATH,
    COUNTS_PER_DEG,
    SimServoParams,
)


def test_refit_is_the_default():
    p = SimServoParams.load()
    # speed_counts_s follows the 2000/80 write contract (config default).
    assert p.speed_counts_s == 2000.0
    for ax in ("yaw", "hip", "knee"):
        assert p.axes[ax].vel_max_deg_s == pytest.approx(
            2000.0 / COUNTS_PER_DEG, abs=1e-3)
    # latency = the bench values; NOT the 09-21 130/125 ms (profile ramp
    # counted twice). deadband small: the fit prefers <= 0.15 deg.
    assert p.axes["yaw"].latency_ms == pytest.approx(29.7)
    assert p.axes["hip"].latency_ms == pytest.approx(25.613, abs=0.01)
    assert p.axes["knee"].latency_ms < 20.0
    assert p.axes["yaw"].deadband_deg == pytest.approx(0.15)
    assert p.axes["hip"].deadband_deg == pytest.approx(0.15)
    assert p.axes["knee"].deadband_deg == pytest.approx(0.25)
    # knee kp keeps the 09-21 loaded refit.
    assert p.axes["knee"].kp == pytest.approx(250.0)


def test_0921_refit_kept_and_selectable():
    path = AIR_MODEL_PATH.with_name("sim_model_20260921_refit.json")
    assert path.is_file()
    old = SimServoParams.from_cfg({"bus": {"servo_params": str(path)}})
    assert old.axes["yaw"].latency_ms == pytest.approx(130.0)
    assert old.axes["hip"].latency_ms == pytest.approx(125.0)
    assert old.speed_counts_s == 400.0


def test_air_backup_selectable_and_pre_refit():
    air = SimServoParams.from_cfg({"bus": {"servo_params": "air"}})
    assert air.speed_counts_s == 350.0
    # pre-refit air ceiling was the 350-count profile speed.
    assert air.axes["hip"].vel_max_deg_s == pytest.approx(
        350.0 / COUNTS_PER_DEG, abs=1e-3)
    assert air.axes["yaw"].latency_ms < 40.0  # air's short command latency
    assert AIR_MODEL_PATH.is_file()


def test_refit_differs_from_air():
    default = SimServoParams.load()
    air = SimServoParams.load(AIR_MODEL_PATH)
    assert default.axes["yaw"].deadband_deg != air.axes["yaw"].deadband_deg
    assert default.axes["knee"].kp != air.axes["knee"].kp
    assert default.axes["hip"].vel_max_deg_s != air.axes["hip"].vel_max_deg_s
    # DR spread ranges preserved across the refit (stay interpretable).
    assert default.spread == air.spread
