import json

import pytest

from hexapod_lab.offline_guarded_replay import run_replay


def replay_spec():
    return {
        "simulation_only": True,
        "robot_motion": False,
        "replay_target": "torque_off_feedback_imu_soak_v1",
        "robot_id": "hexapod-1",
        "required_servos": 18,
        "sample_hz": 10,
        "mock_capture_duration_s": 30,
        "max_state_age_ms": 150,
        "expected_artifacts": ["telemetry.jsonl", "runner-result.json"],
        "required_checks": [
            "executor_resolves",
            "proposal_schema_accepts",
            "300_samples_emitted",
            "artifacts_registered",
            "clean_exit_status_0",
        ],
    }


def test_replay_emits_deterministic_bounded_artifacts(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"

    first_result = run_replay(replay_spec(), first, artifacts_registered=True)
    second_result = run_replay(replay_spec(), second, artifacts_registered=True)

    assert first_result == second_result
    assert first_result["passed"] is True
    assert first_result["sample_count"] == 300
    assert (first / "telemetry.jsonl").read_bytes() == (
        second / "telemetry.jsonl"
    ).read_bytes()
    samples = [
        json.loads(line)
        for line in (first / "telemetry.jsonl").read_text().splitlines()
    ]
    assert [sample["sample_sequence"] for sample in samples] == list(range(300))
    assert all(sample["live_servo_ids"] == list(range(1, 19)) for sample in samples)
    assert all(sample["position_age_ms"] <= 150 for sample in samples)
    assert all(sample["simulated"] is True for sample in samples)
    assert all(sample["robot_motion"] is False for sample in samples)


@pytest.mark.parametrize(
    ("field", "value"),
    [("simulation_only", False), ("robot_motion", True), ("required_servos", 17)],
)
def test_replay_rejects_nonmatching_or_physical_proposals(tmp_path, field, value):
    spec = replay_spec()
    spec[field] = value

    with pytest.raises(ValueError):
        run_replay(spec, tmp_path, artifacts_registered=False)
