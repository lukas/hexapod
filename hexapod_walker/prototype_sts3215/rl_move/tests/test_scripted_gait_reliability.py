from __future__ import annotations

import csv
import json
from pathlib import Path

from rl_move.scripts.summarize_scripted_gait_reliability import build_report


def _make_run(root: Path, name: str, gait0: float, gait10: float) -> Path:
    run = root / name
    run.mkdir()
    (run / "config.json").write_text(json.dumps({
        "gaits": [0, 10], "speed_mm_s": 30.0,
    }))
    (run / "manifest.json").write_text(json.dumps({"status": "complete"}))
    phases = {}
    for direction in ("forward", "backward"):
        phases[f"gait_0_{direction}"] = {
            "commanded_axis_speed_mm_s": gait0,
        }
        phases[f"gait_10_{direction}"] = {
            "commanded_axis_speed_mm_s": gait10,
        }
    (run / "apriltag_motion.json").write_text(json.dumps({"phases": phases}))
    with (run / "telemetry.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "phase", "max_joint_current_a", "max_temp_c", "min_voltage_v",
            "roll_deg", "pitch_deg", "joint_temperatures_c",
        ])
        writer.writeheader()
        for phase in phases:
            writer.writerow({
                "phase": phase, "max_joint_current_a": 0.5,
                "max_temp_c": 35, "min_voltage_v": 11.5,
                "roll_deg": 2, "pitch_deg": 3,
                "joint_temperatures_c": json.dumps([35] * 18),
            })
    return run


def test_reliability_summary_is_paired_against_gait0(tmp_path):
    first = _make_run(tmp_path, "scripted_gait_suite_a", 10.0, 20.0)
    second = _make_run(tmp_path, "scripted_gait_suite_b", 12.0, 24.0)
    report = build_report([first, second])
    gait10_forward = next(
        item for item in report["groups"]
        if item["gait"] == 10 and item["direction"] == "forward"
    )
    assert gait10_forward["actual_speed_mm_s"]["median"] == 22.0
    paired = next(
        item for item in report["paired_vs_gait0"]
        if item["gait"] == 10 and item["direction"] == "forward"
    )
    assert paired["speed_ratio_vs_gait0"]["median"] == 2.0
    bidirectional = next(
        item for item in report["paired_vs_gait0"]
        if item["gait"] == 10 and item["direction"] == "bidirectional_mean"
    )
    assert bidirectional["speed_ratio_vs_gait0"]["median"] == 2.0


def test_reliability_summary_rejects_partial_runs_and_temperature_glitches(
        tmp_path):
    run = _make_run(tmp_path, "scripted_gait_suite_partial", 10.0, 20.0)
    (run / "manifest.json").write_text(json.dumps({"status": "failed"}))
    rows = list(csv.DictReader((run / "telemetry.csv").open(newline="")))
    rows[0]["max_temp_c"] = "52"
    temperatures = [35] * 18
    temperatures[7] = 52
    rows[0]["joint_temperatures_c"] = json.dumps(temperatures)
    fieldnames = list(rows[0])
    with (run / "telemetry.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    report = build_report([run])
    assert all(group["successful"] == 0 for group in report["groups"])
    safety = report["trials"][0]["safety"]
    assert safety["raw_peak_temperature_c"] == 52
    # Each phase has one sample in this compact fixture, so no joint value is
    # locally confirmed.  The raw peak is still retained for diagnosis.
    assert safety["confirmed_peak_temperature_c"] is None
