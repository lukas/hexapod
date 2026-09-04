#!/usr/bin/env python3
"""Measure floor-referenced gait translation and yaw from AprilTag video."""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from scipy.spatial.transform import Rotation


_TRACKER_SRC = Path(__file__).resolve().parents[2] / "hexapod-tracker" / "src"
if str(_TRACKER_SRC) not in sys.path:
    sys.path.insert(0, str(_TRACKER_SRC))

from hexapod_tracker.gait_motion import _best_floor_homography  # noqa: E402


def _csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


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


def _reference_axis(
    phases: dict[str, dict[str, Any]],
) -> tuple[np.ndarray | None, int | None]:
    candidates = [0, 9, 14]
    candidates.extend(sorted({
        int(phase.split("_")[1]) for phase in phases
        if phase.startswith("gait_")
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--pose-jsonl", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--floor-map", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    telemetry = _csv(args.run_dir / "telemetry.csv")
    telemetry_unix = np.asarray([
        float(row["receipt_unix_s"]) for row in telemetry
    ])
    timestamps = _csv(args.run_dir / "iphone_raw_timestamps.csv")
    source_frame = np.asarray([float(row["frame"]) for row in timestamps])
    source_unix = np.asarray([float(row["unix_s"]) for row in timestamps])
    capture = cv2.VideoCapture(str(args.run_dir / "iphone_raw.mp4"))
    raw_fps = float(capture.get(cv2.CAP_PROP_FPS)) or 30.0
    capture.release()

    config = json.loads(args.config.read_text())
    specs, marker_size_m = _floor_specs(config, args.floor_map)
    floor_corners = _floor_corners(specs, marker_size_m)
    floor_ids = set(floor_corners)
    robot_ids = {int(value) for value in config["robot_pose"]["tags"]}
    mount_yaw_deg = float(
        config["robot_pose"]["tags"]["0"]["frame_from_tag"]
        ["euler_xyz_deg"][2]
    )

    groups: dict[str, list[list[float]]] = defaultdict(list)
    with args.pose_jsonl.open() as stream:
        for line in stream:
            pose = json.loads(line)
            detections = {
                int(item["tag_id"]): item
                for item in pose.get("detections", [])
                if item.get("source") == "detected"
            }
            if 0 not in detections:
                continue
            direct_robot_tags = len(robot_ids.intersection(detections))
            if direct_robot_tags < 6:
                continue
            fit = _best_floor_homography(detections, floor_corners)
            if fit is None:
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
            unix_s = float(np.interp(
                float(pose["time_s"]) * raw_fps, source_frame, source_unix
            ))
            index = int(np.argmin(np.abs(telemetry_unix - unix_s)))
            if abs(float(telemetry_unix[index]) - unix_s) > 0.6:
                continue
            phase = telemetry[index]["phase"]
            if not (
                phase.startswith("gait_")
                and phase.rsplit("_", 1)[-1] in {"forward", "backward"}
            ):
                continue
            groups[phase].append([
                unix_s, *body_floor_xy, yaw_deg,
                direct_robot_tags, len(floor_ids.intersection(detections)),
                len(selected_floor), floor_rms_m,
            ])

    phases: dict[str, dict[str, Any]] = {}
    for phase, values in sorted(groups.items()):
        array = np.asarray(values, dtype=float)
        edge = max(2, round(len(array) * 0.15))
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
    gait_ids = sorted({int(phase.split("_")[1]) for phase in phases})
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

    report = {
        "visual_knees_used": False,
        "measurement": (
            "planar homography from 2+ mapped floor tags to chassis tag "
            "center and orientation"
        ),
        "scale_caution": (
            "relative motion is robust to camera movement; chassis height "
            "above the floor leaves small oblique-view parallax"
        ),
        "time_alignment": "raw frame index -> iphone_raw_timestamps.csv",
        "floor_map": None if args.floor_map is None else str(args.floor_map),
        "baseline_forward_axis_source_gait": reference_gait,
        "baseline_forward_axis_world_xy": (
            None if reference is None else np.round(reference, 6).tolist()
        ),
        "phases": phases,
        "by_gait": by_gait,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
