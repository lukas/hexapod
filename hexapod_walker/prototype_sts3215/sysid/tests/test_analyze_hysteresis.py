from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from sysid.analyze_hysteresis import analyze_hysteresis
from sysid.trace import write


def _ik(x_mm: float, y_mm: float) -> tuple[float, float]:
    cosine = (x_mm**2 + y_mm**2 - 90.0**2 - 150.0**2) / (
        2.0 * 90.0 * 150.0
    )
    relative_knee = math.acos(cosine)
    hip = math.atan2(y_mm, x_mm) - math.atan2(
        150.0 * math.sin(relative_knee),
        90.0 + 150.0 * math.cos(relative_knee),
    )
    return round(math.degrees(hip), 3), round(
        math.degrees(hip + relative_knee), 3
    )


def _synthetic_trace(
    tmp_path: Path,
    *,
    leg: int,
    profile: str,
    amplitudes: list[float],
    loops: list[list[tuple[float, float]]],
    dwell_samples: int,
) -> Path:
    hip_joint, knee_joint = 3 * leg + 1, 3 * leg + 2
    y_mm = 60.0 if profile == "air" else 120.0
    rows_cmd: list[np.ndarray] = []
    rows_q: list[np.ndarray] = []

    def pose(x_mm: float) -> np.ndarray:
        command = np.zeros(18)
        command[[hip_joint, knee_joint]] = _ik(x_mm, y_mm)
        # Exercise auto-leg detection in the presence of camera-clearance yaw.
        command[((leg + 1) % 6) * 3] = 35.0
        return command

    def plateau(
        command: np.ndarray,
        measured_offset: tuple[float, float] | None = None,
        *,
        arrival_sign: float = 1.0,
    ) -> None:
        # One arrival endpoint plus the actual dwell, matching generated traces.
        for sample in range(dwell_samples + 1):
            measured = command.copy()
            if measured_offset is not None:
                if sample == 0:
                    # This deliberately different endpoint proves it is excluded.
                    measured[hip_joint] += arrival_sign * 40.0
                    measured[knee_joint] -= arrival_sign * 40.0
                else:
                    measured[hip_joint] += measured_offset[0]
                    measured[knee_joint] += measured_offset[1]
            rows_cmd.append(command.copy())
            rows_q.append(measured)

    def transition(start: np.ndarray, stop: np.ndarray) -> None:
        # Short enough not to be classified as a dwell plateau.
        command = (start + stop) / 2.0
        rows_cmd.append(command)
        rows_q.append(command.copy())

    base = pose(180.0)
    plateau(base)
    current = base
    for amplitude, condition_loops in zip(amplitudes, loops):
        midpoint = pose(180.0 + amplitude / 2.0)
        peak = pose(180.0 + amplitude)
        for hip_loop, knee_loop in condition_loops:
            transition(current, midpoint)
            plateau(midpoint, (0.0, 0.0), arrival_sign=1.0)
            transition(midpoint, peak)
            plateau(peak)
            transition(peak, midpoint)
            plateau(
                midpoint,
                (hip_loop, -knee_loop),
                arrival_sign=-1.0,
            )
            transition(midpoint, base)
            plateau(base)
            current = base

    cmd = np.asarray(rows_cmd)
    q = np.asarray(rows_q)
    count = len(cmd)
    path = tmp_path / f"l{leg}_{profile}_radial_shear.csv"
    return write(
        path,
        t=np.arange(count) / 10.0,
        tick=np.arange(count),
        seg=np.zeros(count, dtype=int),
        phase=["traj"] * count,
        joint=np.full(count, -1, dtype=int),
        t_send=np.arange(count) / 10.0,
        t_recv=np.arange(count) / 10.0,
        q=q,
        cmd=cmd,
        summary={
            "protocol": {
                "name": f"l{leg}_{profile}_radial_shear_hysteresis_v1"
            }
        },
    )


def test_air_reproduces_accepted_matched_dwell_method_for_any_leg(
    tmp_path: Path,
) -> None:
    path = _synthetic_trace(
        tmp_path,
        leg=2,
        profile="air",
        amplitudes=[15.0],
        loops=[[(0.867, 0.182), (0.806, 0.179), (0.817, 0.182)]],
        dwell_samples=30,
    )

    result = analyze_hysteresis(path)

    assert result["leg_name"] == "L2"
    assert result["profile"] == "air"
    assert result["cycle_count"] == 3
    assert result["conditions"][0]["dwell_samples_per_side"] == [30]
    assert result["conditions"][0]["hip_loop_deg"] == pytest.approx(0.830)
    assert result["conditions"][0]["knee_loop_deg"] == pytest.approx(0.181)


def test_planted_groups_three_cycles_at_each_accepted_amplitude(
    tmp_path: Path,
) -> None:
    path = _synthetic_trace(
        tmp_path,
        leg=0,
        profile="ground",
        amplitudes=[3.75, 7.5, 11.25, 15.0],
        loops=[
            [(0.874, 0.791), (0.650, 0.659), (0.804, 0.615)],
            [(1.055, 0.835), (1.108, 0.879), (0.971, 0.791)],
            [(1.331, 0.967), (1.164, 1.050), (1.318, 1.239)],
            [(0.979, 0.970), (1.146, 0.966), (1.147, 0.966)],
        ],
        dwell_samples=20,
    )

    result = analyze_hysteresis(path, leg="L0")

    assert result["profile"] == "planted"
    assert result["cycle_count"] == 12
    assert [condition["amplitude_mm"] for condition in result["conditions"]] == [
        3.75,
        7.5,
        11.25,
        15.0,
    ]
    assert [
        (condition["hip_loop_deg"], condition["knee_loop_deg"])
        for condition in result["conditions"]
    ] == [
        pytest.approx((0.776, 0.688)),
        pytest.approx((1.045, 0.835)),
        pytest.approx((1.271, 1.085)),
        pytest.approx((1.091, 0.967)),
    ]
    assert all(
        condition["cycle_count"] == 3
        and condition["dwell_samples_per_side"] == [20]
        for condition in result["conditions"]
    )


def test_refuses_ambiguous_active_leg(tmp_path: Path) -> None:
    path = _synthetic_trace(
        tmp_path,
        leg=1,
        profile="air",
        amplitudes=[15.0],
        loops=[[(0.2, 0.1)]],
        dwell_samples=6,
    )
    # Add commanded hip motion on another leg without changing the cycle path.
    from sysid.trace import load

    trace = load(path)
    trace["cmd"][:, 13] = np.linspace(0.0, 2.0, len(trace["cmd"]))
    write(
        path,
        t=trace["t"],
        tick=trace["tick"],
        seg=trace["seg"],
        phase=trace["phase"],
        joint=trace["joint"],
        t_send=trace["t_send"],
        t_recv=trace["t_recv"],
        q=trace["q"],
        cmd=trace["cmd"],
        summary=trace["summary"],
    )

    with pytest.raises(ValueError, match="could not infer one active leg"):
        analyze_hysteresis(path)
