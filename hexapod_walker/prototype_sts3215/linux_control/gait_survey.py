"""Background controller for Vision UI scripted-gait survey sessions.

The controller deliberately launches the already-audited HTTP-only hardware
suite instead of adding a second motor-control implementation to the web
process.  The Vision camera is handed to the recorder for the duration of the
run, restored afterwards, and the saved raw video is then processed offline
for AprilTag pose plus an equivalent MuJoCo replay.
"""
from __future__ import annotations

import json
import shutil
import signal
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = ROOT / "rl_move" / "hardware_traces"
POSE_CONFIG = (
    ROOT / "hexapod-tracker" / "configs" / "apriltag_pose_config_20260831.json"
)
FLOOR_MAP = ROOT / "linux_control" / "floor_tag_map_20260903.json"

GAITS = {
    0: "tripod drag",
    1: "no-slip tripod",
    2: "no-slip ripple",
    3: "no-slip wave",
    4: "SE(2) tetrapod",
    5: "SE(2) wave",
    6: "SE(2) CPG robust120",
    7: "no-slip clamp fit",
    8: "middle-tuck quad",
    9: "no-slip fluid",
    10: "no-slip fluid fast",
    11: "no-slip fluid hybrid",
    12: "no-slip fluid push",
    13: "no-slip fluid pulse",
    14: "no-slip fluid mid",
}


