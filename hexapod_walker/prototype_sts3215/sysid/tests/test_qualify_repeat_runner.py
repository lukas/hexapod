import json

from sysid import PROTO_DIR
from sysid.qualify_repeat_runner import qualify


def experiment():
    return {
        "id": "34d436422e284be4b4bfdba705309fa2",
        "parameters": {
            "robot_id": "hexapod-1",
            "kind": "independent_leg_hysteresis_repeat",
            "legs": ["L2", "L5"],
            "order": ["L2", "L5"],
            "profile": "air",
            "cycles_per_leg": 6,
            "seconds_per_leg": 156,
            "timeout_seconds": 60,
            "hz": 10,
            "foot_path": {"x_mm": [180, 187.5, 195], "y_mm": 60},
            "final_state": "limp",
            "supported_chassis": True,
            "camera_required": True,
            "expected_live_motors": 18,
            "healthy_motor_samples": 3,
            "remote_abort_required": True,
            "camera": {
                "minimum_target_tag_coverage_fraction": 0.9,
                "required_target_tags": {"L2": [18, 25], "L5": [48, 64]},
            },
            "stop_conditions": [
                "Any configured current, temperature, voltage, or communication safety trip",
                "hard or sustained current",
                "A cable enters a leg sweep volume",
                "Camera or state timestamps stop advancing or lose synchronization",
            ],
        },
    }


def test_legacy_plan_still_fails_closed_on_short_execution_timeout():
    report = qualify(experiment(), PROTO_DIR)

    assert report["qualified"] is False
    assert report["executor_class"] is None
    assert report["robot_contacted"] is False
    assert report["robot_motion"] is False
    assert report["checks"]["parameter_schema"]["passed"] is True
    assert report["checks"]["executor_availability"]["passed"] is True
    assert report["checks"]["runtime_compatibility"]["passed"] is True
    assert report["checks"]["camera_guard_binding"]["passed"] is True
    assert report["checks"]["telemetry_guard_binding"]["passed"] is True
    assert report["checks"]["remote_abort_binding"]["passed"] is True
    assert report["checks"]["final_limp_binding"]["passed"] is True
    assert report["trusted_deterministic_executor_name"] is None
    assert report["runtime_compatibility_result"]["passed"] is True
    assert report["duration_timeout_compatibility_result"]["passed"] is False
    assert "312s ordered sequence" in (
        report["duration_timeout_compatibility_result"]["detail"]
    )
    assert len(report["command_sequence_digest"]) == 64
    assert report["final_state_limp_assertion"]["passed"] is True
    assert [item["executor_bound"] for item in report["stop_condition_mapping"]] == [
        False,
        True,
        False,
        True,
    ]
    assert report["stop_condition_mapping"][0]["coverage"] == "partial"
    assert report["protocols"]["L2"]["moving_joints"] == [7, 8]
    assert report["protocols"]["L5"]["moving_joints"] == [16, 17]


def test_qualification_is_deterministic():
    first = qualify(experiment(), PROTO_DIR)
    second = qualify(json.loads(json.dumps(experiment())), PROTO_DIR)
    assert first == second


def test_parameter_mismatch_is_reported_without_executor_admission():
    proposed = experiment()
    proposed["parameters"]["hz"] = 25

    report = qualify(proposed, PROTO_DIR)

    assert report["qualified"] is False
    assert report["checks"]["parameter_schema"]["passed"] is False
    assert "hz" in report["checks"]["parameter_schema"]["detail"]


def test_legacy_nested_supervision_shape_remains_accepted():
    proposed = experiment()
    proposed["parameters"]["guarded_supervision"] = {
        key: proposed["parameters"].pop(key)
        for key in (
            "camera_required",
            "expected_live_motors",
            "healthy_motor_samples",
            "remote_abort_required",
        )
    }

    report = qualify(proposed, PROTO_DIR)

    assert report["checks"]["parameter_schema"]["passed"] is True


def test_robot_lab_top_level_tag_guard_shape_is_accepted():
    proposed = experiment()
    camera = proposed["parameters"].pop("camera")
    proposed["parameters"].update(camera)

    report = qualify(proposed, PROTO_DIR)

    assert report["checks"]["parameter_schema"]["passed"] is True
    assert report["qualified"] is False
    assert report["checks"]["camera_guard_binding"]["passed"] is True
    assert report["checks"]["telemetry_guard_binding"]["passed"] is True


def test_duration_timeout_compatibility_can_pass():
    proposed = experiment()
    proposed["parameters"]["timeout_seconds"] = 312

    report = qualify(proposed, PROTO_DIR)

    assert report["duration_timeout_compatibility_result"]["passed"] is True
    assert "312s ordered sequence fits" in (
        report["duration_timeout_compatibility_result"]["detail"]
    )


def test_missing_timeout_still_reports_required_bounded_duration():
    proposed = experiment()
    proposed["parameters"].pop("timeout_seconds")

    report = qualify(proposed, PROTO_DIR)

    assert report["bounded_duration_seconds"] == 312
    assert report["duration_timeout_compatibility_result"]["passed"] is False
    assert "requires an explicit timeout_seconds >= 312" in (
        report["duration_timeout_compatibility_result"]["detail"]
    )


def test_requalification_uses_sealed_input_and_exact_protocol_hashes():
    proposed = {
        "id": "requalification",
        "parameters": {
            "task": "runner_compatibility_validation",
            "simulation_only": True,
            "robot_motion": False,
            "command_hardware": False,
            "timeout_seconds": 60,
            "required_executor_class": "trusted_deterministic",
            "checks": [
                "parameter_schema", "executor_availability",
                "runtime_compatibility", "camera_guard_binding",
                "telemetry_guard_binding", "remote_abort_binding",
                "final_limp_binding",
            ],
            "protocols": {
                "L2": {"sha256": "c837cdec25d49a254ea7c288f30f68782155afb48e2f9fe6eac853b9fc0ab634", "ticks": 1560, "hz": 10.0},
                "L5": {"sha256": "2343e7e471e4fbf3a33cbc0518c5d70cc82b7cf885440937b9e7cd4161a0cd6e", "ticks": 1560, "hz": 10.0},
            },
        },
    }
    sealed = experiment()
    sealed["parameters"].pop("timeout_seconds")

    report = qualify(proposed, PROTO_DIR, sealed)

    assert report["qualified"] is True
    assert report["executor_class"] == "trusted_deterministic"
    assert report["duration_timeout_compatibility_result"]["passed"] is True
    assert set(report["checks"]) == set(proposed["parameters"]["checks"])
    assert all(item["passed"] for item in report["checks"].values())
    assert report["protocols"]["L2"]["requested_values_match"] is True
    assert report["fault_injections"]["stale_camera_timestamp"]["passed"] is True
    assert report["fault_injections"]["tag_coverage_below_0.9"]["passed"] is True
    assert set(report["fault_injections"]) == {
        "stale_camera_timestamp", "tag_coverage_below_0.9",
        "stale_state_timestamp", "incomplete_servo_sample",
        "out_of_bounds_voltage", "remote_abort",
        "nonadvancing_state_timestamp_during_glide",
        "nonadvancing_state_timestamp_during_trajectory",
    }
    assert all(item["passed"] for item in report["fault_injections"].values())
