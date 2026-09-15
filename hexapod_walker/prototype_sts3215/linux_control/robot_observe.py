"""Read-only robot evidence helpers. No arm, motion, zero, or torque-off calls.

Run with ``uv run python -m linux_control.robot_observe --help``.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
import time
import urllib.request

from hexapod_core.joint_frame import N_JOINTS


def get_bytes(base: str, path: str, timeout: float = 3.0) -> bytes:
    request = urllib.request.Request(base.rstrip("/") + path, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def get_json(base: str, path: str) -> dict:
    def invalid_constant(value):
        raise ValueError(f"non-finite JSON value: {value}")

    def parse_float(value):
        number = float(value)
        if not math.isfinite(number):
            invalid_constant(value)
        return number

    try:
        value = json.loads(get_bytes(base, path), parse_constant=invalid_constant,
                           parse_float=parse_float)
        if not isinstance(value, dict):
            raise ValueError("expected a JSON object")
        return value
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": str(exc), "path": path}


def save_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def finite(value) -> bool:
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def summarize_feedback(feedback: dict, observed_unix: float | None = None) -> dict:
    """Report readings, not a motion permit or inferred foot contact."""
    now = time.time() if observed_unix is None else observed_unix
    stamp = feedback.get("t_unix")
    age = now - stamp if finite(stamp) else None
    joints = feedback.get("joints")
    joints = joints if isinstance(joints, list) else []
    fields = ("deg", "cur_a", "temp_c", "volt", "load_pct")
    missing = [i for i, joint in enumerate(joints)
               if not isinstance(joint, dict) or not all(finite(joint.get(k)) for k in fields)
               or ("raw_deg" in joint and not finite(joint["raw_deg"]))]
    valid = [j for j in joints if isinstance(j, dict)]

    def values(key):
        return [j[key] for j in valid if finite(j.get(key))]

    return {
        "t_unix": stamp if finite(stamp) else None,
        "age_s": round(age, 3) if age is not None else None,
        "fresh": age is not None and -0.5 <= age <= 2.0,
        "complete": feedback.get("ok") is True and feedback.get("live") == N_JOINTS
                    and len(joints) == N_JOINTS and not missing
                    and finite(feedback.get("roll_deg")) and finite(feedback.get("pitch_deg")),
        "live": feedback.get("live"),
        "raw_positions_available": len(joints) == N_JOINTS
                                   and all(isinstance(j, dict) and finite(j.get("raw_deg")) for j in joints),
        "invalid_joint_indices": missing,
        "max_current_a": max(map(abs, values("cur_a")), default=None),
        "max_load_pct": max(map(abs, values("load_pct")), default=None),
        "max_temp_c": max(values("temp_c"), default=None),
        "voltage_range": [min(values("volt"), default=None), max(values("volt"), default=None)],
        "max_abs_logical_deg": max(map(abs, values("deg")), default=None),
        "roll_deg": feedback.get("roll_deg") if finite(feedback.get("roll_deg")) else None,
        "pitch_deg": feedback.get("pitch_deg") if finite(feedback.get("pitch_deg")) else None,
        "error": feedback.get("error"),
    }


def read_feedback(robot_url: str) -> dict:
    feedback = get_json(robot_url, "/api/feedback")
    observed = time.time()
    return {"observed_unix": observed, "feedback": feedback,
            "summary": summarize_feedback(feedback, observed)}


def complete_status(status: dict) -> bool:
    demo = status.get("demo")
    return (not status.get("error") and isinstance(status.get("armed"), bool)
            and isinstance(demo, dict) and isinstance(demo.get("running"), bool))


def collect_feedback(robot_url: str, *, attempts: int = 12, interval: float = 0.35) -> dict:
    """Collect three consecutive complete, fresh, distinct scans; keep all attempts.

    Cached duplicate scans do not count. Incomplete/stale scans reset the run.
    Electrical/thermal readings remain evidence for the operator to interpret.
    """
    rows, accepted = [], []
    last_stamp = None
    for index in range(attempts):
        row = read_feedback(robot_url)
        rows.append(row)
        summary = row["summary"]
        stamp = summary["t_unix"]
        if not summary["complete"] or not summary["fresh"]:
            accepted = []
        elif last_stamp is not None and stamp < last_stamp:
            accepted = []
        elif stamp != last_stamp:
            accepted.append(row)
        if stamp is not None:
            last_stamp = stamp
        if len(accepted) == 3:
            break
        if index + 1 < attempts:
            time.sleep(interval)
    return {"three_fresh_complete_samples": len(accepted) == 3,
            "samples": accepted, "attempts": rows}


def capture_camera(camera_url: str, camera_id: int, out: Path) -> dict:
    started = time.time()
    path = out / f"camera{camera_id}.jpg"
    try:
        data = get_bytes(camera_url, f"/snapshot/{camera_id}.jpg")
        if not (data.startswith(b"\xff\xd8") and data.rstrip().endswith(b"\xff\xd9")):
            raise ValueError("camera did not return a complete JPEG")
        with path.open("xb") as stream:
            stream.write(data)
        return {"ok": True, "path": str(path.resolve()), "bytes": len(data),
                "request_started_unix": started, "received_unix": time.time()}
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": str(exc), "request_started_unix": started,
                "received_unix": time.time()}


def capture_snapshot(robot_url: str, camera_url: str, out: Path) -> dict:
    """One evidence bundle, preserving partial results when one camera/read fails."""
    out.mkdir(parents=True, exist_ok=False)
    with ThreadPoolExecutor(max_workers=4) as pool:
        cameras = [pool.submit(capture_camera, camera_url, i, out) for i in (0, 1)]
        status = pool.submit(get_json, robot_url, "/api/demo/status")
        feedback = pool.submit(collect_feedback, robot_url)
        report = {"robot_url": robot_url, "camera_url": camera_url,
                  "cameras": [future.result() for future in cameras],
                  "status": status.result(), "feedback": feedback.result()}
    report["observations_complete"] = (
        all(camera["ok"] for camera in report["cameras"])
        and complete_status(report["status"])
        and report["feedback"]["three_fresh_complete_samples"])
    report["interpretation"] = (
        "Read-only evidence, not a motion clearance. Inspect both images and electrical/thermal "
        "readings. Camera receive time does not prove sensor frame freshness or foot contact.")
    save_json(out / "observation.json", report)
    return report


def watch_feedback(robot_url: str, out: Path, seconds: float, interval: float) -> dict:
    """Bounded passive JSONL recording; never changes torque on error or exit."""
    if not finite(seconds) or not 0 < seconds <= 1800:
        raise ValueError("seconds must be finite, > 0 and <= 1800")
    if not finite(interval) or not 0.1 <= interval <= 60:
        raise ValueError("interval must be finite and between 0.1 and 60 seconds")
    out.parent.mkdir(parents=True, exist_ok=True)
    count, invalid = 0, 0
    end = time.monotonic() + seconds
    last = None
    with out.open("x") as stream:
        while time.monotonic() < end:
            row = read_feedback(robot_url)
            stream.write(json.dumps(row, allow_nan=False) + "\n")
            stream.flush()
            count += 1
            last = row["summary"]
            invalid += not (last["fresh"] and last["complete"])
            time.sleep(min(interval, max(0, end - time.monotonic())))
    return {"path": str(out.resolve()), "samples": count, "invalid_or_stale": invalid,
            "last": last, "observer_only": True}


def summarize_trial(path: Path) -> dict:
    """Summarize the saved recovery-nudge trial format without hardware reads."""
    path = path / "trial.json" if path.is_dir() else path
    data = json.loads(path.read_text())
    result = data.get("result", {})
    command = data.get("command", {})
    phases = command.get("phases", [{"deltas_deg": command.get("deltas_deg", {})}])
    movers = {str(j) for phase in phases for j in phase.get("deltas_deg", {})}
    keys = ("before_deg", "target_deg", "reached_deg", "after_deg", "peak_current_a",
            "max_load_pct", "max_support_drift_deg")
    summary = {key: result.get(key) for key in
               ("ok", "error", "active_seconds", "torque_off", "max_pair_error_deg", "phase_index")}
    summary["prediction"] = data.get("prediction")
    summary["phases"] = [{key: phase.get(key) for key in ("index", "settled", "elapsed_s")}
                         for phase in result.get("phases", [])]
    summary["joints"] = {j: {key: value.get(key) for key in keys}
                         for j, value in result.get("joints", {}).items()
                         if j in movers or (value.get("peak_current_a") or 0) > 0.05}
    after = data.get("after_feedback", {})
    summary["after_feedback"] = summarize_feedback(after)
    # A historical artifact must never masquerade as live/fresh telemetry.
    summary["after_feedback"].pop("age_s")
    summary["after_feedback"].pop("fresh")
    summary["after_feedback"]["historical"] = True
    summary["joint_angles"] = [
        {"index": i, "raw_deg": joint.get("raw_deg"), "logical_deg": joint.get("deg")}
        for i, joint in enumerate(after.get("joints", []))]
    monitor_path = path.parent / "body-monitor.json"
    monitor = json.loads(monitor_path.read_text()) if monitor_path.exists() else []
    for key in ("roll_deg", "pitch_deg"):
        values = [row.get("feedback", {}).get(key) for row in monitor]
        summary["max_abs_" + key] = max((abs(v) for v in values if finite(v)), default=None)
    summary["physical_outcome"] = "Inspect recorded images; encoder progress does not establish support or release."
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--robot-url", default=os.environ.get("HEXAPOD_HOST", "http://hexapod.local:8080"))
    parser.add_argument("--camera-url", default=os.environ.get("HEXAPOD_CAMERA_URL"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="compact controller state and one telemetry sample")
    snapshot = commands.add_parser("snapshot", help="both cameras + three distinct fresh scans + controller state")
    snapshot.add_argument("--out", type=Path, required=True, help="new output directory (never overwritten)")
    watch = commands.add_parser("watch", help="bounded passive telemetry JSONL; no abort/hold behavior")
    watch.add_argument("--out", type=Path, required=True, help="new JSONL file (never overwritten)")
    watch.add_argument("--seconds", type=float, default=10)
    watch.add_argument("--interval", type=float, default=0.5)
    trial = commands.add_parser("trial", help="offline summary of a saved recovery-nudge trial")
    trial.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot":
            if not args.camera_url:
                parser.error("snapshot requires --camera-url or HEXAPOD_CAMERA_URL")
            report = capture_snapshot(args.robot_url, args.camera_url, args.out)
            result = {"path": str((args.out / "observation.json").resolve()),
                      "observations_complete": report["observations_complete"],
                      "cameras": report["cameras"], "demo": report["status"].get("demo"),
                      "armed": report["status"].get("armed"),
                      "feedback": [row["summary"] for row in report["feedback"]["samples"]],
                      "interpretation": report["interpretation"]}
            code = 0 if report["observations_complete"] else 2
        elif args.command == "watch":
            result = watch_feedback(args.robot_url, args.out, args.seconds, args.interval)
            code = 0 if result["samples"] and not result["invalid_or_stale"] else 2
        elif args.command == "trial":
            result, code = summarize_trial(args.path), 0
        else:
            with ThreadPoolExecutor(max_workers=2) as pool:
                state_future = pool.submit(get_json, args.robot_url, "/api/demo/status")
                row = read_feedback(args.robot_url)
                state = state_future.result()
            result = {"armed": state.get("armed"), "mode": state.get("mode"),
                      "demo": state.get("demo"), "servo": state.get("servo"),
                      "status_error": state.get("error"), "feedback": row["summary"]}
            code = 0 if complete_status(state) and row["summary"]["complete"] and row["summary"]["fresh"] else 2
        print(json.dumps(result, indent=2, allow_nan=False))
        return code
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
