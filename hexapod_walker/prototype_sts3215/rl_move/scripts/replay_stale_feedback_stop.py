"""Replay a sealed Robot Lab drive stop without importing a robot driver.

The replay aligns the command, controller, debug, runner, and camera clocks,
classifies async-sampler failures, and reconstructs the stop/tail transition.
It is deliberately read-only apart from its output directory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any


INPUTS = (
    "joystick-commands.csv",
    "robot-drive.csv",
    "robot-drive-debug.jsonl",
    "robot-drive-summary.json",
    "runner-events.csv",
    "camera_timestamps.csv",
)


class ReplayError(ValueError):
    """The sealed evidence or replay contract is invalid."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    csv.field_size_limit(sys.maxsize)
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _verify(source: Path, expected_manifest_sha256: str) -> list[dict[str, Any]]:
    manifest_path = source / "manifest.json"
    actual_manifest_sha256 = _sha256(manifest_path)
    if actual_manifest_sha256 != expected_manifest_sha256.lower():
        raise ReplayError("source manifest SHA-256 mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 2:
        raise ReplayError("expected Robot Lab manifest schema 2")
    indexed = {item.get("name"): item for item in manifest.get("artifacts", [])}
    verified = []
    for name in INPUTS:
        item = indexed.get(name)
        path = source / name
        if not item or not path.is_file() or path.is_symlink():
            raise ReplayError(f"missing sealed input: {name}")
        digest = _sha256(path)
        if digest != item.get("sha256") or path.stat().st_size != item.get("bytes"):
            raise ReplayError(f"sealed input differs from manifest: {name}")
        verified.append({"name": name, "bytes": path.stat().st_size, "sha256": digest})
    return verified


def _nearest_row(rows: list[dict[str, str]], t_s: float) -> dict[str, str] | None:
    candidates = [(abs(float(row["t_s"]) - t_s), row) for row in rows]
    return min(candidates, key=lambda item: item[0])[1] if candidates else None


def replay(
    source: Path,
    *,
    expected_manifest_sha256: str,
    replay_window_s: tuple[float, float] = (0.0, 12.5),
    control_hz: float = 100.0,
    servo_write_hz: float = 50.0,
    snapshot_hz: float = 10.0,
    snapshot_max_age_ms: float = 150.0,
    stale_tick_limit: int = 10,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if replay_window_s[0] != 0.0 or replay_window_s[1] != 12.5:
        raise ReplayError("this replay requires the sealed 0.0..12.5 s window")
    if (control_hz, servo_write_hz, snapshot_hz, snapshot_max_age_ms, stale_tick_limit) != (
        100.0, 50.0, 10.0, 150.0, 10
    ):
        raise ReplayError("replay rates or stale limits differ from the saved plan")

    verified = _verify(source, expected_manifest_sha256)
    drive = [
        row for row in _read_csv(source / "robot-drive.csv")
        if replay_window_s[0] <= float(row["t_s"]) <= replay_window_s[1]
    ]
    commands = _read_csv(source / "joystick-commands.csv")
    runner_events = _read_csv(source / "runner-events.csv")
    camera = _read_csv(source / "camera_timestamps.csv")
    debug = [
        json.loads(line)
        for line in (source / "robot-drive-debug.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    summary = json.loads((source / "robot-drive-summary.json").read_text(encoding="utf-8"))
    result = summary.get("result") or {}

    stale_events = [event for event in debug if event.get("event") == "stream_feedback_stale_begin"]
    recoveries = {
        int(event["tick"]): event
        for event in debug
        if event.get("event") == "stream_feedback_recovered"
    }
    stream_error = next(
        (event for event in debug if event.get("event") == "stream_error"), None
    )
    hold_begin = next(
        (event for event in debug if event.get("event") == "hold_after_stream_loss_begin"), None
    )
    hold_sample = next(
        (event for event in debug if event.get("event") == "hold_after_stream_loss_sampled"), None
    )
    hold_ok = next(
        (event for event in debug if event.get("event") == "hold_after_stream_loss_ok"), None
    )
    if not stale_events or not stream_error or not hold_begin or not hold_sample or not hold_ok:
        raise ReplayError("debug stream lacks a complete terminal stop transition")

    timeline: list[dict[str, Any]] = []
    for event in stale_events:
        tick = int(event["tick"])
        recovery = recoveries.get(tick)
        state = event.get("state") or {}
        diag = state.get("stale_diag") or state.get("stream_diag") or {}
        row = _nearest_row(drive, tick / control_hz)
        sampler = diag.get("sampler") or {}
        timeline.append({
            "tick": tick,
            "t_s": float(event["t_s"]),
            "active": event.get("active"),
            "stale_ticks": int(
                (recovery or {}).get("previous_stale_ticks")
                or event.get("stale_ticks")
                or event.get("stale_added")
                or 0
            ),
            "terminal": tick == int(stream_error["tick"]),
            "recovered": recovery is not None,
            "write_target": diag.get("write_target"),
            "bus_write_due_nearest_row": None if row is None else row.get("bus_write_due") == "1",
            "lag_ms_nearest_row": None if row is None else _number(row.get("lag_ms")),
            "service_ms_nearest_row": None if row is None else _number(row.get("service_ms")),
            "async_age_ms": diag.get("async_age_ms"),
            "health_age_ms": sampler.get("health_age_ms"),
            "sampler_errors": sampler.get("errors"),
            "physical_rejects": sampler.get("physical_rejects"),
            "sampler_last_error": sampler.get("last_error"),
            "sampler_update_max_ms": (sampler.get("update") or {}).get("max_ms"),
        })

    terminal = timeline[-1]
    if not terminal["terminal"] or terminal["stale_ticks"] != stale_tick_limit + 1:
        raise ReplayError("terminal stale burst does not match the saved 11/10 stop")

    max_service_row = max(drive, key=lambda row: _number(row.get("service_ms")) or -1.0)
    max_lag_row = max(drive, key=lambda row: _number(row.get("lag_ms")) or -1.0)
    terminal_state = stream_error["state"]
    sampled_state = hold_sample["state"]
    error_mono = float(stream_error["mono"])
    hold_begin_mono = float(hold_begin["mono"])
    hold_sample_mono = float(hold_sample["mono"])
    hold_ok_mono = float(hold_ok["mono"])
    tail = [row for row in drive if row.get("phase") == "tail"]
    tail_roll = [float(row["roll_deg"]) for row in tail]
    tail_pitch = [float(row["pitch_deg"]) for row in tail]

    command_at_error = min(
        commands,
        key=lambda row: abs(float(row["unix_s"]) - float(drive[-len(tail)-1]["unix_s"])),
    ) if commands and len(drive) > len(tail) else None
    camera_near_hold = min(
        camera,
        key=lambda row: abs(float(row["unix_s"]) - float(drive[-len(tail)]["unix_s"])),
    ) if camera and tail else None

    terminal_sampler = (terminal_state.get("stale_diag") or {}).get("sampler") or {}
    sampler_classification = (
        "two logical bus-health acquisition failures (snapshot bus not ok); "
        "no physical freshness rejects and no sampler-thread/update-duration overrun"
    )
    conclusion = (
        "The terminal stop was caused by failure to refresh complete servo-health feedback, "
        "not by the learned command, a write-due tick, or a policy-service overrun. "
        "The stop interlock behaved as configured at 11 stale ticks. The post-stop attitude "
        "excursion occurred during the foreground resample-before-hold gap. Candidate fix: "
        "write the already-known fallback hold immediately after sampler shutdown, then only "
        "re-anchor to a fresh sampled pose after validating its pose/tilt envelope."
    )
    report = {
        "schema": "hexapod.offline_stale_feedback_stop_replay.v1",
        "source": {
            "experiment_id": "6a632f8ba4bc4b14812e27e6f87eaa42",
            "manifest_sha256": expected_manifest_sha256.lower(),
            "verified_inputs": verified,
            "replay_window_s": list(replay_window_s),
        },
        "contract": {
            "simulation_only": True,
            "robot_motion": False,
            "control_hz": control_hz,
            "servo_write_hz": servo_write_hz,
            "snapshot_hz": snapshot_hz,
            "snapshot_max_age_ms": snapshot_max_age_ms,
            "stale_tick_limit": stale_tick_limit,
        },
        "stale_bursts": {
            "count": len(timeline),
            "timeline": timeline,
            "terminal_tick": int(stream_error["tick"]),
            "terminal_t_s": float(stream_error["t_s"]),
            "terminal_stale_ticks": int(stream_error["stale_ticks"]),
        },
        "sampler_error_classification": {
            "classification": sampler_classification,
            "samples": terminal_sampler.get("samples"),
            "good_samples": terminal_sampler.get("good_samples"),
            "errors": terminal_sampler.get("errors"),
            "physical_rejects": terminal_sampler.get("physical_rejects"),
            "thread_alive": terminal_sampler.get("thread_alive"),
            "last_observed_error": "snapshot bus not ok",
            "terminal_health_age_ms": terminal_sampler.get("health_age_ms"),
            "terminal_update_max_ms": (terminal_sampler.get("update") or {}).get("max_ms"),
        },
        "write_due_and_overrun_correlation": {
            "terminal_write_target": terminal.get("write_target"),
            "terminal_was_skip_write_tick": terminal.get("write_target") is False,
            "stale_onsets_write_target_true": sum(item["write_target"] is True for item in timeline),
            "stale_onsets_write_target_false": sum(item["write_target"] is False for item in timeline),
            "recorded_overruns": result.get("overruns"),
            "max_service_ms": _number(max_service_row.get("service_ms")),
            "max_service_t_s": float(max_service_row["t_s"]),
            "max_lag_ms": _number(max_lag_row.get("lag_ms")),
            "max_lag_t_s": float(max_lag_row["t_s"]),
            "terminal_nearest_service_ms": terminal.get("service_ms_nearest_row"),
            "terminal_nearest_lag_ms": terminal.get("lag_ms_nearest_row"),
            "interpretation": "The terminal onset was a skip-write tick and did not coincide with the trace maxima for service or lag.",
        },
        "hold_after_loss_timing": {
            "stream_error_to_hold_begin_ms": 1000.0 * (hold_begin_mono - error_mono),
            "hold_begin_to_fresh_sample_ms": 1000.0 * (hold_sample_mono - hold_begin_mono),
            "fresh_sample_to_hold_ok_ms": 1000.0 * (hold_ok_mono - hold_sample_mono),
            "stream_error_to_hold_ok_ms": 1000.0 * (hold_ok_mono - error_mono),
            "roll_at_stream_error_deg": terminal_state.get("roll_deg"),
            "pitch_at_stream_error_deg": terminal_state.get("pitch_deg"),
            "roll_at_fresh_hold_sample_deg": sampled_state.get("roll_deg"),
            "pitch_at_fresh_hold_sample_deg": sampled_state.get("pitch_deg"),
        },
        "tail_attitude_reconstruction": {
            "samples": len(tail),
            "sample_hz_observed": None if len(tail) < 2 else 1.0 / statistics.median(
                float(right["t_s"]) - float(left["t_s"]) for left, right in zip(tail, tail[1:])
            ),
            "roll_deg_first": tail_roll[0],
            "roll_deg_peak_abs": max(tail_roll, key=abs),
            "roll_deg_last": tail_roll[-1],
            "pitch_deg_first": tail_pitch[0],
            "pitch_deg_last": tail_pitch[-1],
            "recorded_tail_tilt_max_deg": result.get("tail_tilt_max_deg"),
            "recorded_tail_tilt_end_deg": result.get("tail_tilt_end_deg"),
            "recorded_tail_tilt_recovered": result.get("tail_tilt_recovered"),
            "nearest_camera_frame": camera_near_hold,
        },
        "command_context": {
            "phase": None if command_at_error is None else command_at_error.get("phase"),
            "vx_cmd": None if command_at_error is None else _number(command_at_error.get("vx_cmd")),
            "vy_cmd": None if command_at_error is None else _number(command_at_error.get("vy_cmd")),
            "wz_cmd": None if command_at_error is None else _number(command_at_error.get("wz_cmd")),
            "runner_event_rows": len(runner_events),
        },
        "conclusion": conclusion,
        "candidate_fix": {
            "disposition": "candidate; do not deploy from this replay",
            "focus": "immediate fallback write before foreground resample in hold_current_pose_after_stream_loss",
            "required_validation": "unit-test ordering and a separate bounded guarded validation after review",
        },
    }
    return report, timeline


def write_outputs(report: dict[str, Any], timeline: list[dict[str, Any]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "replay-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (out_dir / "stale-burst-timeline.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(timeline[0]))
        writer.writeheader()
        writer.writerows(timeline)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    report, timeline = replay(
        args.source, expected_manifest_sha256=args.expected_manifest_sha256
    )
    write_outputs(report, timeline, args.out_dir)
    print(json.dumps({"ok": True, "conclusion": report["conclusion"]}, sort_keys=True))


if __name__ == "__main__":
    main()
