from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
from pathlib import Path

import pytest
import yaml


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("joint_flex_run", HERE / "joint_flex_run.py")
assert SPEC and SPEC.loader
joint_flex_run = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(joint_flex_run)


def test_create_run_populates_identity_and_refuses_overwrite(tmp_path):
    now = datetime(2026, 9, 2, 14, 30, tzinfo=timezone.utc)
    run_dir = joint_flex_run.create_run(
        leg="L2", joint="hip", output_root=tmp_path, now=now
    )
    manifest = yaml.safe_load((run_dir / "manifest.yaml").read_text())

    assert run_dir.name == "20260902T143000-static-hip-L2"
    assert manifest["run_id"] == run_dir.name
    assert manifest["target"] == {
        "leg": "L2", "joint": "hip", "tested_side_or_face": None
    }
    assert manifest["started_at"] == "2026-09-02T14:30:00+00:00"
    with pytest.raises(FileExistsError):
        joint_flex_run.create_run(
            leg="L2", joint="hip", output_root=tmp_path, now=now
        )


def test_template_is_not_capture_ready():
    manifest = joint_flex_run.load_yaml(joint_flex_run.TEMPLATE)
    issues = joint_flex_run.readiness_issues(manifest)
    assert "target.leg must be L0 through L5" in issues
    assert "operator_confirmations.chassis_rigidly_supported must be true" in issues
    assert "cameras.face.device_model is required" in issues
    assert "markers.world_reference is required" in issues
    assert "load.lever_arm_mm is required" in issues


def test_missing_confirmation_section_fails_closed():
    manifest = joint_flex_run.load_yaml(joint_flex_run.TEMPLATE)
    manifest.pop("operator_confirmations")
    issues = joint_flex_run.readiness_issues(manifest)
    assert len([issue for issue in issues if issue.startswith("operator_confirmations.")]) == 6


def test_completed_preflight_is_capture_ready():
    manifest = deepcopy(joint_flex_run.load_yaml(joint_flex_run.TEMPLATE))
    manifest.update({
        "run_id": "20260902T143000-static-knee-L5",
        "started_at": "2026-09-02T14:30:00-07:00",
    })
    manifest["target"].update({"leg": "L5", "joint": "knee"})
    for name in manifest["operator_confirmations"]:
        manifest["operator_confirmations"][name] = True
    manifest["servo_state"].update({"power": "on", "torque": "disabled"})
    for view, index in (("face", 0), ("edge", 1)):
        manifest["cameras"][view].update({
            "device_model": "camera", "device_index": index,
            "resolution_px": [1920, 1080], "frame_rate_hz": 60,
        })
    for field in (
        "world_reference", "R_fixed_reference", "S_perimeter_screw",
        "Y_adjacent_yoke", "F1_proximal_femur", "F2_distal_femur",
    ):
        manifest["markers"][field] = "recorded"
    manifest["load"].update({
        "application_point_description": "marked distal point",
        "lever_arm_mm": 120,
        "force_measurement_device": "force gauge",
        "operator_max_force_N": 5,
        "sweep_steps_N": [1, 2, 3, 4, 5],
    })

    assert joint_flex_run.readiness_issues(manifest) == []
