"""Deterministically relate controller timing signals to joint tracking error.

This is an offline evidence tool.  It verifies the sealed Robot Lab manifest,
reads the recorded walk CSV/debug log/events file, and writes JSON statistics
plus a timestamped CSV outlier table.  It never imports a robot driver.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from collections.abc import Sequence
from pathlib import Path
from typing import Any


class AnalysisError(ValueError):
    """Raised when the evidence contract is incomplete or inconsistent."""


INPUT_NAMES = (
    "robot_rl_drive_20260905_192627.csv",
    "robot_rl_drive_20260905_192626_debug.jsonl",
    "events.csv",
)
JOINTS = 18
BOOTSTRAP_SEED = 20260905


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _percentile(values: Sequence[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise AnalysisError("percentile requires at least one value")
    position = (len(ordered) - 1) * quantile
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    x_mean = statistics.fmean(xs)
    y_mean = statistics.fmean(ys)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    x_ss = sum((x - x_mean) ** 2 for x in xs)
    y_ss = sum((y - y_mean) ** 2 for y in ys)
    denominator = math.sqrt(x_ss * y_ss)
    return numerator / denominator if denominator else None


def _moving_block_bootstrap_ci(
    xs: Sequence[float],
    ys: Sequence[float],
    resamples: int,
    seed: int,
    block_rows: int,
) -> list[float | None]:
    """Bootstrap paired correlations while preserving local time dependence."""

    if len(xs) != len(ys) or not xs:
        raise AnalysisError("moving-block bootstrap requires nonempty paired values")
    if resamples <= 0:
        raise AnalysisError("bootstrap_resamples must be positive")
    if not 1 <= block_rows <= len(xs):
        raise AnalysisError("bootstrap_block_rows must be between 1 and row count")
    rng = random.Random(seed)
    count = len(xs)
    correlations: list[float] = []
    for _ in range(resamples):
        indices: list[int] = []
        while len(indices) < count:
            start = rng.randrange(count)
            indices.extend((start + offset) % count for offset in range(block_rows))
        indices = indices[:count]
        value = _pearson([xs[i] for i in indices], [ys[i] for i in indices])
        if value is not None:
            correlations.append(value)
    if not correlations:
        return [None, None]
    return [_percentile(correlations, 0.025), _percentile(correlations, 0.975)]


def _verified_inputs(source_dir: Path, expected_manifest_sha256: str) -> list[dict[str, Any]]:
    manifest_path = source_dir / "manifest.json"
    actual_manifest_sha256 = _sha256(manifest_path)
    if actual_manifest_sha256 != expected_manifest_sha256:
        raise AnalysisError(
            f"manifest SHA-256 mismatch: {actual_manifest_sha256} != "
            f"{expected_manifest_sha256}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 2:
        raise AnalysisError("expected a Robot Lab schema_version=2 manifest")
    indexed = {item["name"]: item for item in manifest.get("artifacts", [])}
    verified = []
    for name in INPUT_NAMES:
        if name not in indexed:
            raise AnalysisError(f"manifest does not list required input {name}")
        path = source_dir / name
        digest = _sha256(path)
        expected = indexed[name]
        size = path.stat().st_size
        if digest != expected.get("sha256") or size != expected.get("bytes"):
            raise AnalysisError(f"sealed input verification failed for {name}")
        verified.append({"name": name, "bytes": size, "sha256": digest})
    return verified


def _read_rows(source_dir: Path, active_phase: str) -> list[dict[str, Any]]:
    with (source_dir / INPUT_NAMES[0]).open(newline="", encoding="utf-8") as stream:
        raw_rows = [row for row in csv.DictReader(stream) if row["phase"] == active_phase]
    if len(raw_rows) < 3:
        raise AnalysisError(f"need at least three {active_phase!r} rows")
    rows = []
    previous_mono: float | None = None
    for index, raw in enumerate(raw_rows):
        mono = float(raw["mono_s"])
        errors = [abs(float(raw[f"q{joint}_deg"]) - float(raw[f"cmd{joint}_deg"])) for joint in range(JOINTS)]
        rows.append(
            {
                "index": index,
                "tick": round(float(raw["t_s"]) * 100),
                "t_s": float(raw["t_s"]),
                "unix_s": float(raw["unix_s"]),
                "tick_interval_ms": 0.0 if previous_mono is None else (mono - previous_mono) * 1000.0,
                "lag_ms": float(raw["lag_ms"] or 0.0),
                "imu_age_ms": float(raw["imu_age_ms"]),
                "per_joint_abs_tracking_error_deg": errors,
                "global_abs_tracking_error_deg": statistics.fmean(errors),
            }
        )
        previous_mono = mono
    return rows


def _recovery_ticks(source_dir: Path) -> list[int]:
    ticks = []
    with (source_dir / INPUT_NAMES[1]).open(encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            if event.get("event") == "stream_feedback_recovered" and event.get("active") == "walk":
                ticks.append(int(event["tick"]))
    return ticks


def _event_stats(
    rows: Sequence[dict[str, Any]], event_ticks: Sequence[int], offsets_ms: Sequence[int]
) -> dict[str, Any]:
    by_tick = {row["tick"]: row for row in rows}
    baseline = statistics.fmean(row["global_abs_tracking_error_deg"] for row in rows)
    offsets = []
    for offset_ms in offsets_ms:
        values = [
            by_tick[tick + round(offset_ms / 10)]["global_abs_tracking_error_deg"]
            for tick in event_ticks
            if tick + round(offset_ms / 10) in by_tick
        ]
        mean = statistics.fmean(values) if values else None
        offsets.append(
            {
                "offset_ms": offset_ms,
                "samples": len(values),
                "mean_global_abs_tracking_error_deg": mean,
                "delta_from_all_rows_mean_deg": None if mean is None else mean - baseline,
            }
        )
    return {
        "events": len(event_ticks),
        "event_ticks": list(event_ticks),
        "all_rows_mean_global_abs_tracking_error_deg": baseline,
        "offsets": offsets,
    }


def analyze(
    source_dir: Path,
    *,
    expected_manifest_sha256: str,
    active_phase: str = "walk",
    event_windows_ms: Sequence[int] = (-100, -50, 0, 50, 100),
    bootstrap_resamples: int = 10_000,
    bootstrap_block_rows: int | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    verified = _verified_inputs(source_dir, expected_manifest_sha256)
    rows = _read_rows(source_dir, active_phase)
    recovery_ticks = _recovery_ticks(source_dir)
    overrun_ticks = [row["tick"] for row in rows if row["lag_ms"] > 0]
    global_error = [row["global_abs_tracking_error_deg"] for row in rows]
    if bootstrap_block_rows is None:
        bootstrap_block_rows = max(2, round(math.sqrt(len(rows))))

    correlations: dict[str, Any] = {}
    for signal_index, signal in enumerate(("tick_interval_ms", "lag_ms", "imu_age_ms")):
        xs = [row[signal] for row in rows]
        correlations[signal] = {
            "pearson_r": _pearson(xs, global_error),
            "bootstrap_95pct_ci": _moving_block_bootstrap_ci(
                xs,
                global_error,
                bootstrap_resamples,
                BOOTSTRAP_SEED + signal_index,
                bootstrap_block_rows,
            ),
            "per_joint_pearson_r": [
                _pearson(xs, [row["per_joint_abs_tracking_error_deg"][joint] for row in rows])
                for joint in range(JOINTS)
            ],
        }

    outlier_threshold = _percentile(global_error, 0.95)
    outliers = []
    for row in rows:
        if row["global_abs_tracking_error_deg"] < outlier_threshold:
            continue
        outliers.append(
            {
                "unix_s": row["unix_s"],
                "t_s": row["t_s"],
                "tick": row["tick"],
                "tick_interval_ms": row["tick_interval_ms"],
                "lag_ms": row["lag_ms"],
                "imu_age_ms": row["imu_age_ms"],
                "global_abs_tracking_error_deg": row["global_abs_tracking_error_deg"],
                "worst_joint": max(range(JOINTS), key=row["per_joint_abs_tracking_error_deg"].__getitem__),
                "worst_joint_abs_tracking_error_deg": max(row["per_joint_abs_tracking_error_deg"]),
                "within_100ms_of_cadence_overrun": any(abs(row["tick"] - tick) <= 10 for tick in overrun_ticks),
                "within_100ms_of_imu_stale_recovery": any(abs(row["tick"] - tick) <= 10 for tick in recovery_ticks),
            }
        )

    result = {
        "schema": "hexapod.timing_tracking_correlation.v1",
        "source": {
            "run_dir": str(source_dir),
            "manifest_sha256": expected_manifest_sha256,
            "verified_inputs": verified,
            "active_phase": active_phase,
            "rows": len(rows),
        },
        "definitions": {
            "tick_interval_ms": "difference between consecutive active-row mono_s values; first row is 0",
            "global_abs_tracking_error_deg": "row mean of abs(qN_deg - cmdN_deg), N=0..17",
            "per_joint_abs_tracking_error_deg": "abs(qN_deg - cmdN_deg) on each active row",
            "cadence_overrun_event": "active row with recorded lag_ms > 0, preserving the parent audit definition",
            "imu_stale_recovery_event": "walk stream_feedback_recovered event tick from the debug JSONL",
            "correlation": "Pearson correlation across active rows; paired circular moving-block bootstrap percentile CI",
            "outlier": "global absolute tracking error at or above the active-row 95th percentile",
        },
        "correlation_with_bootstrap_95pct_ci": {
            "resamples": bootstrap_resamples,
            "seed": BOOTSTRAP_SEED,
            "method": "paired circular moving-block bootstrap",
            "block_rows": bootstrap_block_rows,
            "block_length_rule": "round(sqrt(active rows)), minimum 2, unless explicitly provided",
            "percentile_method": "linear interpolation (R type 7)",
            "signals_vs_global_abs_tracking_error_deg": correlations,
        },
        "event_aligned_statistics": {
            "cadence_overrun": _event_stats(rows, overrun_ticks, event_windows_ms),
            "imu_stale_recovery": _event_stats(rows, recovery_ticks, event_windows_ms),
        },
        "timestamped_outlier_table": {
            "threshold_p95_global_abs_tracking_error_deg": outlier_threshold,
            "rows": len(outliers),
            "csv": "timestamped_outliers.csv",
        },
        "limitations": [
            "This single 3.1 s scheduled walk trace is observational and cannot establish causation.",
            "The circular moving-block bootstrap preserves local row dependence, but its intervals remain sensitive to block length in this short trace.",
            "Only two IMU stale recoveries occurred, so their event-aligned means are descriptive rather than inferential.",
        ],
    }
    return result, outliers


def write_outputs(result: dict[str, Any], outliers: Sequence[dict[str, Any]], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "event_aligned_statistics.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fieldnames = list(outliers[0]) if outliers else ["unix_s"]
    with (out_dir / "timestamped_outliers.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(outliers)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--bootstrap-resamples", type=int, default=10_000)
    parser.add_argument("--bootstrap-block-rows", type=int)
    args = parser.parse_args()
    result, outliers = analyze(
        args.source_dir,
        expected_manifest_sha256=args.expected_manifest_sha256,
        bootstrap_resamples=args.bootstrap_resamples,
        bootstrap_block_rows=args.bootstrap_block_rows,
    )
    write_outputs(result, outliers, args.out_dir)


if __name__ == "__main__":
    main()
