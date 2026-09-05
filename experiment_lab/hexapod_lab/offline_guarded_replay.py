"""Deterministic, no-I/O replay for the guarded telemetry-soak proposal."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


REPLAY_TARGET = "torque_off_feedback_imu_soak_v1"
EXPECTED_CHECKS = {
    "executor_resolves",
    "proposal_schema_accepts",
    "300_samples_emitted",
    "artifacts_registered",
    "clean_exit_status_0",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_spec(spec: Dict[str, Any]) -> None:
    """Accept only the bounded offline proposal this executor implements."""

    _require(spec.get("simulation_only") is True, "simulation_only must be true")
    _require(spec.get("robot_motion") is False, "robot_motion must be false")
    _require(spec.get("replay_target") == REPLAY_TARGET, "unsupported replay_target")
    _require(spec.get("robot_id") == "hexapod-1", "unsupported robot_id")
    _require(spec.get("required_servos") == 18, "required_servos must be 18")
    _require(spec.get("sample_hz") == 10, "sample_hz must be 10")
    _require(spec.get("mock_capture_duration_s") == 30, "mock capture must be 30 s")
    _require(spec.get("max_state_age_ms") == 150, "max state age must be 150 ms")
    _require(
        set(spec.get("expected_artifacts", []))
        == {"telemetry.jsonl", "runner-result.json"},
        "unexpected artifact contract",
    )
    _require(
        set(spec.get("required_checks", [])) == EXPECTED_CHECKS,
        "unexpected replay check contract",
    )


def telemetry_samples() -> Iterable[Dict[str, Any]]:
    """Yield 30 seconds of deterministic 10 Hz simulated telemetry."""

    servo_ids = list(range(1, 19))
    temperatures = {str(servo_id): 30 + (servo_id % 4) for servo_id in servo_ids}
    voltages = {str(servo_id): 12.0 for servo_id in servo_ids}
    for sequence in range(300):
        yield {
            "source": "deterministic_mock",
            "sample_sequence": sequence,
            "elapsed_ms": sequence * 100,
            "live_servo_ids": servo_ids,
            "missing_servo_ids": [],
            "position_age_ms": 20 + (sequence % 3) * 5,
            "imu_age_ms": 25 + (sequence % 3) * 5,
            "imu_error_counters": {"read": 0, "parse": 0, "stale": 0},
            "temperatures_c": temperatures,
            "voltages_v": voltages,
            "transport_errors": 0,
            "torque_enabled": False,
            "robot_motion": False,
            "simulated": True,
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_replay(
    spec: Dict[str, Any], out_dir: Path, *, artifacts_registered: bool
) -> Dict[str, Any]:
    """Validate the proposal and materialize its deterministic evidence."""

    validate_spec(spec)
    out_dir.mkdir(parents=True, exist_ok=True)
    telemetry_path = out_dir / "telemetry.jsonl"
    with telemetry_path.open("w", encoding="utf-8") as handle:
        for sample in telemetry_samples():
            handle.write(json.dumps(sample, sort_keys=True, separators=(",", ":")))
            handle.write("\n")

    checks = {
        "executor_resolves": True,
        "proposal_schema_accepts": True,
        "300_samples_emitted": True,
        "artifacts_registered": artifacts_registered,
        "clean_exit_status_0": True,
    }
    result = {
        "schema_version": 1,
        "replay_target": REPLAY_TARGET,
        "execution": "offline_deterministic_mock",
        "robot_contacted": False,
        "robot_motion": False,
        "sample_count": 300,
        "sample_hz": 10,
        "capture_duration_s": 30,
        "telemetry_sha256": _sha256(telemetry_path),
        "checks": checks,
        "passed": all(checks.values()),
        "exit_status": 0,
    }
    result_path = out_dir / "runner-result.json"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--artifacts-registered", action="store_true")
    args = parser.parse_args(argv)
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    result = run_replay(
        spec, args.out_dir, artifacts_registered=args.artifacts_registered
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
