"""Mechanics tests for Robot Lab hardware-trace replay."""
from __future__ import annotations

import csv

import numpy as np

from rl_move.sim.replay_trace import _replay_substeps, analyze, load_trace


def _row(phase: str, t_s: float, mono_s: float) -> dict[str, object]:
    row: dict[str, object] = {
        "phase": phase,
        "t_s": t_s,
        "mono_s": mono_s,
        "roll_deg": 1.0,
        "pitch_deg": 2.0,
        "gyro_x_dps": 3.0,
        "gyro_y_dps": 4.0,
    }
    for j in range(18):
        row[f"q{j}_deg"] = float(j)
        row[f"cmd{j}_deg"] = float(j + 1)
        row[f"cur{j}_a"] = 0.1 * j
    return row


def test_load_trace_accepts_walk_and_preserves_in_run_holds(tmp_path):
    rows = [_row("walk", i * 0.01, 1000.0 + i * 0.01)
            for i in range(10)]
    rows += [_row("hold", 0.10, 1000.10)]
    rows += [_row("walk", 0.11 + i * 0.01, 1000.11 + i * 0.01)
             for i in range(30)]
    path = tmp_path / "robot.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    trace = load_trace(path)

    assert trace["phase"] == "walk"
    assert trace["time_source"] == "mono_s"
    assert len(trace["t"]) == 41
    assert trace["active_phase_mask"].sum() == 40
    assert trace["interrupted_ticks"] == 1
    assert trace["t"][0] == 0.0
    assert np.isclose(np.median(np.diff(trace["t"])), 0.01)
    assert trace["current_a"].shape == (41, 18)
    assert trace["accel_g"].shape == (41, 3)
    assert np.isnan(trace["accel_g"]).all()


def test_load_trace_falls_back_to_old_run_and_t_s(tmp_path):
    rows = [_row("run", i * 0.04, 2000.0 + i * 0.04)
            for i in range(25)]
    for row in rows:
        row.pop("mono_s")
        row.pop("cur7_a")
    path = tmp_path / "old.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    trace = load_trace(path)

    assert trace["phase"] == "run"
    assert trace["time_source"] == "t_s"
    assert np.isnan(trace["current_a"][:, 7]).all()
    assert np.isfinite(trace["current_a"][:, 6]).all()


def test_100hz_trace_is_not_clamped_to_50hz():
    t_s = np.arange(101, dtype=float) * 0.01

    steps = _replay_substeps(t_s, physics_dt_s=0.0025)

    assert np.all(steps == 4)
    assert len(steps) == len(t_s) - 1
    assert np.isclose(steps.sum() * 0.0025, t_s[-1] - t_s[0])


def test_replay_samples_row_zero_before_advancing_first_command(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")
    from rl_move.sim.replay_trace import _ReplaySim
    from rl_move.sim.servo_model import SimServoParams

    q0 = np.tile([0.0, 20.0, 80.0], 6)
    command = q0.copy()
    command[1::3] += 20.0
    trace = {
        "q": np.tile(q0, (25, 1)),
        "cmd": np.tile(command, (25, 1)),
        "t": np.arange(25, dtype=float) * 0.04,
    }

    result = _ReplaySim(SimServoParams.load()).replay(trace, settle_s=0.0)

    assert len(result["q"]) == len(trace["t"])
    assert np.allclose(result["q"][0], q0, atol=1e-9)
    assert np.max(np.abs(result["q"][-1] - q0)) > 1.0


def test_initial_settle_preserves_robot_absolute_knee_pose(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "mesh_mjx")
    from rl_move.sim.replay_trace import _ReplaySim
    from rl_move.sim.servo_model import SimServoParams

    q0 = np.tile([0.0, 20.0, 80.0], 6)
    trace = {
        "q": np.tile(q0, (25, 1)),
        "cmd": np.tile(q0, (25, 1)),
        "t": np.arange(25, dtype=float) * 0.04,
    }

    result = _ReplaySim(SimServoParams.load()).replay(trace)

    # A frame mix-up commands knee=80 as a MuJoCo-relative angle and moves
    # the first sample about 20 degrees. Correct conversion stays sub-degree.
    assert np.max(np.abs(result["q"][0] - q0)) < 1.0
    assert result["imu_roll"].shape == result["roll"].shape == (25,)


def test_analysis_compares_like_for_like_imu_estimates():
    n = 25
    hardware_roll = np.linspace(0.0, 10.0, n)
    trace = {
        "t": np.arange(n, dtype=float) * 0.02,
        "roll": hardware_roll,
        "pitch": np.zeros(n),
        "ref_roll": 0.0,
        "ref_pitch": 0.0,
        "q": np.tile(np.arange(18, dtype=float), (n, 1)),
        "current_a": np.full((n, 18), np.nan),
    }
    sim = {
        # Rigid-body truth deliberately differs. The simulated sensor
        # estimate matches the hardware CSV and is the valid comparison.
        "roll": np.zeros(n),
        "pitch": np.zeros(n),
        "ref_roll": 0.0,
        "ref_pitch": 0.0,
        "imu_roll": hardware_roll.copy(),
        "imu_pitch": np.zeros(n),
        "ref_imu_roll": 0.0,
        "ref_imu_pitch": 0.0,
        "q": trace["q"].copy(),
        "foot_f": np.zeros((n, 6)),
        "foot_xyz": np.zeros((n, 6, 3)),
        "base_xyz": np.zeros((n, 3)),
        "flex_deg": np.zeros((n, 6)),
        "current_proxy_a": np.zeros((n, 18)),
    }

    result = analyze(trace, sim)

    assert result["sim_peak_roll_rel_deg"] == 10.0
    assert result["sim_true_peak_roll_rel_deg"] == 0.0
    assert result["roll_waveform_rmse_deg"] == 0.0
