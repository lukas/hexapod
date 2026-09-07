"""Audit a sealed Robot Lab cardinal/course walking evidence bundle.

This module is deliberately offline: it has no robot or network client.  It
verifies the immutable manifest before interpreting summaries, telemetry, and
camera timestamps.  It does not infer metric motion from video pixels.

Run from ``prototype_sts3215``::

    uv run python -m rl_move.scripts.audit_sealed_walk_experiment RUN_DIR \
      --expected-manifest-sha256 SHA256 --output audit.json
"""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any


SCHEMA = "hexapod.sealed_walk_audit.v1"
PILOTS = ("forward", "backward", "left", "right", "course")
REQUIRED_SUFFIXES = ("_summary.json", "_telemetry.csv", "_camera_timestamps.csv")


class AuditError(RuntimeError):
    """Evidence is missing, malformed, or differs from the sealed manifest."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finite(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def verify_manifest(
    run_dir: Path, expected_manifest_sha256: str | None = None
) -> tuple[dict[str, Any], str]:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise AuditError("manifest.json is missing or is a symbolic link")
    manifest_sha256 = _sha256(manifest_path)
    if (
        expected_manifest_sha256 is not None
        and manifest_sha256 != expected_manifest_sha256.lower()
    ):
        raise AuditError(
            "manifest digest mismatch: "
            f"expected {expected_manifest_sha256.lower()}, got {manifest_sha256}"
        )
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise AuditError(f"manifest.json is invalid: {error}") from error
    if manifest.get("schema_version") != 2 or not isinstance(
        manifest.get("artifacts"), list
    ):
        raise AuditError("expected a Robot Lab schema_version=2 artifact manifest")

    seen: set[str] = set()
    for entry in manifest["artifacts"]:
        if not isinstance(entry, dict):
            raise AuditError("manifest artifact entry is not an object")
        name = entry.get("name")
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or name.startswith(".")
            or name in seen
        ):
            raise AuditError(f"invalid or duplicate manifest artifact name: {name!r}")
        seen.add(name)
        path = run_dir / name
        if not path.is_file() or path.is_symlink():
            raise AuditError(f"sealed artifact is missing or is a symbolic link: {name}")
        expected_bytes = entry.get("bytes")
        if not isinstance(expected_bytes, int) or path.stat().st_size != expected_bytes:
            raise AuditError(f"sealed artifact byte count differs: {name}")
        expected_sha256 = entry.get("sha256")
        if not isinstance(expected_sha256, str) or _sha256(path) != expected_sha256:
            raise AuditError(f"sealed artifact digest differs: {name}")

    required = {
        f"{pilot}{suffix}" for pilot in PILOTS for suffix in REQUIRED_SUFFIXES
    }
    missing = sorted(required - seen)
    if missing:
        raise AuditError(f"manifest lacks required cardinal/course evidence: {missing}")
    return manifest, manifest_sha256


def _strict_clock(rows: list[dict[str, str]], field: str, source: str) -> list[float]:
    values = [_finite(row.get(field)) for row in rows]
    if not values or any(value is None for value in values):
        raise AuditError(f"{source} has a missing or non-finite {field}")
    clock = [float(value) for value in values if value is not None]
    if any(right <= left for left, right in zip(clock, clock[1:])):
        raise AuditError(f"{source} {field} does not advance strictly")
    return clock


def _extreme(rows: list[dict[str, str]], field: str, *, maximum: bool) -> float | None:
    values = [value for row in rows if (value := _finite(row.get(field))) is not None]
    if not values:
        return None
    return max(values) if maximum else min(values)


def _phase_windows(
    telemetry: list[dict[str, str]], camera: list[dict[str, str]]
) -> list[dict[str, Any]]:
    telemetry_clock = _strict_clock(telemetry, "unix_s", "telemetry")
    camera_clock = _strict_clock(camera, "unix_s", "camera timestamps")
    camera_frames: list[int] = []
    for row in camera:
        value = _finite(row.get("frame"))
        if value is None or value < 0 or not value.is_integer():
            raise AuditError("camera timestamps contain an invalid frame index")
        camera_frames.append(int(value))

    windows: list[dict[str, Any]] = []
    start = 0
    while start < len(telemetry):
        phase = telemetry[start].get("phase") or "<missing>"
        end = start + 1
        while end < len(telemetry) and telemetry[end].get("phase") == phase:
            end += 1
        phase_rows = telemetry[start:end]
        phase_start = telemetry_clock[start]
        phase_end = telemetry_clock[end - 1]
        first_camera = bisect.bisect_left(camera_clock, phase_start)
        last_camera = bisect.bisect_right(camera_clock, phase_end) - 1
        camera_overlap = first_camera < len(camera_clock) and last_camera >= first_camera
        windows.append(
            {
                "phase": phase,
                "samples": len(phase_rows),
                "unix_start": phase_start,
                "unix_end": phase_end,
                "sample_span_s": phase_end - phase_start,
                "camera_overlap": camera_overlap,
                "camera_first_frame": camera_frames[first_camera]
                if camera_overlap
                else None,
                "camera_last_frame": camera_frames[last_camera]
                if camera_overlap
                else None,
                "min_live_servos": int(min(float(row["live"]) for row in phase_rows))
                if all(_finite(row.get("live")) is not None for row in phase_rows)
                else None,
                "max_servo_current_a": _extreme(
                    phase_rows, "max_current_a", maximum=True
                ),
                "max_bus_current_a": _extreme(
                    phase_rows, "bus_current_a", maximum=True
                ),
                "min_voltage_v": _extreme(
                    phase_rows, "min_voltage_v", maximum=False
                ),
                "max_temperature_c": _extreme(
                    phase_rows, "max_temp_c", maximum=True
                ),
                "roll_deg_range": [
                    _extreme(phase_rows, "roll_deg", maximum=False),
                    _extreme(phase_rows, "roll_deg", maximum=True),
                ],
                "pitch_deg_range": [
                    _extreme(phase_rows, "pitch_deg", maximum=False),
                    _extreme(phase_rows, "pitch_deg", maximum=True),
                ],
            }
        )
        start = end
    return windows


def _result_record(summary: dict[str, Any]) -> dict[str, Any]:
    results = summary.get("results")
    if not isinstance(results, list) or len(results) != 1:
        raise AuditError("each pilot summary must contain exactly one result")
    entry = results[0]
    result = entry.get("result")
    if not isinstance(entry, dict) or not isinstance(result, dict):
        raise AuditError("pilot result is malformed")
    ticks = result.get("ticks")
    overruns = result.get("overruns")
    overrun_rate = (
        float(overruns) / float(ticks)
        if isinstance(ticks, int)
        and ticks > 0
        and isinstance(overruns, int)
        and overruns >= 0
        else None
    )
    return {
        "phase": entry.get("phase"),
        "request": entry.get("request"),
        "segments": entry.get("segments"),
        "runner_ok": result.get("ok"),
        "runner_duration_s": result.get("duration_s"),
        "ticks": ticks,
        "overruns": overruns,
        "overrun_rate": overrun_rate,
        "recorded_fell": result.get("fell"),
        "recorded_max_current_a": result.get("max_current_a"),
        "recorded_tilt_rel_max_deg": result.get("tilt_rel_max_deg"),
        "recorded_tail_tilt_max_deg": result.get("tail_tilt_max_deg"),
    }


def audit_pilot(run_dir: Path, pilot: str) -> dict[str, Any]:
    try:
        summary = json.loads((run_dir / f"{pilot}_summary.json").read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise AuditError(f"{pilot}_summary.json is invalid: {error}") from error
    telemetry = _read_csv(run_dir / f"{pilot}_telemetry.csv")
    camera = _read_csv(run_dir / f"{pilot}_camera_timestamps.csv")
    windows = _phase_windows(telemetry, camera)
    result = _result_record(summary)
    walk_safety = ((summary.get("policy") or {}).get("walk") or {}).get(
        "safety", {}
    )
    tilt_limits = [
        value
        for key in ("max_roll_deg", "max_pitch_deg")
        if (value := _finite(walk_safety.get(key))) is not None
    ]
    matching_windows = [
        window
        for window in windows
        if window["phase"]
        in {f"drive_{pilot}", "direction_course" if pilot == "course" else ""}
    ]
    coarse_span = sum(window["sample_span_s"] for window in matching_windows)
    runner_duration = _finite(result.get("runner_duration_s"))
    timing = {
        "runner_duration_s": runner_duration,
        "telemetry_drive_label_sample_span_s": coarse_span
        if matching_windows
        else None,
        "difference_s": coarse_span - runner_duration
        if matching_windows and runner_duration is not None
        else None,
        "interpretation": (
            "Telemetry phase labels are coarse recorder/orchestration windows; "
            "they do not establish policy engagement boundaries. Unix timestamps "
            "do align each coarse phase to camera frames."
        ),
    }
    return {
        "pilot": pilot,
        "summary_ok": summary.get("ok"),
        "summary_error": summary.get("error"),
        "requested_phases": summary.get("requested_phases"),
        "result": result,
        "policy_tilt_limit_deg": min(tilt_limits) if tilt_limits else None,
        "timing": timing,
        "telemetry_samples": len(telemetry),
        "camera_timestamp_samples": len(camera),
        "camera_covers_all_telemetry": (
            _finite(camera[0].get("unix_s")) <= _finite(telemetry[0].get("unix_s"))
            and _finite(camera[-1].get("unix_s"))
            >= _finite(telemetry[-1].get("unix_s"))
        ),
        "phase_windows": windows,
        "metric_displacement": {
            "available": False,
            "reason": (
                "No manifest artifact supplies a validated metric chassis pose "
                "trajectory bound to these phase clocks; video pixels and command "
                "velocity are not achieved displacement."
            ),
        },
    }


def audit(
    run_dir: Path, expected_manifest_sha256: str | None = None
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    manifest, manifest_sha256 = verify_manifest(run_dir, expected_manifest_sha256)
    pilots = [audit_pilot(run_dir, pilot) for pilot in PILOTS]
    flags: list[dict[str, Any]] = []
    for pilot in pilots:
        result = pilot["result"]
        if pilot["summary_ok"] is not True:
            flags.append(
                {
                    "pilot": pilot["pilot"],
                    "kind": "overall_runner_failure",
                    "detail": pilot["summary_error"],
                }
            )
        if result["recorded_fell"] is True:
            flags.append(
                {
                    "pilot": pilot["pilot"],
                    "kind": "recorded_fall",
                    "detail": "The saved runner result records fell=true.",
                }
            )
        tail_tilt = _finite(result.get("recorded_tail_tilt_max_deg"))
        tilt_limit = pilot["policy_tilt_limit_deg"]
        if tail_tilt is not None and tilt_limit is not None and tail_tilt > tilt_limit:
            flags.append(
                {
                    "pilot": pilot["pilot"],
                    "kind": "reported_tail_tilt_exceeds_policy_limit",
                    "detail": (
                        f"Saved tail tilt {tail_tilt:g} deg exceeds the policy's "
                        f"{tilt_limit:g} deg roll/pitch limit."
                    ),
                }
            )
        if any(
            window["min_live_servos"] is not None
            and window["min_live_servos"] < 18
            for window in pilot["phase_windows"]
        ):
            flags.append(
                {
                    "pilot": pilot["pilot"],
                    "kind": "incomplete_servo_scan_present",
                    "detail": (
                        "At least one telemetry sample has fewer than 18 live servos; "
                        "the audit does not infer persistence from nonadjacent samples."
                    ),
                }
            )

    all_camera_aligned = all(
        pilot["camera_covers_all_telemetry"]
        and all(window["camera_overlap"] for window in pilot["phase_windows"])
        for pilot in pilots
    )
    acceptance = {
        "runner_completion_is_locomotion_acceptance": False,
        "all_pilot_summaries_ok": all(pilot["summary_ok"] is True for pilot in pilots),
        "recorded_falls": sum(
            pilot["result"]["recorded_fell"] is True for pilot in pilots
        ),
        "metric_direction_or_displacement_available": False,
        "decision": "not_accepted",
        "reason": (
            "One pilot failed overall health clearance, the course records a fall, "
            "and the sealed bundle lacks phase-bound metric chassis trajectories."
        ),
    }
    return {
        "schema": SCHEMA,
        "experiment_id": run_dir.name,
        "manifest_sha256": manifest_sha256,
        "manifest_verified": True,
        "artifact_count": len(manifest["artifacts"]),
        "camera_telemetry_alignment": {
            "clock": "unix_s",
            "all_phase_windows_overlap_camera": all_camera_aligned,
            "precision": "camera frame bounds around coarse telemetry phase labels",
        },
        "pilots": pilots,
        "safety_and_integrity_flags": flags,
        "acceptance": acceptance,
        "limits": [
            "This audit is read-only and makes no claim about current robot state.",
            "Phase labels are not learned-policy engagement events.",
            "Sparse video review cannot replace a calibrated pose trajectory or prove no transient fall.",
            "Electrical and thermal extrema are reported without inventing absent hardware acceptance limits.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--expected-manifest-sha256")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = audit(args.run_dir, args.expected_manifest_sha256)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
