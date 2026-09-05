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
            "hz": 10,
            "foot_path": {"x_mm": [180, 187.5, 195], "y_mm": 60},
            "final_state": "limp",
            "supported_chassis": True,
            "guarded_supervision": {
                "camera_required": True,
                "expected_live_motors": 18,
                "healthy_motor_samples": 3,
                "remote_abort_required": True,
            },
            "camera": {
                "minimum_target_tag_coverage_fraction": 0.9,
                "required_target_tags": {"L2": [18, 25], "L5": [48, 64]},
            },
        },
    }


def test_current_runner_fails_closed_on_unbound_guards():
    report = qualify(experiment(), PROTO_DIR)

    assert report["qualified"] is False
    assert report["executor_class"] is None
    assert report["robot_contacted"] is False
    assert report["robot_motion"] is False
    assert report["checks"]["parameter_schema"]["passed"] is True
    assert report["checks"]["executor_availability"]["passed"] is True
    assert report["checks"]["runtime_compatibility"]["passed"] is True
    assert report["checks"]["camera_guard_binding"]["passed"] is False
    assert report["checks"]["telemetry_guard_binding"]["passed"] is False
    assert report["checks"]["remote_abort_binding"]["passed"] is True
    assert report["checks"]["final_limp_binding"]["passed"] is True
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
