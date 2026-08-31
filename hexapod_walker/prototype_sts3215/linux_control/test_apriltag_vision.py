"""Off-robot tests for calibrated AprilTag vision.

Run locally:
    uv run pytest linux_control/test_apriltag_vision.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy.spatial.transform import Rotation

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from apriltag_vision import (  # noqa: E402
    CameraCalibration,
    TagCorners,
    TemporalTagCornerTracker,
    detect_tag_corners,
    estimate_world_reference,
    marker_object_corners,
)
from foot_tip_tracking import FootTipTracker  # noqa: E402
from housing_pose import RigidTransform  # noqa: E402
from track_apriltags import _camera_order_after, _parse_camera_cycle  # noqa: E402


def test_detects_generated_tag36h11_and_decodes_orientation() -> None:
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    marker = cv2.aruco.generateImageMarker(dictionary, 7, 240, borderBits=1)
    canvas = np.full((400, 400), 255, dtype=np.uint8)
    canvas[80:320, 80:320] = marker

    detections = detect_tag_corners(canvas)

    assert [item.tag_id for item in detections] == [7]
    assert np.allclose(detections[0].center_px, [199.5, 199.5], atol=1.0)
    assert abs(detections[0].tag_y_clockwise_from_image_up_deg) < 0.5


def test_scales_intrinsics_only_for_same_aspect_ratio() -> None:
    calibration = CameraCalibration.from_dict({
        "image_size_px": [1000, 500],
        "camera_matrix": [[800, 0, 500], [0, 810, 250], [0, 0, 1]],
        "distortion_coefficients": [0, 0, 0, 0, 0],
    })
    matrix, _ = calibration.for_image(2000, 1000)
    assert np.allclose(matrix, [[1600, 0, 1000], [0, 1620, 500], [0, 0, 1]])
    try:
        calibration.for_image(1920, 1080)
    except ValueError as error:
        assert "aspect ratios differ" in str(error)
    else:
        raise AssertionError("mismatched aspect ratio should fail")


def test_scales_rotated_center_crop_for_landscape_phone_video() -> None:
    calibration = CameraCalibration.from_dict({
        "image_size_px": [4284, 5712],
        "camera_matrix": [
            [3960.0, 0.0, 2142.0],
            [0.0, 3960.0, 2856.0],
            [0.0, 0.0, 1.0],
        ],
        "distortion_coefficients": [0, 0, 0, 0, 0],
        "allow_center_crop": True,
        "allow_quarter_turn": True,
    })

    matrix, _ = calibration.for_image(1920, 1080)

    assert np.allclose(matrix[0, 0], 1331.0924, atol=0.01)
    assert np.allclose(matrix[1, 1], 1331.0924, atol=0.01)
    assert np.allclose(matrix[:2, 2], [959.664, 540.0], atol=0.5)


def test_recovers_camera_pose_from_multiple_floor_tags() -> None:
    marker_size = 0.04
    camera_matrix = np.asarray([
        [900.0, 0.0, 640.0],
        [0.0, 900.0, 360.0],
        [0.0, 0.0, 1.0],
    ])
    distortion = np.zeros(5)
    world_from_camera = RigidTransform(
        np.asarray([0.12, -0.08, 1.15]),
        Rotation.from_euler("xyz", [180.0, 0.0, 8.0], degrees=True),
    )
    camera_from_world = world_from_camera.inverse()
    floor_tags = {
        12: RigidTransform.identity(),
        13: RigidTransform(
            np.asarray([0.48, 0.22, 0.0]),
            Rotation.from_euler("z", 17.0, degrees=True),
        ),
        15: RigidTransform(
            np.asarray([-0.31, 0.37, 0.0]),
            Rotation.from_euler("z", -73.0, degrees=True),
        ),
    }
    detections: list[TagCorners] = []
    for tag_id, world_from_tag in floor_tags.items():
        world_points = np.stack([
            world_from_tag.apply(point)
            for point in marker_object_corners(marker_size)
        ])
        camera_points = np.stack([
            camera_from_world.apply(point) for point in world_points
        ])
        pixels = np.column_stack([
            camera_matrix[0, 0] * camera_points[:, 0] / camera_points[:, 2]
            + camera_matrix[0, 2],
            camera_matrix[1, 1] * camera_points[:, 1] / camera_points[:, 2]
            + camera_matrix[1, 2],
        ]).astype(np.float32)
        detections.append(TagCorners(tag_id, pixels))

    reference = estimate_world_reference(
        detections,
        floor_tags,
        camera_matrix,
        distortion,
        marker_size_m=marker_size,
    )

    assert reference is not None
    assert reference.floor_tag_ids == (12, 13, 15)
    assert reference.reprojection_rms_px < 1e-3
    assert np.allclose(
        reference.world_from_camera.translation_m,
        world_from_camera.translation_m,
        atol=1e-6,
    )
    rotation_error = (
        reference.world_from_camera.rotation.inv() * world_from_camera.rotation
    ).magnitude()
    assert math.degrees(float(rotation_error)) < 1e-4


def test_as_photographed_config_maps_handwritten_zero_to_l0() -> None:
    config_path = _HERE / "apriltag_pose_config_20260831.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    tags = config["robot_pose"]["tags"]

    assert tags["1"]["frame"] == "L0_coxa"
    assert tags["7"]["frame"] == "L0_femur"
    assert "handwritten 0" in tags["1"]["label"]
    assert set(map(int, config["floor_tags"])) == {12, 13, 15}
    assert config["marker_size_m"] == 0.027
    assert config["marker_size_verified"] is True


def test_temporal_tag_tracker_bridges_a_decoder_miss_with_optical_flow() -> None:
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    marker = cv2.aruco.generateImageMarker(dictionary, 3, 180, borderBits=1)
    first = np.full((420, 520), 210, dtype=np.uint8)
    second = first.copy()
    first[120:300, 150:330] = marker
    second[126:306, 159:339] = marker
    tracker = TemporalTagCornerTracker(max_occlusion_frames=3)

    decoded = tracker.update(first, detect_tag_corners(first))
    carried = tracker.update(second, [])

    assert decoded[0].source == "detected"
    assert len(carried) == 1
    assert carried[0].tag_id == 3
    assert carried[0].source == "optical_flow"
    assert carried[0].occlusion_age_frames == 1
    assert np.allclose(
        carried[0].center_px - decoded[0].center_px, [9.0, 6.0], atol=1.0
    )


def _synthetic_red_foot_scene() -> tuple[np.ndarray, np.ndarray, dict[int, np.ndarray]]:
    image = np.full((900, 900, 3), 80, dtype=np.uint8)
    body = np.asarray([450.0, 450.0])
    anchors: dict[int, np.ndarray] = {}
    for leg in range(6):
        angle = (leg + 0.5) * math.pi / 3.0
        direction = np.asarray([math.cos(angle), math.sin(angle)])
        anchor = body + 150.0 * direction
        foot = body + 340.0 * direction
        anchors[leg] = anchor
        cv2.ellipse(
            image,
            tuple(np.rint(foot).astype(int)),
            (22, 34),
            math.degrees(angle),
            0,
            360,
            (0, 0, 240),
            -1,
        )
    return image, body, anchors


def test_red_boot_detector_associates_all_six_legs_by_outward_ray() -> None:
    image, body, anchors = _synthetic_red_foot_scene()
    tracker = FootTipTracker(max_occlusion_frames=3)

    feet = tracker.update(
        image,
        body_center_px=body,
        femur_anchor_px=anchors,
        tag_scale_px=60.0,
    )

    assert [foot.leg for foot in feet] == list(range(6))
    assert all(foot.source == "color" for foot in feet)
    for foot in feet:
        radial_distance = np.linalg.norm(foot.point_px - body)
        assert 350.0 <= radial_distance <= 385.0


def test_red_boot_tracker_marks_short_missing_measurement_as_inferred() -> None:
    image, body, anchors = _synthetic_red_foot_scene()
    tracker = FootTipTracker(max_occlusion_frames=3)
    first = tracker.update(
        image,
        body_center_px=body,
        femur_anchor_px=anchors,
        tag_scale_px=60.0,
    )
    second = tracker.update(
        image,
        body_center_px=None,
        femur_anchor_px={},
        tag_scale_px=60.0,
    )

    assert len(first) == len(second) == 6
    assert all(foot.source in {"optical_flow", "prediction"} for foot in second)
    assert all(foot.occlusion_age_frames == 1 for foot in second)


def test_live_camera_cycle_is_deduplicated_and_wraps() -> None:
    cycle = _parse_camera_cycle("0, 1, 1")

    assert cycle == (0, 1)
    assert _camera_order_after(0, cycle) == (1, 0)
    assert _camera_order_after(1, cycle) == (0, 1)
