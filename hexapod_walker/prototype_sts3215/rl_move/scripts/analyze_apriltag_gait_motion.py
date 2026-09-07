#!/usr/bin/env python3
"""Measure floor-referenced gait translation and yaw from AprilTag video."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from scipy.spatial.transform import Rotation


_TRACKER_SRC = Path(__file__).resolve().parents[2] / "hexapod-tracker" / "src"
if str(_TRACKER_SRC) not in sys.path:
    sys.path.insert(0, str(_TRACKER_SRC))

from hexapod_tracker.gait_motion import _best_floor_homography  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
TRACKER_CONFIGS = ROOT / "hexapod-tracker" / "configs"
CURRENT_LAYOUT = TRACKER_CONFIGS / "hexapod-1-apriltag-layout.json"
CURRENT_FLOOR_MAP = TRACKER_CONFIGS / "floor_tag_map.json"
MIN_DIRECT_ROBOT_TAGS = 6
MIN_DIRECT_FLOOR_TAGS = 2
MAX_ENDPOINT_BRACKET_AGE_S = 0.25
MAX_INTERIOR_COVERAGE_GAP_S = 0.35
_LEGACY_PHASE = re.compile(r"^gait_(\d+)_(forward|backward)$")
_DRIVE_PHASE = re.compile(r"^drive_(forward|backward|left|right)$")


class MotionEvidenceError(ValueError):
    """The supplied files cannot support calibrated motion evidence."""


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json_sha256(value: Any) -> str:
    encoded = (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise MotionEvidenceError(f"could not read {label}: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise MotionEvidenceError(f"{label} must contain a JSON object: {path}")
    return value


def _unix_timestamp(value: Any, *, label: str) -> float:
    if not isinstance(value, str) or not value.strip():
        raise MotionEvidenceError(f"{label} must be a timezone-aware timestamp")
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise MotionEvidenceError(
            f"{label} must be a timezone-aware timestamp"
        ) from exc
    if parsed.tzinfo is None:
        raise MotionEvidenceError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc).timestamp()


def _recording_paths(run_dir: Path) -> tuple[Path, Path, str]:
    """Resolve the walk-trial names first, then the legacy survey names."""
    candidates = (
        ("camera_raw.mp4", "camera_timestamps.csv", "run_rl_walk_trial"),
        ("iphone_raw.mp4", "iphone_raw_timestamps.csv", "scripted_gait_survey"),
    )
    incomplete: list[str] = []
    for video_name, timestamps_name, source in candidates:
        video = run_dir / video_name
        timestamps = run_dir / timestamps_name
        if video.is_file() and timestamps.is_file():
            return video, timestamps, source
        if video.exists() or timestamps.exists():
            incomplete.append(f"{video_name} + {timestamps_name}")
    detail = ""
    if incomplete:
        detail = f"; incomplete pair(s): {', '.join(incomplete)}"
    raise MotionEvidenceError(
        "run directory has neither camera_raw.mp4/camera_timestamps.csv nor "
        f"iphone_raw.mp4/iphone_raw_timestamps.csv{detail}"
    )


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "1.0", "true"}


def _timestamp_arrays(path: Path) -> dict[str, Any]:
    rows = _csv(path)
    if not rows:
        raise MotionEvidenceError(f"camera timestamp file is empty: {path}")
    has_capture_clock = "capture_unix_s" in rows[0]
    time_key = "capture_unix_s" if has_capture_clock else "unix_s"
    try:
        frames = np.asarray([float(row["frame"]) for row in rows], dtype=float)
        unix = np.asarray([float(row[time_key]) for row in rows], dtype=float)
    except (KeyError, TypeError, ValueError) as exc:
        raise MotionEvidenceError(
            f"camera timestamps need finite frame and {time_key} columns: {path}"
        ) from exc
    if not np.all(np.isfinite(frames)) or not np.all(np.isfinite(unix)):
        raise MotionEvidenceError(f"camera timestamps are not finite: {path}")
    if np.any(np.diff(frames) <= 0.0):
        raise MotionEvidenceError(
            f"camera frame column must advance strictly: {path}"
        )
    expected_frames = np.arange(len(rows), dtype=float)
    if not np.array_equal(frames, expected_frames):
        raise MotionEvidenceError(
            f"camera timestamp frames must be contiguous from zero: {path}"
        )

    delta = np.diff(unix)
    if np.any(delta < 0.0):
        raise MotionEvidenceError(
            f"camera {time_key} column moves backward: {path}"
        )
    duplicate_indices = {
        index + 1 for index, difference in enumerate(delta)
        if difference == 0.0
    }
    if duplicate_indices and not has_capture_clock:
        raise MotionEvidenceError(
            f"camera unix_s column must advance strictly: {path}"
        )
    keep = np.asarray([
        index not in duplicate_indices for index in range(len(rows))
    ], dtype=bool)
    kept_frames = frames[keep]
    kept_unix = unix[keep]
    if np.any(np.diff(kept_unix) <= 0.0):
        raise MotionEvidenceError(
            f"camera {time_key} column cannot be made strictly advancing: {path}"
        )
    return {
        "frames": kept_frames,
        "unix": kept_unix,
        "frame_to_unix": dict(zip(kept_frames.tolist(), kept_unix.tolist())),
        "duplicate_frames": duplicate_indices,
        "row_count": len(rows),
        "clock": time_key,
        "duplicates_collapsed": len(duplicate_indices),
    }


def _video_metadata(path: Path, *, timestamp_rows: int) -> dict[str, Any]:
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            raise MotionEvidenceError(f"could not open camera video: {path}")
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        frame_count_raw = float(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(round(float(capture.get(cv2.CAP_PROP_FRAME_WIDTH))))
        height = int(round(float(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))))
        ok, first = capture.read()
        if not ok or first is None:
            raise MotionEvidenceError(f"could not decode first camera frame: {path}")
        frame_count = int(round(frame_count_raw))
        if frame_count > 1:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_count - 1)
            ok, last = capture.read()
            if not ok or last is None:
                raise MotionEvidenceError(
                    f"could not decode final camera frame: {path}"
                )
    finally:
        capture.release()
    if not math.isfinite(fps) or fps <= 0.0:
        raise MotionEvidenceError(f"camera video has no valid frame rate: {path}")
    if (not math.isfinite(frame_count_raw) or frame_count <= 0
            or not math.isclose(frame_count_raw, frame_count, abs_tol=0.01)):
        raise MotionEvidenceError(f"camera video has no valid frame count: {path}")
    if frame_count != timestamp_rows:
        raise MotionEvidenceError(
            "camera video frame count does not match camera timestamp rows: "
            f"{frame_count} != {timestamp_rows}"
        )
    if width <= 0 or height <= 0:
        raise MotionEvidenceError(f"camera video has invalid dimensions: {path}")
    return {
        "fps": fps,
        "frames": frame_count,
        "width": width,
        "height": height,
        "sha256": _sha256(path),
    }


def _floor_specs(config: dict[str, Any], floor_map: Path | None) \
        -> tuple[dict[str, Any], float]:
    if floor_map is None:
        return config["floor_tags"], float(config["marker_size_m"])
    measured = json.loads(floor_map.read_text())
    if measured.get("units") != "millimeters":
        raise ValueError(f"unsupported floor-map units in {floor_map}")
    specs = {
        str(int(item["id"])): {
            "world_from_tag": {
                "translation_m": [
                    float(value) / 1000.0 for value in item["center"]
                ],
                "euler_xyz_deg": [
                    0.0, 0.0, float(item.get("yaw_degrees", 0.0))
                ],
            }
        }
        for item in measured["tags"]
    }
    return specs, float(measured["tag_black_square_size"]) / 1000.0


def _floor_corners(specs: dict[str, Any], marker_size_m: float) \
        -> dict[int, np.ndarray]:
    half = marker_size_m / 2.0
    local = np.asarray([
        [-half, +half, 0.0], [+half, +half, 0.0],
        [+half, -half, 0.0], [-half, -half, 0.0],
    ])
    result: dict[int, np.ndarray] = {}
    for raw_id, item in specs.items():
        transform = item["world_from_tag"]
        rotation = Rotation.from_euler(
            "xyz", transform.get("euler_xyz_deg", [0.0, 0.0, 0.0]),
            degrees=True,
        )
        translation = np.asarray(transform["translation_m"], dtype=float)
        result[int(raw_id)] = (
            rotation.apply(local) + translation
        )[:, :2]
    return result


def _validate_layout_context(
    config: dict[str, Any],
    *,
    config_path: Path,
    floor_map_path: Path,
    layout_path: Path,
    vision_context_path: Path,
    tag_layout_revision_id: str,
    interval: dict[str, Any],
) -> dict[str, Any]:
    """Verify exact Robot Lab replay inputs and their effective-dated revision."""
    layout = _json_object(layout_path, label="AprilTag layout snapshot")
    floor_map = _json_object(floor_map_path, label="floor-map snapshot")
    context = _json_object(vision_context_path, label="vision context")
    if context.get("kind") != "hexapod_vision_context":
        raise MotionEvidenceError("vision context has the wrong kind")
    revision = context.get("tag_layout_revision")
    if not isinstance(revision, dict) or not revision.get("id"):
        raise MotionEvidenceError("vision context has no tag-layout revision")
    if revision["id"] != tag_layout_revision_id:
        raise MotionEvidenceError(
            "tag-layout revision ID does not match vision context"
        )
    if revision.get("robot_id") != layout.get("robot_id"):
        raise MotionEvidenceError(
            "vision context and layout snapshot robot IDs disagree"
        )
    snapshots = context.get("snapshots")
    if not isinstance(snapshots, dict):
        raise MotionEvidenceError("vision context has no snapshot digests")
    for name, path in (
        ("layout", layout_path),
        ("pose_config", config_path),
        ("floor_map", floor_map_path),
    ):
        record = snapshots.get(name)
        expected = record.get("sha256") if isinstance(record, dict) else None
        if not isinstance(expected, str) or expected != _sha256(path):
            raise MotionEvidenceError(
                f"{name} snapshot bytes do not match vision context"
            )

    recording = context.get("recording_interval")
    if not isinstance(recording, dict):
        raise MotionEvidenceError("vision context has no recording interval")
    if recording.get("crosses_known_revision_boundary") is not False:
        raise MotionEvidenceError(
            "vision context does not prove a single tag-layout revision"
        )
    recorded_unix = _unix_timestamp(
        recording.get("start", context.get("recorded_at")),
        label="vision-context recording start",
    )
    if recorded_unix > interval["start_unix_s"] + MAX_ENDPOINT_BRACKET_AGE_S:
        raise MotionEvidenceError(
            "vision-context recording starts after the engagement trace"
        )
    effective_from = _unix_timestamp(
        revision.get("effective_from"),
        label="tag-layout effective_from",
    )
    if interval["start_unix_s"] < effective_from:
        raise MotionEvidenceError(
            "engagement predates the tag-layout revision in vision context"
        )
    effective_to = revision.get("effective_to_known_at_pin")
    if effective_to is not None:
        effective_to_unix = _unix_timestamp(
            effective_to, label="tag-layout effective_to_known_at_pin"
        )
        if interval["end_unix_s"] >= effective_to_unix:
            raise MotionEvidenceError(
                "engagement crosses the tag-layout revision boundary"
            )

    if not layout.get("robot_id"):
        raise MotionEvidenceError("layout snapshot has no robot_id")
    if layout.get("tag_family") != config.get("tag_family"):
        raise MotionEvidenceError("layout and pose config tag families disagree")
    if floor_map.get("family") != config.get("tag_family"):
        raise MotionEvidenceError("floor map and pose config tag families disagree")

    layout_floor = {
        int(item["id"]) for item in layout.get("floor", {}).get("tags", [])
    }
    map_floor = {int(item["id"]) for item in floor_map.get("tags", [])}
    active_floor = {int(value) for value in floor_map.get("active_anchor_ids", [])}
    if not map_floor or map_floor != layout_floor or active_floor != map_floor:
        raise MotionEvidenceError(
            "layout floor tags and floor-map active anchors do not match"
        )

    layout_robot = {int(item["id"]) for item in layout.get("robot_tags", [])}
    configured_robot = {
        int(value) for value in config.get("robot_pose", {}).get("tags", {})
    }
    if not configured_robot or not configured_robot.issubset(layout_robot):
        raise MotionEvidenceError(
            "pose config robot tags are not contained in the layout snapshot"
        )
    configured_body = config.get("robot_pose", {}).get("tags", {}).get("0", {})
    layout_body = next(
        (
            item for item in layout.get("robot_tags", [])
            if int(item.get("id", -1)) == 0
        ),
        {},
    )
    if (configured_body.get("frame") != "body"
            or layout_body.get("frame") != "body"):
        raise MotionEvidenceError(
            "pose config and layout snapshot must identify tag 0 as chassis body"
        )
    configured_yaw = _number(
        configured_body.get("frame_from_tag", {}).get("euler_xyz_deg", [
            None, None, None,
        ])[2]
    )
    layout_yaw = _number(
        layout_body.get("frame_from_tag", {}).get("euler_xyz_deg", [
            None, None, None,
        ])[2]
    )
    if (configured_yaw is None or layout_yaw is None
            or not math.isclose(configured_yaw, layout_yaw, abs_tol=1e-9)):
        raise MotionEvidenceError(
            "pose config and layout snapshot disagree on chassis-tag yaw"
        )

    map_size = _number(floor_map.get("tag_black_square_size"))
    layout_size = _number(
        layout.get("tag_geometry", {}).get("black_square_m")
    )
    if map_size is None or layout_size is None:
        raise MotionEvidenceError("layout is missing AprilTag black-square size")
    if not math.isclose(map_size / 1000.0, layout_size, abs_tol=1e-9):
        raise MotionEvidenceError("layout and floor-map marker sizes disagree")

    return {
        "robot_id": layout["robot_id"],
        "captured": layout.get("captured"),
        "vision_context_path": str(vision_context_path),
        "vision_context_sha256": _sha256(vision_context_path),
        "experiment_id": context.get("experiment_id"),
        "tag_layout_revision": revision,
        "layout_path": str(layout_path),
        "layout_sha256": _sha256(layout_path),
        "pose_config_path": str(config_path),
        "pose_config_sha256": _sha256(config_path),
        "floor_map_path": str(floor_map_path),
        "floor_map_sha256": _sha256(floor_map_path),
        "floor_tag_ids": sorted(map_floor),
        "robot_tag_ids": sorted(layout_robot),
    }


def _validate_calibration_record(
    path: Path,
    *,
    calibration_id: str,
    config: dict[str, Any],
    tag_layout_revision_id: str,
    robot_id: str,
    layout_sha256: str,
    layout_pose_config_sha256: str,
    floor_map_sha256: str,
    vision_revision: dict[str, Any],
) -> dict[str, Any]:
    """Validate explicitly selected, content-addressed Lab archive evidence.

    Robot Lab's calibration endpoint is deliberately archival-only: a genuine
    export always says ``current=false`` and ``replay_ready=false``.  Offline
    metric analysis may nevertheless select one exact record explicitly when
    its embedded pose configuration and historical layout snapshot match all
    caller-supplied replay inputs byte-for-byte.
    """
    record = _json_object(path, label="calibration record")
    if record.get("id") != calibration_id:
        raise MotionEvidenceError(
            "calibration ID does not match calibration record"
        )
    request_hash = record.get("request_sha256")
    if (not isinstance(request_hash, str)
            or re.fullmatch(r"[0-9a-f]{64}", request_hash) is None
            or record.get("id") != f"cal-{request_hash}"):
        raise MotionEvidenceError(
            "calibration record ID is not bound to its request digest"
        )
    if (record.get("status") != "archived"
            or record.get("current") is not False
            or record.get("replay_ready") is not False
            or record.get("replay_status") != "archived_not_activated"):
        raise MotionEvidenceError(
            "calibration record is not a complete archival Robot Lab record"
        )
    sequence = record.get("sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise MotionEvidenceError("calibration record has no valid archive sequence")
    if not isinstance(record.get("created_by"), str) or not record["created_by"].strip():
        raise MotionEvidenceError("calibration record has no archive creator")
    _unix_timestamp(record.get("created_at"), label="calibration created_at")
    if record.get("robot_id") != robot_id:
        raise MotionEvidenceError(
            "calibration record and layout robot IDs disagree"
        )
    calibration_revision = record.get("tag_layout_revision")
    if (not isinstance(calibration_revision, dict)
            or calibration_revision.get("id") != tag_layout_revision_id):
        raise MotionEvidenceError(
            "calibration record is not bound to the selected tag-layout revision"
        )
    expected_snapshot_hashes = {
        "layout_sha256": layout_sha256,
        "pose_config_sha256": layout_pose_config_sha256,
        "floor_map_sha256": floor_map_sha256,
    }
    for field, expected in expected_snapshot_hashes.items():
        if calibration_revision.get(field) != expected:
            raise MotionEvidenceError(
                "calibration record tag-layout snapshot does not match the "
                f"selected {field.removesuffix('_sha256').replace('_', ' ')} bytes"
            )
    for field in (
        "revision_number", "robot_id", "effective_from", "observed_at",
        "source_kind",
    ):
        selected = vision_revision.get(field)
        archived = calibration_revision.get(field)
        if selected is not None and archived is not None and selected != archived:
            raise MotionEvidenceError(
                f"calibration record and vision context disagree on {field}"
            )
    report = record.get("report")
    pose_config = record.get("pose_config")
    if not isinstance(report, dict) or not isinstance(pose_config, dict):
        raise MotionEvidenceError(
            "calibration record needs its exact report and pose config"
        )
    if record.get("report_sha256") != _canonical_json_sha256(report):
        raise MotionEvidenceError("calibration report digest does not match")
    pose_hash = _canonical_json_sha256(pose_config)
    if record.get("pose_config_sha256") != pose_hash:
        raise MotionEvidenceError("calibration pose-config digest does not match")
    if pose_hash != _canonical_json_sha256(config):
        raise MotionEvidenceError(
            "calibration pose config is not the pose config used for analysis"
        )
    if report.get("kind") != record.get("kind"):
        raise MotionEvidenceError("calibration kind does not match its report")
    if report.get("schema_version") != record.get("schema_version"):
        raise MotionEvidenceError(
            "calibration schema version does not match its report"
        )

    request_document = {
        "observed_at": record.get("observed_at"),
        "pose_config": pose_config,
        "report": report,
        "robot_id": record.get("robot_id"),
    }
    source_metadata = record.get("source_metadata")
    if not isinstance(source_metadata, dict):
        raise MotionEvidenceError(
            "calibration record source metadata must be an object"
        )
    if source_metadata:
        request_document["source_metadata"] = source_metadata
    candidates = [request_document]
    if report.get("robot_id") is None and record.get("robot_id") == robot_id:
        derived = dict(request_document)
        derived["robot_id"] = None
        candidates.append(derived)
    if not any(
        _canonical_json_sha256(candidate) == request_hash
        for candidate in candidates
    ):
        raise MotionEvidenceError(
            "calibration request digest does not match its archived documents"
        )
    return {
        "calibration_record_path": str(path),
        "calibration_record_sha256": _sha256(path),
        "calibration_request_sha256": request_hash,
        "calibration_report_sha256": record["report_sha256"],
        "calibration_pose_config_sha256": pose_hash,
        "calibration_selection": "explicit_content_addressed_archive",
        "calibration_archive_sequence": sequence,
        "calibration_archive_status": "archived",
        "calibration_current": False,
        "calibration_replay_ready": False,
        "calibration_replay_status": record.get("replay_status"),
    }


def _pose_frame_number(
    pose: dict[str, Any], *, raw_fps: float | None
) -> float:
    frame = _number(pose.get("frame_index"))
    if frame is not None:
        return frame
    time_s = _number(pose.get("time_s"))
    if time_s is None:
        raise MotionEvidenceError(
            "pose row has neither finite frame_index nor time_s"
        )
    if raw_fps is None:
        raise MotionEvidenceError("video frame rate is required for time_s poses")
    return time_s * raw_fps


def _pose_observations(
    pose_jsonl: Path,
    *,
    timestamps: dict[str, Any],
    raw_fps: float | None,
    floor_corners: dict[int, np.ndarray],
    robot_ids: set[int],
    mount_yaw_deg: float,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    observations: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    floor_ids = set(floor_corners)
    source_frame = timestamps["frames"]
    source_unix = timestamps["unix"]
    frame_to_unix = timestamps["frame_to_unix"]
    duplicate_frames = timestamps["duplicate_frames"]
    try:
        stream = pose_jsonl.open()
    except OSError as exc:
        raise MotionEvidenceError(f"could not read pose JSONL: {pose_jsonl}") from exc
    with stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            counts["pose_rows"] += 1
            try:
                pose = json.loads(line)
            except json.JSONDecodeError as exc:
                raise MotionEvidenceError(
                    f"invalid pose JSON on line {line_number}"
                ) from exc
            detections = {
                int(item["tag_id"]): item
                for item in pose.get("detections", [])
                if item.get("source") == "detected"
            }
            if 0 not in detections:
                counts["missing_body_tag_0"] += 1
                continue
            direct_robot = len(robot_ids.intersection(detections))
            if direct_robot < MIN_DIRECT_ROBOT_TAGS:
                counts["fewer_than_6_robot_tags"] += 1
                continue
            visible_floor = len(floor_ids.intersection(detections))
            if visible_floor < MIN_DIRECT_FLOOR_TAGS:
                counts["fewer_than_2_floor_tags"] += 1
                continue
            fit = _best_floor_homography(detections, floor_corners)
            if fit is None:
                counts["floor_homography_rejected"] += 1
                continue
            homography, selected_floor, floor_rms_m = fit
            body = detections[0]
            body_center = np.asarray(
                body["center_px"], dtype=np.float32
            ).reshape(1, 1, 2)
            body_floor_xy = cv2.perspectiveTransform(
                body_center, homography
            ).reshape(2)
            yaw_deg = _body_yaw_deg(
                np.asarray(body["corners_px"], dtype=np.float32),
                homography,
                mount_yaw_deg,
            )
            measured = [*body_floor_xy.tolist(), yaw_deg, floor_rms_m]
            if not all(math.isfinite(float(value)) for value in measured):
                counts["nonfinite_pose_measurement"] += 1
                continue
            direct_frame = _number(pose.get("frame_index"))
            if direct_frame is not None:
                rounded_frame = int(round(direct_frame))
                if not math.isclose(direct_frame, rounded_frame, abs_tol=1e-9):
                    raise MotionEvidenceError(
                        "pose frame_index must be an integer source frame"
                    )
                frame = float(rounded_frame)
                if rounded_frame in duplicate_frames:
                    counts["duplicate_capture_pose_rows_dropped"] += 1
                    continue
                if frame not in frame_to_unix:
                    counts["frame_outside_timestamp_range"] += 1
                    continue
                unix_s = float(frame_to_unix[frame])
            else:
                if duplicate_frames:
                    raise MotionEvidenceError(
                        "time_s-only poses cannot safely align a recording with "
                        "duplicate capture timestamps"
                    )
                frame = _pose_frame_number(pose, raw_fps=raw_fps)
                if frame < source_frame[0] or frame > source_frame[-1]:
                    counts["frame_outside_timestamp_range"] += 1
                    continue
                unix_s = float(np.interp(frame, source_frame, source_unix))
            observations.append({
                "frame": frame,
                "unix_s": unix_s,
                "x": float(body_floor_xy[0]),
                "y": float(body_floor_xy[1]),
                "yaw_deg": float(yaw_deg),
                "direct_robot_tags": direct_robot,
                "visible_floor_tags": visible_floor,
                "selected_floor_tags": len(selected_floor),
                "selected_floor_tag_ids": list(selected_floor),
                "floor_rms_m": float(floor_rms_m),
            })
            counts["usable_pose_rows"] += 1
    observations.sort(key=lambda item: item["unix_s"])
    if any(
        second["unix_s"] <= first["unix_s"]
        for first, second in zip(observations, observations[1:])
    ):
        raise MotionEvidenceError("usable pose timestamps do not advance strictly")
    return observations, dict(counts)


def _body_yaw_deg(
    corners_px: np.ndarray,
    homography: np.ndarray,
    mount_yaw_deg: float,
) -> float:
    center = corners_px.mean(axis=0)
    tag_x = (
        corners_px[1] + corners_px[2]
        - corners_px[0] - corners_px[3]
    ) / 2.0
    tag_y = (
        corners_px[0] + corners_px[1]
        - corners_px[2] - corners_px[3]
    ) / 2.0
    mount = math.radians(mount_yaw_deg)
    body_x = math.cos(mount) * tag_x - math.sin(mount) * tag_y
    projected = cv2.perspectiveTransform(
        np.asarray([center, center + body_x], dtype=np.float32).reshape(1, 2, 2),
        homography,
    )[0]
    vector = projected[1] - projected[0]
    return math.degrees(math.atan2(float(vector[1]), float(vector[0])))


def _phase_supported(phase: str) -> bool:
    return bool(
        _LEGACY_PHASE.fullmatch(phase) or _DRIVE_PHASE.fullmatch(phase)
    )


def _requested_phase_matches(requested: str | None, phase: str) -> bool:
    if requested is None:
        return True
    return requested == phase or f"drive_{requested}" == phase


def _trace_interval(trace: Path) -> dict[str, Any]:
    rows = _csv(trace)
    if len(rows) < 2:
        raise MotionEvidenceError(f"raw trace needs at least two rows: {trace}")
    clock = next((
        key for key in ("mono_s", "wall_elapsed_s", "unix_s")
        if all(_number(row.get(key)) is not None for row in rows)
    ), None)
    if clock is None:
        raise MotionEvidenceError(
            f"raw trace lacks a complete mono_s, wall_elapsed_s, or unix_s clock: {trace}"
        )
    if not all(_number(row.get("unix_s")) is not None for row in rows):
        raise MotionEvidenceError(
            f"raw trace needs unix_s to align camera frames: {trace}"
        )
    flag = next((
        key for key in ("walk_engaged", "learned_policy_active")
        if all(row.get(key) not in (None, "") for row in rows)
    ), None)
    if flag is None:
        raise MotionEvidenceError(
            f"raw trace lacks an explicit engagement flag: {trace}"
        )
    engaged = [index for index, row in enumerate(rows) if _truthy(row[flag])]
    if len(engaged) < 2:
        raise MotionEvidenceError(
            f"raw trace has fewer than two explicitly engaged rows: {trace}"
        )
    first, last = engaged[0], engaged[-1]
    if any(not _truthy(rows[index][flag]) for index in range(first, last + 1)):
        raise MotionEvidenceError(
            f"raw trace engagement is interrupted; split attempts first: {trace}"
        )

    trace_unix = np.asarray([float(row["unix_s"]) for row in rows], dtype=float)
    trace_clock = np.asarray([float(row[clock]) for row in rows], dtype=float)
    if np.any(np.diff(trace_unix) <= 0.0) or np.any(np.diff(trace_clock) <= 0.0):
        raise MotionEvidenceError(
            f"raw trace unix_s and {clock} must advance strictly: {trace}"
        )
    return {
        "path": trace,
        "clock": clock,
        "engagement_flag": flag,
        "start_unix_s": float(trace_unix[first]),
        "end_unix_s": float(trace_unix[last]),
        "start_clock": float(trace_clock[first]),
        "end_clock": float(trace_clock[last]),
        "trace_unix": trace_unix,
        "trace_clock": trace_clock,
    }


def _run_rl_bindings(
    run_dir: Path,
    *,
    requested_phase: str | None,
    trace_override: Path | None,
) -> list[dict[str, Any]]:
    summary_path = run_dir / "summary.json"
    if not summary_path.is_file():
        return []
    try:
        summary = json.loads(summary_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise MotionEvidenceError(f"could not read walk summary: {summary_path}") from exc
    raw_results = summary.get("results")
    if not isinstance(raw_results, list):
        return []
    candidates: list[tuple[str, dict[str, Any], list[Path]]] = []
    for entry in raw_results:
        if not isinstance(entry, dict) or not isinstance(entry.get("phase"), str):
            continue
        raw_phase = entry["phase"]
        phase = raw_phase if raw_phase.startswith("drive_") else f"drive_{raw_phase}"
        if not _phase_supported(phase) or not _requested_phase_matches(
            requested_phase, phase
        ):
            continue
        traces = [
            run_dir / name for name in entry.get("robot_logs", [])
            if isinstance(name, str)
            and name.endswith(".csv")
            and "debug" not in name
            and "summary" not in name
        ]
        candidates.append((phase, entry, traces))
    if not candidates:
        return []
    if trace_override is not None and len(candidates) != 1:
        raise MotionEvidenceError(
            "--trace requires exactly one selected run_rl_walk_trial phase"
        )

    bindings: list[dict[str, Any]] = []
    for phase, entry, traces in candidates:
        if trace_override is not None:
            trace = trace_override
        else:
            existing = list(dict.fromkeys(path for path in traces if path.is_file()))
            if len(existing) != 1:
                raise MotionEvidenceError(
                    f"{phase} needs exactly one raw robot CSV; found {len(existing)}"
                )
            trace = existing[0]
        interval = _trace_interval(trace)
        bindings.append({
            "phase": phase,
            "request": dict(entry.get("request") or {}),
            "interval": interval,
        })
    return bindings


def _bracketed_observations(
    observations: list[dict[str, Any]],
    *,
    start_unix_s: float,
    end_unix_s: float,
    max_endpoint_age_s: float = MAX_ENDPOINT_BRACKET_AGE_S,
    max_gap_s: float = MAX_INTERIOR_COVERAGE_GAP_S,
) -> list[dict[str, Any]]:
    if (not math.isfinite(start_unix_s) or not math.isfinite(end_unix_s)
            or end_unix_s <= start_unix_s):
        raise MotionEvidenceError("engagement interval is invalid")
    before = [item for item in observations if item["unix_s"] <= start_unix_s]
    after = [item for item in observations if item["unix_s"] >= end_unix_s]
    if not before:
        raise MotionEvidenceError(
            "no coverage-qualified camera pose at or before engagement start"
        )
    if not after:
        raise MotionEvidenceError(
            "no coverage-qualified camera pose at or after engagement end"
        )
    start = before[-1]
    end = after[0]
    start_age_s = start_unix_s - start["unix_s"]
    end_age_s = end["unix_s"] - end_unix_s
    if start_age_s > max_endpoint_age_s:
        raise MotionEvidenceError(
            "coverage-qualified pose before engagement start is too old: "
            f"{start_age_s:.3f} s"
        )
    if end_age_s > max_endpoint_age_s:
        raise MotionEvidenceError(
            "coverage-qualified pose after engagement end is too late: "
            f"{end_age_s:.3f} s"
        )
    selected = [
        item for item in observations
        if start["unix_s"] <= item["unix_s"] <= end["unix_s"]
    ]
    if len(selected) < 2:
        raise MotionEvidenceError(
            "fewer than two coverage-qualified poses bracket engagement"
        )
    gaps = [
        second["unix_s"] - first["unix_s"]
        for first, second in zip(selected, selected[1:])
    ]
    if gaps and max(gaps) > max_gap_s:
        raise MotionEvidenceError(
            "coverage-qualified camera poses have an interior gap of "
            f"{max(gaps):.3f} s (limit {max_gap_s:.3f} s)"
        )
    return selected


def _clock_at_unix(unix_s: float, interval: dict[str, Any]) -> float:
    source = interval["trace_unix"]
    target = interval["trace_clock"]
    if unix_s < source[0]:
        slope = (target[1] - target[0]) / (source[1] - source[0])
        return float(target[0] + slope * (unix_s - source[0]))
    if unix_s > source[-1]:
        slope = (target[-1] - target[-2]) / (source[-1] - source[-2])
        return float(target[-1] + slope * (unix_s - source[-1]))
    return float(np.interp(unix_s, source, target))


def _phase_rows_from_observations(
    observations: list[dict[str, Any]],
) -> list[list[float]]:
    return [[
        item["unix_s"], item["x"], item["y"], item["yaw_deg"],
        item["direct_robot_tags"], item["visible_floor_tags"],
        item["selected_floor_tags"], item["floor_rms_m"],
    ] for item in observations]


def _legacy_groups(
    run_dir: Path,
    observations: list[dict[str, Any]],
    *,
    requested_phase: str | None,
) -> dict[str, list[list[float]]]:
    telemetry = _csv(run_dir / "telemetry.csv")
    if not telemetry:
        return {}
    time_key = next((
        key for key in ("receipt_unix_s", "unix_s")
        if all(_number(row.get(key)) is not None for row in telemetry)
    ), None)
    if time_key is None:
        raise MotionEvidenceError(
            "telemetry needs a complete receipt_unix_s or unix_s column"
        )
    telemetry_unix = np.asarray(
        [float(row[time_key]) for row in telemetry], dtype=float
    )
    groups: dict[str, list[list[float]]] = defaultdict(list)
    for item in observations:
        index = int(np.argmin(np.abs(telemetry_unix - item["unix_s"])))
        if abs(float(telemetry_unix[index]) - item["unix_s"]) > 0.6:
            continue
        phase = telemetry[index].get("phase", "")
        if not _phase_supported(phase) or not _requested_phase_matches(
            requested_phase, phase
        ):
            continue
        groups[phase].extend(_phase_rows_from_observations([item]))
    return groups


def _reference_axis(
    phases: dict[str, dict[str, Any]],
) -> tuple[np.ndarray | None, int | None]:
    candidates = [0, 9, 14]
    candidates.extend(sorted({
        int(match.group(1))
        for phase in phases
        if (match := _LEGACY_PHASE.fullmatch(phase)) is not None
    }))
    for gait in dict.fromkeys(candidates):
        forward = phases.get(f"gait_{gait}_forward")
        backward = phases.get(f"gait_{gait}_backward")
        if forward is None or backward is None:
            continue
        candidate = (
            np.asarray(forward["floor_projected_body_delta_xy_m"])
            - np.asarray(backward["floor_projected_body_delta_xy_m"])
        )
        norm = float(np.linalg.norm(candidate))
        if norm > 1e-6:
            return candidate / norm, gait
    return None, None


def _summarize_phases(
    groups: dict[str, list[list[float]]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], int | None,
           np.ndarray | None]:
    phases: dict[str, dict[str, Any]] = {}
    for phase, values in sorted(groups.items()):
        array = np.asarray(values, dtype=float)
        if len(array) < 2:
            continue
        edge = max(2, round(len(array) * 0.15))
        edge = min(edge, len(array))
        start = np.median(array[:edge, 1:3], axis=0)
        end = np.median(array[-edge:, 1:3], axis=0)
        start_t = float(np.median(array[:edge, 0]))
        end_t = float(np.median(array[-edge:, 0]))
        duration_s = max(0.0, end_t - start_t)
        delta = end - start
        yaw_unwrapped = np.degrees(np.unwrap(np.radians(array[:, 3])))
        yaw_delta = float(
            np.median(yaw_unwrapped[-edge:])
            - np.median(yaw_unwrapped[:edge])
        )
        phases[phase] = {
            "usable_vision_frames": len(array),
            "measured_duration_s": round(duration_s, 4),
            "floor_projected_body_delta_xy_m": np.round(delta, 5).tolist(),
            "horizontal_distance_m": round(float(np.linalg.norm(delta)), 5),
            "yaw_delta_deg": round(yaw_delta, 3),
            "mean_direct_robot_tags": round(float(np.mean(array[:, 4])), 2),
            "mean_visible_mapped_floor_tags": round(
                float(np.mean(array[:, 5])), 2
            ),
            "mean_floor_tags_used": round(float(np.mean(array[:, 6])), 2),
            "median_floor_homography_rms_mm": round(
                float(np.median(array[:, 7])) * 1000.0, 3
            ),
        }

    reference, reference_gait = _reference_axis(phases)
    if reference is not None:
        lateral_axis = np.asarray([-reference[1], reference[0]])
        for phase, record in phases.items():
            delta = np.asarray(record["floor_projected_body_delta_xy_m"])
            progress = float(np.dot(delta, reference))
            lateral = float(np.dot(delta, lateral_axis))
            duration_s = float(record["measured_duration_s"])
            sign = -1.0 if phase.endswith("_backward") else 1.0
            record["baseline_axis_progress_m"] = round(progress, 5)
            record["baseline_axis_lateral_m"] = round(lateral, 5)
            record["commanded_axis_speed_mm_s"] = (
                None if duration_s <= 0.0
                else round(sign * progress / duration_s * 1000.0, 3)
            )

    by_gait: dict[str, dict[str, Any]] = {}
    gait_ids = sorted({
        int(match.group(1))
        for phase in phases
        if (match := _LEGACY_PHASE.fullmatch(phase)) is not None
    })
    for gait in gait_ids:
        pair = [
            phases.get(f"gait_{gait}_forward"),
            phases.get(f"gait_{gait}_backward"),
        ]
        clean = [item for item in pair if item is not None]
        speeds = [
            float(item["commanded_axis_speed_mm_s"])
            for item in clean
            if item.get("commanded_axis_speed_mm_s") is not None
        ]
        by_gait[str(gait)] = {
            "two_direction_mean_speed_mm_s": (
                None if not speeds else round(float(np.mean(speeds)), 3)
            ),
            "mean_abs_lateral_drift_mm": round(float(np.mean([
                abs(float(item.get("baseline_axis_lateral_m", 0.0))) * 1000.0
                for item in clean
            ])), 3) if clean else None,
            "mean_abs_yaw_deg": round(float(np.mean([
                abs(float(item["yaw_delta_deg"])) for item in clean
            ])), 3) if clean else None,
        }
    return phases, by_gait, reference_gait, reference


def _calibrated_motion(
    binding: dict[str, Any],
    observations: list[dict[str, Any]],
    *,
    calibration_id: str,
    tag_layout_revision_id: str,
    provenance: dict[str, Any],
    pose_jsonl: Path,
    timestamps: Path,
    video: Path,
    video_metadata: dict[str, Any],
) -> dict[str, Any]:
    calibration_id = calibration_id.strip()
    tag_layout_revision_id = tag_layout_revision_id.strip()
    if not calibration_id:
        raise MotionEvidenceError("--calibration-id is required for metric evidence")
    if not tag_layout_revision_id:
        raise MotionEvidenceError(
            "--tag-layout-revision-id is required for metric evidence"
        )
    if not observations:
        raise MotionEvidenceError(
            "no usable poses: each emitted sample requires direct tag 0, at "
            f"least {MIN_DIRECT_ROBOT_TAGS} robot tags, and at least "
            f"{MIN_DIRECT_FLOOR_TAGS} context-bound floor anchors"
        )

    interval = binding["interval"]
    selected = _bracketed_observations(
        observations,
        start_unix_s=interval["start_unix_s"],
        end_unix_s=interval["end_unix_s"],
    )
    samples = [{
        "t": round(_clock_at_unix(item["unix_s"], interval), 9),
        "x": round(float(item["x"]), 8),
        "y": round(float(item["y"]), 8),
        "yaw_deg": round(float(item["yaw_deg"]), 6),
        "source_frame": int(round(item["frame"])),
        "source_unix_s": round(float(item["unix_s"]), 9),
        "direct_robot_tags": int(item["direct_robot_tags"]),
        "mapped_floor_tags": int(item["visible_floor_tags"]),
        "floor_tags_used": list(item["selected_floor_tag_ids"]),
        "floor_homography_rms_mm": round(float(item["floor_rms_m"]) * 1000, 4),
    } for item in selected]
    if any(
        second["t"] <= first["t"] for first, second in zip(samples, samples[1:])
    ):
        raise MotionEvidenceError("calibrated sample clock does not advance strictly")
    if samples[0]["t"] > interval["start_clock"] + 1e-6:
        raise MotionEvidenceError("calibrated poses do not cover engagement start")
    if samples[-1]["t"] < interval["end_clock"] - 1e-6:
        raise MotionEvidenceError("calibrated poses do not cover engagement end")

    trace = interval["path"]
    return {
        "schema": "hexapod.calibrated_motion.v1",
        "calibration_status": "validated",
        "calibration_id": calibration_id,
        "tag_layout_revision_id": tag_layout_revision_id,
        "frame": "floor",
        "units": "m",
        "trace_sha256": _sha256(trace),
        "clock": interval["clock"],
        "phase": binding["phase"],
        "samples": samples,
        "coverage_gate": {
            "body_tag_id": 0,
            "minimum_direct_robot_tags": MIN_DIRECT_ROBOT_TAGS,
            "minimum_direct_floor_tags": MIN_DIRECT_FLOOR_TAGS,
            "maximum_endpoint_bracket_age_s": MAX_ENDPOINT_BRACKET_AGE_S,
            "maximum_interior_gap_s": MAX_INTERIOR_COVERAGE_GAP_S,
            "all_samples_passed": True,
        },
        "engagement": {
            "flag": interval["engagement_flag"],
            "start": interval["start_clock"],
            "end": interval["end_clock"],
            "start_unix_s": interval["start_unix_s"],
            "end_unix_s": interval["end_unix_s"],
        },
        "provenance": {
            **provenance,
            "trace_path": str(trace),
            "pose_jsonl_path": str(pose_jsonl),
            "pose_jsonl_sha256": _sha256(pose_jsonl),
            "camera_timestamps_path": str(timestamps),
            "camera_timestamps_sha256": _sha256(timestamps),
            "camera_video_path": str(video),
            "camera_video_sha256": video_metadata["sha256"],
            "camera_video_frames": video_metadata["frames"],
            "camera_video_fps": video_metadata["fps"],
            "camera_video_size_px": [
                video_metadata["width"], video_metadata["height"],
            ],
        },
        "limitations": [
            "The chassis tag is above the floor, so oblique-view parallax makes absolute distance provisional.",
            "Floor-grid uncertainty remains whatever is recorded in the bound historical floor-map snapshot.",
            "This offline producer verifies an explicitly selected, content-addressed Robot Lab calibration archive; it does not claim that the record is current or automatically replay-ready and does not mutate Robot Lab.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Measure floor-referenced AprilTag motion and optionally emit a "
            "trace-bound calibrated-motion artifact."
        )
    )
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--pose-jsonl", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--floor-map", type=Path,
        help=(
            "measured floor-map snapshot; omission preserves legacy report-only "
            "behavior by using floor_tags from --config, but calibrated emission "
            "requires this exact Robot Lab snapshot"
        ),
    )
    parser.add_argument(
        "--layout", type=Path,
        help=(
            "physical tag-layout snapshot; optional for legacy reports and "
            "required for calibrated emission"
        ),
    )
    parser.add_argument(
        "--vision-context", type=Path,
        help=(
            "Robot Lab vision-context.json binding --layout, --config, and "
            "--floor-map to the effective revision; required for calibrated emission"
        ),
    )
    parser.add_argument(
        "--phase",
        help="optional gait_N_direction, drive_direction, or direction selector",
    )
    parser.add_argument(
        "--trace", type=Path,
        help="explicit raw robot CSV for one selected run_rl_walk_trial phase",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--calibrated-motion-output", type=Path,
        help=(
            "emit hexapod.calibrated_motion.v1 here after coverage and clock "
            "validation"
        ),
    )
    parser.add_argument(
        "--calibration-id",
        help="reviewed calibration record ID for calibrated-motion provenance",
    )
    parser.add_argument(
        "--calibration-record", type=Path,
        help=(
            "exact Robot Lab calibration-record JSON including its report, pose "
            "config, content digests, and historical layout snapshot; genuine "
            "records remain archival/current=false/replay_ready=false and must "
            "be selected explicitly with --calibration-id"
        ),
    )
    parser.add_argument(
        "--tag-layout-revision-id",
        help="active Robot Lab tag-layout revision at recording time",
    )
    args = parser.parse_args()
    if args.calibrated_motion_output is not None:
        # Parsing has established that this is genuinely the requested output,
        # but remove old evidence before any remaining validation can reject.
        args.calibrated_motion_output.unlink(missing_ok=True)
        required = {
            "--calibration-id": args.calibration_id,
            "--calibration-record": args.calibration_record,
            "--tag-layout-revision-id": args.tag_layout_revision_id,
            "--vision-context": args.vision_context,
            "--layout": args.layout,
            "--floor-map": args.floor_map,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            parser.error(
                f"{', '.join(missing)} required with --calibrated-motion-output"
            )

    try:
        video, timestamps, recording_source = _recording_paths(args.run_dir)
        timestamp_info = _timestamp_arrays(timestamps)
        video_metadata = _video_metadata(
            video, timestamp_rows=timestamp_info["row_count"]
        )
        config = _json_object(args.config, label="pose config")
        specs, marker_size_m = _floor_specs(config, args.floor_map)
        floor_corners = _floor_corners(specs, marker_size_m)
        if args.layout is not None:
            layout = _json_object(args.layout, label="AprilTag layout")
            robot_ids = {
                int(item["id"]) for item in layout.get("robot_tags", [])
            }
            body_layout = next(
                item for item in layout.get("robot_tags", [])
                if int(item.get("id", -1)) == 0
            )
            mount_yaw_deg = float(
                body_layout["frame_from_tag"]["euler_xyz_deg"][2]
            )
        else:
            robot_tags = config.get("robot_pose", {}).get("tags", {})
            robot_ids = {int(value) for value in robot_tags}
            mount_yaw_deg = float(
                robot_tags["0"]["frame_from_tag"]["euler_xyz_deg"][2]
            )

        # Modern tracker output records the source frame directly.  Read the
        # container frame rate only for older JSONL files that provide time_s.
        needs_fps = False
        with args.pose_jsonl.open() as stream:
            for line in stream:
                if line.strip() and json.loads(line).get("frame_index") is None:
                    needs_fps = True
                    break
        raw_fps = video_metadata["fps"] if needs_fps else None
        observations, coverage = _pose_observations(
            args.pose_jsonl,
            timestamps=timestamp_info,
            raw_fps=raw_fps,
            floor_corners=floor_corners,
            robot_ids=robot_ids,
            mount_yaw_deg=mount_yaw_deg,
        )
        bindings = _run_rl_bindings(
            args.run_dir,
            requested_phase=args.phase,
            trace_override=args.trace,
        )
        if bindings:
            groups = {}
            for binding in bindings:
                try:
                    bracketed = _bracketed_observations(
                        observations,
                        start_unix_s=binding["interval"]["start_unix_s"],
                        end_unix_s=binding["interval"]["end_unix_s"],
                    )
                except MotionEvidenceError:
                    bracketed = []
                groups[binding["phase"]] = _phase_rows_from_observations(
                    bracketed
                )
        else:
            groups = _legacy_groups(
                args.run_dir, observations, requested_phase=args.phase
            )
        phases, by_gait, reference_gait, reference = _summarize_phases(groups)

        report: dict[str, Any] = {
            "ok": True,
            "visual_knees_used": False,
            "measurement": (
                "planar homography from 2+ mapped floor tags to chassis tag "
                "center and orientation"
            ),
            "scale_caution": (
                "relative motion is robust to camera movement; chassis height "
                "above the floor leaves small oblique-view parallax"
            ),
            "time_alignment": (
                f"raw frame index -> {timestamps.name}:{timestamp_info['clock']}"
            ),
            "camera_timestamp_duplicates_collapsed": (
                timestamp_info["duplicates_collapsed"]
            ),
            "recording_source": recording_source,
            "camera_video": str(video),
            "camera_timestamps": str(timestamps),
            "floor_map": None if args.floor_map is None else str(args.floor_map),
            "layout": None if args.layout is None else str(args.layout),
            "coverage_gate": {
                "body_tag_id": 0,
                "minimum_direct_robot_tags": MIN_DIRECT_ROBOT_TAGS,
                "minimum_direct_floor_tags": MIN_DIRECT_FLOOR_TAGS,
                "counts": coverage,
            },
            "baseline_forward_axis_source_gait": reference_gait,
            "baseline_forward_axis_world_xy": (
                None if reference is None else np.round(reference, 6).tolist()
            ),
            "phases": phases,
            "by_gait": by_gait,
        }

        motion = None
        motion_error = None
        if args.calibrated_motion_output is not None:
            try:
                if len(bindings) != 1:
                    raise MotionEvidenceError(
                        "calibrated motion needs exactly one selected "
                        "run_rl_walk_trial phase; use --phase"
                    )
                provenance = _validate_layout_context(
                    config,
                    config_path=args.config,
                    floor_map_path=args.floor_map,
                    layout_path=args.layout,
                    vision_context_path=args.vision_context,
                    tag_layout_revision_id=args.tag_layout_revision_id,
                    interval=bindings[0]["interval"],
                )
                provenance.update(_validate_calibration_record(
                    args.calibration_record,
                    calibration_id=args.calibration_id,
                    config=config,
                    tag_layout_revision_id=args.tag_layout_revision_id,
                    robot_id=provenance["robot_id"],
                    layout_sha256=provenance["layout_sha256"],
                    layout_pose_config_sha256=provenance["pose_config_sha256"],
                    floor_map_sha256=provenance["floor_map_sha256"],
                    vision_revision=provenance["tag_layout_revision"],
                ))
                provenance.update({
                    "camera_timestamp_clock": timestamp_info["clock"],
                    "duplicate_capture_frames_collapsed": (
                        timestamp_info["duplicates_collapsed"]
                    ),
                })
                motion = _calibrated_motion(
                    bindings[0], observations,
                    calibration_id=args.calibration_id,
                    tag_layout_revision_id=args.tag_layout_revision_id,
                    provenance=provenance,
                    pose_jsonl=args.pose_jsonl,
                    timestamps=timestamps,
                    video=video,
                    video_metadata=video_metadata,
                )
                report["calibrated_motion"] = {
                    "status": "emitted",
                    "path": str(args.calibrated_motion_output),
                    "trace_sha256": motion["trace_sha256"],
                    "samples": len(motion["samples"]),
                }
            except MotionEvidenceError as exc:
                motion_error = str(exc)
                report["ok"] = False
                report["calibrated_motion"] = {
                    "status": "rejected",
                    "error": motion_error,
                    "path": str(args.calibrated_motion_output),
                }
        else:
            report["calibrated_motion"] = {"status": "not_requested"}

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        if motion is not None:
            args.calibrated_motion_output.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.calibrated_motion_output.with_suffix(
                args.calibrated_motion_output.suffix + ".tmp"
            )
            temporary.write_text(json.dumps(motion, indent=2) + "\n")
            temporary.replace(args.calibrated_motion_output)
        print(json.dumps(report, indent=2))
        if motion_error is not None:
            print(f"calibrated motion rejected: {motion_error}", file=sys.stderr)
            return 2
        return 0
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        report = {"ok": False, "error": str(exc)}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
