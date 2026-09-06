import ast
from pathlib import Path

import pytest

import hexapod_lab.motionless_telemetry_qualification as qualification_module
from hexapod_lab.motionless_telemetry_qualification import (
    EXPECTED_RESULTS,
    FIXTURE_CASES,
    evaluate_samples,
    fixture_samples,
    qualify,
)


def qualification_spec():
    return {
        "simulation_only": True,
        "robot_motion": False,
        "hardware_access": False,
        "duration_seconds": 60,
        "assert_no_motor_commands": True,
        "assert_no_torque_enable": True,
        "require_deterministic_result": True,
        "required_advancing_samples": 3,
        "required_servo_coverage": "18/18",
        "capture_fields": [
            "sample_sequence",
            "sample_time",
            "temperature_c",
            "current_a",
            "voltage_v",
            "fault_status",
        ],
        "fixture_cases": list(FIXTURE_CASES),
    }


def test_fixture_bank_has_expected_fail_closed_decisions():
    observed = {
        case: evaluate_samples(fixture_samples(case))["decision"]
        for case in FIXTURE_CASES
    }
    assert observed == EXPECTED_RESULTS


def test_qualification_is_deterministic_and_hardware_inert():
    first = qualify(qualification_spec())
    second = qualify(qualification_spec())

    assert first == second
    assert first["passed"] is True
    assert first["robot_contacted"] is False
    assert first["robot_motion"] is False
    assert first["checks"]["hardware_access_disabled"] is True
    assert first["checks"]["motor_commands_emitted"] is False
    assert first["checks"]["torque_enable_emitted"] is False
    assert len(first["fixture_results_sha256"]) == 64


def test_qualification_module_has_no_hardware_or_network_imports():
    source = Path(qualification_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )

    assert imported_roots <= {
        "__future__",
        "argparse",
        "hashlib",
        "json",
        "pathlib",
        "typing",
    }
    assert imported_roots.isdisjoint(
        {"http", "requests", "serial", "socket", "subprocess", "urllib"}
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("simulation_only", False),
        ("robot_motion", True),
        ("hardware_access", True),
        ("assert_no_motor_commands", False),
        ("assert_no_torque_enable", False),
        ("required_advancing_samples", 2),
        ("required_servo_coverage", "17/18"),
    ],
)
def test_qualification_rejects_physical_or_weakened_specs(field, value):
    spec = qualification_spec()
    spec[field] = value

    with pytest.raises(ValueError):
        qualify(spec)


def test_malformed_sample_is_rejected():
    samples = fixture_samples("healthy_advancing_18_of_18")
    del samples[1]["servos"]["7"]["voltage_v"]

    assert evaluate_samples(samples)["decision"] == "reject_malformed_sample"
