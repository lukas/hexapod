"""Evidence-boundary regression tests; no hardware or network operations."""
import csv
import json
from pathlib import Path

import pytest

from rl_move.scripts.hardware_walk_benchmark import (
    ROOT, analyze, analyze_trial, build_plan, engaged_interval, motion_metrics, sha256,
)


def test_nominal_policy_time_cannot_prove_engaged_duration():
    rows = [{"t_s": str(t), "phase": "walk"} for t in (0, 30, 60)]
    assert engaged_interval(rows)["seconds"] is None
    for row in rows:
        row.update(mono_s=row["t_s"], walk_engaged="1")
    assert engaged_interval(rows)["seconds"] == 60
    rows[1]["walk_engaged"] = "0"
    assert engaged_interval(rows)["seconds"] is None


def test_duplicate_or_backwards_timestamps_cannot_pass():
    for times in ((100, 100, 161), (100, 99, 161)):
        assert engaged_interval([{"mono_s": t, "walk_engaged": True}
                                 for t in times])["seconds"] is None


def test_calibrated_motion_requires_provenance_and_matching_clock(tmp_path):
    trace = tmp_path / "trace.csv"
    trace.write_text("raw recorded data")
    motion = tmp_path / "calibrated_motion.json"
    interval = {"seconds": 2.0, "clock": "mono_s", "start": 100.0, "end": 102.0}
    data = {"schema": "hexapod.calibrated_motion.v1", "calibration_status": "validated",
            "calibration_id": "measured-floor-1", "frame": "floor", "units": "m",
            "trace_sha256": sha256(trace), "clock": "mono_s",
            "samples": [{"t": 100, "x": 1, "y": 2, "yaw_deg": 90},
                        {"t": 102, "x": .98, "y": 2.04, "yaw_deg": 92}]}
    motion.write_text(json.dumps(data))
    report = motion_metrics(motion, trace, interval, {"vx": .08, "vy": 0})
    assert report["progress_m"] == pytest.approx(.04)
    assert report["lateral_m"] == pytest.approx(.02)
    assert report["speed_m_s"] == pytest.approx(.02)
    assert report["progress_ratio"] == pytest.approx(.25)
    assert report["course_error_deg"] == pytest.approx(26.565051)
    data["calibration_status"] = "unverified"
    motion.write_text(json.dumps(data))
    assert not motion_metrics(motion, trace, interval, {"vx": .08, "vy": 0})["available"]


def _trial(path: Path, *, seconds: int, token: str):
    path.mkdir()
    trace = path / "robot_rl_drive_test.csv"
    with trace.open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=["phase", "t_s", "mono_s", "walk_engaged", "token"])
        writer.writeheader()
        for t in range(seconds + 1):
            writer.writerow({"phase": "walk", "t_s": t / 10, "mono_s": 100 + t,
                             "walk_engaged": 1, "token": token})
    (path / "summary.json").write_text(json.dumps({"ok": True, "duration_s": 3,
        "policy": {"walk": {"run": "test"}}, "results": [{"phase": "forward",
        "request": {"vx": .08, "vy": 0}, "robot_logs": [trace.name],
        "result": {"ok": True, "fell": False}}]}))
    (path / "calibrated_motion.json").write_text(json.dumps({
        "schema": "hexapod.calibrated_motion.v1", "calibration_status": "validated",
        "calibration_id": "fixture", "frame": "floor", "units": "m",
        "trace_sha256": sha256(trace), "clock": "mono_s",
        "samples": [{"t": 100, "x": 0, "y": 0, "yaw_deg": 0},
                    {"t": 100 + seconds, "x": .02 * seconds, "y": 0, "yaw_deg": 0}]}))


