#!/usr/bin/env python3
"""Compare timestamped hardware scripted-gait telemetry with MuJoCo."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from hexapod_core.joint_frame import (
    FRAME_ROBOT_ABS,
    JOINT_CONTRACT,
    require_robot_abs_joint_frame,
)


AXES = {
    "yaw": np.asarray([3 * leg for leg in range(6)]),
    "hip": np.asarray([3 * leg + 1 for leg in range(6)]),
    "knee": np.asarray([3 * leg + 2 for leg in range(6)]),
}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def _motion_groups(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    segments: dict[str, list[list[dict[str, str]]]] = defaultdict(list)
    for row in rows:
        phase = row["phase"]
        if phase.startswith("gait_") and not phase.endswith("_settle") \
                and phase.rsplit("_", 1)[-1] in {"forward", "backward"}:
            phase_segments = segments[phase]
            if not phase_segments:
                phase_segments.append([])
            current = phase_segments[-1]
            if current:
                time_key = "elapsed_s" if "elapsed_s" in row else "sim_t_s"
                gap = float(row[time_key]) - float(current[-1][time_key])
                # Recovery and adaptive centering use different phases. When
                # the measured direction resumes, keep only a contiguous
                # clean attempt instead of interpolating across that pause.
                if gap > 0.75:
                    current = []
                    phase_segments.append(current)
            current.append(row)
    return {
        phase: max(phase_segments, key=len)
        for phase, phase_segments in segments.items()
        if phase_segments
    }


def _trajectory(
    rows: list[dict[str, str]], time_key: str,
) -> tuple[np.ndarray, np.ndarray]:
    t = np.asarray([float(row[time_key]) for row in rows], dtype=float)
    t -= t[0]
    q = np.asarray([json.loads(row["joint_degrees"]) for row in rows], dtype=float)
    keep = np.isfinite(q).all(axis=1)
    return t[keep], q[keep]


def _phase_compare(
    hardware: list[dict[str, str]], simulation: list[dict[str, str]],
) -> dict[str, Any]:
    ht, hq = _trajectory(hardware, "elapsed_s")
    st, sq = _trajectory(simulation, "sim_t_s")
    duration = min(float(ht[-1]), float(st[-1]), 10.0)
    grid = np.linspace(0.0, duration, 201)
    hi = np.column_stack([np.interp(grid, ht, hq[:, j]) for j in range(18)])
    si = np.column_stack([np.interp(grid, st, sq[:, j]) for j in range(18)])
    error = hi - si
    joint_rmse = np.sqrt(np.mean(error * error, axis=0))
    hroll = np.asarray([
        float(row.get("body_roll_deg") or row.get("roll_deg") or 0.0)
        for row in hardware
    ])
    hpitch = np.asarray([
        float(row.get("body_pitch_deg") or row.get("pitch_deg") or 0.0)
        for row in hardware
    ])
    sroll = np.asarray([float(row["roll_deg"]) for row in simulation])
    spitch = np.asarray([float(row["pitch_deg"]) for row in simulation])
    # Hardware body_roll/body_pitch are the complementary-filter IMU
    # estimate, not an external measurement of the rigid chassis.  Keep the
    # MuJoCo rigid-body attitude and its simulated IMU estimate separate so
    # acceleration at an off-centre IMU cannot masquerade as missing rocking.
    has_sim_imu = all(
        row.get("imu_roll_deg") not in (None, "")
        and row.get("imu_pitch_deg") not in (None, "")
        for row in simulation
    )
    sim_imu_roll = (
        np.asarray([float(row["imu_roll_deg"]) for row in simulation])
        if has_sim_imu else None
    )
    sim_imu_pitch = (
        np.asarray([float(row["imu_pitch_deg"]) for row in simulation])
        if has_sim_imu else None
    )
    x0, y0 = float(simulation[0]["chassis_x_m"]), float(simulation[0]["chassis_y_m"])
    x1, y1 = float(simulation[-1]["chassis_x_m"]), float(simulation[-1]["chassis_y_m"])
    return {
        "duration_compared_s": round(duration, 3),
        "hardware_samples": len(hardware),
        "mujoco_samples": len(simulation),
        "joint_rmse_deg": round(float(np.sqrt(np.mean(error * error))), 3),
        "joint_rmse_by_axis_deg": {
            axis: round(float(np.sqrt(np.mean(error[:, indexes] ** 2))), 3)
            for axis, indexes in AXES.items()
        },
        "worst_joint_rmse_deg": [
            {"joint": int(j), "rmse_deg": round(float(joint_rmse[j]), 3)}
            for j in np.argsort(joint_rmse)[-3:][::-1]
        ],
        "hardware_imu_estimator_peak_tilt_deg": round(float(max(
            np.max(np.abs(hroll)), np.max(np.abs(hpitch)))), 3),
        "mujoco_physical_peak_tilt_deg": round(float(max(
            np.max(np.abs(sroll)), np.max(np.abs(spitch)))), 3),
        "mujoco_imu_estimator_peak_tilt_deg": (
            None if sim_imu_roll is None else round(float(max(
                np.max(np.abs(sim_imu_roll)),
                np.max(np.abs(sim_imu_pitch)))), 3)
        ),
        "hardware_peak_joint_current_a": round(max(
            float(row["max_joint_current_a"]) for row in hardware), 4),
        "mujoco_peak_joint_current_a": round(max(
            float(row["max_joint_current_a"]) for row in simulation), 4),
        "mujoco_displacement_xy_m": [round(x1 - x0, 5), round(y1 - y0, 5)],
    }


def _temperature_glitches(rows: list[dict[str, str]], threshold: float = 55.0) \
        -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    counts = [0] * 18
    longest = [0] * 18
    for row in rows:
        values = json.loads(row["joint_temperatures_c"])
        for joint, value in enumerate(values):
            hot = value is not None and float(value) >= threshold
            counts[joint] = counts[joint] + 1 if hot else 0
            longest[joint] = max(longest[joint], counts[joint])
            if hot:
                events.append({
                    "elapsed_s": float(row["elapsed_s"]),
                    "phase": row["phase"],
                    "joint": joint,
                    "temperature_c": float(value),
                })
    return {
        "threshold_c": threshold,
        "samples_at_or_above_threshold": len(events),
        "maximum_consecutive_samples_same_joint": max(longest, default=0),
        "events": events,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hardware", type=Path, required=True)
    parser.add_argument("--mujoco", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    hardware = _rows(args.hardware / "telemetry.csv")
    simulation = _rows(args.mujoco / "sim_telemetry.csv")
    hardware_config = json.loads((args.hardware / "config.json").read_text())
    require_robot_abs_joint_frame(
        hardware_config, source=str(args.hardware / "config.json"))
    sim_summary = json.loads((args.mujoco / "summary.json").read_text())
    sim_protocol = sim_summary.get("protocol") or {}
    require_robot_abs_joint_frame(
        sim_protocol, source=str(args.mujoco / "summary.json"))
    if sim_protocol.get("joint_frame_roundtrip_verified") is not True:
        raise RuntimeError(
            "refusing physical hardware/MuJoCo comparison: simulation run "
            "did not verify hardware-absolute -> MuJoCo-relative -> "
            "hardware-absolute plant round trip"
        )
    hardware_runtime = hardware_config.get("robot_runtime") or {}
    hardware_scripted = hardware_runtime.get("scripted_walk")
    protocol_match = None
    if hardware_scripted is not None:
        expected = {
            "control_hz": sim_protocol.get("scripted_control_hz"),
            "servo_speed_counts_s": sim_protocol.get(
                "servo_speed_counts_s"),
            "servo_acc_units": sim_protocol.get("servo_acc_units"),
        }
        mismatch = {
            key: {"hardware": hardware_scripted.get(key), "mujoco": value}
            for key, value in expected.items()
            if value is None or hardware_scripted.get(key) != value
        }
        if mismatch:
            raise RuntimeError(
                "refusing hardware/MuJoCo comparison with different "
                "scripted-walk timing/profile contracts: "
                + json.dumps(mismatch, sort_keys=True)
            )
        protocol_match = {"verified": True, **expected}
    hg = _motion_groups(hardware)
    sg = _motion_groups(simulation)
    phases = sorted(set(hg) & set(sg))
    comparisons = {
        phase: _phase_compare(hg[phase], sg[phase]) for phase in phases
    }

    # The direct hardware knee values below are encoder telemetry. No
    # monocular/foot-tip visual knee estimate is consumed by this report.
    first_phase = phases[0]
    hq = np.asarray([
        json.loads(row["joint_degrees"]) for row in hg[first_phase]
    ], dtype=float)
    sq = np.asarray([
        json.loads(row["joint_degrees"]) for row in sg[first_phase]
    ], dtype=float)
    posture = {
        "hardware_mean_deg": {
            axis: round(float(np.mean(hq[:, indexes])), 3)
            for axis, indexes in AXES.items()
        },
        "mujoco_mean_deg": {
            axis: round(float(np.mean(sq[:, indexes])), 3)
            for axis, indexes in AXES.items()
        },
    }
    report = {
        "hardware": str(args.hardware),
        "mujoco": str(args.mujoco),
        "visual_knees_used": False,
        "tilt_signal_contract": {
            "hardware": "complementary-filter IMU estimate",
            "mujoco_physical": "rigid chassis orientation from qpos",
            "mujoco_imu_estimator": (
                "same simulated complementary-filter estimate; null for "
                "legacy replay CSVs"
            ),
            "warning": (
                "hardware IMU tilt and MuJoCo physical tilt are different "
                "signals and must not be interpreted as a direct physics "
                "residual"
            ),
        },
        "joint_frame": {
            "name": FRAME_ROBOT_ABS,
            "contract": JOINT_CONTRACT,
            "roundtrip_verified": True,
            "plant_robot_absolute_deg": sim_protocol[
                "plant_robot_absolute_deg"
            ],
            "plant_mujoco_relative_deg": sim_protocol[
                "plant_mujoco_relative_deg"
            ],
        },
        "scripted_walk_contract_match": protocol_match,
        "matching_motion_phases": phases,
        "posture_during_first_phase": posture,
        "temperature_glitches": _temperature_glitches(hardware),
        "phases": comparisons,
        "aggregate": {
            "mean_joint_rmse_deg": round(float(np.mean([
                item["joint_rmse_deg"] for item in comparisons.values()
            ])), 3),
            "mean_hardware_imu_estimator_peak_tilt_deg": round(float(np.mean([
                item["hardware_imu_estimator_peak_tilt_deg"]
                for item in comparisons.values()
            ])), 3),
            "mean_mujoco_physical_peak_tilt_deg": round(float(np.mean([
                item["mujoco_physical_peak_tilt_deg"]
                for item in comparisons.values()
            ])), 3),
            "mean_mujoco_imu_estimator_peak_tilt_deg": (
                None if not comparisons or any(
                    item["mujoco_imu_estimator_peak_tilt_deg"] is None
                    for item in comparisons.values()
                ) else round(float(np.mean([
                    item["mujoco_imu_estimator_peak_tilt_deg"]
                    for item in comparisons.values()
                ])), 3)
            ),
        },
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
