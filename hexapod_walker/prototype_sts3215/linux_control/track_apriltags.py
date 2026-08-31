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
from urllib.error import URLError
from urllib.request import Request, urlopen

import cv2

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from apriltag_vision import AprilTagPoseTracker  # noqa: E402
from housing_pose import JOINT_NAMES  # noqa: E402


_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}


class FeedbackClient:
    """Rate-limited, read-only client for the robot's bulk feedback route."""

    def __init__(self, base_url: str, *, hz: float = 3.0, timeout_s: float = 0.6):
        self.url = base_url.rstrip("/") + "/api/feedback"
        self.minimum_interval_s = 1.0 / hz
        self.timeout_s = timeout_s
        self.last_poll = -float("inf")
        self.last_angles: dict[str, float] = {}
        self.status: dict[str, Any] = {
            "configured": True,
            "ok": False,
            "endpoint": self.url,
            "error": "not polled yet",
        }

    def sample(self) -> tuple[dict[str, float], dict[str, Any]]:
        now = time.monotonic()
        if now - self.last_poll < self.minimum_interval_s:
            return self.last_angles, self.status
        self.last_poll = now
        try:
            request = Request(self.url, headers={"Accept": "application/json"})
            with urlopen(request, timeout=self.timeout_s) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not payload.get("ok"):
                raise OSError(str(payload.get("error", "feedback not ok")))
            joints = payload.get("joints", [])
            angles = {
                name: float(item["deg"])
                for name, item in zip(JOINT_NAMES, joints)
                if isinstance(item, dict) and item.get("deg") is not None
            }
            self.last_angles = angles
            self.status = {
                "configured": True,
                "ok": True,
                "endpoint": self.url,
                "sample_time_unix": payload.get("t_unix"),
                "live_joint_count": len(angles),
                "roll_deg": payload.get("roll_deg"),
                "pitch_deg": payload.get("pitch_deg"),
            }
        except (OSError, URLError, ValueError, json.JSONDecodeError) as error:
            self.status = {
                "configured": True,
                "ok": False,
                "endpoint": self.url,
                "using_cached_joint_count": len(self.last_angles),
                "error": str(error),
            }
        return self.last_angles, self.status


class VideoDiagnosticAccumulator:
    """Compact cross-frame evidence for calibration and gait triage."""

    def __init__(self) -> None:
        self.frames = 0
        self.decoded_tags = 0
        self.foot_direct = [0] * 6
        self.foot_inferred = [0] * 6
        self.foot_speeds: list[list[float]] = [[] for _ in range(6)]
        self.disagreement_count: dict[str, int] = {}
        self.disagreement_max: dict[str, float] = {}
        self.zero_error_count: dict[str, int] = {}
        self.max_body_tilt_deg = 0.0

    def update(self, result: dict[str, Any]) -> None:
        self.frames += 1
        self.decoded_tags += len(result.get("detected_tag_ids", []))
        for foot in result.get("foot_tips", []):
            leg = int(foot["leg"])
            if foot.get("source") == "color":
                self.foot_direct[leg] += 1
            else:
                self.foot_inferred[leg] += 1
            speed = foot.get("floor_projection_speed_m_s")
            if speed is not None:
                self.foot_speeds[leg].append(float(speed))
        full = result.get("full_pose") or {}
        for item in full.get("calibration_disagreements", []):
            name = str(item["joint"])
            raw_error = item.get(
                "visual_minus_encoder_deg",
                item.get("visual_abs_minus_encoder_abs_deg", 0.0),
            )
            error = abs(float(raw_error))
            self.disagreement_count[name] = self.disagreement_count.get(name, 0) + 1
            self.disagreement_max[name] = max(
                error, self.disagreement_max.get(name, 0.0)
            )
        for item in full.get("zero_check", {}).get("out_of_tolerance", []):
            name = str(item["joint"])
            self.zero_error_count[name] = self.zero_error_count.get(name, 0) + 1
        tilt = full.get("walking_check", {}).get("body_tilt_deg")
        if tilt is not None:
            self.max_body_tilt_deg = max(self.max_body_tilt_deg, float(tilt))

    def summary(self) -> dict[str, Any]:
        frames = max(1, self.frames)
        feet = []
        for leg in range(6):
            speeds = sorted(self.foot_speeds[leg])
            percentile = None
            if speeds:
                percentile = speeds[min(len(speeds) - 1, round(0.95 * (len(speeds) - 1)))]
            feet.append({
                "leg": leg,
                "direct_visible_fraction": round(self.foot_direct[leg] / frames, 3),
                "inferred_fraction": round(self.foot_inferred[leg] / frames, 3),
                "floor_projection_speed_p95_m_s": (
                    None if percentile is None else round(percentile, 4)
                ),
            })
        persistent_disagreements = [
            {
                "joint": name,
                "frame_fraction": round(count / frames, 3),
                "max_abs_deg": round(self.disagreement_max[name], 3),
            }
            for name, count in sorted(self.disagreement_count.items())
            if count / frames >= 0.2
        ]
        persistent_zero_errors = [
            {"joint": name, "frame_fraction": round(count / frames, 3)}
            for name, count in sorted(self.zero_error_count.items())
            if count / frames >= 0.2
        ]
        return {
            "frames": self.frames,
            "mean_decoded_tags_per_frame": round(self.decoded_tags / frames, 2),
            "max_body_tilt_deg": round(self.max_body_tilt_deg, 3),
            "feet": feet,
            "persistent_visual_encoder_disagreements": persistent_disagreements,
            "persistent_zero_pose_errors": persistent_zero_errors,
            "notes": [
                "High direct-visible fractions make per-leg trajectory comparisons reliable.",
                "Floor-projection speed is a slip candidate signal, not proof of contact.",
                "Persistent visual/encoder disagreement is stronger evidence "
                "of a zero or mount problem than one frame.",
            ],
        }


