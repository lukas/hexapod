#!/usr/bin/env python3
"""Record and safely exercise every scripted hardware gait.

The camera path is deliberately independent of the AprilTag worker: it opens
AVFoundation directly and writes clean frames plus a timestamp sidecar.  Robot
motion uses the HTTP API only.  Any guard trip calls the bench-level emergency
stop, which preempts workers before limping the bus.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import signal
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
LINUX_CONTROL = ROOT / "linux_control"
if str(LINUX_CONTROL) not in sys.path:
    sys.path.insert(0, str(LINUX_CONTROL))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from avfoundation_capture import AVFoundationYuvCapture  # noqa: E402
from hexapod_core.joint_frame import FRAME_ROBOT_ABS, JOINT_CONTRACT  # noqa: E402


GAITS = {
    0: "tripod_drag",
    1: "noslip_tripod",
    2: "noslip_ripple",
    3: "noslip_wave",
    4: "se2_tetrapod",
    5: "se2_wave",
    6: "se2_cpg_robust120",
    7: "noslip_clamp_fit",
    8: "middle_tuck_quad",
    9: "noslip_fluid",
    10: "noslip_fluid_fast",
    11: "noslip_fluid_hybrid",
    12: "noslip_fluid_push",
    13: "noslip_fluid_pulse",
}


def _request(
    base: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
    text_body: str | None = None,
    timeout: float = 5.0,
) -> Any:
    data = None
    headers: dict[str, str] = {}
    method = "GET"
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
        method = "POST"
    elif text_body is not None:
        data = text_body.encode()
        headers["Content-Type"] = "text/plain; charset=utf-8"
        method = "POST"
    req = urllib.request.Request(
        base.rstrip("/") + path,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            ctype = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as error:
        raw = error.read()
        raise RuntimeError(
            f"{method} {path} -> HTTP {error.code}: "
            f"{raw.decode('utf-8', 'replace')[:500]}"
        ) from error
    if "json" in ctype:
        return json.loads(raw)
    text = raw.decode("utf-8", "replace").strip()
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return text


class RawRecorder:
    def __init__(self, output: Path, timestamps: Path, camera_index: int) -> None:
        self.output = output
        self.timestamps = timestamps
        self.camera_index = camera_index
        self.stop_event = threading.Event()
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.error: str | None = None
        self.frames = 0
        self.started_monotonic: float | None = None
        self.latest_lock = threading.Lock()
        self.latest_frame: Any | None = None
        self.latest_frame_unix_s: float | None = None

    def start(self) -> None:
        self.thread.start()
        if not self.ready.wait(10.0):
            raise RuntimeError("raw camera recorder did not become ready")
        if self.error:
            raise RuntimeError(self.error)

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=8.0)

    def snapshot(self) -> tuple[Any, float]:
        """Return one clean camera frame without interrupting recording."""
        with self.latest_lock:
            if self.latest_frame is None or self.latest_frame_unix_s is None:
                raise RuntimeError("camera has not produced a frame")
            return self.latest_frame.copy(), self.latest_frame_unix_s

    def assert_live(self, max_age_s: float = 2.0) -> None:
        """Fail motion promptly when recording has stopped or gone stale."""
        if self.error:
            raise RuntimeError(f"recorder failed: {self.error}")
        with self.latest_lock:
            latest_unix_s = self.latest_frame_unix_s
        if latest_unix_s is None:
            raise RuntimeError("recorder has not produced its first frame")
        age_s = time.time() - latest_unix_s
        if age_s > max_age_s:
            raise RuntimeError(f"recorder frame is stale by {age_s:.2f} s")

    def _run(self) -> None:
        capture = AVFoundationYuvCapture(
            self.camera_index,
            preferred_sizes=((1920, 1440), (1920, 1080), (1280, 720)),
            fps=30.0,
            processing_width=1920,
            frame_timeout_s=6.0,
        )
        writer: cv2.VideoWriter | None = None
        csv_file = None
        try:
            ok, frame = capture.read()
            if not ok or frame is None:
                raise RuntimeError(capture.last_error or "camera produced no frame")
            height, width = frame.shape[:2]
            for codec in ("avc1", "mp4v"):
                candidate = cv2.VideoWriter(
                    str(self.output), cv2.VideoWriter_fourcc(*codec),
                    30.0, (width, height)
                )
                if candidate.isOpened():
                    writer = candidate
                    break
                candidate.release()
            if writer is None:
                raise RuntimeError("could not open an H.264/mp4v video writer")
            csv_file = self.timestamps.open("w", newline="")
            rows = csv.writer(csv_file)
            rows.writerow(["frame", "elapsed_s", "unix_s", "width", "height"])
            self.started_monotonic = time.monotonic()
            with self.latest_lock:
                self.latest_frame = frame
                self.latest_frame_unix_s = time.time()
            self.ready.set()
            while not self.stop_event.is_set():
                now = time.monotonic()
                now_unix = time.time()
                with self.latest_lock:
                    self.latest_frame = frame
                    self.latest_frame_unix_s = now_unix
                writer.write(frame)
                rows.writerow([
                    self.frames,
                    round(now - self.started_monotonic, 6),
                    round(now_unix, 6),
                    width,
                    height,
                ])
                self.frames += 1
                if self.frames % 30 == 0:
                    csv_file.flush()
                ok, frame = capture.read()
                if not ok or frame is None:
                    raise RuntimeError(
                        capture.last_error or "camera stopped producing frames"
                    )
        except Exception as error:  # recorder failure must abort motion
            self.error = str(error)
            self.ready.set()
        finally:
            if writer is not None:
                writer.release()
            if csv_file is not None:
                csv_file.close()
            capture.release()


class Suite:
    def __init__(
        self,
        args: argparse.Namespace,
        output_dir: Path,
        recorder: RawRecorder,
    ) -> None:
        self.args = args
        self.base = args.robot_url.rstrip("/")
        self.output_dir = output_dir
        self.recorder = recorder
        self.stop_requested = False
        self.motion_started = False
        self.completed = False
        self.started = time.monotonic()
        self.phase = "preflight"
        self.gait: int | None = None
        self.direction = ""
        self.high_current_count = 0
        self.high_tilt_count = 0
        self.high_temp_counts = [0] * 18
        self.feedback_failures = 0
        self.low_live_count = 0
        self.events_file = (output_dir / "events.csv").open("w", newline="")
        self.events = csv.writer(self.events_file)
        self.events.writerow([
            "receipt_unix_s", "elapsed_s", "event", "phase", "gait",
            "direction", "detail"
        ])
        self.telemetry_file = (output_dir / "telemetry.csv").open(
            "w", newline=""
        )
        self.telemetry = csv.writer(self.telemetry_file)
        self.telemetry.writerow([
            "robot_unix_s", "receipt_unix_s", "elapsed_s", "phase", "gait",
            "direction", "live",
            "max_joint_current_a", "bus_current_a", "max_temp_c",
            "min_voltage_v", "roll_deg", "pitch_deg", "body_roll_deg",
            "body_pitch_deg", "gyro_xyz_dps", "joint_degrees",
            "joint_currents_a", "joint_temperatures_c", "joint_load_pct",
            "joint_voltages_v", "joint_frame", "joint_contract",
        ])
        self.apriltag_detector: Any | None = None
        pose_config = json.loads(
            (LINUX_CONTROL / "apriltag_pose_config_20260831.json").read_text()
        )
        self.floor_tag_specs = pose_config["floor_tags"]
        self.tag_size_m = float(pose_config["marker_size_m"])
        self.body_from_tag_yaw_deg = float(
            pose_config["robot_pose"]["tags"]["0"]["frame_from_tag"]
            ["euler_xyz_deg"][2]
        )

    def close(self) -> None:
        self.events_file.close()
        self.telemetry_file.close()

    def log_event(self, event: str, detail: Any = "") -> None:
        elapsed = time.monotonic() - self.started
        clean = detail if isinstance(detail, str) else json.dumps(detail, sort_keys=True)
        self.events.writerow([
            round(time.time(), 6), round(elapsed, 3), event, self.phase,
            "" if self.gait is None else self.gait,
            self.direction, clean,
        ])
        self.events_file.flush()
        print(
            f"[{elapsed:7.2f}s] {event}: {clean}",
            flush=True,
        )

    def command(self, line: str) -> str:
        response = _request(self.base, "/cmd", text_body=line, timeout=5.0)
        self.log_event("command", {"line": line, "response": response})
        return str(response)

    def emergency_stop(self, reason: str) -> None:
        self.log_event("EMERGENCY_STOP", reason)
        try:
            _request(self.base, "/cmd", text_body="X", timeout=3.0)
        except Exception as error:
            self.log_event("emergency_stop_error", str(error))

    def robot_state(self) -> dict[str, Any]:
        state = _request(self.base, "/api/robot", timeout=5.0)
        if not isinstance(state, dict):
            raise RuntimeError(f"invalid robot state: {state!r}")
        return state

    def assert_robot_health(self, *, require_armed: bool) -> None:
        state = self.robot_state()
        servo = state.get("servo") or {}
        if int(servo.get("live", 0)) != 18 or servo.get("missing"):
            raise RuntimeError(f"servo health is not 18/18: {servo}")
        # ServoWatch intentionally publishes even a one-scan WARN_C sample so
        # the UI can display it, while its hard cutoff is already two-read
        # debounced. Do not turn that display warning back into a one-read
        # suite abort; sample_feedback() owns the same two-read confirmation.
        if servo.get("tripped"):
            raise RuntimeError(f"servo thermal cutoff is latched: {servo}")
        if float(servo.get("max_temp_c", 0.0) or 0.0) >= self.args.temp_trip_c:
            self.log_event("unconfirmed_temperature_warning", servo)
        if require_armed and not state.get("armed"):
            raise RuntimeError(f"robot unexpectedly limp: {state}")
        if (state.get("demo") or {}).get("running"):
            raise RuntimeError(f"robot job unexpectedly active: {state}")

    def sample_feedback(self) -> None:
        if self.stop_requested:
            raise RuntimeError("operator stop requested")
        self.recorder.assert_live()
        try:
            feedback = _request(self.base, "/api/feedback", timeout=2.0)
            if not isinstance(feedback, dict) or not feedback.get("ok"):
                raise RuntimeError(f"bad feedback: {feedback!r}")
            self.feedback_failures = 0
        except Exception as error:
            self.feedback_failures += 1
            self.log_event("feedback_error", str(error))
            if self.feedback_failures >= 3:
                raise RuntimeError("three consecutive telemetry failures") from error
            return

        joints = feedback.get("joints") or []
        records = [item for item in joints if isinstance(item, dict)]
        live = int(feedback.get("live", len(records)) or 0)
        degrees = [
            None if not isinstance(item, dict) else item.get("deg")
            for item in joints
        ]
        currents = [
            None if not isinstance(item, dict)
            else abs(float(item.get("cur_a", 0.0) or 0.0))
            for item in joints
        ]
        temperatures = [
            None if not isinstance(item, dict)
            else float(item.get("temp_c", 0.0) or 0.0)
            for item in joints
        ]
        loads = [
            None if not isinstance(item, dict)
            else float(item.get("load_pct", 0.0) or 0.0)
            for item in joints
        ]
        voltages = [
            None if not isinstance(item, dict)
            else float(item.get("volt", 99.0) or 99.0)
            for item in joints
        ]
        current_values = [value for value in currents if value is not None]
        temperature_values = [
            value for value in temperatures if value is not None
        ]
        voltage_values = [value for value in voltages if value is not None]
        max_current = max(current_values or [0.0])
        bus_current = sum(current_values)
        max_temp = max(temperature_values or [0.0])
        min_voltage = min(voltage_values or [99.0])
        roll = float(feedback.get("roll_deg", 0.0) or 0.0)
        pitch = float(feedback.get("pitch_deg", 0.0) or 0.0)
        body_roll = feedback.get("body_roll_deg")
        body_pitch = feedback.get("body_pitch_deg")
        gyro = feedback.get("gyro_dps") or []
        elapsed = time.monotonic() - self.started
        self.telemetry.writerow([
            feedback.get("t_unix"), round(time.time(), 6), round(elapsed, 3),
            self.phase,
            "" if self.gait is None else self.gait,
            self.direction, live, round(max_current, 4), round(bus_current, 4),
            round(max_temp, 1), round(min_voltage, 2), round(roll, 2),
            round(pitch, 2), body_roll, body_pitch, json.dumps(gyro),
            json.dumps(degrees),
            json.dumps([
                None if value is None else round(value, 4)
                for value in currents
            ]),
            json.dumps([
                None if value is None else round(value, 1)
                for value in temperatures
            ]),
            json.dumps([
                None if value is None else round(value, 2)
                for value in loads
            ]),
            json.dumps([
                None if value is None else round(value, 2)
                for value in voltages
            ]),
            FRAME_ROBOT_ABS,
            JOINT_CONTRACT,
        ])
        self.telemetry_file.flush()

        self.low_live_count = self.low_live_count + 1 if live < 16 else 0
        if self.low_live_count >= 3:
            raise RuntimeError(f"persistent incomplete servo feedback: {live}/18")
        # A corrupt bulk-feedback byte can look like a physically impossible
        # 30+ C jump for one sample. Confirm the SAME servo on consecutive
        # samples so unrelated glitches cannot combine into a false trip. The
        # robot's independent ServoWatch uses its own consecutive-read cutoff.
        for joint, value in enumerate(temperatures):
            self.high_temp_counts[joint] = (
                self.high_temp_counts[joint] + 1
                if value is not None and value >= self.args.temp_trip_c
                else 0
            )
        confirmed_hot = [
            joint for joint, count in enumerate(self.high_temp_counts)
            if count >= 2
        ]
        if confirmed_hot:
            raise RuntimeError(
                f"temperature {max_temp:.1f} C confirmed on joints "
                f"{confirmed_hot} across consecutive samples"
            )
        if min_voltage < self.args.voltage_trip_v:
            raise RuntimeError(f"bus voltage {min_voltage:.2f} V below trip")
        if max_current >= self.args.current_hard_a:
            raise RuntimeError(f"joint current {max_current:.2f} A exceeds hard trip")
        self.high_current_count = (
            self.high_current_count + 1
            if max_current >= self.args.current_sustained_a else 0
        )
        if self.high_current_count >= 2:
            raise RuntimeError(
                f"joint current {max_current:.2f} A sustained across samples"
            )
        tilt = max(abs(roll), abs(pitch))
        self.high_tilt_count = (
            self.high_tilt_count + 1 if tilt >= self.args.tilt_trip_deg else 0
        )
        if self.high_tilt_count >= 2:
            raise RuntimeError(f"body tilt {tilt:.1f} deg sustained across samples")

    def wait_guarded(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.sample_feedback()
            time.sleep(min(0.18, max(0.0, deadline - time.monotonic())))

    def wait_for_job(self, label: str, timeout_s: float = 35.0) -> None:
        deadline = time.monotonic() + timeout_s
        saw_running = False
        while time.monotonic() < deadline:
            if self.stop_requested:
                raise RuntimeError("operator stop requested")
            state = self.robot_state()
            demo = state.get("demo") or {}
            running = bool(demo.get("running"))
            saw_running = saw_running or running
            if not running and saw_running:
                detail = str(state.get("detail") or demo.get("status") or "")
                if "error" in detail.lower() or "abort" in detail.lower():
                    raise RuntimeError(f"{label} failed: {detail}")
                self.log_event(f"{label}_done", state)
                return
            time.sleep(0.25)
        raise RuntimeError(f"{label} timed out")

    def camera_center_observation(self) -> dict[str, Any]:
        """Project chassis and image center into the fixed floor-tag plane."""
        if not hasattr(cv2, "aruco"):
            raise RuntimeError("OpenCV AprilTag support is unavailable")
        if self.apriltag_detector is None:
            dictionary = cv2.aruco.getPredefinedDictionary(
                cv2.aruco.DICT_APRILTAG_36h11
            )
            parameters = cv2.aruco.DetectorParameters()
            parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
            self.apriltag_detector = cv2.aruco.ArucoDetector(
                dictionary, parameters
            )

        last_ids: list[int] = []
        for _attempt in range(8):
            frame, frame_unix_s = self.recorder.snapshot()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _rejected = self.apriltag_detector.detectMarkers(gray)
            by_id: dict[int, np.ndarray] = {}
            if ids is not None:
                last_ids = [int(value) for value in ids.flatten()]
                for marker_corners, marker_id in zip(corners, last_ids):
                    by_id[marker_id] = marker_corners.reshape(4, 2)

            floor_ids = sorted(
                marker_id
                for marker_id in by_id
                if str(marker_id) in self.floor_tag_specs
            )
            if 0 not in by_id or len(floor_ids) < self.args.center_min_floor_tags:
                time.sleep(0.12)
                continue

            half = self.tag_size_m / 2.0
            local_corners = np.asarray([
                [-half, half],
                [half, half],
                [half, -half],
                [-half, -half],
            ])
            image_points = []
            floor_points = []
            for marker_id in floor_ids:
                spec = self.floor_tag_specs[str(marker_id)]["world_from_tag"]
                tx, ty, _tz = spec["translation_m"]
                yaw = math.radians(float(spec["euler_xyz_deg"][2]))
                rotation = np.asarray([
                    [math.cos(yaw), -math.sin(yaw)],
                    [math.sin(yaw), math.cos(yaw)],
                ])
                image_points.extend(by_id[marker_id])
                floor_points.extend(
                    local_corners @ rotation.T + np.asarray([tx, ty])
                )
            image_points_array = np.asarray(image_points, dtype=np.float32)
            floor_points_array = np.asarray(floor_points, dtype=np.float32)
            image_to_floor, _mask = cv2.findHomography(
                image_points_array, floor_points_array, method=0
            )
            if image_to_floor is None:
                time.sleep(0.12)
                continue

            def to_floor(points: Any) -> np.ndarray:
                return cv2.perspectiveTransform(
                    np.asarray(points, dtype=np.float32).reshape(1, -1, 2),
                    image_to_floor,
                )[0].astype(float)

            projected_control_points = to_floor(image_points_array)
            floor_rms_mm = float(
                np.sqrt(np.mean(np.sum(
                    (projected_control_points - floor_points_array) ** 2,
                    axis=1,
                ))) * 1000.0
            )
            if floor_rms_mm > self.args.center_floor_rms_max_mm:
                time.sleep(0.12)
                continue

            chassis_corners = by_id[0]
            chassis_px = chassis_corners.mean(axis=0)
            height, width = frame.shape[:2]
            target_px = np.asarray([width / 2.0, height / 2.0])
            chassis_floor, target_floor = to_floor([chassis_px, target_px])
            error_floor = target_floor - chassis_floor

            # Tag 0 is body-fixed. Convert its decoded axes through the same
            # floor homography, then undo the configured tag mounting yaw.
            tag_x_px = (
                chassis_corners[1] + chassis_corners[2]
                - chassis_corners[0] - chassis_corners[3]
            ) / 2.0
            tag_y_px = (
                chassis_corners[0] + chassis_corners[1]
                - chassis_corners[2] - chassis_corners[3]
            ) / 2.0
            mount = math.radians(self.body_from_tag_yaw_deg)
            body_x_px = math.cos(mount) * tag_x_px - math.sin(mount) * tag_y_px
            body_y_px = math.sin(mount) * tag_x_px + math.cos(mount) * tag_y_px
            basis_floor = to_floor([
                chassis_px,
                chassis_px + body_x_px,
                chassis_px + body_y_px,
            ])
            body_to_floor = np.column_stack([
                basis_floor[1] - basis_floor[0],
                basis_floor[2] - basis_floor[0],
            ])
            if abs(float(np.linalg.det(body_to_floor))) < 1e-8:
                time.sleep(0.12)
                continue
            error_body = np.linalg.solve(body_to_floor, error_floor)
            error_px = target_px - chassis_px
            return {
                "frame_unix_s": round(frame_unix_s, 6),
                "image_size_px": [width, height],
                "seen_ids": sorted(last_ids),
                "floor_tag_ids": floor_ids,
                "floor_fit_rms_mm": round(floor_rms_mm, 3),
                "chassis_px": [round(float(value), 2) for value in chassis_px],
                "target_px": [round(float(value), 2) for value in target_px],
                "chassis_floor_m": [
                    round(float(value), 5) for value in chassis_floor
                ],
                "target_floor_m": [
                    round(float(value), 5) for value in target_floor
                ],
                "body_to_floor": [
                    [round(float(value), 6) for value in row]
                    for row in body_to_floor
                ],
                "error_px": [round(float(value), 2) for value in error_px],
                "error_px_norm": round(float(np.linalg.norm(error_px)), 2),
                "error_floor_m": [
                    round(float(value), 5) for value in error_floor
                ],
                "error_floor_norm_m": round(
                    float(np.linalg.norm(error_floor)), 4
                ),
                "error_body": [round(float(value), 4) for value in error_body],
            }
        raise RuntimeError(
            "centering vision unavailable: need chassis tag 0 and "
            f"{self.args.center_min_floor_tags} fixed floor tags; last seen "
            f"IDs were {sorted(last_ids)}"
        )

    def return_to_camera_center(self) -> None:
        """Move toward image center in guarded, visually checked pulses."""
        self.phase = "return_to_camera_center"
        self.direction = "camera_center"
        previous_error: float | None = None
        for correction in range(self.args.center_max_corrections + 1):
            try:
                observation = self.camera_center_observation()
            except Exception as error:
                self.log_event("camera_center_unavailable", str(error))
                return
            error_px = float(observation["error_px_norm"])
            self.log_event(
                "camera_center_observation",
                {"correction": correction, **observation},
            )
            if error_px <= self.args.center_deadband_px:
                self.log_event("camera_center_reached", observation)
                return
            if (
                float(observation["error_floor_norm_m"])
                > self.args.center_max_distance_m
            ):
                self.log_event(
                    "camera_center_too_far",
                    {
                        "limit_m": self.args.center_max_distance_m,
                        **observation,
                    },
                )
                return
            if correction >= self.args.center_max_corrections:
                self.log_event("camera_center_limit", observation)
                return
            if (
                previous_error is not None
                and error_px > previous_error * self.args.center_wrong_way_ratio
            ):
                self.log_event(
                    "camera_center_wrong_way",
                    {"previous_error_px": previous_error, **observation},
                )
                return

            error_body = observation["error_body"]
            desired_angle = math.degrees(
                math.atan2(float(error_body[1]), float(error_body[0]))
            )
            # Floor-stabilized sweep result: the current hardware response is
            # orientation reversing, actual ~= reflection - command.
            command_angle = self.args.center_reflection_deg - desired_angle
            vx = self.args.center_speed_mm_s * math.cos(math.radians(command_angle))
            vy = self.args.center_speed_mm_s * math.sin(math.radians(command_angle))
            self.log_event(
                "camera_center_correction",
                {
                    "correction": correction + 1,
                    "desired_body_angle_deg": round(desired_angle, 2),
                    "command_body_angle_deg": round(command_angle, 2),
                    "vx_mm_s": round(vx, 2),
                    "vy_mm_s": round(vy, 2),
                },
            )
            response = self.command(
                f"J {vx:.1f} {vy:.1f} 0 {self.args.center_gait}"
            )
            if response != "J":
                self.log_event("camera_center_refused", response)
                return
            self.wait_guarded(self.args.center_pulse_s)
            response = self.command("J 0 0 0")
            if response != "J":
                raise RuntimeError(f"centering stop refused: {response}")
            self.wait_guarded(self.args.center_settle_s)
            self.assert_robot_health(require_armed=True)
            previous_error = error_px

    def run(self) -> None:
        self.recorder.assert_live()
        self.assert_robot_health(require_armed=False)
        pose = _request(self.base, "/api/pose", timeout=5.0)
        degrees = pose.get("degrees") if isinstance(pose, dict) else None
        if not isinstance(degrees, list) or len(degrees) != 18:
            raise RuntimeError(f"preflight pose unavailable: {pose}")
        if max(abs(float(value)) for value in degrees if value is not None) > 6.0:
            raise RuntimeError(f"robot is not at visually verified zero: {degrees}")
        self.log_event("preflight_ok", {"pose_deg": degrees})

        self.phase = "stand"
        self.motion_started = True
        reply = _request(
            self.base, "/api/zero", json_body={"pose": "stand"}, timeout=8.0
        )
        self.log_event("stand_start", reply)
        self.wait_for_job("stand")
        self.assert_robot_health(require_armed=True)
        self.sample_feedback()

        # Loading a CPG artifact is relevant only to gait 6.  Keeping this
        # conditional also lets the canonical-frame guard reject an old CPG
        # artifact without blocking unrelated scripted gait experiments.
        if 6 in self.args.gaits:
            loaded = self.command(f"CPGLOAD {self.args.cpg}")
            if loaded.lower().startswith(("bad", "refused", "unknown")):
                raise RuntimeError(loaded)

        for gait in self.args.gaits:
            self.gait = gait
            self.phase = f"gait_{gait}_select"
            gait_command = (
                f"GAIT 1 {self.args.gait1_alpha:.3f}"
                if gait == 1
                else f"GAIT {gait}"
            )
            selected = self.command(gait_command)
            if selected.lower().startswith(("bad", "refused", "unknown")):
                raise RuntimeError(selected)
            self.assert_robot_health(require_armed=True)
            self.wait_guarded(0.8)
            if self.args.headings_deg:
                directions = tuple(
                    (
                        f"heading_{int(round(heading)) % 360:03d}",
                        self.args.speed_mm_s * math.cos(math.radians(heading)),
                        self.args.speed_mm_s * math.sin(math.radians(heading)),
                    )
                    for heading in self.args.headings_deg
                )
            else:
                directions = (
                    ("forward", self.args.speed_mm_s, 0.0),
                    ("backward", -self.args.speed_mm_s, 0.0),
                )
            for direction_index, (direction, vx_mm_s, vy_mm_s) in enumerate(directions):
                self.direction = direction
                self.phase = f"gait_{gait}_{direction}"
                response = self.command(
                    f"J {vx_mm_s:.1f} {vy_mm_s:.1f} 0 {gait}"
                )
                if response != "J":
                    raise RuntimeError(f"gait {gait} {direction} refused: {response}")
                self.wait_guarded(self.args.direction_s)
                self.phase = f"gait_{gait}_{direction}_settle"
                response = self.command("J 0 0 0")
                if response != "J":
                    raise RuntimeError(f"stop refused: {response}")
                self.wait_guarded(self.args.settle_s)
                self.assert_robot_health(require_armed=True)
                if gait == 8 and direction_index == 0:
                    # Middle-tuck quad intentionally stops with its middle
                    # legs folded, which is not the common walk-ready plant
                    # pose. Re-seat all six feet before asking it to reverse.
                    self.phase = "gait_8_reverse_restand"
                    reply = _request(
                        self.base,
                        "/api/zero",
                        json_body={"pose": "stand"},
                        timeout=8.0,
                    )
                    self.log_event("gait_8_restand_start", reply)
                    self.wait_for_job("gait_8_restand")
                    self.assert_robot_health(require_armed=True)
            self.direction = ""

        if self.args.return_to_camera_center:
            self.gait = self.args.center_gait
            selected = self.command(f"GAIT {self.args.center_gait}")
            if selected.lower().startswith(("bad", "refused", "unknown")):
                raise RuntimeError(selected)
            self.return_to_camera_center()
            self.direction = ""

        self.phase = "sit"
        self.gait = None
        reply = _request(
            self.base, "/api/zero", json_body={"pose": "sit"}, timeout=8.0
        )
        self.log_event("sit_start", reply)
        self.wait_for_job("sit")
        self.command("X")
        self.motion_started = False
        self.completed = True
        self.log_event("suite_complete")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--robot-url", default="http://192.168.4.39:8080")
    parser.add_argument("--camera-index", type=int, default=1)
    parser.add_argument("--camera-warmup-s", type=float, default=3.0)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--gaits", type=int, nargs="+", default=list(GAITS))
    parser.add_argument("--gait1-alpha", type=float, default=0.75)
    parser.add_argument("--cpg", default="cpg_controller_robust120_yawtrim.json")
    parser.add_argument("--speed-mm-s", type=float, default=30.0)
    parser.add_argument(
        "--headings-deg", type=float, nargs="+",
        help=("replace the forward/back pair with body-frame translation "
              "headings; 0 is +vx and 90 is +vy"),
    )
    parser.add_argument("--direction-s", type=float, default=10.0)
    parser.add_argument("--settle-s", type=float, default=1.5)
    parser.add_argument(
        "--return-to-camera-center",
        action="store_true",
        help="use fixed floor tags to return to image center before sitting",
    )
    parser.add_argument("--center-gait", type=int, default=11)
    parser.add_argument("--center-speed-mm-s", type=float, default=30.0)
    parser.add_argument("--center-pulse-s", type=float, default=6.4)
    parser.add_argument("--center-settle-s", type=float, default=0.8)
    parser.add_argument("--center-deadband-px", type=float, default=90.0)
    parser.add_argument("--center-max-distance-m", type=float, default=0.25)
    parser.add_argument("--center-max-corrections", type=int, default=4)
    parser.add_argument("--center-wrong-way-ratio", type=float, default=1.12)
    parser.add_argument("--center-min-floor-tags", type=int, default=2)
    parser.add_argument("--center-floor-rms-max-mm", type=float, default=8.0)
    parser.add_argument(
        "--center-reflection-deg",
        type=float,
        default=52.0,
        help="floor-stabilized actual+command angle of the gait response",
    )
    parser.add_argument("--current-sustained-a", type=float, default=2.4)
    parser.add_argument("--current-hard-a", type=float, default=3.0)
    parser.add_argument("--tilt-trip-deg", type=float, default=22.0)
    parser.add_argument("--temp-trip-c", type=float, default=55.0)
    parser.add_argument("--voltage-trip-v", type=float, default=9.5)
    args = parser.parse_args()
    bad = [gait for gait in [*args.gaits, args.center_gait] if gait not in GAITS]
    if bad:
        parser.error(f"unknown gait IDs: {bad}")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir / f"scripted_gait_suite_{stamp}"
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "config.json").write_text(
        json.dumps({**vars(args), "output_dir": str(output_dir),
                    "joint_frame": FRAME_ROBOT_ABS,
                    "joint_contract": JOINT_CONTRACT},
                   default=str, indent=2)
        + "\n"
    )

    recorder = RawRecorder(
        output_dir / "iphone_raw.mp4",
        output_dir / "iphone_raw_timestamps.csv",
        args.camera_index,
    )
    suite = Suite(args, output_dir, recorder)

    def request_stop(_signum: int, _frame: Any) -> None:
        suite.stop_requested = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    print(f"OUTPUT_DIR={output_dir}", flush=True)
    try:
        recorder.start()
        suite.log_event("recorder_ready")
        warmup_deadline = time.monotonic() + max(0.0, args.camera_warmup_s)
        while time.monotonic() < warmup_deadline:
            recorder.assert_live()
            time.sleep(min(0.25, warmup_deadline - time.monotonic()))
        suite.log_event(
            "camera_warmup_done",
            {"seconds": args.camera_warmup_s, "frames": recorder.frames},
        )
        suite.run()
        if recorder.error:
            raise RuntimeError(f"recorder failed: {recorder.error}")
        return 0
    except Exception as error:
        suite.log_event("suite_error", str(error))
        if suite.motion_started:
            suite.emergency_stop(str(error))
        return 1
    finally:
        recorder.stop()
        suite.log_event(
            "recorder_stopped",
            {"frames": recorder.frames, "error": recorder.error},
        )
        suite.close()


if __name__ == "__main__":
    raise SystemExit(main())
