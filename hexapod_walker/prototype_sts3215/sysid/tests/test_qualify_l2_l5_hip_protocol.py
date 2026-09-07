import json

from sysid import PROTO_DIR
from sysid.qualify_l2_l5_hip_protocol import NAME, main, offsets, qualify


def test_exact_protocol_is_runner_compatible_and_qualified():
    protocol, report = qualify(PROTO_DIR)

    assert protocol["name"] == NAME
    assert report["qualified"] is True
    assert report["runner_compatibility"]["passed"] is True
    assert report["runner_acceptance_unchanged"]["passed"] is True
    assert report["runner_acceptance_unchanged"]["accepted_tick_count"] == 900
    assert report["deterministic_replay_result"] == {
        "passed": True,
        "replay_count": 2,
        "tick_count_each": 900,
        "materialized_ticks_sha256": report["deterministic_replay_result"][
            "materialized_ticks_sha256"
        ],
    }
    assert report["timing_validation"] == {
        "passed": True,
        "sample_rate_hz": 10.0,
        "sample_count": 900,
        "duration_seconds": 90.0,
        "pre_baseline_seconds": 5,
        "post_baseline_seconds": 5,
        "cycles": 4,
    }
    assert report["joint_limit_validation"]["active_joints"] == {
        "L2_hip": 7,
        "L5_hip": 16,
    }
    assert report["joint_limit_validation"]["maximum_slew_deg_per_s"] <= 0.5
    assert report["robot_contacted"] is False
    assert report["robot_motion"] is False
    assert report["inspection_clearance_granted"] is False


def test_cycle_timing_and_amplitudes_are_exact():
    values = offsets()

    assert len(values) == 900
    assert values[:50] == [0.0] * 50
    assert values[-50:] == [0.0] * 50
    for start in (50, 250, 450, 650):
        cycle = values[start:start + 200]
        assert cycle[39] == 2.0
        assert cycle[40:60] == [2.0] * 20
        assert cycle[139] == -2.0
        assert cycle[140:160] == [-2.0] * 20
        assert cycle[199] == 0.0


def test_cli_records_current_provenance_and_verifies_saved_bytes(tmp_path):
    assert main([
        "--out-dir", str(tmp_path),
        "--engineering-job-id", "engineering-current",
        "--source-analysis-job-id", "analysis-current",
        "--source-experiment-id", "experiment-current",
    ]) == 0

    report = json.loads(
        (tmp_path / f"{NAME}.qualification.json").read_text(encoding="utf-8")
    )
    assert report["engineering_job_id"] == "engineering-current"
    assert report["source_analysis_job_id"] == "analysis-current"
    assert report["source_experiment_id"] == "experiment-current"
    assert report["runner_acceptance_unchanged"]["saved_bytes_unchanged"] is True
    assert (
        report["runner_acceptance_unchanged"]["saved_stream_sha256"]
        == report["full_stream_sha256"]
    )