def _process_one(
    tracker: AprilTagPoseTracker,
    frame: Any,
    *,
    frame_index: int = 0,
    time_s: float | None = None,
    feedback: FeedbackClient | None = None,
) -> tuple[dict[str, Any], Any]:
    encoder, feedback_status = ({}, {"configured": False})
    if feedback is not None:
        encoder, feedback_status = feedback.sample()
    result, annotated = tracker.process_frame(
        frame,
        frame_index=frame_index,
        time_s=time_s,
        encoder_joint_deg=encoder or None,
    )
    result["encoder_feedback"] = feedback_status
    return result, annotated


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
    feedback: FeedbackClient | None,
    summary_output: Path | None,
) -> int:
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise OSError(f"could not read image {image_path}")
    result, annotated = _process_one(tracker, image, feedback=feedback)
    _write_json(pose_output, result)
    if summary_output is not None:
        diagnostics = VideoDiagnosticAccumulator()
        diagnostics.update(result)
        _write_json(summary_output, diagnostics.summary())
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
    feedback: FeedbackClient | None,
    preview: bool,
    summary_output: Path | None,
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
    diagnostics = VideoDiagnosticAccumulator()
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
            result, annotated = _process_one(
                tracker,
                frame,
                frame_index=frame_index,
                time_s=time_s,
                feedback=feedback,
            )
            last_result = result
            diagnostics.update(result)
            if raw_writer is not None:
                raw_writer.write(frame)
            if annotated_writer is not None:
                annotated_writer.write(annotated)
            if json_handle is not None:
                json_handle.write(json.dumps(result, separators=(",", ":")) + "\n")
            if preview:
                cv2.imshow("Hexapod visual checkup (Q/Esc to stop)", annotated)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q"), 27):
                    frame_index += 1
                    break

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
        if preview:
            cv2.destroyAllWindows()

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
        "diagnostic_summary": diagnostics.summary(),
    }
    if summary_output is not None:
        _write_json(summary_output, summary)
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
    feedback: FeedbackClient | None,
    summary_output: Path | None,
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
    result, annotated = _process_one(tracker, frame, feedback=feedback)
    _write_json(pose_output, result)
    if summary_output is not None:
        diagnostics = VideoDiagnosticAccumulator()
        diagnostics.update(result)
        _write_json(summary_output, diagnostics.summary())
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
    parser.add_argument("--summary-output", type=Path,
                        help="write a compact cross-frame diagnostic JSON")
    parser.add_argument("--raw-output", type=Path,
                        help="save raw camera photo or MP4 (camera mode only)")
    parser.add_argument("--duration", type=float,
                        help="camera recording duration; omitted means one photo")
    parser.add_argument("--max-frames", type=int,
                        help="optional video frame limit for testing")
    parser.add_argument(
        "--robot-url",
        help=("optional robot base URL, e.g. http://hexapod.local:8080; "
              "only GET /api/feedback is used and no motor command is sent"),
    )
    parser.add_argument("--feedback-hz", type=float, default=3.0,
                        help="read-only robot feedback rate (default: 3 Hz)")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="show the annotated live/video checkup; press Q or Esc to stop",
    )
    args = parser.parse_args(argv)
    if args.duration is not None and args.duration <= 0.0:
        parser.error("--duration must be positive")
    if args.max_frames is not None and args.max_frames <= 0:
        parser.error("--max-frames must be positive")
    if args.feedback_hz <= 0.0:
        parser.error("--feedback-hz must be positive")
    if args.input is not None and args.raw_output is not None:
        parser.error("--raw-output is only for --camera capture")

    tracker = AprilTagPoseTracker.from_json(args.config)
    feedback = (
        None if args.robot_url is None
        else FeedbackClient(args.robot_url, hz=args.feedback_hz)
    )
    if args.input is not None and args.input.suffix.lower() in _IMAGE_SUFFIXES:
        return _process_image(
            tracker,
            args.input,
            pose_output=args.pose_output,
            annotated_output=args.annotated_output,
            feedback=feedback,
            summary_output=args.summary_output,
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
            feedback=feedback,
            preview=args.preview,
            summary_output=args.summary_output,
        )
    if args.duration is None and not args.preview:
        return _capture_still(
            tracker,
            args.camera,
            pose_output=args.pose_output,
            annotated_output=args.annotated_output,
            raw_output=args.raw_output,
            feedback=feedback,
            summary_output=args.summary_output,
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
        feedback=feedback,
        preview=args.preview,
        summary_output=args.summary_output,
    )


if __name__ == "__main__":
    raise SystemExit(main())
