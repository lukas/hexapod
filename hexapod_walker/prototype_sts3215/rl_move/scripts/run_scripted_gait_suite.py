#!/usr/bin/env python3
"""Record and safely exercise every scripted hardware gait.

The camera path is deliberately independent of the AprilTag worker: it opens
AVFoundation directly and writes clean frames plus a timestamp sidecar.  Robot
motion uses the HTTP API only.  Hard guard trips call the bench-level emergency
stop, which preempts workers before limping the bus. Optional survey recovery
acts only on lower pre-trip thresholds: stop, pause until readings clear,
collision-aware safe-zero, stand, then retry. A tip, brownout, hot servo,
missing ID, or hard-current event is never auto-retried.
"""
from __future__ import annotations

import argparse
import csv
import itertools
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
from hexapod_core.scripted_walk_contract import (  # noqa: E402
    SCRIPTED_WALK_ACC_UNITS,
    SCRIPTED_WALK_CONTROL_HZ,
    SCRIPTED_WALK_SPEED_COUNTS_S,
)


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


def _select_floor_homography(
    candidates_by_id: dict[int, list[np.ndarray]],
    floor_tag_specs: dict[str, Any],
    tag_size_m: float,
) -> tuple[dict[int, np.ndarray], list[int], np.ndarray, np.ndarray,
           np.ndarray, float] | None:
    """Choose duplicate floor-tag decodes by global reprojection fit.

    A second physical tag with the same ID can be visible in a workshop.  A
    last-decode-wins dictionary makes centering intermittently fail or, worse,
    use the wrong floor point.  Testing the small candidate product against
    every configured floor-tag corner makes the choice deterministic.
    """
    floor_ids = sorted(
        marker_id
        for marker_id in candidates_by_id
        if str(marker_id) in floor_tag_specs
    )
    if len(floor_ids) < 2:
        return None
    candidate_groups = [
        sorted(
            candidates_by_id[marker_id],
            key=lambda corners: abs(float(cv2.contourArea(
                corners.astype(np.float32)
            ))),
            reverse=True,
        )[:3]
        for marker_id in floor_ids
    ]
    half = tag_size_m / 2.0
    local_corners = np.asarray([
        [-half, half],
        [half, half],
        [half, -half],
        [-half, -half],
    ])
    world_corners: dict[int, np.ndarray] = {}
    for marker_id in floor_ids:
        spec = floor_tag_specs[str(marker_id)]["world_from_tag"]
        tx, ty, _tz = spec["translation_m"]
        yaw = math.radians(float(spec["euler_xyz_deg"][2]))
        rotation = np.asarray([
            [math.cos(yaw), -math.sin(yaw)],
            [math.sin(yaw), math.cos(yaw)],
        ])
        world_corners[marker_id] = (
            local_corners @ rotation.T + np.asarray([tx, ty])
        )

    best: tuple[dict[int, np.ndarray], np.ndarray, np.ndarray,
                np.ndarray, float] | None = None
    for combination in itertools.product(*candidate_groups):
        image_points_array = np.asarray(
            [point for corners in combination for point in corners],
            dtype=np.float32,
        )
        floor_points_array = np.asarray(
            [
                point
                for marker_id in floor_ids
                for point in world_corners[marker_id]
            ],
            dtype=np.float32,
        )
        image_to_floor, _mask = cv2.findHomography(
            image_points_array, floor_points_array, method=0
        )
        if image_to_floor is None:
            continue
        projected = cv2.perspectiveTransform(
            image_points_array.reshape(1, -1, 2), image_to_floor
        )[0].astype(float)
        rms_mm = float(np.sqrt(np.mean(np.sum(
            (projected - floor_points_array) ** 2, axis=1
        ))) * 1000.0)
        if best is None or rms_mm < best[-1]:
            best = (
                dict(zip(floor_ids, combination)),
                image_to_floor,
                image_points_array,
                floor_points_array,
                rms_mm,
            )
    if best is None:
        return None
    selected, transform, image_points, floor_points, rms_mm = best
    return selected, floor_ids, transform, image_points, floor_points, rms_mm


class HardSafetyTrip(RuntimeError):
    """A condition for which automatic motion must never resume."""


class ThermalSafetyTrip(HardSafetyTrip):
    """Confirmed heat: limp immediately, then record until clearly cool."""


