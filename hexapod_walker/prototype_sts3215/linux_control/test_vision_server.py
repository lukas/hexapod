"""Off-robot tests for the React vision service's calibration contract."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from vision_server import (  # noqa: E402
    VisionRuntime,
    assess_visual_calibration_readiness,
    build_current_pose_config,
    build_visual_calibration_report,
    materialize_default_config,
    updated_visual_bias_config,
)
from avfoundation_capture import AVFoundationYuvCapture  # noqa: E402


ROBOT_TAG_IDS = set(range(13))
FLOOR_TAG_IDS = {20, 21, 22}
CONFIG_PATH = (
    HERE.parent
    / "hexapod-tracker"
    / "configs"
    / "apriltag_pose_config_20260831.json"
)


def test_current_floor_map_overlays_retired_tracker_anchors(tmp_path):
    base = tmp_path / "base.json"
    floor = tmp_path / "floor.json"
    base.write_text(
        '{"tag_family":"tag36h11","marker_size_m":0.027,'
        '"floor_tags":{"12":{}}}'
    )
    floor.write_text(
        '{"family":"tag36h11","units":"millimeters",'
        '"tag_black_square_size":27.2,"tags":['
        '{"id":104,"center":[0,0,0],"yaw_degrees":-89.8},'
        '{"id":102,"center":[304.8,0,0],"yaw_degrees":-90.4}]}'
    )

    config = build_current_pose_config(base, floor)

    assert set(config["floor_tags"]) == {"102", "104"}
    assert config["floor_tags"]["102"]["world_from_tag"] == {
        "translation_m": [0.3048, 0.0, 0.0],
        "euler_xyz_deg": [0.0, 0.0, -90.4],
    }
    assert config["marker_size_m"] == pytest.approx(0.0272)


def test_materialized_active_layout_keeps_newer_live_bias_across_restart(
        tmp_path):
    revision = tmp_path / "revision-7"
    revision.mkdir()
    pose = revision / "apriltag-pose-config.snapshot.json"
    floor = revision / "floor-tag-map.snapshot.json"
    manifest = revision / "bundle.json"
    target = tmp_path / "state" / "live.json"
    pose.write_text(json.dumps({
        "tag_family": "tag36h11",
        "marker_size_m": 0.027,
        "floor_tags": {"12": {}},
        "robot_pose": {
            "tags": {"1": {"frame_from_tag": {
                "euler_xyz_deg": [0.0, 0.0, 90.0],
            }}},
            "visual_joint_bias_deg": {"L0_yaw": 1.0},
        },
        "visual_calibration": {"applied_unix": 10.0},
    }))
    floor.write_text(json.dumps({
        "family": "tag36h11",
        "units": "millimeters",
        "tag_black_square_size": 27.2,
        "tags": [
            {"id": 104, "center": [0, 0, 0], "yaw_degrees": -89.8},
            {"id": 102, "center": [304.8, 0, 0], "yaw_degrees": -90.4},
        ],
    }))
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    manifest.write_text(json.dumps({
        "revision_id": "revision-7",
        "pose_config_sha256": digest(pose),
        "floor_map_sha256": digest(floor),
    }))
    target.parent.mkdir()
    target.write_text(json.dumps({
        "robot_pose": {
            "tags": {"1": {"frame_from_tag": {
                "euler_xyz_deg": [0.0, 0.0, -90.0],
            }}},
            "visual_joint_bias_deg": {"L0_yaw": 3.0},
        },
        "visual_calibration": {"applied_unix": 20.0, "kind": "test"},
    }))

    first = materialize_default_config(
        target_path=target, active_bundle_path=revision)
    first_bytes = first.read_bytes()
    config = json.loads(first_bytes)

    assert config["robot_pose"]["tags"]["1"]["frame_from_tag"][
        "euler_xyz_deg"] == [0.0, 0.0, 90.0]
    assert config["robot_pose"]["visual_joint_bias_deg"] == {"L0_yaw": 3.0}
    assert config["visual_calibration"]["applied_unix"] == 20.0
    assert config["runtime_layout_source"] == {
        "kind": "robot_lab_active_bundle",
        "revision_id": "revision-7",
        "pose_config_sha256": digest(pose),
        "floor_map_sha256": digest(floor),
    }
    assert materialize_default_config(
        target_path=target, active_bundle_path=revision).read_bytes() == first_bytes


class _ClosedCapture:
    def isOpened(self) -> bool:
        return False

    def read(self) -> tuple[bool, None]:
        return False, None

    def release(self) -> None:
        pass


def _ready_frame(*, offset_deg: float = 1.5, pose_deg: float = 0.0) -> dict:
    detections = [
        {
            "tag_id": tag_id,
            "source": "detected",
            "label": f"robot {tag_id}",
        }
        for tag_id in sorted(ROBOT_TAG_IDS)
    ] + [
        {"tag_id": tag_id, "source": "detected", "label": f"floor {tag_id}"}
        for tag_id in sorted(FLOOR_TAG_IDS)
    ]
    joints = {}
    for leg in range(6):
        for axis in ("yaw", "hip"):
            name = f"L{leg}_{axis}"
            joints[name] = {
                "value_deg": pose_deg + offset_deg,
                "visual_deg": pose_deg + offset_deg,
                "visual_source": "apriltag",
                "visual_confidence": 0.96,
                "encoder_deg": pose_deg,
                "visual_minus_encoder_deg": offset_deg,
            }
        knee = f"L{leg}_knee"
        joints[knee] = {
            "value_deg": pose_deg,
            "visual_deg": None,
            "visual_absolute_deg": abs(pose_deg) + 0.8,
            "visual_source": "foot_tip_projection_magnitude",
            "visual_confidence": 0.55,
            "encoder_deg": pose_deg,
            "visual_abs_minus_encoder_abs_deg": 0.8,
        }
    return {
        "detections": detections,
        "foot_tips": [
            {"leg": leg, "source": "color", "confidence": 0.9}
            for leg in range(6)
        ],
        "encoder_feedback": {"ok": True, "live_joint_count": 18},
        "safety_assessment": {
            "verdict": "safe",
            "unsafe_reasons": [],
            "unknown_reasons": [],
        },
        "pose_reference": "floor",
        "camera_calibration_approximate": True,
        "full_pose": {"joints": joints},
    }


def test_readiness_requires_a_stable_run_of_direct_measurements() -> None:
    frame = _ready_frame()

    warming = assess_visual_calibration_readiness(
        [copy.deepcopy(frame) for _ in range(7)],
        robot_tag_ids=ROBOT_TAG_IDS,
        floor_tag_ids=FLOOR_TAG_IDS,
        stable_frames=12,
    )
    ready = assess_visual_calibration_readiness(
        [copy.deepcopy(frame) for _ in range(12)],
        robot_tag_ids=ROBOT_TAG_IDS,
        floor_tag_ids=FLOOR_TAG_IDS,
        stable_frames=12,
    )

    assert warming["ready"] is False
    assert warming["status"] == "hold_still"
    assert warming["stable_frames"] == 7
    assert ready["ready"] is True
    assert ready["status"] == "ready_provisional"
    assert ready["scope"] == "lid_joints"
    assert "Knees are not observed" in ready["warnings"][-1]
    assert "approximate" in ready["warnings"][0]


def test_readiness_identifies_missing_direct_tag_instead_of_using_flow() -> None:
    frame = _ready_frame()
    frame["detections"][3]["source"] = "optical_flow"

    readiness = assess_visual_calibration_readiness(
        [copy.deepcopy(frame) for _ in range(15)],
        robot_tag_ids=ROBOT_TAG_IDS,
        floor_tag_ids=FLOOR_TAG_IDS,
    )

    assert readiness["ready"] is False
    assert "missing 3" in readiness["blockers"][0]


def test_readiness_rejects_a_physically_moving_pose() -> None:
    history = [
        _ready_frame(pose_deg=index * 0.5)
        for index in range(12)
    ]

    readiness = assess_visual_calibration_readiness(
        history,
        robot_tag_ids=ROBOT_TAG_IDS,
        floor_tag_ids=FLOOR_TAG_IDS,
        stable_frames=12,
        maximum_motion_deg=2.0,
    )

    assert readiness["ready"] is False
    assert readiness["maximum_joint_motion_deg"] == 5.5
    assert "Hold still" in readiness["blockers"][-1]


def test_readiness_uses_encoders_to_distinguish_visual_jitter_from_motion() -> None:
    history = []
    for index in range(12):
        frame = _ready_frame(pose_deg=0.0)
        for record in frame["full_pose"]["joints"].values():
            if record.get("visual_deg") is not None:
                record["visual_deg"] += (-1.0 if index % 2 else 1.0) * 4.0
        history.append(frame)

    readiness = assess_visual_calibration_readiness(
        history,
        robot_tag_ids=ROBOT_TAG_IDS,
        floor_tag_ids=FLOOR_TAG_IDS,
        stable_frames=12,
        maximum_motion_deg=2.0,
    )

    assert readiness["ready"] is True
    assert readiness["maximum_joint_motion_deg"] == 0.0


def test_visual_calibration_report_is_robust_and_never_applies_offsets() -> None:
    samples = [
        _ready_frame(offset_deg=value)
        for value in [2.0, 2.1, 1.9, 2.0, 2.2, 40.0, 2.0]
    ]

    report = build_visual_calibration_report(
        samples,
        camera_index=1,
        config_path=Path("test-config.json"),
    )

    yaw = next(item for item in report["joints"] if item["joint"] == "L0_yaw")
    knee = next(item for item in report["joints"] if item["joint"] == "L0_knee")
    assert yaw["visual_minus_encoder_deg"] == 2.0
    assert yaw["median_absolute_deviation_deg"] == 0.1
    assert knee["signed"] is False
    assert knee["observable"] is False
    assert report["quality"] == "provisional"
    assert report["advisory_only"] is True
    assert report["servo_zeros_changed"] is False
    assert report["motor_commands_sent"] is False


def test_good_signed_report_accumulates_visual_bias_without_servo_changes() -> None:
    samples = [_ready_frame(offset_deg=2.0) for _ in range(12)]
    report = build_visual_calibration_report(
        samples,
        camera_index=1,
        config_path=Path("test-config.json"),
    )
    config = {
        "robot_pose": {"visual_joint_bias_deg": {"L0_yaw": 1.0}}
    }

    updated, applied = updated_visual_bias_config(config, report)

    assert len(applied) == 12
    assert updated["robot_pose"]["visual_joint_bias_deg"]["L0_yaw"] == 3.0
    assert config["robot_pose"]["visual_joint_bias_deg"]["L0_yaw"] == 1.0
    assert updated["visual_calibration"]["servo_zeros_changed"] is False
    assert updated["visual_calibration"]["motor_commands_sent"] is False


def test_shared_server_worker_leaves_camera_off_until_explicit_start() -> None:
    opened: list[int] = []

    def capture_factory(index: int) -> _ClosedCapture:
        opened.append(index)
        return _ClosedCapture()

    runtime = VisionRuntime(CONFIG_PATH, capture_factory=capture_factory)
    try:
        runtime.start()
        time.sleep(0.15)
        state = runtime.public_state()
        assert opened == []
        assert state["camera"]["enabled"] is False
        assert state["camera"]["status"] == "off"
        assert state["readiness"]["status"] == "camera_off"

        runtime.enable_camera(1)
        deadline = time.monotonic() + 1.0
        while not opened and time.monotonic() < deadline:
            time.sleep(0.01)
        assert opened[0] == 1

        state = runtime.disable_camera()
        assert state["camera"]["enabled"] is False
        assert state["camera"]["status"] == "off"
    finally:
        runtime.stop()


def test_runtime_reports_named_configured_camera_choices() -> None:
    runtime = VisionRuntime(
        CONFIG_PATH,
        camera_cycle=(0, 3),
        capture_factory=lambda _index: _ClosedCapture(),
    )
    try:
        state = runtime.public_state()
        assert state["camera"]["devices"] == [
            {
                "index": 0,
                "name": "Camera 0",
                "kind": "configured",
                "available": True,
            },
            {
                "index": 3,
                "name": "Camera 3",
                "kind": "configured",
                "available": True,
            },
        ]
        assert state["camera"]["discovery_exact"] is False
    finally:
        runtime.stop()


def test_exact_camera_discovery_rejects_a_missing_index_without_switching() -> None:
    runtime = VisionRuntime(
        CONFIG_PATH,
        camera_cycle=(0, 1),
        capture_factory=lambda _index: _ClosedCapture(),
    )
    try:
        runtime._camera_discovery_exact = True
        runtime._camera_devices = [{
            "index": 0,
            "name": "Built-in",
            "kind": "built_in",
            "available": True,
        }]
        runtime.refresh_camera_devices = lambda: runtime.public_state()

        with pytest.raises(ValueError, match="not currently available"):
            runtime.switch_camera(1)

        assert runtime.public_state()["camera"]["requested_index"] == 0
    finally:
        runtime.stop()


def test_avfoundation_descriptors_preserve_names_and_camera_kinds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Device:
        def __init__(self, name: str, device_type: str) -> None:
            self.name = name
            self.device_type = device_type

        def localizedName(self) -> str:
            return self.name

        def deviceType(self) -> str:
            return self.device_type

        def isConnected(self) -> bool:
            return True

        def isSuspended(self) -> bool:
            return False

    monkeypatch.setattr(
        AVFoundationYuvCapture,
        "_devices",
        staticmethod(lambda: [
            Device("MacBook Pro Camera", "AVCaptureDeviceTypeBuiltInWideAngleCamera"),
            Device("Lukas's iPhone", "AVCaptureDeviceTypeExternal"),
        ]),
    )

    assert AVFoundationYuvCapture.device_descriptors() == [
        {
            "index": 0,
            "name": "MacBook Pro Camera",
            "kind": "built_in",
            "available": True,
        },
        {
            "index": 1,
            "name": "Lukas's iPhone",
            "kind": "continuity",
            "available": True,
        },
    ]


def test_native_nv12_capture_keeps_full_luma_and_downsizes_color() -> None:
    capture = AVFoundationYuvCapture(
        1,
        preferred_sizes=((8, 6),),
        processing_width=4,
    )
    y = np.arange(48, dtype=np.uint8).reshape(6, 8)
    uv = np.full((3, 4, 2), 128, dtype=np.uint8)

    color = capture._frame_from_planes(y, uv)

    assert color.shape == (2, 4, 3)
    assert capture.detection_gray is not None
    assert capture.detection_gray.shape == (6, 8)
    assert capture.tracking_gray is not None
    assert capture.tracking_gray.shape == (2, 4)
    assert capture.capture_info()["native_luma"] is True
