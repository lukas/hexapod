"""Reality-gap refit of the per-axis actuator (2026-09-21, claude/sim-refit).

The default sim_model.json was refit against the real combo-walk tape
(run 20260920-205326-b616). The pre-refit air fit is preserved as
sim_model_air_20260807.json and selectable with bus.servo_params=air for
A/B. This pins the refit values and the selection wiring so a later edit
that silently reverts them is caught.
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
    # speed_counts_s follows the run's write_speed=400 (was stale 350).
    assert p.speed_counts_s == 400.0
    # vel_max lifted 30.76 -> 35.16 deg/s so the 400-count profile is no
    # longer clamped to the old 350-count ceiling (all axes).
    for ax in ("yaw", "hip", "knee"):
        assert p.axes[ax].vel_max_deg_s == pytest.approx(
            400.0 / COUNTS_PER_DEG, abs=1e-3)
    # yaw/hip latency raised to match the measured cmd->q lag (~130 ms);
    # knee keeps the short air latency but stiffer kp for tighter tracking.
    assert p.axes["yaw"].latency_ms == pytest.approx(130.0)
    assert p.axes["hip"].latency_ms == pytest.approx(125.0)
    assert p.axes["knee"].latency_ms < 20.0
    assert p.axes["knee"].kp == pytest.approx(250.0)


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
    assert default.axes["yaw"].latency_ms != air.axes["yaw"].latency_ms
    assert default.axes["knee"].kp != air.axes["knee"].kp
    assert default.axes["hip"].vel_max_deg_s != air.axes["hip"].vel_max_deg_s
    # DR spread ranges preserved across the refit (stay interpretable).
    assert default.spread == air.spread