def test_no_concatenated_short_runs_or_duplicate_repeats(tmp_path):
    paths = [tmp_path / f"run{i}" for i in range(3)]
    for i, path in enumerate(paths):
        _trial(path, seconds=20, token=str(i))
    assert not analyze(paths)["three_repeat_duration_and_pose_evidence"]
    long = tmp_path / "long"
    _trial(long, seconds=60, token="long")
    report = analyze([long, long, long])
    assert report["continuous_60s_distinct_traces_with_metric_pose"] == 1
    assert not report["three_repeat_duration_and_pose_evidence"]
    assert analyze_trial(long)["episodes"][0]["engaged_wall"]["seconds"] == 60
    assert analyze_trial(long)["episodes"][0]["nominal_trace_span_s"] == 6


def test_different_policies_cannot_count_as_matched_repeats(tmp_path):
    paths = [tmp_path / f"run{i}" for i in range(3)]
    for i, path in enumerate(paths):
        _trial(path, seconds=60, token=str(i))
        summary = json.loads((path / "summary.json").read_text())
        summary["policy"]["walk"]["run"] = f"policy{i}"
        (path / "summary.json").write_text(json.dumps(summary))
    report = analyze(paths)
    assert report["continuous_60s_distinct_traces_with_metric_pose"] == 3
    assert not report["three_repeat_duration_and_pose_evidence"]


def test_saved_september4_trace_is_a_canary_not_timing_acceptance():
    path = ROOT / "rl_move/hardware_traces/rl_walk_trial_20260904_232355"
    if not path.exists():
        pytest.skip("local hardware evidence is intentionally not checked in")
    report = analyze_trial(path)
    episode = report["episodes"][0]
    assert report["recorded_success"] is True
    assert episode["recorded_overruns"] == 97
    assert episode["declared_rates_hz"] == {"policy": 100, "bus_write": 50, "snapshot": 10}
    assert episode["repeated_joint_vectors"] == 168
    assert episode["engaged_wall"]["seconds"] is None
    assert episode["command_wall_window"]["seconds"] == pytest.approx(3.36268, abs=.00001)
    assert not episode["motion"]["available"]
    assert episode["sensor_age_ms"]["state_age_ms"]["n"] == 0
    assert not episode["continuous_60s_evidence"]


def test_plans_only_queue_supported_bounded_external_work():
    protocol = ROOT / "sysid/protocols/l0_ground_radial_shear_amplitude_ladder_v1.json"
    if not protocol.exists():
        pytest.skip("optional all-leg protocol set is not installed in this checkout")
    result = build_plan(include_planted=True)
    jobs = result["queue_payloads"]
    assert len(jobs) == 7
    assert all(job["execution_mode"] == "external_guarded" for job in jobs)
    assert jobs[0]["duration_seconds"] == 3
    assert jobs[0]["parameters"]["wz_rad_s"] == 0
    assert jobs[0]["parameters"]["speed_m_s"] == .08
    assert "--learned-rise" not in jobs[0]["parameters"]["argv_template"]
    for job in jobs[1:]:
        p = job["parameters"]
        leg = p["leg"]
        assert p["moving_joints"] == [3 * leg + 1, 3 * leg + 2]
        assert p["protocol_sha256"] == sha256(ROOT / p["protocol"])
        assert p["camera_telemetry_supervision_required"] is True
        assert p["hands_on_operator_required"] is False
        assert p["standing_campaign_authority"] is True
        assert "operator_go_required" not in p
        assert p["safety_contract"]["current_trip_polls"] == 3
    assert result["future_acceptance_not_queued"]["continuous_engaged_seconds_per_run"] == 60


def test_canary_plan_needs_no_optional_protocols(tmp_path, monkeypatch):
    from rl_move.scripts import hardware_walk_benchmark as benchmark
    runner = tmp_path / "rl_move/scripts/run_rl_walk_trial.py"
    runner.parent.mkdir(parents=True)
    runner.write_text("# isolated runner fixture")
    monkeypatch.setattr(benchmark, "ROOT", tmp_path)
    plan = benchmark.build_plan()
    assert len(plan["queue_payloads"]) == 1
    assert plan["queue_payloads"][0]["duration_seconds"] == 3
