#!/usr/bin/env python3
"""Record short hardware walks for a deployed RL policy.

The timed legs use ``/api/rl/walk``. The optional course uses the persistent
drive API with translation-only heartbeats; it never sends yaw. A
normal trial starts from verified logical zero, runs the known STEP transition
to the simulator walk-ready pose, records each policy episode, then performs a
planned STEP lower and limps. Robot-side policy guards remain authoritative.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import threading
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hexapod_core.joint_frame import FRAME_ROBOT_ABS, JOINT_CONTRACT
from rl_move.deployed_policy import WALK_OBS_DIMS, WALK_PHASE_OBS_DIMS
from rl_move.np_policy import ARCH_DUAL_GRU, MODE_ONEHOT_ORDER
from rl_move.scripts.run_scripted_gait_suite import RawRecorder, _request


DIRECTIONS = {
    "forward": (1.0, 0.0),
    "backward": (-1.0, 0.0),
    "left": (0.0, 1.0),
    "right": (0.0, -1.0),
}
COURSE = ("forward", "left", "backward", "right")


class HttpFrameRecorder:
    """Record the already-running local Vision JPEG stream.

    This is the fallback for app/uv processes that cannot import PyObjC's
    native AVFoundation bindings. It intentionally has the same small
    interface as ``RawRecorder`` so motion still fails closed on a stale or
    unavailable camera.
    """

    OUTPUT_FPS = 10.0
    MAX_CAPTURE_AGE_S = 2.0

    def __init__(self, output: Path, timestamps: Path, frame_url: str) -> None:
        self.output = output
        self.timestamps = timestamps
        self.frame_url = frame_url
        self.stop_event = threading.Event()
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.error: str | None = None
        self.frames = 0
        self.latest_lock = threading.Lock()
        self.latest_frame: Any | None = None
        self.latest_frame_unix_s: float | None = None

    def start(self) -> None:
        self.thread.start()
        if not self.ready.wait(10.0):
            raise RuntimeError("HTTP camera recorder did not become ready")
        if self.error:
            raise RuntimeError(self.error)

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=8.0)

    def snapshot(self) -> tuple[Any, float]:
        with self.latest_lock:
            if self.latest_frame is None or self.latest_frame_unix_s is None:
                raise RuntimeError("camera has not produced a frame")
            return self.latest_frame.copy(), self.latest_frame_unix_s

    def assert_live(self, max_age_s: float = 2.0) -> None:
        if self.error:
            raise RuntimeError(f"recorder failed: {self.error}")
        with self.latest_lock:
            latest_unix_s = self.latest_frame_unix_s
        if latest_unix_s is None:
            raise RuntimeError("recorder has not produced its first frame")
        age_s = time.time() - latest_unix_s
        if age_s > max_age_s:
            raise RuntimeError(f"recorder frame is stale by {age_s:.2f} s")

    def _read_frame(self) -> tuple[Any, float]:
        with urllib.request.urlopen(self.frame_url, timeout=3.0) as response:
            payload = response.read()
            raw_capture_time = response.headers.get("X-Capture-Unix-S")
        try:
            capture_unix_s = float(raw_capture_time)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                "HTTP camera lacks X-Capture-Unix-S; receipt time cannot "
                "prove the camera is live") from exc
        age_s = time.time() - capture_unix_s
        if (not math.isfinite(capture_unix_s)
                or not -0.25 <= age_s <= self.MAX_CAPTURE_AGE_S):
            raise RuntimeError("HTTP camera capture timestamp is stale or invalid")
        frame = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise RuntimeError("Vision frame endpoint returned an invalid JPEG")
        return frame, capture_unix_s

    def _run(self) -> None:
        writer: cv2.VideoWriter | None = None
        csv_file = None
        try:
            frame, frame_unix_s = self._read_frame()
            height, width = frame.shape[:2]
            for codec in ("avc1", "mp4v"):
                candidate = cv2.VideoWriter(
                    str(self.output), cv2.VideoWriter_fourcc(*codec),
                    self.OUTPUT_FPS, (width, height),
                )
                if candidate.isOpened():
                    writer = candidate
                    break
                candidate.release()
            if writer is None:
                raise RuntimeError("could not open an H.264/mp4v video writer")
            csv_file = self.timestamps.open("w", newline="")
            rows = csv.writer(csv_file)
            rows.writerow([
                "frame", "elapsed_s", "unix_s", "capture_unix_s",
                "width", "height",
            ])
            started_monotonic = time.monotonic()
            with self.latest_lock:
                self.latest_frame = frame
                self.latest_frame_unix_s = frame_unix_s
            self.ready.set()
            next_frame = started_monotonic
            while not self.stop_event.is_set():
                now = time.monotonic()
                if now < next_frame:
                    self.stop_event.wait(next_frame - now)
                    continue
                frame, frame_unix_s = self._read_frame()
                with self.latest_lock:
                    self.latest_frame = frame
                    self.latest_frame_unix_s = frame_unix_s
                writer.write(frame)
                rows.writerow([
                    self.frames,
                    round(time.monotonic() - started_monotonic, 6),
                    round(time.time(), 6),
                    round(frame_unix_s, 6),
                    width,
                    height,
                ])
                self.frames += 1
                if self.frames % int(self.OUTPUT_FPS) == 0:
                    csv_file.flush()
                next_frame += 1.0 / self.OUTPUT_FPS
        except Exception as error:
            self.error = str(error)
            self.ready.set()
        finally:
            if writer is not None:
                writer.release()
            if csv_file is not None:
                csv_file.close()


class ConfirmedHealthTrip(RuntimeError):
    """Three fresh scans confirmed a hard health fault."""


class Trial:
    def __init__(self, args: argparse.Namespace, output_dir: Path) -> None:
        self.args = args
        self.base = args.robot_url.rstrip("/")
        self.output_dir = output_dir
        self.started = time.monotonic()
        self.phase = "preflight"
        self.motion_started = False
        self.completed = False
        self.results: list[dict[str, Any]] = []
        if args.vision_frame_url:
            self.recorder = HttpFrameRecorder(
                output_dir / "camera_raw.mp4",
                output_dir / "camera_timestamps.csv",
                args.vision_frame_url,
            )
        else:
            self.recorder = RawRecorder(
                output_dir / "camera_raw.mp4",
                output_dir / "camera_timestamps.csv",
                args.camera_index,
            )
        self.events_file = (output_dir / "events.csv").open("w", newline="")
        self.events = csv.writer(self.events_file)
        self.events.writerow(["unix_s", "elapsed_s", "phase", "event", "detail"])
        self.telemetry_file = (output_dir / "telemetry.csv").open("w", newline="")
        self.telemetry = csv.writer(self.telemetry_file)
        self.telemetry.writerow([
            "unix_s", "elapsed_s", "phase", "live", "roll_deg",
            "pitch_deg", "gyro_xyz_dps", "max_current_a", "bus_current_a",
            "max_temp_c", "min_voltage_v", "degrees", "currents_a",
            "temperatures_c", "voltages_v",
        ])

    def close(self) -> None:
        self.events_file.close()
        self.telemetry_file.close()

    def event(self, name: str, detail: Any = "") -> None:
        elapsed = time.monotonic() - self.started
        clean = detail if isinstance(detail, str) else json.dumps(detail, sort_keys=True)
        self.events.writerow([
            round(time.time(), 6), round(elapsed, 3), self.phase, name, clean,
        ])
        self.events_file.flush()
        print(f"[{elapsed:7.2f}s] {self.phase} {name}: {clean}", flush=True)

    def request(self, path: str, body: dict[str, Any] | None = None) -> Any:
        return _request(
            self.base, path, json_body=body,
            timeout=8.0 if body is not None else 5.0,
        )

    def snapshot(self, label: str) -> Path:
        frame, frame_unix_s = self.recorder.snapshot()
        path = self.output_dir / f"camera_{label}.jpg"
        if not cv2.imwrite(str(path), frame):
            raise RuntimeError(f"could not write {path}")
        self.event("camera_snapshot", {
            "label": label, "path": path.name, "frame_unix_s": frame_unix_s,
        })
        return path

    def sample(self) -> dict[str, Any]:
        self.recorder.assert_live()
        feedback = self.request("/api/feedback")
        if not isinstance(feedback, dict) or not feedback.get("ok"):
            raise RuntimeError(f"bad feedback: {feedback}")
        joints = feedback.get("joints") or []
        records = [item for item in joints if isinstance(item, dict)]
        live = int(feedback.get("live", len(records)) or 0)
        currents = [
            None if not isinstance(item, dict) else item.get("cur_a")
            for item in joints
        ]
        temperatures = [
            None if not isinstance(item, dict) else item.get("temp_c")
            for item in joints
        ]
        voltages = [
            None if not isinstance(item, dict) else item.get("volt")
            for item in joints
        ]
        degrees = [
            None if not isinstance(item, dict) else item.get("deg")
            for item in joints
        ]
        current_values = [abs(float(x)) for x in currents if x is not None]
        temperature_values = [float(x) for x in temperatures if x is not None]
        voltage_values = [float(x) for x in voltages if x is not None]
        metrics = {
            "live": live,
            "roll_deg": float(feedback.get("roll_deg", 0.0) or 0.0),
            "pitch_deg": float(feedback.get("pitch_deg", 0.0) or 0.0),
            "max_current_a": max(current_values or [0.0]),
            "bus_current_a": sum(current_values),
            "max_temp_c": max(temperature_values or [0.0]),
            "min_voltage_v": min(voltage_values or [99.0]),
        }
        self.telemetry.writerow([
            round(time.time(), 6), round(time.monotonic() - self.started, 3),
            self.phase, live, metrics["roll_deg"], metrics["pitch_deg"],
            json.dumps(feedback.get("gyro_dps") or []),
            round(metrics["max_current_a"], 4),
            round(metrics["bus_current_a"], 4),
            round(metrics["max_temp_c"], 1),
            round(metrics["min_voltage_v"], 2),
            json.dumps(degrees), json.dumps(currents),
            json.dumps(temperatures), json.dumps(voltages),
        ])
        self.telemetry_file.flush()
        return metrics

    def three_fresh_health_samples(self, *, require_armed: bool) -> list[dict[str, Any]]:
        samples: list[dict[str, Any]] = []
        timestamps: set[Any] = set()
        deadline = time.monotonic() + 8.0
        while len(samples) < 3 and time.monotonic() < deadline:
            robot = self.request("/api/robot")
            if not isinstance(robot, dict):
                time.sleep(0.15)
                continue
            servo = robot.get("servo") or {}
            stamp = servo.get("ts")
            if stamp in timestamps:
                time.sleep(0.12)
                continue
            timestamps.add(stamp)
            sample = {
                "ts": stamp,
                "live": int(servo.get("live", 0) or 0),
                "missing": servo.get("missing") or [],
                "max_temp_c": float(servo.get("max_temp_c", 0.0) or 0.0),
                "tripped": servo.get("tripped") or [],
                "armed": bool(robot.get("armed")),
                "activity": robot.get("activity"),
            }
            samples.append(sample)
            time.sleep(0.12)
        if len(samples) < 3:
            raise RuntimeError(f"could not obtain three fresh health samples: {samples}")
        # One dropped feedback read is expected bus telemetry noise.  Match
        # the robot-side emergency rule: a missing ID is actionable only
        # after three consecutive fresh samples.  Confirmed servo trips,
        # heat, and unexpected torque-off remain immediate failures.
        missing_samples = [
            sample for sample in samples
            if sample["live"] != 18 or sample["missing"]
        ]
        missing_confirmed = len(missing_samples) == len(samples)
        hot_samples = [
            sample for sample in samples
            if sample["max_temp_c"] >= self.args.temp_trip_c
        ]
        hot_confirmed = len(hot_samples) == len(samples)
        bad = [
            sample for sample in samples
            if sample["tripped"]
            or (require_armed and not sample["armed"])
        ]
        if missing_samples and not missing_confirmed:
            self.event("single_missing_feedback_tolerated", missing_samples)
        if missing_confirmed:
            bad.extend(missing_samples)
        if hot_samples and not hot_confirmed:
            self.event("isolated_temperature_sample_tolerated", hot_samples)
        if hot_confirmed:
            bad.extend(hot_samples)
        if bad:
            raise ConfirmedHealthTrip(
                f"health samples not clear: {samples}"
            )
        self.event("three_fresh_health_samples", samples)
        return samples

    def wait_job(self, label: str, timeout_s: float) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_s
        saw_running = False
        last: dict[str, Any] = {}
        while time.monotonic() < deadline:
            state = self.request("/api/rl/state")
            if not isinstance(state, dict):
                raise RuntimeError(f"invalid RL state: {state}")
            last = state
            calibrate = state.get("calibrate") or {}
            robot = state.get("robot") or {}
            demo = robot.get("demo") or calibrate.get("demo") or {}
            running = bool(calibrate.get("running") or demo.get("running"))
            saw_running = saw_running or running
            self.sample()
            result = calibrate.get("result")
            if not running and (saw_running or result is not None):
                self.event(f"{label}_terminal", result or calibrate)
                return result if isinstance(result, dict) else {"ok": False, "error": "no result"}
            time.sleep(0.35)
        raise RuntimeError(f"{label} timed out; last state: {last}")

    def pull_policy_logs(self, after_unix_s: float, prefix: str) -> list[str]:
        listing = self.request("/api/logs")
        entries = None
        if isinstance(listing, dict):
            entries = listing.get("logs") or listing.get("files")
        if not isinstance(entries, list):
            self.event("policy_log_list_unavailable", listing)
            return []
        selected = [
            item for item in entries
            if isinstance(item, dict)
            and str(item.get("name") or "").startswith(prefix)
            and float(item.get("mtime_unix", 0.0) or 0.0) >= after_unix_s - 1.0
        ]
        pulled = []
        for item in selected:
            name = str(item["name"])
            url = f"{self.base}/api/logs/{urllib.parse.quote(name)}"
            with urllib.request.urlopen(url, timeout=15.0) as response:
                payload = response.read()
            destination = self.output_dir / f"robot_{name}"
            destination.write_bytes(payload)
            pulled.append(destination.name)
        self.event("policy_logs_pulled", pulled)
        return pulled

    def validate_walk_policy(self) -> dict[str, Any]:
        """Fail closed on the deploy contract before moving to stand."""
        policy = self.request("/api/rl/policy")
        walk = policy.get("walk") if isinstance(policy, dict) else None
        if not isinstance(walk, dict):
            raise RuntimeError(f"walk policy metadata unavailable: {policy}")
        problems: list[str] = []
        if walk.get("joint_frame") != FRAME_ROBOT_ABS:
            problems.append(
                f"joint_frame={walk.get('joint_frame')!r}, expected "
                f"{FRAME_ROBOT_ABS!r}"
            )
        if walk.get("joint_contract") != JOINT_CONTRACT:
            problems.append(
                f"joint_contract={walk.get('joint_contract')!r}, expected "
                f"{JOINT_CONTRACT!r}"
            )
        obs_dim = walk.get("obs_dim")
        if obs_dim not in WALK_OBS_DIMS:
            problems.append(f"unsupported walk obs_dim={walk.get('obs_dim')!r}")
        try:
            training_hz = float(walk["training_hz"])
        except (KeyError, TypeError, ValueError):
            problems.append("training_hz is missing or invalid")
        else:
            if abs(training_hz - 100.0) > 1e-6:
                problems.append(f"training_hz={training_hz}, expected 100")
        try:
            speed_min = float(walk["walk_speed_min_m_s"])
            speed_max = float(walk["walk_speed_max_m_s"])
        except (KeyError, TypeError, ValueError):
            problems.append("trained walk speed band is missing or invalid")
        else:
            if not speed_min <= self.args.speed_m_s <= speed_max:
                problems.append(
                    f"requested {self.args.speed_m_s} m/s is outside trained "
                    f"band [{speed_min}, {speed_max}]"
                )
        if obs_dim in WALK_PHASE_OBS_DIMS:
            try:
                phase_hz = float(walk["phase_hz"])
            except (KeyError, TypeError, ValueError):
                problems.append("phase-clock policy has no valid phase_hz")
            else:
                if not math.isfinite(phase_hz) or phase_hz <= 0.0:
                    problems.append("phase-clock policy phase_hz is not positive")
        if obs_dim in (75, 81):
            if walk.get("walk_yaw_cmd") is not True:
                problems.append(f"obs-{obs_dim} policy has no yaw-command stamp")
            if not isinstance(walk.get("walk_phase_run_on_yaw"), bool):
                problems.append(
                    f"obs-{obs_dim} policy has no explicit yaw-clock stamp")
        if obs_dim == 81:
            if walk.get("architecture") != ARCH_DUAL_GRU:
                problems.append("obs-81 policy is not a dual_gru export")
            if list(walk.get("mode_onehot_order") or []) != list(
                    MODE_ONEHOT_ORDER):
                problems.append("obs-81 policy has the wrong mode-onehot order")
        self.event("walk_policy_contract", {"walk": walk, "problems": problems})
        if problems:
            raise RuntimeError("walk policy contract refused: " + "; ".join(problems))
        return walk

    def stand_walk_ready(self) -> None:
        self.phase = "stand_walk_ready"
        self.validate_walk_policy()
        pose = self.request("/api/pose")
        degrees = pose.get("degrees") if isinstance(pose, dict) else None
        if not isinstance(degrees, list) or len(degrees) != 18:
            raise RuntimeError(f"pose unavailable: {pose}")
        max_abs_deg = max(
            abs(float(value)) for value in degrees if value is not None
        )
        if max_abs_deg > 6.0:
            if self.args.resume_walk_ready:
                preflight = self.request("/api/rl/preflight?mode=walk")
                self.event("resume_walk_ready_preflight", preflight)
                if not isinstance(preflight, dict) or not preflight.get("ok"):
                    raise RuntimeError(
                        "non-zero resume pose is not verified walk-ready: "
                        f"{preflight}"
                    )
            elif self.args.acquire_current:
                self.event(
                    "safe_start_acquisition_requested",
                    {"max_abs_joint_deg": round(max_abs_deg, 2)},
                )
            else:
                raise RuntimeError(
                    f"start is not verified logical zero: {degrees}"
                )
        self.three_fresh_health_samples(
            require_armed=self.args.keep_current_walk_ready
        )
        self.snapshot(
            ("resume_walk_ready" if self.args.resume_walk_ready
             else "current_preflight" if max_abs_deg > 6.0
             else "zero_preflight")
        )
        self.motion_started = True
        if self.args.keep_current_walk_ready:
            if not self.args.resume_walk_ready:
                raise RuntimeError(
                    "--keep-current-walk-ready requires --resume-walk-ready"
                )
            self.event("stand_reused", "armed, verified walk-ready pose")
        else:
            if self.args.tuck_recovery:
                reply = self.request("/api/standup", {
                    "mode": "tuck", "direction": "up", "speed": 1.0,
                    "torque": 700, "force": True,
                })
                self.event("tuck_recovery_start", reply)
                if not isinstance(reply, dict) or not reply.get("ok"):
                    raise RuntimeError(f"tuck recovery refused: {reply}")
                result = self.wait_job("tuck_recovery", 90.0)
                if not result.get("ok"):
                    raise RuntimeError(f"tuck recovery failed: {result}")
                self.snapshot("after_tuck_recovery")
            stand_body: dict[str, Any] = {}
            if self.args.learned_rise:
                stand_body = {
                    "learned": True,
                    "tilt_trip_deg": self.args.learned_rise_tilt_trip_deg,
                }
            reply = self.request("/api/rl/stand", stand_body)
            self.event("stand_start", reply)
            if not isinstance(reply, dict) or not reply.get("ok"):
                raise RuntimeError(f"stand refused: {reply}")
            result = self.wait_job("stand", 45.0)
            if not result.get("ok"):
                # The stand endpoint applies a strict <=5 deg *start-pose*
                # check before running the learned stance policy.  A guarded
                # tuck recovery can finish a fraction outside that diagnostic
                # threshold while still satisfying the deployment walk
                # preflight's independently defined, hardware-tested envelope.
                # Accept only that exact non-motion refusal, and only after a
                # fresh preflight says the present pose is walk-ready.  Every
                # motion/current/thermal/fault failure still stops here.
                error = str(result.get("error") or "")
                verification_only = (
                    "walk-ready start failed verification" in error
                )
                post = (self.request("/api/rl/preflight?mode=walk")
                        if verification_only else None)
                if (verification_only and isinstance(post, dict)
                        and post.get("ok")):
                    self.event("stand_start_verification_accepted", {
                        "stand_result": result,
                        "walk_preflight": post,
                    })
                else:
                    raise RuntimeError(f"stand failed: {result}")
            if self.args.learned_rise and result.get("stood") is not True:
                raise RuntimeError(
                    f"learned rise did not finish standing: {result}"
                )
        preflight = self.request("/api/rl/preflight?mode=walk")
        self.event("walk_preflight", preflight)
        if not isinstance(preflight, dict) or not preflight.get("ok"):
            raise RuntimeError(f"walk-ready preflight failed: {preflight}")
        self.three_fresh_health_samples(require_armed=True)
        self.snapshot("walk_ready")

    def timed_leg(self, name: str) -> None:
        unit_x, unit_y = DIRECTIONS[name]
        vx = unit_x * self.args.speed_m_s
        vy = unit_y * self.args.speed_m_s
        self.phase = f"walk_{name}"
        self.event("walk_request", {
            "vx_m_s": vx, "vy_m_s": vy,
            "duration_s": self.args.duration_s, "yaw_command": 0.0,
        })
        started_unix_s = time.time()
        reply = self.request("/api/rl/walk", {
            "vx": vx, "vy": vy, "duration_s": self.args.duration_s,
            "rot60": True,
        })
        if not isinstance(reply, dict) or not reply.get("ok"):
            raise RuntimeError(f"walk {name} refused: {reply}")
        result = self.wait_job(name, self.args.duration_s + 20.0)
        logs = self.pull_policy_logs(started_unix_s, "rl_walk_")
        entry = {
            "phase": name, "request": {"vx": vx, "vy": vy},
            "result": result, "robot_logs": logs,
        }
        self.results.append(entry)
        self.snapshot(f"after_{name}")
        if not result.get("ok"):
            raise RuntimeError(f"walk {name} failed: {result}")
        self.three_fresh_health_samples(require_armed=True)

    def drive_start_payload(
            self, *, active_duration_s: float | None = None) -> dict[str, Any]:
        self._drive_command_owner = uuid.uuid4().hex
        payload = {"vx": 0.0, "vy": 0.0, "wz": 0.0, "dh": 0.0,
                   "command_owner": self._drive_command_owner}
        if active_duration_s is not None:
            # Enforced by the board from first learned-walk engagement;
            # host polling remains supervision/evidence.
            payload["active_duration_s"] = active_duration_s
        alpha = getattr(self.args, "velocity_filter_alpha", None)
        if alpha is not None:
            payload["velocity_filter_alpha"] = alpha
        return payload

    def drive_leg(self, name: str) -> None:
        """Run one cardinal leg through the 100 Hz combined-snapshot drive path."""
        unit_x, unit_y = DIRECTIONS[name]
        vx = unit_x * self.args.speed_m_s
        vy = unit_y * self.args.speed_m_s
        self.phase = f"drive_{name}"
        started_unix_s = time.time()
        started_monotonic_s = time.monotonic()
        reply = self.request(
            "/api/rl/drive/start",
            self.drive_start_payload(active_duration_s=self.args.duration_s),
        )
        self.event("drive_start", reply)
        if not isinstance(reply, dict) or not reply.get("ok"):
            raise RuntimeError(f"drive start refused: {reply}")
        samples = 0
        stop: Any = None
        command_started_s = time.monotonic()
        activation_s: float | None = None
        activation_unix_s: float | None = None
        last_live_t: float | None = None
        last_live_advanced_s: float | None = None
        duration_details: dict[str, Any] = {}
        loop_error: Exception | None = None
        server_cap_candidate: dict[str, Any] | None = None
        try:
            startup_deadline = command_started_s + 8.0
            self.event("walk_request", {
                "vx_m_s": vx, "vy_m_s": vy,
                "duration_s": self.args.duration_s,
                "yaw_command": 0.0, "transport": "drive",
                "duration_basis": "confirmed_active_walk_wall_time",
                "startup_timeout_s": 8.0,
            })
            while (activation_s is None
                   or time.monotonic() - activation_s < self.args.duration_s):
                self.recorder.assert_live()
                if activation_s is None and time.monotonic() >= startup_deadline:
                    raise RuntimeError("drive did not engage within 8 seconds")
                response = self.request("/api/rl/drive/cmd", {
                    "vx": vx, "vy": vy, "wz": 0.0, "dh": 0.0,
                    "command_owner": self._drive_command_owner,
                })
                now = time.monotonic()
                elapsed_active_s = (now - activation_s
                                    if activation_s is not None else None)
                server_cap_complete = (
                    activation_s is not None
                    and response.get("active") is False
                    and elapsed_active_s is not None
                    and elapsed_active_s >= self.args.duration_s - 0.25
                ) if isinstance(response, dict) else False
                if server_cap_complete:
                    server_cap_candidate = {
                        "host_elapsed_active_s": elapsed_active_s,
                        "response": response,
                    }
                    break
                if (not isinstance(response, dict) or not response.get("ok")
                        or response.get("active") is not True):
                    raise RuntimeError(f"drive command refused or session ended: {response}")
                if activation_s is None and now >= startup_deadline:
                    raise RuntimeError("drive did not engage within 8 seconds")
                if (activation_s is not None and last_live_advanced_s is not None
                        and now - last_live_advanced_s > 0.6):
                    raise RuntimeError("drive live progress stopped advancing")
                live = response.get("live") or {}
                if isinstance(response.get("live"), dict):
                    self.event("drive_live", response["live"])
                if live.get("stopping"):
                    raise RuntimeError(f"controller stopped during drive: {live}")
                try:
                    live_t = float(live.get("t_s"))
                except (TypeError, ValueError):
                    live_t = float("nan")
                advanced = (math.isfinite(live_t)
                            and (last_live_t is None or live_t > last_live_t))
                if advanced:
                    last_live_t = live_t
                    last_live_advanced_s = now
                # live.t_s is a rounded policy clock, used only as a progress
                # marker. The duration itself uses this host's monotonic clock.
                engaged = (live.get("model") == "walk"
                           and live.get("walk_has_engaged") is True
                           and live.get("learned_policy_active") is True
                           and live.get("walk_arming") is False)
                try:
                    command_matches = all(
                        abs(float(live[key]) - expected) <= 0.00051
                        for key, expected in (("vx_cmd", vx), ("vy_cmd", vy),
                                              ("wz_cmd", 0.0)))
                except (KeyError, TypeError, ValueError):
                    command_matches = False
                if activation_s is None:
                    if advanced and engaged and command_matches:
                        activation_s = now
                        activation_unix_s = time.time()
                        self.event("drive_walk_activated", {
                            "activation_unix_s": activation_unix_s,
                            "activation_monotonic_s": activation_s,
                            "startup_duration_s": now - started_monotonic_s,
                            "live": live,
                        })
                elif not engaged or not command_matches:
                    raise RuntimeError(f"drive activation or command changed: {live}")
                elif (last_live_advanced_s is None
                      or now - last_live_advanced_s > 0.6):
                    raise RuntimeError("drive live progress stopped advancing")
                samples += 1
                time.sleep(0.05)
        except Exception as error:
            loop_error = error
            self.event("drive_command_error", str(error))
        finally:
            stop_requested_s = time.monotonic()
            duration_details = {
                "requested_active_duration_s": self.args.duration_s,
                "activation_unix_s": activation_unix_s,
                "activation_monotonic_s": activation_s,
                "startup_duration_s": (activation_s - started_monotonic_s
                                       if activation_s is not None else None),
                "command_duration_s": stop_requested_s - command_started_s,
                "confirmed_active_window_s": (stop_requested_s - activation_s
                                              if activation_s is not None else 0.0),
                "duration_basis": "host_wall_time_since_confirmed_walk",
            }
            self.event("drive_duration", duration_details)
            try:
                stop = self.request("/api/rl/drive/stop", {})
                self.event("drive_stop", stop)
            except Exception as error:
                self.event("drive_stop_error", str(error))
                if loop_error is None:
                    loop_error = error
        try:
            terminal_result = stop.get("result") if isinstance(stop, dict) else None
            if (isinstance(terminal_result, dict)
                    and not stop.get("active")):
                result = terminal_result
            else:
                result = self.wait_job(name, 25.0)
        except Exception as error:
            self.event("drive_terminal_error", str(error))
            result = {"ok": False, "error": f"terminal result unavailable: {error}"}
            if loop_error is None:
                loop_error = error
        expected_cap_end = (
            f"active walk cap {self.args.duration_s:g}s reached")
        try:
            duration_limit_matches = math.isclose(
                float(result.get("active_duration_limit_s")),
                float(self.args.duration_s), rel_tol=0.0, abs_tol=1e-9)
            active_wall_time_s = float(result.get("active_wall_time_s"))
        except (AttributeError, TypeError, ValueError):
            duration_limit_matches = False
            active_wall_time_s = float("nan")
        duration_evidence_matches = (
            isinstance(result, dict)
            and result.get("ok") is True
            and result.get("ended") in (expected_cap_end, "stopped")
            and duration_limit_matches
            and math.isfinite(active_wall_time_s)
            and active_wall_time_s >= self.args.duration_s
        )
        duration_detail = {
            **(server_cap_candidate or {}),
            "result": result,
        }
        if duration_evidence_matches and result.get("ended") == expected_cap_end:
            self.event("drive_server_duration_limit_observed", duration_detail)
        elif duration_evidence_matches:
            self.event("drive_host_duration_stop_confirmed", duration_detail)
        else:
            error = RuntimeError(
                "drive ended without matching controller-side active-duration "
                f"evidence: {result}")
            self.event("drive_server_duration_limit_mismatch", duration_detail)
            if loop_error is None:
                loop_error = error
        try:
            logs = self.pull_policy_logs(started_unix_s, "rl_drive_")
        except Exception as error:
            self.event("drive_log_pull_error", str(error))
            logs = []
            if loop_error is None:
                loop_error = error
        self.results.append({
            "phase": name,
            "transport": "drive_100hz_combined_snapshot",
            "request": {"vx": vx, "vy": vy},
            "command_samples": samples,
            **duration_details,
            "stop": stop,
            "result": result,
            "robot_logs": logs,
            "trial_error": str(loop_error) if loop_error is not None else None,
        })
        try:
            self.snapshot(f"after_{name}")
        except Exception:
            if loop_error is None:
                raise
        if loop_error is not None:
            raise loop_error
        if not result.get("ok"):
            raise RuntimeError(f"drive {name} failed: {result}")
        self.three_fresh_health_samples(require_armed=True)

    def direction_course(self) -> None:
        self.phase = "direction_course"
        started_unix_s = time.time()
        reply = self.request("/api/rl/drive/start", self.drive_start_payload())
        self.event("course_start", reply)
        if not isinstance(reply, dict) or not reply.get("ok"):
            raise RuntimeError(f"drive start refused: {reply}")
        segment_results = []
        try:
            for name in COURSE:
                unit_x, unit_y = DIRECTIONS[name]
                vx = unit_x * self.args.speed_m_s
                vy = unit_y * self.args.speed_m_s
                self.event("course_segment", {
                    "name": name, "vx_m_s": vx, "vy_m_s": vy,
                    "seconds": self.args.course_segment_s, "wz": 0.0,
                })
                deadline = time.monotonic() + self.args.course_segment_s
                command_samples = 0
                while time.monotonic() < deadline:
                    self.recorder.assert_live()
                    response = self.request("/api/rl/drive/cmd", {
                        "vx": vx, "vy": vy, "wz": 0.0, "dh": 0.0,
                        "command_owner": self._drive_command_owner,
                    })
                    if not isinstance(response, dict) or not response.get("ok"):
                        raise RuntimeError(f"drive command refused: {response}")
                    if isinstance(response.get("live"), dict):
                        self.event("drive_live", response["live"])
                    command_samples += 1
                    time.sleep(0.05)
                segment_results.append({"name": name, "command_samples": command_samples})
        finally:
            stop = self.request("/api/rl/drive/stop", {})
            self.event("course_stop", stop)
        result = self.wait_job("course", 20.0)
        logs = self.pull_policy_logs(started_unix_s, "rl_drive_")
        self.results.append({
            "phase": "course", "segments": segment_results, "result": result,
            "robot_logs": logs,
        })
        self.snapshot("after_course")
        if not result.get("ok"):
            raise RuntimeError(f"direction course failed: {result}")
        self.three_fresh_health_samples(require_armed=True)

    def planned_lower(self) -> None:
        self.phase = "planned_lower"
        lower_preflight = self.request("/api/rl/preflight?mode=lower")
        self.event("lower_preflight", lower_preflight)
        if (not isinstance(lower_preflight, dict)
                or not lower_preflight.get("ok")):
            # A drive stop hands off to the learned hold policy, whose quiet
            # pose can be a few tenths outside the STEP lower's walk-ready
            # envelope.  Re-settle through the established STEP stand route
            # before lowering instead of forcing lower from an arbitrary gait
            # phase.
            self.event("lower_walk_ready_resettle_requested", lower_preflight)
            stand_reply = self.request("/api/rl/stand", {})
            self.event("lower_resettle_start", stand_reply)
            if (not isinstance(stand_reply, dict)
                    or not stand_reply.get("ok")):
                raise RuntimeError(
                    f"lower re-settle stand refused: {stand_reply}"
                )
            stand_result = self.wait_job("lower_resettle", 45.0)
            if not stand_result.get("ok"):
                error = str(stand_result.get("error") or "")
                verification_only = (
                    "walk-ready start failed verification" in error
                )
                post = (self.request("/api/rl/preflight?mode=lower")
                        if verification_only else None)
                if (verification_only and isinstance(post, dict)
                        and post.get("ok")):
                    self.event("lower_resettle_verification_accepted", {
                        "stand_result": stand_result,
                        "lower_preflight": post,
                    })
                else:
                    raise RuntimeError(
                        f"lower re-settle stand failed: {stand_result}"
                    )
            lower_preflight = self.request("/api/rl/preflight?mode=lower")
            self.event("lower_preflight_after_resettle", lower_preflight)
            if (not isinstance(lower_preflight, dict)
                    or not lower_preflight.get("ok")):
                raise RuntimeError(
                    f"lower preflight still failed after re-settle: "
                    f"{lower_preflight}"
                )
        reply = self.request("/api/rl/lower", {})
        self.event("lower_start", reply)
        if not isinstance(reply, dict) or not reply.get("ok"):
            raise RuntimeError(f"lower refused: {reply}")
        result = self.wait_job("lower", 45.0)
        if not result.get("ok"):
            raise RuntimeError(f"lower failed: {result}")
        limp = _request(self.base, "/cmd", text_body="X", timeout=5.0)
        self.event("planned_limp", limp)
        self.motion_started = False
        self.completed = True

    def write_summary(self, *, error: str | None = None) -> None:
        policy = self.request("/api/rl/policy")
        summary = {
            "ok": error is None and self.completed,
            "error": error,
            "policy": policy,
            "requested_phases": self.args.phases,
            "speed_m_s": self.args.speed_m_s,
            "duration_s": self.args.duration_s,
            "course_segment_s": self.args.course_segment_s,
            "yaw_commands": False,
            "results": self.results,
            "artifacts": {
                "video": "camera_raw.mp4",
                "camera_timestamps": "camera_timestamps.csv",
                "telemetry": "telemetry.csv",
                "events": "events.csv",
            },
        }
        (self.output_dir / "summary.json").write_text(
            json.dumps(summary, indent=2) + "\n"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--robot-url", default="http://192.168.4.39:8080")
    parser.add_argument("--camera-index", type=int, default=1)
    parser.add_argument(
        "--vision-frame-url",
        help=("record a JPEG stream with a trustworthy X-Capture-Unix-S "
              "header instead of opening AVFoundation directly; streams "
              "without capture timestamps are refused before motion"),
    )
    parser.add_argument(
        "--learned-rise", action="store_true",
        help=("opt in to the explicit stand-role RL rise instead of the "
              "known STEP rise; requires a runnable stand role"),
    )
    parser.add_argument(
        "--learned-rise-tilt-trip-deg", type=float, default=8.0,
        help="roll/pitch trip for --learned-rise (robot clamps to 5..30 deg)",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--phases", nargs="+", choices=(*DIRECTIONS, "course"),
        default=["forward"],
    )
    parser.add_argument("--speed-m-s", type=float, default=0.08)
    parser.add_argument("--duration-s", type=float, default=3.0)
    parser.add_argument("--course-segment-s", type=float, default=2.0)
    parser.add_argument("--temp-trip-c", type=float, default=55.0)
    parser.add_argument(
        "--velocity-filter-alpha", type=float, default=None,
        help="per-session joint-velocity filter alpha in [0, 1]; drive path only",
    )
    parser.add_argument(
        "--walk-transport", choices=("timed", "drive"), default="timed",
        help=("timed uses /api/rl/walk; drive uses the live 100 Hz policy "
              "loop with a combined motor-command/snapshot transaction each tick"),
    )
    parser.add_argument(
        "--resume-walk-ready", action="store_true",
        help=("allow a non-zero starting pose only when the robot's "
              "read-only walk preflight confirms it is already near the "
              "sim walk-ready stance; the normal STEP stand route still "
              "re-arms and re-settles it before policy motion"),
    )
    parser.add_argument(
        "--acquire-current", action="store_true",
        help=("allow the robot's guarded start-acquisition routine to "
              "recover a visually checked non-zero pose before STEP stand; "
              "walk motion remains gated by post-acquisition preflight"),
    )
    parser.add_argument(
        "--tuck-recovery", action="store_true",
        help=("from an operator/camera-verified belly-down untrapped pose, "
              "run the guarded tuck stand with force-start before the "
              "normal walk-ready settle; use when grounded safe-zero is "
              "blocked by carpet friction"),
    )
    parser.add_argument(
        "--keep-current-walk-ready", action="store_true",
        help=("reuse an already armed pose after read-only walk preflight and "
              "three fresh health samples; avoids an unnecessary stand "
              "transition during a recoverable retry"),
    )
    args = parser.parse_args()
    if args.velocity_filter_alpha is not None:
        if (not math.isfinite(args.velocity_filter_alpha)
                or not 0.0 <= args.velocity_filter_alpha <= 1.0):
            parser.error("--velocity-filter-alpha must be finite and in [0, 1]")
        if args.walk_transport != "drive":
            parser.error("--velocity-filter-alpha requires --walk-transport drive")
    if not 0.0 < args.speed_m_s <= 0.08:
        parser.error("--speed-m-s must be in (0, 0.08]")
    if not 3.0 <= args.duration_s <= 20.0:
        parser.error("--duration-s must be in [3, 20]")
    if not 1.0 <= args.course_segment_s <= 5.0:
        parser.error("--course-segment-s must be in [1, 5]")
    if not 5.0 <= args.learned_rise_tilt_trip_deg <= 30.0:
        parser.error("--learned-rise-tilt-trip-deg must be in [5, 30]")

    stamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir / f"rl_walk_trial_{stamp}"
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "config.json").write_text(
        json.dumps({**vars(args), "output_dir": str(output_dir)}, default=str, indent=2)
        + "\n"
    )
    print(f"OUTPUT_DIR={output_dir}", flush=True)
    trial = Trial(args, output_dir)
    error: str | None = None
    try:
        trial.recorder.start()
        trial.event("recorder_ready")
        trial.stand_walk_ready()
        for phase in args.phases:
            if phase == "course":
                trial.direction_course()
            elif args.walk_transport == "drive":
                trial.drive_leg(phase)
            else:
                trial.timed_leg(phase)
        trial.planned_lower()
        trial.event("trial_complete")
        return 0
    except Exception as issue:
        error = str(issue)
        trial.event("trial_error", error)
        limped_for_confirmed_health = False
        if isinstance(issue, ConfirmedHealthTrip):
            try:
                limped = _request(
                    trial.base, "/cmd", text_body="X", timeout=5.0,
                )
                limped_for_confirmed_health = True
                trial.event("confirmed_health_limp", limped)
            except Exception as limp_error:
                trial.event("confirmed_health_limp_error", str(limp_error))
        elif trial.motion_started:
            try:
                stopped = trial.request("/api/rl/stop", {})
                trial.event("failure_pause", stopped)
            except Exception as stop_error:
                trial.event("failure_pause_error", str(stop_error))
        try:
            trial.snapshot("failure")
        except Exception as camera_error:
            trial.event("failure_camera_error", str(camera_error))
        try:
            trial.three_fresh_health_samples(require_armed=False)
        except ConfirmedHealthTrip as health_error:
            trial.event("failure_health_error", str(health_error))
            if not limped_for_confirmed_health:
                try:
                    limped = _request(
                        trial.base, "/cmd", text_body="X", timeout=5.0,
                    )
                    trial.event("confirmed_health_limp", limped)
                except Exception as limp_error:
                    trial.event(
                        "confirmed_health_limp_error", str(limp_error)
                    )
        except Exception as health_error:
            # An unavailable health snapshot is not itself proof of a tip,
            # hot motor, or lost servo.  Preserve the paused pose and report;
            # only ConfirmedHealthTrip above authorizes the automatic limp.
            trial.event("failure_health_error", str(health_error))
        return 1
    finally:
        trial.recorder.stop()
        trial.event("recorder_stopped", {
            "frames": trial.recorder.frames, "error": trial.recorder.error,
        })
        try:
            trial.write_summary(error=error)
        finally:
            trial.close()


if __name__ == "__main__":
    raise SystemExit(main())
