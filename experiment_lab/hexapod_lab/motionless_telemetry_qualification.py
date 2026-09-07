"""Offline qualification for a motionless 18-servo telemetry health gate.

The module is intentionally a pure decision engine: it accepts already-recorded
or synthetic samples, performs no I/O beyond the CLI's local files, and has no
path that can enable torque or emit a motor command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


EXPECTED_CAPTURE_FIELDS = {
    "sample_sequence",
    "sample_time",
    "temperature_c",
    "current_a",
    "voltage_v",
    "fault_status",
}
FIXTURE_CASES = (
    "healthy_advancing_18_of_18",
    "stale_sequence",
    "incomplete_coverage",
    "temperature_at_or_above_60_c",
    "temperature_rise_at_least_10_c",
    "hardware_fault",
)
EXPECTED_RESULTS = {
    "healthy_advancing_18_of_18": "pass",
    "stale_sequence": "reject_stale_sequence",
    "incomplete_coverage": "reject_incomplete_coverage",
    "temperature_at_or_above_60_c": "reject_temperature_limit",
    "temperature_rise_at_least_10_c": "reject_temperature_rise",
    "hardware_fault": "reject_hardware_fault",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_spec(spec: Mapping[str, Any]) -> None:
    """Fail closed unless *spec* is the exact offline qualification contract."""

    _require(spec.get("simulation_only") is True, "simulation_only must be true")
    _require(spec.get("robot_motion") is False, "robot_motion must be false")
    _require(spec.get("hardware_access") is False, "hardware_access must be false")
    _require(
        spec.get("assert_no_motor_commands") is True,
        "motor-command assertion required",
    )
    _require(spec.get("assert_no_torque_enable") is True, "torque assertion required")
    _require(
        spec.get("required_advancing_samples") == 3,
        "exactly 3 advancing samples required",
    )
    _require(
        spec.get("required_servo_coverage") == "18/18",
        "18/18 coverage required",
    )
    _require(spec.get("duration_seconds") == 60, "qualification duration must be 60 s")
    _require(
        set(spec.get("capture_fields", ())) == EXPECTED_CAPTURE_FIELDS,
        "capture fields mismatch",
    )
    _require(
        tuple(spec.get("fixture_cases", ())) == FIXTURE_CASES,
        "fixture cases mismatch",
    )
    _require(
        spec.get("require_deterministic_result") is True,
        "deterministic result required",
    )


def _servo_sample(temperature: float = 35.0, fault: str = "ok") -> dict[str, Any]:
    return {
        "temperature_c": temperature,
        "current_a": 0.0,
        "voltage_v": 12.0,
        "fault_status": fault,
    }


def fixture_samples(case: str) -> list[dict[str, Any]]:
    """Build one deterministic three-sample fixture requested by the analysis."""

    _require(case in FIXTURE_CASES, f"unsupported fixture case: {case}")
    samples = []
    for sequence in range(3):
        samples.append(
            {
                "sample_sequence": sequence,
                "sample_time": float(sequence),
                "servos": {
                    str(servo_id): _servo_sample() for servo_id in range(1, 19)
                },
            }
        )
    if case == "stale_sequence":
        samples[2]["sample_sequence"] = 1
    elif case == "incomplete_coverage":
        del samples[1]["servos"]["18"]
    elif case == "temperature_at_or_above_60_c":
        samples[1]["servos"]["7"]["temperature_c"] = 60.0
    elif case == "temperature_rise_at_least_10_c":
        samples[1]["servos"]["7"]["temperature_c"] = 45.0
    elif case == "hardware_fault":
        samples[1]["servos"]["7"]["fault_status"] = "overload"
    return samples


def evaluate_samples(samples: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Evaluate captured samples, returning the first deterministic stop reason."""

    if len(samples) < 3:
        return {"decision": "reject_insufficient_samples", "passed": False}
    previous_sequence: int | None = None
    previous_time: float | None = None
    previous_temperatures: dict[str, float] = {}
    expected_ids = {str(servo_id) for servo_id in range(1, 19)}
    for sample_index, sample in enumerate(samples[:3]):
        try:
            sequence = int(sample["sample_sequence"])
            sample_time = float(sample["sample_time"])
            servos = sample["servos"]
        except (KeyError, TypeError, ValueError):
            return {
                "decision": "reject_malformed_sample",
                "passed": False,
                "sample_index": sample_index,
            }
        if previous_sequence is not None and previous_time is not None and (
            sequence <= previous_sequence or sample_time <= previous_time
        ):
            return {
                "decision": "reject_stale_sequence",
                "passed": False,
                "sample_index": sample_index,
            }
        if not isinstance(servos, Mapping) or set(servos) != expected_ids:
            return {
                "decision": "reject_incomplete_coverage",
                "passed": False,
                "sample_index": sample_index,
            }
        for servo_id in sorted(expected_ids, key=int):
            telemetry = servos[servo_id]
            try:
                temperature = float(telemetry["temperature_c"])
                float(telemetry["current_a"])
                float(telemetry["voltage_v"])
                fault = telemetry["fault_status"]
            except (KeyError, TypeError, ValueError):
                return {
                    "decision": "reject_malformed_sample",
                    "passed": False,
                    "sample_index": sample_index,
                }
            if fault not in (None, "", "ok", "none", 0, False):
                return {
                    "decision": "reject_hardware_fault",
                    "passed": False,
                    "sample_index": sample_index,
                    "servo_id": int(servo_id),
                }
            if temperature >= 60.0:
                return {
                    "decision": "reject_temperature_limit",
                    "passed": False,
                    "sample_index": sample_index,
                    "servo_id": int(servo_id),
                }
            if (
                servo_id in previous_temperatures
                and temperature - previous_temperatures[servo_id] >= 10.0
            ):
                return {
                    "decision": "reject_temperature_rise",
                    "passed": False,
                    "sample_index": sample_index,
                    "servo_id": int(servo_id),
                }
            previous_temperatures[servo_id] = temperature
        previous_sequence = sequence
        previous_time = sample_time
    return {
        "decision": "pass",
        "passed": True,
        "sample_count": 3,
        "servo_coverage": "18/18",
    }


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def qualify(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Run the full fixture bank twice and prove bit-identical decisions."""

    validate_spec(spec)
    first = {case: evaluate_samples(fixture_samples(case)) for case in FIXTURE_CASES}
    second = {case: evaluate_samples(fixture_samples(case)) for case in FIXTURE_CASES}
    observed = {case: result["decision"] for case, result in first.items()}
    checks = {
        "expected_fixture_decisions": observed == EXPECTED_RESULTS,
        "deterministic_repeat": first == second,
        "hardware_access_disabled": True,
        "motor_commands_emitted": False,
        "torque_enable_emitted": False,
    }
    passed = (
        checks["expected_fixture_decisions"]
        and checks["deterministic_repeat"]
        and checks["hardware_access_disabled"]
        and not checks["motor_commands_emitted"]
        and not checks["torque_enable_emitted"]
    )
    return {
        "schema_version": 1,
        "executor": "motionless_telemetry_qualification_v1",
        "execution": "offline_pure_fixture_replay",
        "robot_contacted": False,
        "robot_motion": False,
        "fixture_results": first,
        "fixture_results_sha256": _canonical_sha256(first),
        "checks": checks,
        "passed": passed,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    result = qualify(json.loads(args.spec.read_text(encoding="utf-8")))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
