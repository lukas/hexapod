#!/usr/bin/env python3
"""Detect AprilTags in a photo, video, or live camera and estimate pose.

The tool never connects to the robot.  It can save raw camera media, annotated
media, and per-frame JSON/JSONL pose records.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any

import cv2

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from apriltag_vision import AprilTagPoseTracker  # noqa: E402


_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}


def _write_json(path: Path | None, value: dict[str, Any]) -> None:
    rendered = json.dumps(value, indent=2) + "\n"
    if path is None:
        print(rendered, end="")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")


def _write_image(path: Path | None, image: Any) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image):
        raise OSError(f"could not write image {path}")


def _process_image(
    tracker: AprilTagPoseTracker,
    image_path: Path,
    *,
    pose_output: Path | None,
    annotated_output: Path | None,
) -> int:
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise OSError(f"could not read image {image_path}")
    result, annotated = tracker.process_frame(image)
    _write_json(pose_output, result)
    _write_image(annotated_output, annotated)
    hexapod_pose = result.get("hexapod_pose")
    return 0 if not hexapod_pose or hexapod_pose.get("ok", True) else 2


def _video_writer(path: Path, fps: float, size: tuple[int, int]) -> Any:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, size
    )
    if not writer.isOpened():
        raise OSError(f"could not open video writer {path}")
    return writer


def _process_capture(
    tracker: AprilTagPoseTracker,
    capture: Any,
    *,
    pose_output: Path | None,
    annotated_output: Path | None,
    raw_output: Path | None,
    duration_s: float | None,
    max_frames: int | None,
    camera_mode: bool,
) -> int:
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if not math_is_finite_positive(fps):
        fps = 30.0
    annotated_writer = None
    raw_writer = None
    json_handle = None
    start = time.monotonic()
    frame_index = 0
    last_result: dict[str, Any] | None = None
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index == 0:
                height, width = frame.shape[:2]
                if annotated_output is not None:
                    annotated_writer = _video_writer(
                        annotated_output, fps, (width, height)
                    )
                if raw_output is not None:
                    raw_writer = _video_writer(raw_output, fps, (width, height))
                if pose_output is not None:
                    pose_output.parent.mkdir(parents=True, exist_ok=True)
                    json_handle = pose_output.open("w", encoding="utf-8")

            if camera_mode:
                time_s = time.monotonic() - start
            else:
                time_s = float(capture.get(cv2.CAP_PROP_POS_MSEC)) / 1000.0
            result, annotated = tracker.process_frame(
                frame, frame_index=frame_index, time_s=time_s
            )
            last_result = result
            if raw_writer is not None:
                raw_writer.write(frame)
            if annotated_writer is not None:
                annotated_writer.write(annotated)
            if json_handle is not None:
                json_handle.write(json.dumps(result, separators=(",", ":")) + "\n")

            frame_index += 1
            if max_frames is not None and frame_index >= max_frames:
                break
            if duration_s is not None and time.monotonic() - start >= duration_s:
                break
    finally:
        capture.release()
        if annotated_writer is not None:
            annotated_writer.release()
        if raw_writer is not None:
            raw_writer.release()
        if json_handle is not None:
            json_handle.close()

    if frame_index == 0:
        raise OSError("capture produced no frames")
    summary = {
        "frames": frame_index,
        "pose_output": None if pose_output is None else str(pose_output),
        "annotated_output": (
            None if annotated_output is None else str(annotated_output)
        ),
        "raw_output": None if raw_output is None else str(raw_output),
        "last_detected_tag_ids": last_result["detected_tag_ids"],
    }
    print(json.dumps(summary, indent=2))
    return 0


def math_is_finite_positive(value: float) -> bool:
    return value > 0.0 and value < float("inf")


def _capture_still(
    tracker: AprilTagPoseTracker,
    camera_index: int,
    *,
    pose_output: Path | None,
    annotated_output: Path | None,
    raw_output: Path | None,
) -> int:
    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        raise OSError(f"could not open camera {camera_index}")
    try:
        # Let auto-exposure settle without sleeping or retaining stale frames.
        frame = None
        for _ in range(12):
            ok, candidate = capture.read()
            if ok:
                frame = candidate
        if frame is None:
            raise OSError(f"camera {camera_index} produced no frame")
    finally:
        capture.release()
    result, annotated = tracker.process_frame(frame)
    _write_json(pose_output, result)
    _write_image(raw_output, frame)
    _write_image(annotated_output, annotated)
    hexapod_pose = result.get("hexapod_pose")
    return 0 if not hexapod_pose or hexapod_pose.get("ok", True) else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="camera/tag-layout JSON")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="input image or video")
    source.add_argument("--camera", type=int, help="OpenCV camera index")
    parser.add_argument("--pose-output", type=Path,
                        help="JSON for an image, JSONL for video")
    parser.add_argument("--annotated-output", type=Path,
                        help="annotated image or MP4")
    parser.add_argument("--raw-output", type=Path,
                        help="save raw camera photo or MP4 (camera mode only)")
    parser.add_argument("--duration", type=float,
                        help="camera recording duration; omitted means one photo")
    parser.add_argument("--max-frames", type=int,
                        help="optional video frame limit for testing")
    args = parser.parse_args(argv)
    if args.duration is not None and args.duration <= 0.0:
        parser.error("--duration must be positive")
    if args.max_frames is not None and args.max_frames <= 0:
        parser.error("--max-frames must be positive")
    if args.input is not None and args.raw_output is not None:
        parser.error("--raw-output is only for --camera capture")

    tracker = AprilTagPoseTracker.from_json(args.config)
    if args.input is not None and args.input.suffix.lower() in _IMAGE_SUFFIXES:
        return _process_image(
            tracker,
            args.input,
            pose_output=args.pose_output,
            annotated_output=args.annotated_output,
        )
    if args.input is not None:
        capture = cv2.VideoCapture(str(args.input))
        if not capture.isOpened():
            raise OSError(f"could not open video {args.input}")
        return _process_capture(
            tracker,
            capture,
            pose_output=args.pose_output,
            annotated_output=args.annotated_output,
            raw_output=None,
            duration_s=None,
            max_frames=args.max_frames,
            camera_mode=False,
        )
    if args.duration is None:
        return _capture_still(
            tracker,
            args.camera,
            pose_output=args.pose_output,
            annotated_output=args.annotated_output,
            raw_output=args.raw_output,
        )

    capture = cv2.VideoCapture(args.camera)
    if not capture.isOpened():
        raise OSError(f"could not open camera {args.camera}")
    return _process_capture(
        tracker,
        capture,
        pose_output=args.pose_output,
        annotated_output=args.annotated_output,
        raw_output=args.raw_output,
        duration_s=args.duration,
        max_frames=args.max_frames,
        camera_mode=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
