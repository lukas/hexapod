#!/usr/bin/env python3
"""Aggregate repeated camera-recorded scripted-gait surveys.

The report keeps every trial visible, counts missing/failed phases, summarizes
median speed plus spread, and forms within-run ratios against gait 0 so camera
scale drift between sessions does not masquerade as a gait improvement.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def _csv_rows(filename: Path) -> list[dict[str, str]]:
    with filename.open(newline="") as stream:
        return list(csv.DictReader(stream))


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _temperature_summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    """Return both raw and locally-confirmed temperature peaks.

    The STS3215 feedback occasionally contains a single corrupt temperature
    byte for one joint (for example 33, 52, 33 C in consecutive samples).
    A real thermal rise cannot reverse by tens of degrees in one telemetry
    interval, so a sample is confirmed when an adjacent sample for the same
    joint is within 3 C.  Raw values remain in the report for auditability.
    """
    samples_by_joint: dict[int, list[float]] = defaultdict(list)
    scalar_values: list[float] = []
    for row in rows:
        scalar = _finite_float(row.get("max_temp_c"))
        if scalar is not None:
            scalar_values.append(scalar)
        encoded = row.get("joint_temperatures_c")
        if not encoded:
            continue
        try:
            values = json.loads(encoded)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(values, list):
            continue
        for joint, value in enumerate(values):
            parsed = _finite_float(value)
            if parsed is not None:
                samples_by_joint[joint].append(parsed)

    joint_values = [
        value for values in samples_by_joint.values() for value in values
    ]
    raw_values = joint_values or scalar_values
    confirmed: list[float] = []
    for values in samples_by_joint.values():
        for index, value in enumerate(values):
            neighbors = values[max(0, index - 1):index]
            neighbors += values[index + 1:index + 2]
            if any(abs(value - neighbor) <= 3.0 for neighbor in neighbors):
                confirmed.append(value)
    if not samples_by_joint:
        confirmed = scalar_values
    raw_peak = max(raw_values, default=None)
    confirmed_peak = max(confirmed, default=None)
    outliers = 0
    if confirmed_peak is not None:
        outliers = sum(value > confirmed_peak + 10.0 for value in raw_values)
    return {
        "raw_peak_temperature_c": raw_peak,
        "confirmed_peak_temperature_c": confirmed_peak,
        "isolated_high_sample_count": outliers,
    }


def _phase_safety(rows: list[dict[str, str]], phase: str) -> dict[str, Any]:
    selected = [row for row in rows if row.get("phase") == phase]
    currents = [_finite_float(row.get("max_joint_current_a")) for row in selected]
    voltages = [_finite_float(row.get("min_voltage_v")) for row in selected]
    tilts = []
    for row in selected:
        roll = _finite_float(row.get("body_roll_deg") or row.get("roll_deg"))
        pitch = _finite_float(row.get("body_pitch_deg") or row.get("pitch_deg"))
        if roll is not None and pitch is not None:
            tilts.append(max(abs(roll), abs(pitch)))
    current_values = [value for value in currents if value is not None]
    voltage_values = [value for value in voltages if value is not None]
    return {
        "samples": len(selected),
        "peak_joint_current_a": max(current_values, default=None),
        **_temperature_summary(selected),
        "minimum_voltage_v": min(voltage_values, default=None),
        "peak_imu_tilt_deg": max(tilts, default=None),
    }


def _discover_runs(inputs: list[Path]) -> list[Path]:
    found: set[Path] = set()
    for candidate in inputs:
        resolved = candidate.resolve()
        if (resolved / "config.json").is_file():
            found.add(resolved)
            continue
        for child in resolved.glob("scripted_gait_suite_*"):
            if (child / "config.json").is_file():
                found.add(child.resolve())
    return sorted(found)


def _load_trials(run_dir: Path) -> list[dict[str, Any]]:
    config = json.loads((run_dir / "config.json").read_text())
    manifest_file = run_dir / "manifest.json"
    manifest = (
        json.loads(manifest_file.read_text()) if manifest_file.is_file() else {}
    )
    motion_file = run_dir / "apriltag_motion.json"
    motion = json.loads(motion_file.read_text()) if motion_file.is_file() else {}
    motion_phases = motion.get("phases") or {}
    telemetry_file = run_dir / "telemetry.csv"
    telemetry = _csv_rows(telemetry_file) if telemetry_file.is_file() else []
    command_speed = float(config["speed_mm_s"])
    run_complete = manifest.get("status") == "complete"
    trials: list[dict[str, Any]] = []
    for gait in config.get("gaits", []):
        for direction in ("forward", "backward"):
            phase = f"gait_{int(gait)}_{direction}"
            measured = motion_phases.get(phase)
            actual_speed = (
                None if not isinstance(measured, dict)
                else _finite_float(measured.get("commanded_axis_speed_mm_s"))
            )
            trials.append({
                "run_dir": str(run_dir),
                "run_status": manifest.get("status"),
                "run_error": manifest.get("error"),
                "gait": int(gait),
                "direction": direction,
                "phase": phase,
                "command_speed_mm_s": command_speed,
                "actual_speed_mm_s": actual_speed,
                "speed_ratio_to_command": (
                    None if actual_speed is None or command_speed == 0.0
                    else actual_speed / command_speed
                ),
                "ok": (
                    run_complete and actual_speed is not None
                    and actual_speed > 0.0
                ),
                "motion": measured,
                "safety": _phase_safety(telemetry, phase),
            })
    return trials


def _distribution(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "n": 0, "mean": None, "median": None, "mad": None,
            "stdev": None, "cv": None, "minimum": None, "maximum": None,
        }
    median = statistics.median(values)
    mean = statistics.mean(values)
    stdev = statistics.stdev(values) if len(values) >= 2 else None
    return {
        "n": len(values),
        "mean": round(mean, 4),
        "median": round(median, 4),
        "mad": round(statistics.median([abs(value - median) for value in values]), 4),
        "stdev": None if stdev is None else round(stdev, 4),
        "cv": None if stdev is None or mean == 0.0 else round(stdev / abs(mean), 4),
        "minimum": round(min(values), 4),
        "maximum": round(max(values), 4),
    }


def build_report(run_dirs: list[Path]) -> dict[str, Any]:
    trials = [trial for run_dir in run_dirs for trial in _load_trials(run_dir)]
    grouped: dict[tuple[int, str, float], list[dict[str, Any]]] = defaultdict(list)
    for trial in trials:
        grouped[(
            trial["gait"], trial["direction"], trial["command_speed_mm_s"]
        )].append(trial)
    groups = []
    for (gait, direction, command_speed), items in sorted(grouped.items()):
        speeds = [
            float(item["actual_speed_mm_s"])
            for item in items if item["ok"]
        ]
        groups.append({
            "gait": gait,
            "direction": direction,
            "command_speed_mm_s": command_speed,
            "attempted": len(items),
            "successful": len(speeds),
            "success_fraction": round(len(speeds) / len(items), 4),
            "actual_speed_mm_s": _distribution(speeds),
        })

    by_run: dict[str, dict[tuple[int, str], float]] = defaultdict(dict)
    for trial in trials:
        if trial["ok"]:
            by_run[trial["run_dir"]][
                (trial["gait"], trial["direction"])
            ] = float(trial["actual_speed_mm_s"])
    ratio_values: dict[tuple[int, str], list[float]] = defaultdict(list)
    for phase_speeds in by_run.values():
        for (gait, direction), speed in phase_speeds.items():
            baseline = phase_speeds.get((0, direction))
            if gait != 0 and baseline is not None and baseline > 0.0:
                ratio_values[(gait, direction)].append(speed / baseline)
        candidate_gaits = sorted({gait for gait, _ in phase_speeds if gait != 0})
        baseline_pair = [
            phase_speeds.get((0, direction))
            for direction in ("forward", "backward")
        ]
        if all(speed is not None for speed in baseline_pair):
            baseline_mean = statistics.mean(float(speed) for speed in baseline_pair)
            for gait in candidate_gaits:
                candidate_pair = [
                    phase_speeds.get((gait, direction))
                    for direction in ("forward", "backward")
                ]
                if baseline_mean > 0.0 and all(
                    speed is not None for speed in candidate_pair
                ):
                    ratio_values[(gait, "bidirectional_mean")].append(
                        statistics.mean(float(speed) for speed in candidate_pair)
                        / baseline_mean
                    )
    paired = [
        {
            "gait": gait,
            "direction": direction,
            "speed_ratio_vs_gait0": _distribution(values),
        }
        for (gait, direction), values in sorted(ratio_values.items())
    ]
    return {
        "schema_version": 1,
        "measurement": (
            "AprilTag floor-projected chassis progress; candidate/baseline "
            "ratios are paired within one camera session"
        ),
        "runs": [str(run_dir) for run_dir in run_dirs],
        "trial_count": len(trials),
        "groups": groups,
        "paired_vs_gait0": paired,
        "trials": trials,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_dirs = _discover_runs(args.runs)
    if not run_dirs:
        parser.error("no scripted_gait_suite_* run directories found")
    report = build_report(run_dirs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
