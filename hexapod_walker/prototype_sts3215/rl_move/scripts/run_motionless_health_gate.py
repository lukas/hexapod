#!/usr/bin/env python3
"""Capture a bounded, read-only robot health gate.

Only HTTP GET requests are issued.  The runner has no motor-control endpoint,
does not import the robot bus, and rejects an armed robot before accepting any
sample.  The hardware lane supplies resolved HTTP/camera URLs and an unused
evidence directory.
"""
from __future__ import annotations

import argparse
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable


class GateRejected(RuntimeError):
    """The live evidence did not satisfy the motionless gate."""


def _safe_url(value: str, label: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{label} must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(f"{label} may not contain credentials, query, or fragment")
    return value.rstrip("/")


def _get(url: str, *, timeout: float = 5.0) -> tuple[bytes, dict[str, str]]:
    request = urllib.request.Request(url, method="GET", headers={"Cache-Control": "no-cache"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.read(), dict(response.headers.items())
    except urllib.error.HTTPError as error:
        raise GateRejected(f"GET failed with HTTP {error.code}") from error


def _finite(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise GateRejected(f"invalid {label}") from error
    if not math.isfinite(number):
        raise GateRejected(f"invalid {label}")
    return number


def evaluate_sample(
    robot: Any,
    feedback: Any,
    *,
    previous_feedback_time: float | None,
    max_state_age_s: float,
    max_temperature_c: float,
    min_voltage_v: float,
    max_voltage_v: float,
    max_joint_current_a: float,
    max_bus_current_a: float,
    now_unix: float,
) -> dict[str, Any]:
    """Validate one fresh complete unarmed sample and retain all 18 records."""
    if not isinstance(robot, dict) or not isinstance(feedback, dict):
        raise GateRejected("robot or feedback response is not an object")
    if robot.get("armed") is not False:
        raise GateRejected("robot is armed")
    servo = robot.get("servo")
    if not isinstance(servo, dict):
        raise GateRejected("robot response lacks servo health")
    if servo.get("tripped"):
        raise GateRejected("servo watchdog reports a tripped ID")
    if servo.get("missing"):
        raise GateRejected("servo watchdog reports a missing ID")
    if feedback.get("ok") is not True or feedback.get("live") != 18:
        raise GateRejected("feedback does not report 18/18 live servos")
    timestamp = _finite(feedback.get("t_unix"), "feedback timestamp")
    age = now_unix - timestamp
    if age < -0.25 or age > max_state_age_s:
        raise GateRejected("feedback timestamp is stale or invalid")
    if previous_feedback_time is not None and timestamp <= previous_feedback_time:
        raise GateRejected("feedback timestamp did not advance")
    joints = feedback.get("joints")
    if not isinstance(joints, list) or len(joints) != 18:
        raise GateRejected("feedback joint coverage is not exactly 18")

    records: list[dict[str, Any]] = []
    bus_current = 0.0
    for index, joint in enumerate(joints):
        if not isinstance(joint, dict):
            raise GateRejected(f"servo {index + 1} telemetry is missing")
        temperature = _finite(joint.get("temp_c"), "temperature")
        voltage = _finite(joint.get("volt"), "voltage")
        current = abs(_finite(joint.get("cur_a"), "current"))
        if temperature >= max_temperature_c:
            raise GateRejected(f"servo {index + 1} temperature limit reached")
        if not min_voltage_v <= voltage <= max_voltage_v:
            raise GateRejected(f"servo {index + 1} voltage is out of bounds")
        if current > max_joint_current_a:
            raise GateRejected(f"servo {index + 1} current is out of bounds")
        bus_current += current
        records.append({
            "motor_id": index + 1,
            "temperature_c": temperature,
            "voltage_v": voltage,
            "current_a": current,
            "trip_state": False,
        })
    if bus_current > max_bus_current_a:
        raise GateRejected("summed bus current is out of bounds")
    return {
        "timestamp": timestamp,
        "servo_watch_timestamp": servo.get("ts"),
        "live_motor_count": 18,
        "armed": False,
        "bus_current_a": bus_current,
        "servos": records,
    }


def run_gate(
    args: argparse.Namespace,
    *,
    getter: Callable[..., tuple[bytes, dict[str, str]]] = _get,
    clock: Callable[[], float] = time.time,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    robot_base = _safe_url(args.robot_url, "robot URL")
    camera_url = _safe_url(args.vision_frame_url, "vision frame URL")
    if args.samples != 3:
        raise ValueError("the trusted gate requires exactly three samples")
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=False)
    samples: list[dict[str, Any]] = []
    camera_timestamps: list[float] = []
    started = clock()
    for index in range(args.samples):
        # Nine reads at this timeout plus the two sample intervals remain
        # inside the admitted 30-second wall-clock envelope even on failures.
        robot_raw, _ = getter(robot_base + "/api/robot", timeout=2.5)
        feedback_raw, _ = getter(robot_base + "/api/feedback", timeout=2.5)
        camera_raw, camera_headers = getter(camera_url, timeout=2.5)
        now = clock()
        try:
            robot = json.loads(robot_raw)
            feedback = json.loads(feedback_raw)
        except (TypeError, ValueError) as error:
            raise GateRejected("robot telemetry is not valid JSON") from error
        sample = evaluate_sample(
            robot,
            feedback,
            previous_feedback_time=(samples[-1]["timestamp"] if samples else None),
            max_state_age_s=args.max_state_age_s,
            max_temperature_c=args.max_temperature_c,
            min_voltage_v=args.min_voltage_v,
            max_voltage_v=args.max_voltage_v,
            max_joint_current_a=args.max_joint_current_a,
            max_bus_current_a=args.max_bus_current_a,
            now_unix=now,
        )
        header = next((value for key, value in camera_headers.items()
                       if key.lower() == "x-capture-unix-s"), None)
        camera_timestamp = _finite(header, "camera capture timestamp")
        camera_age = now - camera_timestamp
        if camera_age < -0.25 or camera_age > args.max_camera_age_s:
            raise GateRejected("camera capture timestamp is stale or invalid")
        if camera_timestamps and camera_timestamp <= camera_timestamps[-1]:
            raise GateRejected("camera capture timestamp did not advance")
        if not camera_raw:
            raise GateRejected("camera frame is empty")
        (output / f"camera_{index + 1}.jpg").write_bytes(camera_raw)
        sample["camera_capture_unix_s"] = camera_timestamp
        samples.append(sample)
        camera_timestamps.append(camera_timestamp)
        if index + 1 < args.samples:
            sleeper(args.sample_interval_s)
    return {
        "schema_version": 1,
        "executor": "run_motionless_health_gate_v1",
        "passed": True,
        "robot_motion": False,
        "motor_commands_emitted": False,
        "torque_enable_emitted": False,
        "sample_count": len(samples),
        "elapsed_s": clock() - started,
        "samples": samples,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--robot-url", required=True)
    result.add_argument("--vision-frame-url", required=True)
    result.add_argument("--output-dir", required=True, type=Path)
    result.add_argument("--samples", type=int, default=3)
    result.add_argument("--sample-interval-s", type=float, default=0.5)
    result.add_argument("--max-state-age-s", type=float, default=1.5)
    result.add_argument("--max-camera-age-s", type=float, default=2.0)
    result.add_argument("--max-temperature-c", type=float, required=True)
    result.add_argument("--min-voltage-v", type=float, required=True)
    result.add_argument("--max-voltage-v", type=float, required=True)
    result.add_argument("--max-joint-current-a", type=float, required=True)
    result.add_argument("--max-bus-current-a", type=float, required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    result_path = args.output_dir / "result.json"
    try:
        result = run_gate(args)
    except Exception as error:
        if args.output_dir.is_dir():
            result_path.write_text(json.dumps({
                "schema_version": 1,
                "executor": "run_motionless_health_gate_v1",
                "passed": False,
                "robot_motion": False,
                "motor_commands_emitted": False,
                "torque_enable_emitted": False,
                "error": str(error),
            }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
