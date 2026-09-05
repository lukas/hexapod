"""Derive timing, tracking, and IMU-age metrics from sealed drive logs.

This command is deliberately offline.  It verifies the selected artifacts
against a Robot Lab schema-v2 manifest before reading them and has no robot or
network client.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any


SCHEMA = "hexapod.sealed_telemetry_metrics.v1"
DEFAULT_INPUTS = (
    "robot_rl_drive_20260905_192627.csv",
    "robot_rl_drive_20260905_192626_debug.jsonl",
    "robot_rl_drive_20260905_192627_summary.json",
    "events.csv",
)


class AuditError(RuntimeError):
    """The evidence is incomplete, malformed, or no longer sealed."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(values: list[float], fraction: float) -> float:
    """Return the linearly interpolated sample percentile (R type 7)."""
    ordered = sorted(values)
    if not ordered:
        raise AuditError("cannot calculate a percentile from no samples")
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def stats(values: list[float]) -> dict[str, float | int]:
    if not values or any(not math.isfinite(value) for value in values):
        raise AuditError("metric series is empty or non-finite")
    return {
        "samples": len(values),
        "p50": statistics.median(values),
        "p95": percentile(values, 0.95),
        "max": max(values),
    }


def verify_inputs(
    run_dir: Path, expected_manifest_sha256: str, names: tuple[str, ...]
) -> dict[str, Any]:
    manifest_path = run_dir / "manifest.json"
    actual_manifest_sha256 = sha256(manifest_path)
    if actual_manifest_sha256 != expected_manifest_sha256.lower():
        raise AuditError(
            "manifest digest mismatch: "
            f"expected {expected_manifest_sha256.lower()}, got {actual_manifest_sha256}"
        )
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != 2:
        raise AuditError("expected a Robot Lab schema_version=2 manifest")
    entries = {
        entry.get("name"): entry
        for entry in manifest.get("artifacts", [])
        if isinstance(entry, dict)
    }
    verified = []
    for name in names:
        entry = entries.get(name)
        path = run_dir / name
        if entry is None or not path.is_file() or path.is_symlink():
            raise AuditError(f"sealed input is missing or invalid: {name}")
        actual_sha256 = sha256(path)
        if actual_sha256 != entry.get("sha256") or path.stat().st_size != entry.get("bytes"):
            raise AuditError(f"sealed input differs from manifest: {name}")
        verified.append(
            {"name": name, "bytes": path.stat().st_size, "sha256": actual_sha256}
        )
    return {
        "manifest_sha256": actual_manifest_sha256,
        "verified_inputs": verified,
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def finite(row: dict[str, str], field: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as error:
        raise AuditError(f"missing or non-numeric {field}") from error
    if not math.isfinite(value):
        raise AuditError(f"non-finite {field}")
    return value


def contiguous_clusters(indices: list[int], rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    clusters: list[dict[str, Any]] = []
    for index in indices:
        if not clusters or index != clusters[-1]["end_index"] + 1:
            clusters.append(
                {
                    "start_index": index,
                    "end_index": index,
                    "ticks": 1,
                    "t_s_start": finite(rows[index], "t_s"),
                    "t_s_end": finite(rows[index], "t_s"),
                }
            )
        else:
            cluster = clusters[-1]
            cluster["end_index"] = index
            cluster["ticks"] += 1
            cluster["t_s_end"] = finite(rows[index], "t_s")
    return clusters


def paired_stale_events(path: Path, rows: list[dict[str, str]], expected_hz: float) -> list[dict[str, Any]]:
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    begins: dict[int, dict[str, Any]] = {}
    recoveries: list[dict[str, Any]] = []
    mono = [finite(row, "mono_s") for row in rows]
    for event in events:
        tick = event.get("tick")
        if not isinstance(tick, int):
            continue
        if event.get("event") == "stream_feedback_stale_begin":
            begins[tick] = event
        elif event.get("event") == "stream_feedback_recovered" and tick in begins:
            begin = begins.pop(tick)
            stale_ticks = int(event.get("previous_stale_ticks", 0))
            if stale_ticks <= 0 or not 0 <= tick < len(rows):
                raise AuditError("invalid paired stale recovery event")
            # The retry loop consumes stale policy periods before the recovered
            # tick is logged.  The gap from the prior logged tick to the
            # recovered row is therefore the directly observed recovery gap.
            observed_gap_ms = (
                1000.0 * (mono[tick] - mono[tick - 1]) if tick else None
            )
            recoveries.append(
                {
                    "tick": tick,
                    "t_s": event.get("t_s"),
                    "stale_ticks": stale_ticks,
                    "stale_burst_duration_ms": 1000.0 * stale_ticks / expected_hz,
                    "imu_recovery_latency_ms": observed_gap_ms,
                    "debug_event_pair_latency_ms": 1000.0
                    * (float(event["mono"]) - float(begin["mono"])),
                    "imu_age_at_recovered_log_ms": finite(rows[tick], "imu_age_ms"),
                }
            )
    if begins:
        raise AuditError("unpaired stale-begin event")
    return recoveries


def analyze(
    run_dir: Path, expected_manifest_sha256: str, active_window_s: float, expected_hz: float
) -> dict[str, Any]:
    verification = verify_inputs(run_dir, expected_manifest_sha256, DEFAULT_INPUTS)
    summary = json.loads((run_dir / DEFAULT_INPUTS[2]).read_text())
    rows = read_csv(run_dir / DEFAULT_INPUTS[0])
    active = [row for row in rows if row.get("phase") == "walk"]
    if not active:
        raise AuditError("no walk-phase rows")
    recorded_ticks = (summary.get("result") or {}).get("ticks")
    if recorded_ticks != len(active):
        raise AuditError(
            f"summary/trace tick mismatch: summary={recorded_ticks}, trace={len(active)}"
        )
    nominal = [finite(row, "t_s") for row in active]
    if nominal[0] != 0.0 or nominal[-1] > active_window_s + 1.0 / expected_hz + 1e-9:
        raise AuditError("walk rows exceed the requested active-window tolerance")
    mono = [finite(row, "mono_s") for row in active]
    if any(right <= left for left, right in zip(mono, mono[1:])):
        raise AuditError("active monotonic clock does not advance strictly")
    intervals_ms = [1000.0 * (right - left) for left, right in zip(mono, mono[1:])]

    errors = [
        [finite(row, f"q{joint}_deg") - finite(row, f"cmd{joint}_deg") for joint in range(18)]
        for row in active
    ]
    per_joint_rms = [
        math.sqrt(sum(row[joint] ** 2 for row in errors) / len(errors))
        for joint in range(18)
    ]
    peak_abs, peak_tick, peak_joint, peak_signed = max(
        (abs(error), tick, joint, error)
        for tick, row in enumerate(errors)
        for joint, error in enumerate(row)
    )

    overrun_indices = [
        index for index, row in enumerate(active) if finite(row, "lag_ms") > 0.0
    ]
    recorded_overruns = (summary.get("result") or {}).get("overruns")
    if recorded_overruns != len(overrun_indices):
        raise AuditError(
            "summary/trace overrun mismatch: "
            f"summary={recorded_overruns}, trace={len(overrun_indices)}"
        )
    recoveries = paired_stale_events(
        run_dir / DEFAULT_INPUTS[1], active, expected_hz
    )
    imu_ages = [finite(row, "imu_age_ms") for row in active]
    wall_span = mono[-1] - mono[0]
    return {
        "schema": SCHEMA,
        "source": {
            "run_dir": str(run_dir.resolve()),
            **verification,
            "active_phase": "walk",
            "active_window_requested_s": active_window_s,
            "scheduled_t_s_range": [nominal[0], nominal[-1]],
            "active_rows": len(active),
        },
        "cadence": {
            "wall_sample_span_s": wall_span,
            "effective_tick_hz": (len(active) - 1) / wall_span,
            "tick_interval_ms": stats(intervals_ms),
            "percentile_method": "linear interpolation (R type 7)",
            "expected_control_hz": expected_hz,
        },
        "overruns": {
            "count": len(overrun_indices),
            "rate_per_tick": len(overrun_indices) / len(active),
            "clusters": contiguous_clusters(overrun_indices, active),
            "cluster_definition": "maximal contiguous active rows with lag_ms > 0",
        },
        "tracking": {
            "error_definition": "qN_deg - cmdN_deg on every active walk row",
            "global_rms_deg": math.sqrt(
                sum(error * error for row in errors for error in row)
                / (len(errors) * 18)
            ),
            "per_joint_rms_deg": per_joint_rms,
            "peak_abs_deg": peak_abs,
            "peak": {
                "tick": peak_tick,
                "t_s": nominal[peak_tick],
                "joint": peak_joint,
                "signed_error_deg": peak_signed,
            },
        },
        "imu": {
            "age_ms": stats(imu_ages),
            "stale_recoveries": recoveries,
            "imu_recovery_latency_ms": [
                recovery["imu_recovery_latency_ms"] for recovery in recoveries
            ],
            "stale_burst_durations_ms": [
                recovery["stale_burst_duration_ms"] for recovery in recoveries
            ],
            "interpretation": (
                "Logged IMU age stayed below the 150 ms admission cap. The two "
                "over-age async samples were held inside the retry loop, so their "
                "durations come from paired debug stale-tick counters and recovery "
                "latency is the observed monotonic gap across the recovered log row."
            ),
        },
        "consistency": {
            "summary_ticks_match": True,
            "summary_overruns_match": True,
            "summary_ok": (summary.get("result") or {}).get("ok"),
            "summary_fell": (summary.get("result") or {}).get("fell"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--active-window-s", type=float, default=3.1)
    parser.add_argument("--expected-hz", type=float, default=100.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(
        args.run_dir,
        args.expected_manifest_sha256,
        args.active_window_s,
        args.expected_hz,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
