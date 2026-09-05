"""Build operator-only Robot Lab specifications and audit saved walking evidence.

This module has no robot/network client and never executes a generated command.
Run from prototype_sts3215 with ``uv run python -m rl_move.scripts.hardware_walk_benchmark``.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "hexapod.hardware_walk_benchmark.v1"
POLICY = "hardware-walk-noyaw-v2-canary"
FROZEN_POLICY = {
    "checkpoint_sha256": "250643a45ec5acf33004896a26af6129a4dcb5484109963ea93c4a8e97dbc72f",
    "export_json_sha256": "58a9bbf7862dba467aeeba534225ffb450d69b4f3302fe22637cda955fee8d6d",
    "joint_frame": "robot_abs", "joint_contract": "robot_abs_tibia_v2",
    "obs_dim": 74, "model_source": "mesh", "policy_hz": 100,
    "bus_write_hz": 50, "snapshot_hz": 10,
    "phase_hz": 1.333333, "walk_obs_body_vel": 2,
    "speed_min_m_s": .08, "speed_max_m_s": .08, "yaw_commands": False,
    "write_speed": 400, "write_acc": 20, "max_delta_q_deg": .375,
    "training_resolved_vel_max_counts_s": 350,
}
CONTROLLER_FILES = ("linux_control/rl_policy.py", "rl_move/robot_state.py",
                    "rl_move/safety.py", "rl_move/scripts/run_rl_walk_trial.py",
                    "linux_control/api/rl.py", "linux_control/mcu_feetech_bus.py",
                    "linux_control/async_bus_guard.py")
WALL_CLOCKS = ("mono_s", "wall_elapsed_s", "unix_s")
MAX_CONTINUOUS_LOG_GAP_S = .25


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(value: Any) -> float | None:
    try:
        out = float(value)
        return out if math.isfinite(out) else None
    except (TypeError, ValueError):
        return None


def stats(values: list[float]) -> dict[str, Any]:
    values = sorted(values)
    if not values:
        return {"n": 0, "min": None, "median": None, "p95": None, "max": None}
    return {"n": len(values), "min": values[0], "median": statistics.median(values),
            "p95": values[int(.95 * (len(values) - 1))], "max": values[-1]}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def validate_target_only_protocol(protocol: dict, leg: int) -> list[int]:
    """Check every transition, including home acquisition and segment edges.

    Per-segment ranges miss a non-target joint held at a different constant
    angle in each segment. Only the trajectory form used by these screened
    protocols is accepted; another segment type needs a separate audit.
    """
    home = protocol.get("home_deg")
    if not isinstance(home, list) or len(home) != 18 or any(number(v) is None for v in home):
        raise ValueError("Planted protocol needs 18 finite home targets")
    commands = [home]
    segments = protocol.get("segments")
    if not isinstance(segments, list) or not segments:
        raise ValueError("Planted protocol has no trajectory segments")
    for segment in segments:
        if segment.get("kind") != "traj":
            raise ValueError("Planted protocol uses an unaudited segment type")
        rows, times = segment.get("q_deg"), segment.get("t_s")
        if (not isinstance(rows, list) or not isinstance(times, list)
                or len(rows) < 2 or len(rows) != len(times)
                or any(number(t) is None for t in times)
                or any(float(b) <= float(a) for a, b in zip(times, times[1:]))
                or any(not isinstance(row, list) or len(row) != 18
                       or any(number(v) is None for v in row) for row in rows)):
            raise ValueError("Planted trajectory shape or timestamps are invalid")
        commands.extend(rows)
    moving = sorted(j for j in range(18)
                    if any(abs(float(row[j]) - float(home[j])) > 1e-7 for row in commands))
    if moving != [3 * leg + 1, 3 * leg + 2]:
        raise ValueError(f"Unexpected moving joints across home/segments: {moving}")
    return moving


def row_stats(rows: list[dict], key: str) -> dict:
    return stats([v for row in rows if (v := number(row.get(key))) is not None])


def true(value: Any) -> bool:
    return str(value).lower() in {"1", "1.0", "true"}


def engaged_interval(rows: list[dict]) -> dict:
    """An explicit engagement flag + advancing wall clock is required.

    t_s in historical robot logs is scheduled time. Neither it nor the host's
    command-request window proves when the learned walk actually engaged.
    """
    clock = next((key for key in WALL_CLOCKS
                  if rows and all(number(row.get(key)) is not None for row in rows)), None)
    flag = next((key for key in ("walk_engaged", "learned_policy_active")
                 if rows and all(row.get(key) not in (None, "") for row in rows)), None)
    unavailable = {"seconds": None, "clock": clock, "start": None, "end": None,
                   "basis": "unavailable", "gaps": None}
    if clock is None or flag is None:
        return {**unavailable, "reason": "Missing per-tick wall clock or explicit engagement flag; nominal t_s is not wall time."}
    timestamps = [float(row[clock]) for row in rows]
    if any(b <= a for a, b in zip(timestamps, timestamps[1:])):
        return {**unavailable, "reason": "Wall timestamps do not advance strictly."}
    def walking(row: dict) -> bool:
        return true(row[flag]) and row.get("phase", "walk") in {"walk", "run"}
    indices = [i for i, row in enumerate(rows) if walking(row)]
    if len(indices) < 2:
        return {**unavailable, "reason": "Fewer than two explicitly engaged samples."}
    first, last = indices[0], indices[-1]
    gaps = sum(not walking(rows[i]) for i in range(first, last + 1))
    if gaps:
        return {**unavailable, "gaps": gaps,
                "reason": "Engagement is interrupted; separate the continuous runs before scoring."}
    if any(b - a > MAX_CONTINUOUS_LOG_GAP_S
           for a, b in zip(timestamps[first:last], timestamps[first + 1:last + 1])):
        return {**unavailable, "reason": "An engaged log gap exceeds 250 ms; continuity is not established."}
    return {"seconds": timestamps[last] - timestamps[first], "clock": clock,
            "start": timestamps[first], "end": timestamps[last], "gaps": 0,
            "basis": "observed continuous engaged sample span; no extrapolated final tick"}


def motion_metrics(path: Path, trace: Path, interval: dict, request: dict) -> dict:
    missing = lambda why: {"available": False, "reason": why}
    if not path.exists():
        return missing("No calibrated_motion.json supplied; video pixels are not metric progress.")
    data = json.loads(path.read_text())
    if (data.get("schema") != "hexapod.calibrated_motion.v1"
            or data.get("calibration_status") != "validated"
            or not data.get("calibration_id") or data.get("frame") != "floor"
            or data.get("units") != "m" or data.get("trace_sha256") != sha256(trace)):
        return missing("Calibration provenance, floor frame, meter units, or bound trace hash is missing/invalid.")
    if interval["seconds"] is None or data.get("clock") != interval["clock"]:
        return missing("A matching measured engagement clock is required.")
    vx, vy = number(request.get("vx")), number(request.get("vy"))
    if vx is None or vy is None or math.hypot(vx, vy) <= 0:
        return missing("A constant nonzero cardinal command is required; courses need segment-level analysis.")
    samples = data.get("samples", [])
    if len(samples) < 2 or any(any(number(s.get(k)) is None for k in ("t", "x", "y", "yaw_deg")) for s in samples):
        return missing("At least two finite timed metric poses including yaw are required.")
    samples = [{key: float(s[key]) for key in ("t", "x", "y", "yaw_deg")} for s in samples]
    if any(b["t"] <= a["t"] for a, b in zip(samples, samples[1:])):
        return missing("Calibrated pose timestamps do not advance strictly.")
    start, end = interval["start"], interval["end"]
    if samples[0]["t"] > start or samples[-1]["t"] < end:
        return missing("Calibrated poses do not cover the measured engagement interval.")
    def pose_at(t: float) -> dict:
        for a, b in zip(samples, samples[1:]):
            if a["t"] <= t <= b["t"]:
                w = (t - a["t"]) / (b["t"] - a["t"])
                yaw_delta = (b["yaw_deg"] - a["yaw_deg"] + 180) % 360 - 180
                return {"x": a["x"] + w * (b["x"] - a["x"]),
                        "y": a["y"] + w * (b["y"] - a["y"]),
                        "yaw_deg": a["yaw_deg"] + w * yaw_delta}
        raise ValueError("pose interval missing")
    a, b = pose_at(start), pose_at(end)
    heading = math.radians(a["yaw_deg"]) + math.atan2(vy, vx)
    dx, dy = b["x"] - a["x"], b["y"] - a["y"]
    forward = dx * math.cos(heading) + dy * math.sin(heading)
    lateral = -dx * math.sin(heading) + dy * math.cos(heading)
    return {"available": True, "calibration_id": data["calibration_id"],
            "progress_m": forward, "lateral_m": lateral,
            "speed_m_s": forward / interval["seconds"],
            "progress_ratio": forward / (math.hypot(vx, vy) * interval["seconds"]),
            "course_error_deg": math.degrees(math.atan2(lateral, forward)),
            "yaw_change_deg": (b["yaw_deg"] - a["yaw_deg"] + 180) % 360 - 180,
            "basis": "net displacement relative to initial body heading plus constant command direction"}


def analyze_trial(directory: Path) -> dict:
    summary = json.loads((directory / "summary.json").read_text())
    events = read_csv(directory / "events.csv")
    episodes = []
    for entry in summary.get("results", []):
        result = entry.get("result", {})
        candidates = [directory / name for name in entry.get("robot_logs", [])
                      if name.endswith(".csv") and "debug" not in name]
        if not candidates:
            candidates = sorted(directory.glob("robot_rl_drive_*.csv"))
        trace = candidates[0] if len(candidates) == 1 else None
        rows = read_csv(trace) if trace else []
        active = [row for row in rows if row.get("phase") in {"walk", "run"}]
        # Keep hold rows so filtering cannot bridge a known pause between two
        # walk segments. Tail rows deliberately have no engagement columns.
        interval = engaged_interval([row for row in rows if row.get("phase") != "tail"])
        times = [float(row["t_s"]) for row in active if number(row.get("t_s")) is not None]
        clock = interval["clock"]
        wall = [float(row[clock]) for row in active] if clock else []
        cadence = (stats([1000 * (b - a) for a, b in zip(wall, wall[1:])])
                   if wall and all(b > a for a, b in zip(wall, wall[1:])) else stats([]))
        write_times = ([float(row[clock]) for row in active if true(row.get("bus_write_due"))]
                       if clock and cadence["n"] else [])
        q_keys = [f"q{i}_deg" for i in range(18)]
        repeated = sum(all(a.get(k) == b.get(k) for k in q_keys)
                       for a, b in zip(active, active[1:])) if active and all(k in active[0] for k in q_keys) else None
        command_window = None
        for event in events:
            if event.get("phase") != f"drive_{entry.get('phase')}":
                continue
            if event.get("event") == "walk_request":
                command_window = {"start": number(event.get("unix_s")), "end": None, "seconds": None}
            elif event.get("event") == "drive_stop" and command_window:
                command_window["end"] = number(event.get("unix_s"))
                if command_window["start"] is not None and command_window["end"] is not None:
                    command_window["seconds"] = command_window["end"] - command_window["start"]
        motion_path = directory / f"calibrated_motion_{entry.get('phase')}.json"
        if not motion_path.exists():
            motion_path = directory / "calibrated_motion.json"
        motion = motion_metrics(motion_path, trace, interval, entry.get("request", {})) if trace else {"available": False, "reason": "No unique raw trace."}
        episodes.append({
            "phase": entry.get("phase"), "trace": str(trace) if trace else None,
            "trace_sha256": sha256(trace) if trace and trace.exists() else None,
            "recorded_success": result.get("ok"), "recorded_fell": result.get("fell"),
            "recorded_ticks": result.get("ticks"), "recorded_overruns": result.get("overruns"),
            "requested_seconds": summary.get("duration_s"), "command_wall_window": command_window,
            "request": entry.get("request", {}),
            "nominal_trace_span_s": times[-1] - times[0] if len(times) > 1 else None,
            "engaged_wall": interval, "wall_tick_interval_ms": cadence,
            "observed_bus_write_interval_ms": stats([1000 * (b - a) for a, b in zip(write_times, write_times[1:])]),
            "declared_rates_hz": {"policy": result.get("policy_hz"), "bus_write": result.get("drive_write_hz"),
                                  "snapshot": (result.get("async_snapshot") or {}).get("snapshot_hz")},
            "service_ms": row_stats(active, "service_ms"), "write_ms": row_stats(active, "write_ms"),
            "lag_ms": row_stats(active, "lag_ms"),
            "sensor_age_ms": {key: row_stats(active, key) for key in ("state_age_ms", "position_age_ms", "imu_age_ms")},
            "repeated_joint_vectors": repeated, "adjacent_joint_vectors": max(0, len(active) - 1),
            "repeated_joint_vectors_caveat": "Repeated values indicate sample hold or stillness, not proof of a stall or measured sensor age.",
            "tilt_rel_peak_deg": result.get("tilt_rel_max_deg"), "tail_tilt_peak_deg": result.get("tail_tilt_max_deg"),
            "recorded_peak_servo_current_a": result.get("max_current_a"), "motion": motion,
            "continuous_60s_evidence": bool(interval["seconds"] is not None and interval["seconds"] >= 60),
        })
    classification = ("continuous_duration_evidence_only" if any(ep["continuous_60s_evidence"] for ep in episodes)
                      else "short_canary_or_incomplete_evidence")
    return {"directory": str(directory), "recorded_success": summary.get("ok"), "error": summary.get("error"),
            "policy": (summary.get("policy", {}).get("walk") or {}).get("run"),
            "episodes": episodes, "classification": classification,
            "note": "Success means the runner completed; this report does not promote a policy as smooth or hardware-ready."}


def analyze(directories: list[Path]) -> dict:
    # Duplicate folders cannot become independent repeats.
    unique = list(dict.fromkeys(p.resolve() for p in directories))
    trials = [analyze_trial(p) for p in unique]
    groups: dict[str, set] = {}
    for trial in trials:
        for ep in trial["episodes"]:
            if (ep["continuous_60s_evidence"] and ep["recorded_success"] is True
                    and ep["recorded_fell"] is False and ep["motion"].get("available")):
                key = json.dumps({"policy": trial["policy"], "phase": ep["phase"],
                                  "request": ep["request"]}, sort_keys=True)
                groups.setdefault(key, set()).add(ep["trace_sha256"])
    qualified = set().union(*groups.values()) if groups else set()
    return {"schema": SCHEMA, "trials": trials,
            "continuous_60s_distinct_traces_with_metric_pose": len(qualified),
            "matched_repeat_groups": [{**json.loads(key), "distinct_traces": len(traces)} for key, traces in groups.items()],
            "three_repeat_duration_and_pose_evidence": any(len(traces) >= 3 for traces in groups.values()),
            "smooth_walking_acceptance": "not_assessed; duration alone does not establish smoothness, turning, or robustness",
            "limits": ["Legacy nominal t_s never substitutes for wall-clock engagement.",
                       "Missing age/progress/current fields remain unknown.",
                       "Short runs cannot be concatenated into a 60-second acceptance."]}


def build_plan(*, include_planted: bool = False) -> dict:
    common = [
        "Wait in Robot Lab waiting_for_operator with execution_mode=external_guarded; built-in worker must never execute physical work.",
        "Stay within the operator-authorized motion scope, with the operator present and the abort path ready. Queueing is not motion authorization.",
        "Do not preempt another job. Confirm idle/disarmed/limp, visually consistent logical zero, and three distinct fresh healthy scans (18/18, IMU, normal voltage/current/temperature).",
        "Confirm live observation of the robot and its posture; tag-layout calibration is not a prerequisite for this trial.",
        "Follow EMERGENCY_HANDLING.md. Actual tip, brownout, hot motor, jam, unexpected force, support motion, or hard current ends the run without automatic retry.",
    ]
    timing = {
        "name": "Walking recovery v1: bounded forward timing canary",
        "description": "Operator-supervised repeat of the already-tested no-yaw v2 forward canary after control timing verification. One 3-second command window; arming is included by the existing runner, so measure actual engagement separately. This is not 60-second walking acceptance.",
        "duration_seconds": 3.0, "execution_mode": "external_guarded",
        "parameters": {"schema": SCHEMA, "plan_id": "walking-recovery-v1-timing-forward", "robot_id": "hexapod-1",
            "stage": "bounded_timing_canary", "policy_run": POLICY, "speed_m_s": .08, "wz_rad_s": 0,
            "command_window_s": 3, "planned_repeats": 1, "actual_engaged_duration_s": None,
            "working_directory": str(ROOT),
            "runner": "rl_move/scripts/run_rl_walk_trial.py",
            "runner_sha256": sha256(ROOT / "rl_move/scripts/run_rl_walk_trial.py"),
            "frozen_policy_contract": dict(FROZEN_POLICY),
            "controller_sha256": {name: sha256(ROOT / name) for name in CONTROLLER_FILES},
            "argv_template": ["uv", "run", "python", "-m", "rl_move.scripts.run_rl_walk_trial", "--robot-url", "<resolved-robot-http-url>",
                              "--camera-index", "<validated-direct-camera-index>", "--output-dir", "<new-evidence-directory>",
                              "--phases", "forward", "--walk-transport", "drive", "--speed-m-s", "0.08", "--duration-s", "3"],
            "prerequisites": common + [
                "Confirm walk policy robot_abs_tibia_v2, mesh, 100 Hz, fixed 0.08 m/s, phase clock metadata, and no yaw; do not rate-rescale weights or enable learned rise.",
                "Use a validated direct camera with capture timestamps. HTTP JPEG receipt time does not prove source-frame freshness; the existing unversioned JPEG endpoint is insufficient.",
                "Use existing STEP walk-ready acquisition and planned STEP lower. No absolute pose is allowed when encoders disagree with camera.",
            ],
            "analysis_notes": [
                "Record the actual policy, controller version, filter settings, and physical assembly. Source hashes are provenance; a reviewed code change does not require another canary approval solely because its hash changed.",
                "Record actual engagement, timing, and sample ages where available. Missing instrumentation limits the corresponding claims; it is not a prerequisite for trying the walk.",
                "Calibrated floor/tag measurements are optional. Without them report observed behavior and omit metric speed claims.",
            ],
            "evidence_required": ["summary.json", "events.csv", "telemetry.csv", "camera_raw.mp4", "camera_timestamps.csv", "raw robot episode CSV/debug/summary", "calibrated_motion.json if calibrated progress is measured"],
            "advance_gate": "After a stable stop without a physical fault, compare progress and visible smoothness and continue repetitions within the operator-authorized scope. Do not wait for a separate timing, tag-layout, or long-duration acceptance report.",
            "retry_rule": "Only a recoverable camera/recorder/framework or feedback failure may retry the complete bounded step up to twice after camera review and three fresh healthy scans; never retry a physical hazard automatically.",
            "excluded": ["yaw commands", "speed sweep", "learned rise", "60-second run", "automatic retry after physical fault"]}}
    loaded = []
    for leg in ((5, 4, 3, 2, 1, 0) if include_planted else ()):
        version = 2 if leg == 4 else 1
        relative = f"sysid/protocols/l{leg}_ground_radial_shear_amplitude_ladder_v{version}.json"
        protocol = json.loads((ROOT / relative).read_text())
        moving = validate_target_only_protocol(protocol, leg)
        loaded.append({
            "name": f"Walking recovery v1: supported L{leg} planted comparison",
            "description": "One operator-started target-only hip/knee radial-shear ladder with rigid chassis support. Compare every leg under the same load/contact setup; this is characterization, not automatic repair or walking acceptance.",
            "duration_seconds": 174.0, "execution_mode": "external_guarded",
            "parameters": {"schema": SCHEMA, "plan_id": f"walking-recovery-v1-planted-L{leg}", "robot_id": "hexapod-1",
                "stage": "supported_loaded_comparison", "leg": leg, "protocol": relative,
                "protocol_sha256": sha256(ROOT / relative), "motion_duration_s": 174,
                "moving_joints": sorted(moving), "amplitudes_mm": [3.75, 7.5, 11.25, 15], "cycles_per_amplitude": 3,
                "prerequisites": common + [
                    "Review completed matched six-leg air evidence and confirm no intervening mechanical changes; repeat affected air checks if needed.",
                    "Chassis must be rigidly supported; only target foot receives intended contact. Manually rotate/reseat only while limp between jobs, and re-run every preflight.",
                    "An independent external supervisor must enforce supports, target-only motion, live cameras and fresh telemetry throughout; sysid.run_hw alone does not enforce all these gates.",
                    "Require target hip/knee plus body/floor reference visible. Record the actual load; add calibrated force and proximal/distal markers before claiming absolute/component stiffness.",
                ],
                "runner": "sysid.run_hw", "runner_arguments": {"protocol": relative, "capture_vision": True, "capture_frames": True, "vision_hz": 10},
                "operator_go_required": True, "independent_supervisor_required": True,
                "safety_contract": {key: protocol[key] for key in ("hz", "write_speed", "write_acc", "soft_torque", "max_current_a", "current_trip_polls", "hard_current_a")},
                "end_state": "limp on completion, rejection, interrupt, or trip",
                "retry_rule": "No automatic current-trip retry for this coordinated hip/knee trajectory. Recoverable recording/feedback failures only: camera review + three fresh healthy samples, whole-step retry at most twice.",
                "analysis": "uv run python -m sysid.analyze_hysteresis <raw-csv>; compare signed loops, mean absolute hip/knee loops, and within-run scatter across all six legs at every amplitude.",
                "comparison_gate": "Call a leg a loaded outlier only if it separates from every peer beyond scatter and at least four encoder counts (0.352 deg), preferably >=2x largest peer, at >=3 planted amplitudes. No automatic gait/repair decision.",
            }})
    return {"schema": SCHEMA, "queue_payloads": [timing, *loaded],
            "execution_warning": "These are reviewable specifications only. This program never submits jobs or controls the robot.",
            "future_acceptance_not_queued": {"continuous_engaged_seconds_per_run": 60, "independent_repeats": 3,
                "blocked_on": ["existing walk trial CLI accepts only3–20second command windows", "bounded pilots, trustworthy timing and calibrated motion", "a separately reviewed long-run protocol, site clearance, and explicit operator authorization"],
                "required_metrics": ["actual engaged wall duration", "progress and lateral/course/yaw error", "body tilt and angular-rate smoothness", "foot clearance/slip", "current and thermal behavior", "stable stop + post-run tail"],
                "constraints": "Current no-yaw fixed-speed canary cannot establish variable-speed or turning competence."}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="write reviewable external_guarded payloads; never submit")
    plan.add_argument("--output", type=Path, required=True)
    plan.add_argument("--include-planted", action="store_true",
                      help="also include the optional six-leg supported protocols, which must exist locally")
    audit = sub.add_parser("analyze", help="analyze saved trials only")
    audit.add_argument("directories", type=Path, nargs="+")
    audit.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_plan(include_planted=args.include_planted) if args.command == "plan" else analyze(args.directories)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
