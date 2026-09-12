"""Fast mechanics tests for offline Hexapod-2 servo identification."""
from __future__ import annotations

import numpy as np

from rl_move.sim.fit_servo_residuals import (
    NominalAxisProfile,
    ServoResidual,
    Trace1D,
    _paired_comparison,
    _parameter_decisions,
    _play_operator,
    actuator_to_robot_abs_deg,
    predict_servo,
    robot_abs_to_actuator_deg,
)


def _nominal() -> NominalAxisProfile:
    return NominalAxisProfile(
        latency_ms=100.0,
        velocity_deg_s=40.0,
        acceleration_deg_s2=200.0,
        tracking_deadband_deg=0.0,
    )


def test_joint_coordinate_round_trip_preserves_robot_contract():
    rng = np.random.default_rng(7)
    robot = rng.normal(size=(19, 18)) * 30.0

    restored = actuator_to_robot_abs_deg(robot_abs_to_actuator_deg(robot))

    assert np.allclose(restored, robot, atol=1e-12)


def test_play_operator_requires_reversal_travel_before_opposite_flank():
    command = np.array([0.0, 1.0, 2.0, 3.0, 2.5, 2.0, 1.0])

    played = _play_operator(command, initial_deg=0.0, half_width_deg=0.5)

    # Rising load carries on the lower flank; a 1-deg direction reversal is
    # needed to cross from lower to upper flank.
    assert np.allclose(played, [0.0, 0.5, 1.5, 2.5, 2.5, 2.5, 1.5])


def test_prediction_honors_latency_and_zero_offset():
    t = np.arange(0.0, 1.01, 0.01)
    trace = Trace1D(
        name="synthetic",
        family="test",
        t_s=t,
        command_deg=np.full_like(t, 10.0),
        measured_deg=np.zeros_like(t),
    )

    result = predict_servo(
        trace, _nominal(),
        ServoResidual(latency_ms=100.0, velocity_scale=1.0,
                      zero_offset_deg=2.0),
    )

    assert np.all(result[t < 0.1] == 0.0)
    assert result[-1] > 11.5
    assert result[-1] <= 12.0


def test_velocity_scale_changes_only_dynamic_approach_not_final_goal():
    t = np.arange(0.0, 2.01, 0.01)
    trace = Trace1D(
        name="synthetic",
        family="test",
        t_s=t,
        command_deg=np.full_like(t, 30.0),
        measured_deg=np.zeros_like(t),
    )
    slow = predict_servo(
        trace, _nominal(), ServoResidual(0.0, velocity_scale=0.5))
    fast = predict_servo(
        trace, _nominal(), ServoResidual(0.0, velocity_scale=1.5))

    assert fast[50] > slow[50] + 5.0
    assert np.isclose(slow[-1], 30.0, atol=0.05)
    assert np.isclose(fast[-1], 30.0, atol=0.05)


def test_unexcited_parameters_fail_closed_to_neutral():
    t = np.arange(0.0, 1.0, 0.02)
    traces = [Trace1D(
        name=f"still-{i}", family=f"family-{i}", t_s=t,
        command_deg=np.zeros_like(t), measured_deg=np.zeros_like(t),
    ) for i in range(4)]

    decisions = _parameter_decisions(
        ServoResidual(240.0, 0.6, 2.0, 1.0), traces, _nominal())

    for name in ("latency_ms", "velocity_scale", "zero_offset_deg",
                 "reversal_deadband_deg"):
        assert decisions[name]["status"] == "neutral_unidentified"
    assert decisions["latency_ms"]["applied"] == 100.0
    assert decisions["velocity_scale"]["applied"] == 1.0


def test_paired_comparison_preserves_run_pairing():
    before = [{"moving_joint_rmse_deg": 4.0},
              {"moving_joint_rmse_deg": 1.0}]
    after = [{"moving_joint_rmse_deg": 3.0},
             {"moving_joint_rmse_deg": 1.5}]

    result = _paired_comparison(before, after)

    assert result["improved_runs"] == 1
    assert result["worsened_runs"] == 1
    assert np.isclose(result["mean_delta_deg"], -0.25)
