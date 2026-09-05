import csv
import hashlib
import json

import pytest

from rl_move.scripts.analyze_timing_tracking_correlation import AnalysisError, analyze


def _fixture(tmp_path):
    csv_name = "robot_rl_drive_20260905_192627.csv"
    debug_name = "robot_rl_drive_20260905_192626_debug.jsonl"
    events_name = "events.csv"
    fields = ["phase", "mono_s", "t_s", "unix_s", "lag_ms", "imu_age_ms"]
    fields += [f"q{i}_deg" for i in range(18)] + [f"cmd{i}_deg" for i in range(18)]
    with (tmp_path / csv_name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for tick, error in enumerate((0.0, 1.0, 2.0, 4.0, 3.0)):
            row = {"phase": "walk", "mono_s": tick * 0.01, "t_s": tick * 0.01,
                   "unix_s": 1000 + tick * 0.01, "lag_ms": 2 if tick == 3 else 0,
                   "imu_age_ms": tick * 10}
            row.update({f"q{i}_deg": error for i in range(18)})
            row.update({f"cmd{i}_deg": 0 for i in range(18)})
            writer.writerow(row)
    (tmp_path / debug_name).write_text(
        json.dumps({"event": "stream_feedback_recovered", "active": "walk", "tick": 3}) + "\n"
    )
    (tmp_path / events_name).write_text("unix_s,elapsed_s,phase,event,detail\n")
    artifacts = []
    for name in (csv_name, debug_name, events_name):
        data = (tmp_path / name).read_bytes()
        artifacts.append({"name": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    (tmp_path / "manifest.json").write_text(json.dumps({"schema_version": 2, "artifacts": artifacts}))
    return hashlib.sha256((tmp_path / "manifest.json").read_bytes()).hexdigest()


def test_analysis_is_deterministic_and_event_aligned(tmp_path):
    manifest_sha = _fixture(tmp_path)
    first, outliers = analyze(tmp_path, expected_manifest_sha256=manifest_sha, bootstrap_resamples=100)
    second, _ = analyze(tmp_path, expected_manifest_sha256=manifest_sha, bootstrap_resamples=100)
    assert first == second
    assert first["event_aligned_statistics"]["cadence_overrun"]["event_ticks"] == [3]
    assert first["event_aligned_statistics"]["imu_stale_recovery"]["event_ticks"] == [3]
    assert first["correlation_with_bootstrap_95pct_ci"]["signals_vs_global_abs_tracking_error_deg"]["imu_age_ms"]["pearson_r"] > 0.8
    assert outliers[0]["tick"] == 3


def test_manifest_mismatch_stops_before_analysis(tmp_path):
    _fixture(tmp_path)
    with pytest.raises(AnalysisError, match="manifest SHA-256 mismatch"):
        analyze(tmp_path, expected_manifest_sha256="0" * 64, bootstrap_resamples=10)
