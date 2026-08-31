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
    detect_tag_corners,
    estimate_world_reference,
    marker_object_corners,
)
from housing_pose import RigidTransform  # noqa: E402


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
