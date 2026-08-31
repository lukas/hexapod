"""Calibrated AprilTag detection and camera/world pose helpers.

This module is deliberately read-only with respect to the robot.  It reads
images, detects tag36h11 markers, and returns rigid transforms; it contains no
robot networking or motor-control code.

Coordinate conventions
----------------------
OpenCV camera coordinates are x right, y down, z forward.  A tag's x axis is
corner 0 -> corner 1, y is corner 3 -> corner 0 (toward its decoded top), and
z is the printed face normal.  Transforms are named ``A_from_B`` and map B
coordinates into A coordinates, matching :mod:`housing_pose`.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import cv2
import numpy as np
from scipy.spatial.transform import Rotation

from housing_pose import HousingPoseEstimator, RigidTransform


TAG_FAMILY = "tag36h11"
DEFAULT_MARKER_SIZE_M = 37.8968e-3  # black square on the repo's printed sheet


def _finite_array(value: Any, shape: tuple[int, ...], *, name: str) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.shape != shape or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite array with shape {shape}")
    return array


@dataclass(frozen=True)
class CameraCalibration:
    """Pinhole calibration at one reference image resolution."""

    image_size_px: tuple[int, int]  # width, height
    camera_matrix: np.ndarray
    distortion_coefficients: np.ndarray
    approximate: bool = False

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CameraCalibration":
        size = tuple(int(v) for v in value["image_size_px"])
        if len(size) != 2 or min(size) <= 0:
            raise ValueError("camera.image_size_px must be [width, height]")
        matrix = _finite_array(
            value["camera_matrix"], (3, 3), name="camera_matrix"
        )
        distortion = np.asarray(
            value.get("distortion_coefficients", []), dtype=float
        ).reshape(-1)
        if not np.all(np.isfinite(distortion)):
            raise ValueError("distortion coefficients must be finite")
        return cls(
            image_size_px=(size[0], size[1]),
            camera_matrix=matrix,
            distortion_coefficients=distortion,
            approximate=bool(value.get("approximate", False)),
        )

    def for_image(self, width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
        """Scale intrinsics to a same-aspect-ratio image."""
        ref_w, ref_h = self.image_size_px
        sx, sy = width / ref_w, height / ref_h
        if not math.isclose(sx, sy, rel_tol=0.015, abs_tol=0.0):
            raise ValueError(
                f"image is {width}x{height}, but calibration is {ref_w}x{ref_h}; "
                "the aspect ratios differ, so a same-lens scale is unsafe"
            )
        matrix = self.camera_matrix.copy()
        matrix[0, :] *= sx
        matrix[1, :] *= sy
        matrix[2, :] = [0.0, 0.0, 1.0]
        return matrix, self.distortion_coefficients.copy()


@dataclass(frozen=True)
class TagCorners:
    tag_id: int
    corners_px: np.ndarray  # decoded corner order, shape (4, 2)

    @property
    def center_px(self) -> np.ndarray:
        return np.mean(self.corners_px, axis=0)

    @property
    def tag_y_clockwise_from_image_up_deg(self) -> float:
        top = (self.corners_px[0] + self.corners_px[1]) / 2.0
        bottom = (self.corners_px[2] + self.corners_px[3]) / 2.0
        y_axis = top - bottom
        return math.degrees(math.atan2(float(y_axis[0]), float(-y_axis[1])))


@dataclass(frozen=True)
class TagPose:
    tag_id: int
    corners_px: np.ndarray
    camera_from_tag: RigidTransform
    reprojection_rms_px: float
    alternate_reprojection_rms_px: float | None


@dataclass(frozen=True)
class WorldReference:
    world_from_camera: RigidTransform
    floor_tag_ids: tuple[int, ...]
    reprojection_rms_px: float


def marker_object_corners(marker_size_m: float) -> np.ndarray:
    """Return tag corners in the ordering required by IPPE_SQUARE."""
    half = float(marker_size_m) / 2.0
    if not math.isfinite(half) or half <= 0.0:
        raise ValueError("marker_size_m must be positive")
    return np.asarray([
        [-half, +half, 0.0],
        [+half, +half, 0.0],
        [+half, -half, 0.0],
        [-half, -half, 0.0],
    ], dtype=np.float32)


def detect_tag_corners(image: np.ndarray) -> list[TagCorners]:
    """Detect tag36h11 markers and return one record per decoded ID."""
    if image is None or image.ndim not in (2, 3):
        raise ValueError("image must be a grayscale or BGR OpenCV image")
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    parameters = cv2.aruco.DetectorParameters()
    parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_APRILTAG
    # The floor references may be much smaller than the robot in a wide shot.
    parameters.minMarkerPerimeterRate = 0.005
    detector = cv2.aruco.ArucoDetector(dictionary, parameters)
    raw_corners, raw_ids, _rejected = detector.detectMarkers(gray)
    if raw_ids is None:
        return []

    # A duplicate decoded ID is not useful for rigid tracking.  Retain the
    # larger candidate, which is normally the sharper/nearer one.
    by_id: dict[int, TagCorners] = {}
    perimeters: dict[int, float] = {}
    for raw_corner, raw_id in zip(raw_corners, np.asarray(raw_ids).reshape(-1)):
        corners = np.asarray(raw_corner, dtype=np.float32).reshape(4, 2)
        perimeter = float(sum(
            np.linalg.norm(corners[(index + 1) % 4] - corners[index])
            for index in range(4)
        ))
        tag_id = int(raw_id)
        if perimeter > perimeters.get(tag_id, -1.0):
            by_id[tag_id] = TagCorners(tag_id, corners)
            perimeters[tag_id] = perimeter
    return [by_id[tag_id] for tag_id in sorted(by_id)]


def _project_rms(
    object_points: np.ndarray,
    image_points: np.ndarray,
    rvec: np.ndarray,
    tvec: np.ndarray,
    camera_matrix: np.ndarray,
    distortion: np.ndarray,
) -> float:
    projected, _ = cv2.projectPoints(
        object_points, rvec, tvec, camera_matrix, distortion
    )
    error = projected.reshape(-1, 2) - image_points.reshape(-1, 2)
    return math.sqrt(float(np.mean(np.sum(error * error, axis=1))))


def estimate_tag_pose(
    detection: TagCorners,
    camera_matrix: np.ndarray,
    distortion: np.ndarray,
    *,
    marker_size_m: float = DEFAULT_MARKER_SIZE_M,
) -> TagPose:
    """Estimate ``camera_from_tag`` with the square-specific PnP solver."""
    object_points = marker_object_corners(marker_size_m)
    result = cv2.solvePnPGeneric(
        object_points,
        detection.corners_px,
        camera_matrix,
        distortion,
        flags=cv2.SOLVEPNP_IPPE_SQUARE,
    )
    if not result[0] or not result[1]:
        raise ValueError(f"pose solve failed for tag {detection.tag_id}")
    rvecs, tvecs = result[1], result[2]
    ranked = sorted(
        (
            _project_rms(
                object_points,
                detection.corners_px,
                np.asarray(rvec, dtype=float).reshape(3, 1),
                np.asarray(tvec, dtype=float).reshape(3, 1),
                camera_matrix,
                distortion,
            ),
            np.asarray(rvec, dtype=float).reshape(3, 1),
            np.asarray(tvec, dtype=float).reshape(3, 1),
        )
        for rvec, tvec in zip(rvecs, tvecs)
    )
    rms, rvec, tvec = ranked[0]
    rotation_matrix, _ = cv2.Rodrigues(rvec)
    transform = RigidTransform(
        np.asarray(tvec, dtype=float).reshape(3),
        Rotation.from_matrix(rotation_matrix),
    )
    alternate = None if len(ranked) < 2 else float(ranked[1][0])
    return TagPose(
        tag_id=detection.tag_id,
        corners_px=detection.corners_px,
        camera_from_tag=transform,
        reprojection_rms_px=float(rms),
        alternate_reprojection_rms_px=alternate,
    )


def estimate_world_reference(
    detections: Sequence[TagCorners],
    floor_tags: Mapping[int, RigidTransform],
    camera_matrix: np.ndarray,
    distortion: np.ndarray,
    *,
    marker_size_m: float = DEFAULT_MARKER_SIZE_M,
) -> WorldReference | None:
    """Solve camera extrinsics from one or more mapped floor tags."""
    visible = [item for item in detections if item.tag_id in floor_tags]
    if not visible:
        return None

    if len(visible) == 1:
        tag_pose = estimate_tag_pose(
            visible[0], camera_matrix, distortion, marker_size_m=marker_size_m
        )
        world_from_camera = floor_tags[visible[0].tag_id].compose(
            tag_pose.camera_from_tag.inverse()
        )
        return WorldReference(
            world_from_camera,
            (visible[0].tag_id,),
            tag_pose.reprojection_rms_px,
        )

    tag_corners = marker_object_corners(marker_size_m)
    object_points: list[np.ndarray] = []
    image_points: list[np.ndarray] = []
    for detection in visible:
        world_from_tag = floor_tags[detection.tag_id]
        object_points.extend(world_from_tag.apply(point) for point in tag_corners)
        image_points.extend(detection.corners_px)
    world_points = np.asarray(object_points, dtype=np.float32)
    pixels = np.asarray(image_points, dtype=np.float32)
    ok, rvec, tvec = cv2.solvePnP(
        world_points,
        pixels,
        camera_matrix,
        distortion,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not ok:
        return None
    if hasattr(cv2, "solvePnPRefineLM"):
        rvec, tvec = cv2.solvePnPRefineLM(
            world_points, pixels, camera_matrix, distortion, rvec, tvec
        )
    rms = _project_rms(
        world_points, pixels, rvec, tvec, camera_matrix, distortion
    )
    rotation_matrix, _ = cv2.Rodrigues(rvec)
    camera_from_world = RigidTransform(
        np.asarray(tvec, dtype=float).reshape(3),
        Rotation.from_matrix(rotation_matrix),
    )
    return WorldReference(
        camera_from_world.inverse(),
        tuple(item.tag_id for item in visible),
        rms,
    )


def _read_transform_map(value: Mapping[str, Any]) -> dict[int, RigidTransform]:
    result: dict[int, RigidTransform] = {}
    for raw_id, spec in value.items():
        tag_id = int(raw_id)
        transform_value = spec.get("world_from_tag", spec)
        result[tag_id] = RigidTransform.from_dict(transform_value)
    return result


class AprilTagPoseTracker:
    """Detect tags, establish the floor frame, and estimate the hexapod pose."""

    def __init__(self, config: Mapping[str, Any]) -> None:
        family = str(config.get("tag_family", TAG_FAMILY))
        if family != TAG_FAMILY:
            raise ValueError(f"only {TAG_FAMILY} is supported, got {family!r}")
        self.marker_size_m = float(
            config.get("marker_size_m", DEFAULT_MARKER_SIZE_M)
        )
        marker_object_corners(self.marker_size_m)  # validate now
        self.calibration = CameraCalibration.from_dict(config["camera"])
        self.floor_tags = _read_transform_map(config.get("floor_tags", {}))
        self.robot_pose_config = dict(config.get("robot_pose", {}))
        self.tag_labels = {
            int(raw_id): str(spec.get("label", spec.get("frame", f"tag {raw_id}")))
            for raw_id, spec in self.robot_pose_config.get("tags", {}).items()
        }
        for raw_id, spec in config.get("floor_tags", {}).items():
            self.tag_labels[int(raw_id)] = str(
                spec.get("label", f"floor reference {raw_id}")
            )

    @classmethod
    def from_json(cls, path: Path | str) -> "AprilTagPoseTracker":
        with Path(path).open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError("tracker config must contain a JSON object")
        return cls(value)

    def process_frame(
        self,
        image: np.ndarray,
        *,
        frame_index: int = 0,
        time_s: float | None = None,
    ) -> tuple[dict[str, Any], np.ndarray]:
        height, width = image.shape[:2]
        camera_matrix, distortion = self.calibration.for_image(width, height)
        corners = detect_tag_corners(image)
        poses: list[TagPose] = []
        pose_failures: list[int] = []
        for detection in corners:
            try:
                poses.append(estimate_tag_pose(
                    detection,
                    camera_matrix,
                    distortion,
                    marker_size_m=self.marker_size_m,
                ))
            except (ValueError, cv2.error):
                pose_failures.append(detection.tag_id)

        reference = estimate_world_reference(
            corners,
            self.floor_tags,
            camera_matrix,
            distortion,
            marker_size_m=self.marker_size_m,
        )
        if reference is None:
            world_from_camera = RigidTransform.identity()
            reference_name = "camera"
        else:
            world_from_camera = reference.world_from_camera
            reference_name = "floor"

        serialized_detections: list[dict[str, Any]] = []
        estimator_detections: list[dict[str, Any]] = []
        for pose in poses:
            corner = next(item for item in corners if item.tag_id == pose.tag_id)
            world_from_tag = world_from_camera.compose(pose.camera_from_tag)
            record = {
                "tag_id": pose.tag_id,
                "label": self.tag_labels.get(pose.tag_id, f"tag {pose.tag_id}"),
                "center_px": [round(float(v), 3) for v in corner.center_px],
                "corners_px": [
                    [round(float(v), 3) for v in point]
                    for point in corner.corners_px
                ],
                "tag_y_clockwise_from_image_up_deg": round(
                    corner.tag_y_clockwise_from_image_up_deg, 3
                ),
                "reprojection_rms_px": round(pose.reprojection_rms_px, 4),
                "alternate_reprojection_rms_px": (
                    None if pose.alternate_reprojection_rms_px is None
                    else round(pose.alternate_reprojection_rms_px, 4)
                ),
                "camera_from_tag": pose.camera_from_tag.to_dict(),
                f"{reference_name}_from_tag": world_from_tag.to_dict(),
            }
            serialized_detections.append(record)
            estimator_detections.append({
                "tag_id": pose.tag_id,
                "camera": "camera0",
                "camera_from_tag": pose.camera_from_tag.to_dict(),
                "weight": 1.0 / max(0.05, pose.reprojection_rms_px) ** 2,
            })

        robot_result: dict[str, Any] | None = None
        if self.robot_pose_config.get("tags"):
            pose_config = dict(self.robot_pose_config)
            pose_config["cameras"] = {
                "camera0": {"world_from_camera": world_from_camera.to_dict()}
            }
            robot_result = HousingPoseEstimator.from_dict(
                pose_config
            ).estimate_detections(estimator_detections)
            robot_result["pose_reference"] = reference_name

        result: dict[str, Any] = {
            "schema_version": 1,
            "frame_index": int(frame_index),
            "time_s": None if time_s is None else round(float(time_s), 6),
            "image_size_px": [width, height],
            "tag_family": TAG_FAMILY,
            "marker_size_m": self.marker_size_m,
            "camera_calibration_approximate": self.calibration.approximate,
            "pose_reference": reference_name,
            "detected_tag_ids": [pose.tag_id for pose in poses],
            "pose_failure_tag_ids": pose_failures,
            "detections": serialized_detections,
            "world_reference": (
                None if reference is None else {
                    "floor_tag_ids": list(reference.floor_tag_ids),
                    "reprojection_rms_px": round(
                        reference.reprojection_rms_px, 4
                    ),
                    "world_from_camera": reference.world_from_camera.to_dict(),
                }
            ),
            "hexapod_pose": robot_result,
        }
        return result, self.annotate(image, corners, poses, result, camera_matrix,
                                     distortion)

    def annotate(
        self,
        image: np.ndarray,
        corners: Sequence[TagCorners],
        poses: Sequence[TagPose],
        result: Mapping[str, Any],
        camera_matrix: np.ndarray,
        distortion: np.ndarray,
    ) -> np.ndarray:
        output = image.copy()
        scale = max(0.55, output.shape[1] / 2600.0)
        thickness = max(1, round(scale * 2))
        pose_by_id = {pose.tag_id: pose for pose in poses}
        floor_ids = set(self.floor_tags)
        for detection in corners:
            points = np.rint(detection.corners_px).astype(int)
            color = (40, 210, 40) if detection.tag_id in floor_ids else (0, 210, 255)
            cv2.polylines(output, [points], True, color, thickness, cv2.LINE_AA)
            pose = pose_by_id.get(detection.tag_id)
            if pose is not None:
                rvec = pose.camera_from_tag.rotation.as_rotvec().reshape(3, 1)
                tvec = pose.camera_from_tag.translation_m.reshape(3, 1)
                cv2.drawFrameAxes(
                    output,
                    camera_matrix,
                    distortion,
                    rvec,
                    tvec,
                    self.marker_size_m * 0.7,
                    thickness,
                )
            center = detection.center_px.astype(int)
            label = self.tag_labels.get(detection.tag_id, "unmapped")
            text = f"{detection.tag_id}: {label}"
            cv2.putText(
                output,
                text,
                (int(center[0] + 12), int(center[1] - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                scale,
                color,
                thickness,
                cv2.LINE_AA,
            )

        header = (
            f"tag36h11: {len(poses)} tags | pose ref: "
            f"{result['pose_reference']}"
        )
        cv2.putText(
            output, header, (20, 42), cv2.FONT_HERSHEY_SIMPLEX,
            scale, (255, 255, 255), thickness + 2, cv2.LINE_AA,
        )
        cv2.putText(
            output, header, (20, 42), cv2.FONT_HERSHEY_SIMPLEX,
            scale, (20, 20, 20), thickness, cv2.LINE_AA,
        )
        return output
