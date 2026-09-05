import csv
import hashlib
import json

import pytest

from .audit_sealed_telemetry_metrics import AuditError, analyze


def write_bundle(tmp_path):
    names = (
        "robot_rl_drive_20260905_192627.csv",
        "robot_rl_drive_20260905_192626_debug.jsonl",
        "robot_rl_drive_20260905_192627_summary.json",
        "events.csv",
    )
    fields = (
        ["t_s", "phase", "mono_s", "lag_ms", "imu_age_ms"]
        + [f"q{i}_deg" for i in range(18)]
        + [f"cmd{i}_deg" for i in range(18)]
    )
    with (tmp_path / names[0]).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for tick, mono in enumerate((10.0, 10.01, 10.04)):
            row = {
                "t_s": tick / 100,
                "phase": "walk",
                "mono_s": mono,
                "lag_ms": 1 if tick == 2 else 0,
                "imu_age_ms": (10, 20, 5)[tick],
            }
            row.update({f"q{i}_deg": tick + i for i in range(18)})
            row.update({f"cmd{i}_deg": i for i in range(18)})
            writer.writerow(row)
    (tmp_path / names[1]).write_text(
        json.dumps({"event": "stream_feedback_stale_begin", "tick": 2, "mono": 10.02})
        + "\n"
        + json.dumps(
            {
                "event": "stream_feedback_recovered",
                "tick": 2,
                "t_s": 0.02,
                "mono": 10.021,
                "previous_stale_ticks": 2,
            }
        )
        + "\n"
    )
    (tmp_path / names[2]).write_text(
        json.dumps({"result": {"ticks": 3, "overruns": 1, "ok": True, "fell": False}})
    )
    (tmp_path / names[3]).write_text("unix_s,phase,event,detail\n")
    artifacts = []
    for name in names:
        path = tmp_path / name
        artifacts.append(
            {
                "name": name,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 2, "artifacts": artifacts}))
    return hashlib.sha256(manifest.read_bytes()).hexdigest()


def test_analyze_reconciles_and_derives_metrics(tmp_path):
    manifest_sha256 = write_bundle(tmp_path)
    report = analyze(tmp_path, manifest_sha256, 0.02, 100)
    assert report["cadence"]["effective_tick_hz"] == pytest.approx(50)
    assert report["overruns"]["count"] == 1
    assert report["tracking"]["global_rms_deg"] == pytest.approx((5 / 3) ** 0.5)
    assert report["tracking"]["peak_abs_deg"] == 2
    assert report["imu"]["stale_burst_durations_ms"] == [20]
    assert report["imu"]["imu_recovery_latency_ms"] == pytest.approx([30])


def test_analyze_rejects_changed_sealed_input(tmp_path):
    manifest_sha256 = write_bundle(tmp_path)
    (tmp_path / "events.csv").write_text("changed\n")
    with pytest.raises(AuditError, match="differs from manifest"):
        analyze(tmp_path, manifest_sha256, 0.02, 100)