class GaitSurveyManager:
    """Own one bounded gait survey and expose a polling-friendly status."""

    def __init__(self, *, robot_url: str | None, vision_runtime: Any,
                 output_root: Path = DEFAULT_OUTPUT_ROOT) -> None:
        self.robot_url = None if not robot_url else robot_url.rstrip("/")
        self.vision_runtime = vision_runtime
        self.output_root = output_root
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._process: subprocess.Popen[str] | None = None
        self._stop_requested = False
        self._log: deque[str] = deque(maxlen=80)
        self._state: dict[str, Any] = {
            "status": "idle",
            "run_dir": None,
            "error": None,
            "started_unix": None,
            "completed_unix": None,
            "config": None,
            "artifacts": {},
        }

    @staticmethod
    def _validated_config(payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("acknowledge_motion") is not True:
            raise ValueError("motion acknowledgement is required")
        raw_gaits = payload.get("gaits", [1, 11])
        if not isinstance(raw_gaits, list) or not raw_gaits:
            raise ValueError("select at least one gait")
        gaits = list(dict.fromkeys(int(value) for value in raw_gaits))
        unknown = [value for value in gaits if value not in GAITS]
        if unknown:
            raise ValueError(f"unknown gait IDs: {unknown}")
        speed = float(payload.get("speed_mm_s", 30.0))
        direction_s = float(payload.get("direction_s", 8.0))
        settle_s = float(payload.get("settle_s", 1.5))
        gait1_alpha = float(payload.get("gait1_alpha", 0.75))
        max_recoveries = int(payload.get("max_recoveries", 2))
        if not 5.0 <= speed <= 40.0:
            raise ValueError("speed_mm_s must be between 5 and 40")
        if not 1.0 <= direction_s <= 20.0:
            raise ValueError("direction_s must be between 1 and 20")
        if not 0.5 <= settle_s <= 5.0:
            raise ValueError("settle_s must be between 0.5 and 5")
        if not 0.0 <= gait1_alpha <= 1.0:
            raise ValueError("gait1_alpha must be between 0 and 1")
        if not 0 <= max_recoveries <= 3:
            raise ValueError("max_recoveries must be between 0 and 3")
        return {
            "gaits": gaits,
            "speed_mm_s": speed,
            "direction_s": direction_s,
            "settle_s": settle_s,
            "gait1_alpha": gait1_alpha,
            "adaptive_centering": bool(payload.get("adaptive_centering", True)),
            "soft_recovery": (
                bool(payload.get("soft_recovery", True))
                and max_recoveries > 0
            ),
            "max_recoveries": max_recoveries,
        }

    def _preflight(self) -> tuple[int, dict[str, Any]]:
        if self.robot_url is None:
            raise RuntimeError("the Mac web hub has no robot URL configured")
        state = self.vision_runtime.public_state()
        camera = state.get("camera") or {}
        if not camera.get("enabled") or camera.get("status") != "running":
            raise RuntimeError("start the Vision camera before the gait survey")
        camera_index = camera.get("active_index")
        if camera_index is None:
            raise RuntimeError("Vision camera has not produced a frame")
        coverage = state.get("coverage") or {}
        if 0 not in (coverage.get("robot_tag_ids") or []):
            raise RuntimeError("chassis AprilTag 0 must be directly visible")
        if int(coverage.get("floor_tags", 0)) < 2:
            raise RuntimeError("at least two fixed floor tags must be visible")
        if (state.get("calibration") or {}).get("status") == "collecting":
            raise RuntimeError("cancel the stationary calibration capture first")
        safety = (state.get("pose") or {}).get("safety") or {}
        if safety.get("verdict") != "safe":
            reasons = (safety.get("unsafe_reasons")
                       or safety.get("unknown_reasons") or [])
            raise RuntimeError(
                "Vision/IMU preflight is not safe"
                + (f": {reasons[0]}" if reasons else "")
            )
        return int(camera_index), state

    def public_state(self) -> dict[str, Any]:
        with self._lock:
            status = str(self._state["status"])
            return {
                **self._state,
                "available": self.robot_url is not None,
                "active": status in {
                    "starting", "running", "stopping", "postprocessing"
                },
                "gait_choices": [
                    {"id": gait_id, "name": name}
                    for gait_id, name in GAITS.items()
                ],
                "log_tail": list(self._log)[-12:],
                "camera_note": (
                    "The survey recorder owns the camera while active; the "
                    "Vision preview returns after capture."
                ),
                "hard_stop_policy": (
                    "tip, brownout, missing servo, hard current, or failed "
                    "recovery always limp and stop; heat requires three "
                    "same-joint readings and records through cooldown"
                ),
            }

    def start(self, payload: dict[str, Any]) -> dict[str, Any]:
        config = self._validated_config(payload)
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise RuntimeError("a gait survey is already active")
        camera_index, _vision_state = self._preflight()
        with self._lock:
            self._stop_requested = False
            self._log.clear()
            self._state = {
                "status": "starting",
                "run_dir": None,
                "error": None,
                "started_unix": round(time.time(), 3),
                "completed_unix": None,
                "config": config,
                "artifacts": {},
            }
            self._thread = threading.Thread(
                target=self._run,
                args=(config, camera_index),
                name="gait-survey",
                daemon=True,
            )
            self._thread.start()
        return self.public_state()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                raise RuntimeError("no gait survey is active")
            self._stop_requested = True
            self._state["status"] = "stopping"
            process = self._process
        if process is not None and process.poll() is None:
            process.send_signal(signal.SIGINT)
        return self.public_state()

    def shutdown(self, timeout_s: float = 12.0) -> None:
        """Request a safe suite stop and wait briefly during web shutdown."""
        with self._lock:
            thread = self._thread
        if thread is None or not thread.is_alive():
            return
        try:
            self.stop()
        except RuntimeError:
            return
        thread.join(timeout=timeout_s)

    def _append_log(self, line: str) -> None:
        clean = line.rstrip()
        if clean:
            with self._lock:
                self._log.append(clean)

    def _run_command(self, command: list[str], *, label: str,
                     parse_output_dir: bool = False) -> tuple[int, Path | None]:
        self._append_log(f"{label}: starting")
        run_dir: Path | None = None
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        with self._lock:
            self._process = process
        assert process.stdout is not None
        for line in process.stdout:
            self._append_log(line)
            if parse_output_dir and line.startswith("OUTPUT_DIR="):
                run_dir = Path(line.split("=", 1)[1].strip()).resolve()
                with self._lock:
                    self._state["run_dir"] = str(run_dir)
            if self._stop_requested and process.poll() is None:
                process.send_signal(signal.SIGINT)
        code = process.wait()
        with self._lock:
            if self._process is process:
                self._process = None
        self._append_log(f"{label}: exit {code}")
        return code, run_dir

    @staticmethod
    def _uv() -> str:
        executable = shutil.which("uv")
        if executable is not None:
            return executable
        # launchd jobs inherit a deliberately small PATH on macOS, so the
        # Homebrew uv used by the project can be installed and runnable even
        # though shutil.which() cannot see it from the web service.
        for candidate in (
            Path("/opt/homebrew/bin/uv"),
            Path("/usr/local/bin/uv"),
            Path.home() / ".local" / "bin" / "uv",
        ):
            if candidate.is_file():
                return str(candidate)
        raise RuntimeError("uv is unavailable; cannot launch survey tools")

    def _postprocess(self, run_dir: Path, config: dict[str, Any], *,
                     include_sim: bool) -> dict[str, str]:
        uv = self._uv()
        artifacts: dict[str, str] = {
            "config": str(run_dir / "config.json"),
            "events": str(run_dir / "events.csv"),
            "hardware_telemetry": str(run_dir / "telemetry.csv"),
            "camera_video": str(run_dir / "iphone_raw.mp4"),
            "camera_timestamps": str(run_dir / "iphone_raw_timestamps.csv"),
        }
        raw_video = run_dir / "iphone_raw.mp4"
        if raw_video.is_file() and raw_video.stat().st_size > 0:
            pose = run_dir / "apriltag_pose.jsonl"
            annotated = run_dir / "apriltag_annotated.mp4"
            summary = run_dir / "apriltag_summary.json"
            code, _ = self._run_command([
                uv, "run", "python", "linux_control/track_apriltags.py",
                str(POSE_CONFIG), "--input", str(raw_video),
                "--pose-output", str(pose),
                "--annotated-output", str(annotated),
                "--summary-output", str(summary),
                "--processing-width", "1280",
                # The iPhone records at 30 Hz; 10 Hz pose samples are ample
                # for 3.2 s gait cycles and cut offline processing to about a
                # third without changing source timestamps.
                "--frame-step", "3",
            ], label="AprilTag processing")
            if code == 0:
                artifacts.update({
                    "apriltag_pose": str(pose),
                    "apriltag_video": str(annotated),
                    "apriltag_summary": str(summary),
                })
                motion = run_dir / "apriltag_motion.json"
                motion_code, _ = self._run_command([
                    uv, "run", "python", "-m",
                    "rl_move.scripts.analyze_apriltag_gait_motion",
                    "--run-dir", str(run_dir),
                    "--pose-jsonl", str(pose),
                    "--config", str(POSE_CONFIG),
                    "--floor-map", str(FLOOR_MAP),
                    "--output", str(motion),
                ], label="AprilTag gait motion")
                if motion_code == 0:
                    artifacts["apriltag_motion"] = str(motion)
                else:
                    self._append_log(
                        "AprilTag gait-motion analysis failed; pose retained"
                    )
            else:
                self._append_log("AprilTag processing failed; raw video retained")

        if self._stop_requested or not include_sim:
            return artifacts
        sim_dir = run_dir / "mujoco_replay"
        command = [
            uv, "run", "python", "-m",
            "rl_move.scripts.replay_scripted_gait_suite_sim",
            "--output-dir", str(sim_dir),
            "--gaits", *[str(value) for value in config["gaits"]],
            "--speed-mm-s", str(config["speed_mm_s"]),
            "--direction-s", str(config["direction_s"]),
            "--settle-s", str(config["settle_s"]),
            "--gait1-alpha", str(config["gait1_alpha"]),
            "--video", str(sim_dir / "sim_video.mp4"),
        ]
        code, _ = self._run_command(command, label="MuJoCo replay")
        if code == 0:
            sim_artifacts = {
                "mujoco_telemetry": str(sim_dir / "sim_telemetry.csv"),
                "mujoco_summary": str(sim_dir / "summary.json"),
            }
            sim_video = sim_dir / "sim_video.mp4"
            if sim_video.is_file() and sim_video.stat().st_size > 0:
                sim_artifacts["mujoco_video"] = str(sim_video)
            artifacts.update(sim_artifacts)
            comparison = run_dir / "comparison.json"
            compare_code, _ = self._run_command([
                uv, "run", "python", "-m",
                "rl_move.scripts.analyze_scripted_gait_comparison",
                "--hardware", str(run_dir),
                "--mujoco", str(sim_dir),
                "--output", str(comparison),
            ], label="sim-to-real comparison")
            if compare_code == 0:
                artifacts["comparison"] = str(comparison)
        else:
            self._append_log("MuJoCo replay failed; hardware artifacts retained")
        return artifacts

    def _run(self, config: dict[str, Any], camera_index: int) -> None:
        run_dir: Path | None = None
        artifacts: dict[str, str] = {}
        try:
            self.vision_runtime.disable_camera()
            time.sleep(0.35)
            uv = self._uv()
            command = [
                uv, "run", "python", "-m",
                "rl_move.scripts.run_scripted_gait_suite",
                "--robot-url", str(self.robot_url),
                "--camera-index", str(camera_index),
                "--output-dir", str(self.output_root),
                "--gaits", *[str(value) for value in config["gaits"]],
                "--speed-mm-s", str(config["speed_mm_s"]),
                "--direction-s", str(config["direction_s"]),
                "--settle-s", str(config["settle_s"]),
                "--gait1-alpha", str(config["gait1_alpha"]),
                "--return-to-camera-center",
                "--max-recoveries", str(config["max_recoveries"]),
            ]
            if config["adaptive_centering"]:
                command.append("--adaptive-centering")
            if config["soft_recovery"]:
                command.append("--soft-recovery")
            with self._lock:
                self._state["status"] = "running"
            code, run_dir = self._run_command(
                command, label="hardware survey", parse_output_dir=True
            )
            if run_dir is not None:
                with self._lock:
                    self._state["status"] = "postprocessing"
                artifacts = self._postprocess(
                    run_dir, config, include_sim=(code == 0)
                )
            if code != 0:
                raise RuntimeError(
                    "hardware survey stopped before completion; recordings "
                    "were retained"
                )
            if self._stop_requested:
                raise RuntimeError("survey stopped by operator")
            with self._lock:
                self._state["status"] = "complete"
        except Exception as error:
            with self._lock:
                self._state["status"] = "failed"
                self._state["error"] = str(error)
            self._append_log(f"survey failed: {error}")
        finally:
            if run_dir is not None:
                manifest = {
                    "status": self._state["status"],
                    "error": self._state.get("error"),
                    "config": config,
                    "artifacts": artifacts,
                    "completed_unix": round(time.time(), 3),
                }
                manifest_path = run_dir / "manifest.json"
                manifest_path.write_text(
                    json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
                )
                artifacts["manifest"] = str(manifest_path)
            with self._lock:
                self._state["artifacts"] = artifacts
                self._state["completed_unix"] = round(time.time(), 3)
                self._process = None
            try:
                self.vision_runtime.enable_camera(camera_index)
            except Exception as error:
                self._append_log(f"could not restore Vision camera: {error}")