class SoftSafetyPause(RuntimeError):
    """A pre-trip condition eligible for bounded pause/zero recovery."""


class CameraExitRisk(SoftSafetyPause):
    """The chassis is nearing the frame boundary and should be recentered."""

    def __init__(self, observation: dict[str, Any] | None, reason: str) -> None:
        super().__init__(reason)
        self.observation = observation


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
        self.last_trusted_tilt: tuple[float, float, float] | None = None
        self.high_temp_counts = [0] * 18
        self.warm_temp_counts = [0] * 18
        self.pause_current_count = 0
        self.pause_tilt_count = 0
        self.pause_voltage_count = 0
        self.recoveries = 0
        self.recenters = 0
        self.center_check_failures = 0
        self.feedback_failures = 0
        self.low_live_count = 0
        # Adaptive centering returns to the operator-approved starting
        # framing.  It must not assume the optical center is a safe/desired
        # floor position for an oblique camera.
        self.center_target_px: np.ndarray | None = None
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

    def recover_nonhard_failure_to_zero(self, reason: str) -> None:
        """After a non-safety failure, lower to verified zero and limp.

        HardSafetyTrip deliberately never reaches this method.  A confirmed
        tip, brownout, missing servo, hot motor, hard current, or lost
        telemetry remains a stop-and-limp event with no further motion.
        """
        self.log_event("failure_zero_recovery_start", reason)
        reply = _request(
            self.base, "/api/safe_zero", json_body={}, timeout=8.0
        )
        self.log_event("failure_zero_recovery_reply", reply)
        if isinstance(reply, dict) and reply.get("ok") is False:
            raise RuntimeError(
                "collision-aware zero recovery refused: "
                + str(reply.get("error") or reply)
            )

        deadline = time.monotonic() + 50.0
        while time.monotonic() < deadline:
            state = self.robot_state()
            if not bool((state.get("demo") or {}).get("running")):
                pose = _request(self.base, "/api/pose", timeout=5.0)
                degrees = pose.get("degrees") if isinstance(pose, dict) else None
                if isinstance(degrees, list) and len(degrees) == 18:
                    max_error = max(abs(float(value)) for value in degrees)
                    if max_error <= 6.0:
                        self.command("X")
                        self.motion_started = False
                        self.log_event(
                            "failure_zero_recovery_complete",
                            {"max_abs_deg": round(max_error, 3)},
                        )
                        return
            time.sleep(0.25)
        raise RuntimeError("collision-aware zero recovery timed out")

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
        # the UI can display it. Do not turn that display warning back into a
        # one-read suite abort; sample_feedback() owns the same per-joint
        # three-read confirmation.
        if servo.get("tripped"):
            raise ThermalSafetyTrip(
                f"servo thermal cutoff is latched: {servo}"
            )
        if float(servo.get("max_temp_c", 0.0) or 0.0) >= self.args.temp_trip_c:
            self.log_event("unconfirmed_temperature_warning", servo)
        if require_armed and not state.get("armed"):
            raise RuntimeError(f"robot unexpectedly limp: {state}")
        if (state.get("demo") or {}).get("running"):
            raise RuntimeError(f"robot job unexpectedly active: {state}")

    def sample_feedback(self, *, allow_soft_pause: bool = True,
                        enforce_safety: bool = True) -> dict[str, float]:
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
            if enforce_safety and self.feedback_failures >= 3:
                raise HardSafetyTrip(
                    "three consecutive telemetry failures; cannot move blind"
                ) from error
            return {}

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
        sample_monotonic = time.monotonic()
        tilt_sample_valid = True
        if self.last_trusted_tilt is not None:
            previous_roll, previous_pitch, previous_time = (
                self.last_trusted_tilt
            )
            dt = max(0.001, sample_monotonic - previous_time)

            def _wrapped_delta_deg(current: float, previous: float) -> float:
                return abs((current - previous + 180.0) % 360.0 - 180.0)

            observed_jump = max(
                _wrapped_delta_deg(roll, previous_roll),
                _wrapped_delta_deg(pitch, previous_pitch),
            )
            gyro_values = [
                abs(float(value)) for value in gyro
                if value is not None
            ]
            max_gyro_dps = max(gyro_values or [0.0])
            # The Uno occasionally repeats an Euler solution near +/-180 deg
            # while its gyro remains almost still.  A real fall has either a
            # continuous tilt trajectory or a corresponding angular-rate
            # impulse.  Keep comparing rejected samples with the last trusted
            # pose so a frozen corrupt solution cannot accumulate trip votes.
            allowed_jump = max(35.0, max_gyro_dps * dt * 4.0 + 10.0)
            if observed_jump > allowed_jump:
                tilt_sample_valid = False
                self.log_event("tilt_glitch_ignored", {
                    "roll_deg": roll,
                    "pitch_deg": pitch,
                    "previous_roll_deg": previous_roll,
                    "previous_pitch_deg": previous_pitch,
                    "observed_jump_deg": round(observed_jump, 2),
                    "max_gyro_dps": round(max_gyro_dps, 2),
                    "dt_s": round(dt, 3),
                    "allowed_jump_deg": round(allowed_jump, 2),
                })
        if tilt_sample_valid:
            self.last_trusted_tilt = (roll, pitch, sample_monotonic)
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

        metrics = {
            "live": live,
            "max_current_a": max_current,
            "max_temp_c": max_temp,
            "min_voltage_v": min_voltage,
            "tilt_deg": max(abs(roll), abs(pitch)),
            "tilt_sample_valid": tilt_sample_valid,
        }
        # After a thermal stop, motion is already limp. Continue using this
        # exact telemetry writer without recursively firing safety exceptions
        # so the recording contains the complete cooldown trace.
        if not enforce_safety:
            return metrics

        self.low_live_count = self.low_live_count + 1 if live < 16 else 0
        if self.low_live_count >= 3:
            raise HardSafetyTrip(
                f"persistent incomplete servo feedback: {live}/18"
            )
        # A corrupt bulk-feedback byte can look like a physically impossible
        # 30+ C jump for one sample. Confirm the SAME servo on three
        # consecutive samples so unrelated glitches cannot combine into a
        # false trip. The robot's independent ServoWatch uses the same count.
        for joint, value in enumerate(temperatures):
            self.high_temp_counts[joint] = (
                self.high_temp_counts[joint] + 1
                if value is not None and value >= self.args.temp_trip_c
                else 0
            )
            self.warm_temp_counts[joint] = (
                self.warm_temp_counts[joint] + 1
                if value is not None and value >= self.args.temp_pause_c
                else 0
            )
        confirmed_hot = [
            joint for joint, count in enumerate(self.high_temp_counts)
            if count >= self.args.temp_trip_samples
        ]
        if confirmed_hot:
            raise ThermalSafetyTrip(
                f"temperature {max_temp:.1f} C confirmed on joints "
                f"{confirmed_hot} across {self.args.temp_trip_samples} "
                "consecutive samples"
            )
        if min_voltage < self.args.voltage_trip_v:
            raise HardSafetyTrip(
                f"bus voltage {min_voltage:.2f} V below trip"
            )
        if max_current >= self.args.current_hard_a:
            raise HardSafetyTrip(
                f"joint current {max_current:.2f} A exceeds hard trip"
            )
        self.high_current_count = (
            self.high_current_count + 1
            if max_current >= self.args.current_sustained_a else 0
        )
        if self.high_current_count >= 2:
            raise HardSafetyTrip(
                f"joint current {max_current:.2f} A sustained across samples"
            )
        tilt = metrics["tilt_deg"]
        self.high_tilt_count = (
            self.high_tilt_count + 1
            if tilt_sample_valid and tilt >= self.args.tilt_trip_deg else 0
        )
        if self.high_tilt_count >= self.args.tilt_trip_samples:
            raise HardSafetyTrip(
                f"body tilt {tilt:.1f} deg sustained across "
                f"{self.args.tilt_trip_samples} valid samples"
            )

        if not self.args.soft_recovery or not allow_soft_pause:
            return metrics

        self.pause_current_count = (
            self.pause_current_count + 1
            if max_current >= self.args.current_pause_a else 0
        )
        self.pause_tilt_count = (
            self.pause_tilt_count + 1
            if tilt_sample_valid and tilt >= self.args.tilt_pause_deg else 0
        )
        self.pause_voltage_count = (
            self.pause_voltage_count + 1
            if min_voltage <= self.args.voltage_pause_v else 0
        )
        soft_reason = None
        if self.pause_current_count >= 2:
            soft_reason = f"pre-trip current {max_current:.2f} A"
        elif self.pause_tilt_count >= 2:
            soft_reason = f"pre-trip body tilt {tilt:.1f} deg"
        elif any(
            count >= self.args.temp_trip_samples
            for count in self.warm_temp_counts
        ):
            warm_joints = [
                joint for joint, count in enumerate(self.warm_temp_counts)
                if count >= self.args.temp_trip_samples
            ]
            soft_reason = (
                f"warm servo {max_temp:.1f} C on joints {warm_joints}"
            )
        elif self.pause_voltage_count >= 2:
            soft_reason = f"low bus-voltage warning {min_voltage:.2f} V"
        if soft_reason is not None:
            self.pause_current_count = 0
            self.pause_tilt_count = 0
            self.warm_temp_counts = [0] * 18
            self.pause_voltage_count = 0
            raise SoftSafetyPause(soft_reason)
        return metrics

    def monitor_thermal_cooldown(self, reason: str) -> bool:
        """Keep raw video and telemetry running after a thermal limp.

        This method never commands motion or torque. It requires three
        consecutive complete readings below the warning/pause threshold before
        declaring the robot cool. A bounded timeout leaves the robot limp and
        records an explicit incomplete-cooldown event.
        """
        self.phase = "thermal_cooldown"
        self.direction = ""
        clear_samples = 0
        deadline = time.monotonic() + self.args.thermal_cooldown_timeout_s
        self.log_event("thermal_cooldown_start", {
            "reason": reason,
            "clear_below_c": self.args.temp_pause_c,
            "required_clear_samples": self.args.temp_clear_samples,
            "timeout_s": self.args.thermal_cooldown_timeout_s,
        })
        while time.monotonic() < deadline:
            try:
                metrics = self.sample_feedback(
                    allow_soft_pause=False, enforce_safety=False
                )
            except Exception as error:
                clear_samples = 0
                self.log_event("thermal_cooldown_read_error", str(error))
                time.sleep(self.args.thermal_cooldown_poll_s)
                continue
            complete = int(metrics.get("live", 0)) == 18
            max_temp = float(metrics.get("max_temp_c", float("inf")))
            cool = complete and max_temp < self.args.temp_pause_c
            clear_samples = clear_samples + 1 if cool else 0
            self.log_event("thermal_cooldown_sample", {
                **metrics,
                "clear_samples": clear_samples,
            })
            if clear_samples >= self.args.temp_clear_samples:
                self.log_event("thermal_cooldown_complete", {
                    "max_temp_c": max_temp,
                    "clear_samples": clear_samples,
                    "robot_remains_limp": True,
                })
                return True
            time.sleep(self.args.thermal_cooldown_poll_s)
        self.log_event("thermal_cooldown_timeout", {
            "timeout_s": self.args.thermal_cooldown_timeout_s,
            "robot_remains_limp": True,
        })
        return False

    def wait_guarded(self, seconds: float, *,
                     allow_soft_pause: bool = True) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.sample_feedback(allow_soft_pause=allow_soft_pause)
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

    def stop_walk(self, label: str) -> None:
        response = self.command("J 0 0 0")
        if response != "J":
            raise HardSafetyTrip(f"{label} stop refused: {response}")

    def _readings_clear_for_recovery(self, metrics: dict[str, float]) -> bool:
        if not metrics:
            return False
        return (
            metrics["max_current_a"] < self.args.current_pause_a * 0.85
            and metrics["tilt_deg"] < self.args.tilt_pause_deg * 0.8
            and metrics["max_temp_c"] < self.args.temp_pause_c - 2.0
            and metrics["min_voltage_v"] > self.args.voltage_pause_v + 0.1
        )

    def recover_to_zero(self, reason: str, gait: int) -> None:
        """Bounded recovery for a warning that has not crossed a hard trip."""
        if self.recoveries >= self.args.max_recoveries:
            raise RuntimeError(
                f"soft-recovery limit reached ({self.args.max_recoveries}): "
                f"{reason}"
            )
        self.recoveries += 1
        self.phase = f"recovery_{self.recoveries}_pause"
        self.log_event("soft_recovery_start", {
            "attempt": self.recoveries,
            "reason": reason,
            "resume_gait": gait,
        })
        self.stop_walk("soft recovery")

        earliest = time.monotonic() + self.args.recovery_pause_s
        deadline = time.monotonic() + self.args.recovery_clear_timeout_s
        clear_samples = 0
        while time.monotonic() < deadline:
            metrics = self.sample_feedback(allow_soft_pause=False)
            clear_samples = (
                clear_samples + 1
                if self._readings_clear_for_recovery(metrics) else 0
            )
            if time.monotonic() >= earliest and clear_samples >= 3:
                break
            time.sleep(0.25)
        else:
            raise RuntimeError(
                f"readings did not clear during recovery from: {reason}"
            )

        self.phase = f"recovery_{self.recoveries}_safe_zero"
        reply = _request(
            self.base, "/api/safe_zero", json_body={}, timeout=8.0
        )
        self.log_event("soft_recovery_safe_zero_start", reply)
        if isinstance(reply, dict) and reply.get("ok") is False:
            raise RuntimeError(
                "collision-aware safe-zero refused recovery: "
                + str(reply.get("error") or reply)
            )
        self.wait_for_job(f"recovery_{self.recoveries}_safe_zero", timeout_s=45.0)
        self.assert_robot_health(require_armed=False)

        self.phase = f"recovery_{self.recoveries}_stand"
        reply = _request(
            self.base, "/api/zero", json_body={"pose": "stand"}, timeout=8.0
        )
        self.log_event("soft_recovery_stand_start", reply)
        self.wait_for_job(f"recovery_{self.recoveries}_stand")
        self.assert_robot_health(require_armed=True)
        selected = self.command(
            f"GAIT 1 {self.args.gait1_alpha:.3f}" if gait == 1
            else f"GAIT {gait}"
        )
        if selected.lower().startswith(("bad", "refused", "unknown")):
            raise RuntimeError(f"could not restore gait {gait}: {selected}")
        self.log_event("soft_recovery_complete", {
            "attempt": self.recoveries,
            "resume_gait": gait,
        })

    def _adaptive_center_check(self) -> None:
        try:
            observation = self.camera_center_observation()
        except Exception as error:
            self.center_check_failures += 1
            self.log_event("adaptive_center_check_unavailable", {
                "consecutive": self.center_check_failures,
                "error": str(error),
            })
            if self.center_check_failures >= 2:
                raise CameraExitRisk(
                    None, "chassis/floor tags lost during active walk"
                ) from error
            return
        self.center_check_failures = 0
        self.log_event("adaptive_center_check", observation)
        if float(observation["error_px_norm"]) >= self.args.center_trigger_px:
            raise CameraExitRisk(
                observation,
                f"chassis reached {observation['error_px_norm']} px from frame center",
            )

    def run_direction(self, gait: int, direction: str,
                      vx_mm_s: float, vy_mm_s: float) -> None:
        """Run one measured direction, recentering or retrying when allowed."""
        remaining = self.args.direction_s
        while remaining > 1e-6:
            self.direction = direction
            self.phase = f"gait_{gait}_{direction}"
            response = self.command(
                f"J {vx_mm_s:.1f} {vy_mm_s:.1f} 0 {gait}"
            )
            if response != "J":
                raise RuntimeError(
                    f"gait {gait} {direction} refused: {response}"
                )
            try:
                while remaining > 1e-6:
                    chunk = min(
                        remaining,
                        self.args.center_check_s
                        if self.args.adaptive_centering else remaining,
                    )
                    self.wait_guarded(chunk)
                    remaining -= chunk
                    if self.args.adaptive_centering and remaining > 1e-6:
                        self._adaptive_center_check()
            except CameraExitRisk as issue:
                if self.recenters >= self.args.max_recenters:
                    raise RuntimeError(
                        f"adaptive-centering limit reached "
                        f"({self.args.max_recenters}): {issue}"
                    ) from issue
                self.recenters += 1
                self.phase = f"gait_{gait}_{direction}_recenter"
                self.log_event("adaptive_center_pause", {
                    "attempt": self.recenters,
                    "reason": str(issue),
                })
                self.stop_walk("adaptive centering")
                self.wait_guarded(
                    self.args.center_settle_s, allow_soft_pause=False
                )
                selected = self.command(f"GAIT {self.args.center_gait}")
                if selected.lower().startswith(("bad", "refused", "unknown")):
                    raise RuntimeError(selected)
                centered = self.return_to_camera_center()
                if not centered:
                    self.wait_guarded(
                        self.args.recovery_pause_s, allow_soft_pause=False
                    )
                    centered = self.return_to_camera_center()
                if not centered:
                    raise RuntimeError(
                        "camera centering failed twice; refusing blind resume"
                    )
                selected = self.command(
                    f"GAIT 1 {self.args.gait1_alpha:.3f}" if gait == 1
                    else f"GAIT {gait}"
                )
                if selected.lower().startswith(("bad", "refused", "unknown")):
                    raise RuntimeError(f"could not restore gait {gait}: {selected}")
                continue
            except SoftSafetyPause as issue:
                self.log_event("soft_guard_pause", str(issue))
                self.recover_to_zero(str(issue), gait)
                # Start a fresh full-duration sample after recovery so the
                # retained trial is comparable rather than a stitched pulse.
                remaining = self.args.direction_s
                continue

            self.phase = f"gait_{gait}_{direction}_settle"
            self.stop_walk(f"gait {gait} {direction}")
            try:
                self.wait_guarded(self.args.settle_s)
            except SoftSafetyPause as issue:
                self.log_event("soft_guard_pause_during_settle", str(issue))
                self.recover_to_zero(str(issue), gait)
                remaining = self.args.direction_s
                continue
            self.assert_robot_health(require_armed=True)
            return

    def capture_camera_center_anchor(self) -> None:
        """Remember the initial, operator-approved chassis image position."""
        self.center_target_px = None
        observation = self.camera_center_observation()
        self.center_target_px = np.asarray(
            observation["chassis_px"], dtype=float
        )
        self.log_event("camera_center_anchor", {
            "target_px": [
                round(float(value), 2) for value in self.center_target_px
            ],
            "image_size_px": observation["image_size_px"],
            "floor_tag_ids": observation["floor_tag_ids"],
            "floor_fit_rms_mm": observation["floor_fit_rms_mm"],
        })

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
            candidates_by_id: dict[int, list[np.ndarray]] = {}
            if ids is not None:
                last_ids = [int(value) for value in ids.flatten()]
                for marker_corners, marker_id in zip(corners, last_ids):
                    candidates_by_id.setdefault(marker_id, []).append(
                        marker_corners.reshape(4, 2)
                    )

            by_id = {
                marker_id: max(
                    marker_candidates,
                    key=lambda marker_corners: abs(float(cv2.contourArea(
                        marker_corners.astype(np.float32)
                    ))),
                )
                for marker_id, marker_candidates in candidates_by_id.items()
            }

            floor_ids = sorted(
                marker_id
                for marker_id in candidates_by_id
                if str(marker_id) in self.floor_tag_specs
            )
            if 0 not in by_id or len(floor_ids) < self.args.center_min_floor_tags:
                time.sleep(0.12)
                continue

            fit = _select_floor_homography(
                candidates_by_id, self.floor_tag_specs, self.tag_size_m
            )
            if fit is None:
                time.sleep(0.12)
                continue
            (selected_floor, floor_ids, image_to_floor, image_points_array,
             floor_points_array, floor_rms_mm) = fit
            by_id.update(selected_floor)

            def to_floor(points: Any) -> np.ndarray:
                return cv2.perspectiveTransform(
                    np.asarray(points, dtype=np.float32).reshape(1, -1, 2),
                    image_to_floor,
                )[0].astype(float)

            if floor_rms_mm > self.args.center_floor_rms_max_mm:
                time.sleep(0.12)
                continue

            chassis_corners = by_id[0]
            chassis_px = chassis_corners.mean(axis=0)
            height, width = frame.shape[:2]
            target_px = (
                np.asarray([width / 2.0, height / 2.0])
                if self.center_target_px is None
                else self.center_target_px.copy()
            )
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
            basis_norms = np.linalg.norm(body_to_floor, axis=0)
            if float(np.min(basis_norms)) < 1e-6:
                time.sleep(0.12)
                continue
            body_to_floor = body_to_floor / basis_norms
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

    def return_to_camera_center(self) -> bool:
        """Move toward image center in guarded, visually checked pulses."""
        self.phase = "return_to_camera_center"
        self.direction = "camera_center"
        previous_error: float | None = None
        for correction in range(self.args.center_max_corrections + 1):
            try:
                observation = self.camera_center_observation()
            except Exception as error:
                self.log_event("camera_center_unavailable", str(error))
                return False
            error_px = float(observation["error_px_norm"])
            self.log_event(
                "camera_center_observation",
                {"correction": correction, **observation},
            )
            if error_px <= self.args.center_deadband_px:
                self.log_event("camera_center_reached", observation)
                return True
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
                return False
            if correction >= self.args.center_max_corrections:
                self.log_event("camera_center_limit", observation)
                return False
            if (
                previous_error is not None
                and error_px > previous_error * self.args.center_wrong_way_ratio
            ):
                self.log_event(
                    "camera_center_wrong_way",
                    {"previous_error_px": previous_error, **observation},
                )
                return False

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
                return False
            self.wait_guarded(self.args.center_pulse_s)
            response = self.command("J 0 0 0")
            if response != "J":
                raise RuntimeError(f"centering stop refused: {response}")
            self.wait_guarded(self.args.center_settle_s)
            self.assert_robot_health(require_armed=True)
            previous_error = error_px
        return False

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
        if self.args.return_to_camera_center or self.args.adaptive_centering:
            self.capture_camera_center_anchor()

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
                self.run_direction(gait, direction, vx_mm_s, vy_mm_s)
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
            if not self.return_to_camera_center():
                self.log_event(
                    "final_camera_center_incomplete",
                    "continuing to collision-aware sit instead of resuming walk",
                )
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
    parser.add_argument(
        "--adaptive-centering",
        action="store_true",
        help="pause and recenter before the chassis reaches the frame edge",
    )
    parser.add_argument("--center-check-s", type=float, default=1.5)
    parser.add_argument("--center-trigger-px", type=float, default=260.0)
    parser.add_argument("--center-gait", type=int, default=11)
    parser.add_argument("--center-speed-mm-s", type=float, default=30.0)
    parser.add_argument("--center-pulse-s", type=float, default=6.4)
    parser.add_argument("--center-settle-s", type=float, default=0.8)
    parser.add_argument("--center-deadband-px", type=float, default=90.0)
    parser.add_argument("--center-max-distance-m", type=float, default=0.25)
    parser.add_argument("--center-max-corrections", type=int, default=4)
    parser.add_argument("--max-recenters", type=int, default=4)
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
    parser.add_argument("--tilt-trip-samples", type=int, default=3)
    parser.add_argument("--temp-trip-c", type=float, default=55.0)
    parser.add_argument("--temp-trip-samples", type=int, default=3)
    parser.add_argument("--temp-clear-samples", type=int, default=3)
    parser.add_argument("--thermal-cooldown-timeout-s", type=float, default=300.0)
    parser.add_argument("--thermal-cooldown-poll-s", type=float, default=0.5)
    parser.add_argument("--voltage-trip-v", type=float, default=9.5)
    parser.add_argument(
        "--soft-recovery",
        action="store_true",
        help=("on pre-trip warnings only, stop, wait for stable readings, "
              "safe-zero, stand, and retry"),
    )
    parser.add_argument("--max-recoveries", type=int, default=0)
    parser.add_argument("--recovery-pause-s", type=float, default=3.0)
    parser.add_argument("--recovery-clear-timeout-s", type=float, default=30.0)
    parser.add_argument("--current-pause-a", type=float, default=1.8)
    parser.add_argument("--tilt-pause-deg", type=float, default=14.0)
    parser.add_argument("--temp-pause-c", type=float, default=50.0)
    parser.add_argument("--voltage-pause-v", type=float, default=10.5)
    args = parser.parse_args()
    bad = [gait for gait in [*args.gaits, args.center_gait] if gait not in GAITS]
    if bad:
        parser.error(f"unknown gait IDs: {bad}")
    if args.adaptive_centering and not args.return_to_camera_center:
        parser.error("--adaptive-centering requires --return-to-camera-center")
    if args.center_check_s <= 0.0:
        parser.error("--center-check-s must be positive")
    if args.center_trigger_px <= args.center_deadband_px:
        parser.error("--center-trigger-px must exceed --center-deadband-px")
    if not 0 <= args.max_recenters <= 12:
        parser.error("--max-recenters must be between 0 and 12")
    if not 0 <= args.max_recoveries <= 3:
        parser.error("--max-recoveries must be between 0 and 3")
    if args.soft_recovery and args.max_recoveries == 0:
        parser.error("--soft-recovery requires --max-recoveries >= 1")
    if args.recovery_pause_s < 0.0:
        parser.error("--recovery-pause-s must be non-negative")
    if args.recovery_clear_timeout_s <= args.recovery_pause_s:
        parser.error(
            "--recovery-clear-timeout-s must exceed --recovery-pause-s"
        )
    if not args.current_pause_a < args.current_sustained_a <= args.current_hard_a:
        parser.error("current thresholds must satisfy pause < sustained <= hard")
    if not args.tilt_pause_deg < args.tilt_trip_deg:
        parser.error("--tilt-pause-deg must be below --tilt-trip-deg")
    if not args.temp_pause_c < args.temp_trip_c:
        parser.error("--temp-pause-c must be below --temp-trip-c")
    if args.temp_trip_samples < 3:
        parser.error("--temp-trip-samples must be at least 3")
    if args.temp_clear_samples < 3:
        parser.error("--temp-clear-samples must be at least 3")
    if args.thermal_cooldown_timeout_s <= 0.0:
        parser.error("--thermal-cooldown-timeout-s must be positive")
    if args.thermal_cooldown_poll_s <= 0.0:
        parser.error("--thermal-cooldown-poll-s must be positive")
    if not args.voltage_trip_v < args.voltage_pause_v:
        parser.error("--voltage-pause-v must be above --voltage-trip-v")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir / f"scripted_gait_suite_{stamp}"
    output_dir.mkdir(parents=True, exist_ok=False)
    config_path = output_dir / "config.json"
    config_payload = {
        **vars(args),
        "output_dir": str(output_dir),
        "joint_frame": FRAME_ROBOT_ABS,
        "joint_contract": JOINT_CONTRACT,
        "expected_scripted_walk_contract": {
            "control_hz": SCRIPTED_WALK_CONTROL_HZ,
            "servo_speed_counts_s": SCRIPTED_WALK_SPEED_COUNTS_S,
            "servo_acc_units": SCRIPTED_WALK_ACC_UNITS,
        },
    }
    config_path.write_text(
        json.dumps(config_payload, default=str, indent=2) + "\n"
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
        robot_state = suite.robot_state()
        actual_contract = robot_state.get("scripted_walk")
        if not isinstance(actual_contract, dict):
            raise RuntimeError(
                "robot API does not expose scripted_walk contract; deploy "
                "the matching controller before collecting a parity run"
            )
        expected_contract = config_payload["expected_scripted_walk_contract"]
        mismatches = {
            key: {"expected": value, "actual": actual_contract.get(key)}
            for key, value in expected_contract.items()
            if actual_contract.get(key) != value
        }
        if mismatches:
            raise RuntimeError(
                "robot scripted-walk contract does not match this recorder: "
                + json.dumps(mismatches, sort_keys=True)
            )
        config_payload["robot_runtime"] = {
            "scripted_walk": actual_contract,
            "drive_status": robot_state.get("drive_status"),
            "activity": robot_state.get("activity"),
        }
        config_path.write_text(
            json.dumps(config_payload, default=str, indent=2) + "\n"
        )
        suite.log_event("scripted_contract_verified", actual_contract)
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
    except ThermalSafetyTrip as error:
        suite.log_event("suite_error", str(error))
        if suite.motion_started:
            suite.emergency_stop(str(error))
        suite.monitor_thermal_cooldown(str(error))
        return 1
    except HardSafetyTrip as error:
        suite.log_event("suite_error", str(error))
        if suite.motion_started:
            suite.emergency_stop(str(error))
        return 1
    except Exception as error:
        suite.log_event("suite_error", str(error))
        if suite.motion_started:
            suite.emergency_stop(str(error))
            try:
                suite.recover_nonhard_failure_to_zero(str(error))
            except Exception as recovery_error:
                suite.log_event("failure_zero_recovery_error", str(recovery_error))
                suite.emergency_stop(
                    f"zero recovery failed after {error}: {recovery_error}"
                )
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
