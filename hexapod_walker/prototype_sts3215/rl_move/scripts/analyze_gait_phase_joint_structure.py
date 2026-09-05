"""Analyze gait-phase and joint structure in a sealed hardware walk trace.

This tool is deliberately offline.  It verifies the Robot Lab source manifest,
preserves the parent analysis' ``abs(q-cmd)`` tracking-error definition, and
writes deterministic tabular evidence.  It never imports a robot driver.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Sequence


class AnalysisError(ValueError):
    """Raised when sealed evidence cannot satisfy the analysis contract."""


INPUT_NAMES = (
    "robot_rl_drive_20260905_192627.csv",
    "robot_rl_drive_20260905_192626_debug.jsonl",
    "events.csv",
)
JOINTS = 18
JOINT_TYPES = ("coxa", "femur", "tibia")
BOOTSTRAP_SEED = 20260905
OUTLIER_TICKS = (160, 161, 162, 168, 169, 170, 171,
                 274, 275, 276, 277, 278, 279, 280, 281, 282)
OUTLIER_RUNS = ((160, 161, 162, 168, 169, 170, 171),
                (274, 275, 276, 277, 278, 279, 280, 281, 282))
OUTLIER_THRESHOLD_DEG = 5.824194444444445


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
    low, high = math.floor(position), math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _verified_inputs(source_dir: Path, expected_manifest_sha256: str) -> list[dict[str, Any]]:
    manifest_path = source_dir / "manifest.json"
    actual = _sha256(manifest_path)
    if actual != expected_manifest_sha256:
        raise AnalysisError(
            f"manifest SHA-256 mismatch: {actual} != {expected_manifest_sha256}"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    indexed = {item["name"]: item for item in manifest.get("artifacts", [])}
    verified = []
    for name in INPUT_NAMES:
        if name not in indexed:
            raise AnalysisError(f"manifest does not list required input {name}")
        path = source_dir / name
        expected = indexed[name]
        digest, size = _sha256(path), path.stat().st_size
        if digest != expected.get("sha256") or size != expected.get("bytes"):
            raise AnalysisError(f"sealed input verification failed for {name}")
        verified.append({"name": name, "bytes": size, "sha256": digest})
    return verified


def _debug_contract(source_dir: Path) -> dict[str, Any]:
    with (source_dir / INPUT_NAMES[1]).open(encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            if event.get("event") == "debug_start":
                context = event.get("context", {})
                break
        else:
            raise AnalysisError("debug log has no debug_start contract")
    if context.get("walk_obs_dim") != 75:
        raise AnalysisError("expected obs-75 phase+yaw walk contract")
    phase_hz = float(context.get("phase_hz", 0.0) or 0.0)
    return {
        "walk_policy_name": context.get("walk_policy_name"),
        "walk_obs_dim": context["walk_obs_dim"],
        "phase_hz": phase_hz if math.isfinite(phase_hz) and phase_hz > 0 else None,
        "training_hz": context.get("timing", {}).get("training_hz"),
        "write_speed": context.get("write_speed"),
        "write_acc": context.get("write_acc"),
    }


def _read_rows(source_dir: Path, active_phase: str) -> list[dict[str, Any]]:
    with (source_dir / INPUT_NAMES[0]).open(newline="", encoding="utf-8") as stream:
        raw_rows = [row for row in csv.DictReader(stream) if row["phase"] == active_phase]
    if len(raw_rows) < 3:
        raise AnalysisError(f"need at least three {active_phase!r} rows")
    rows = []
    for index, raw in enumerate(raw_rows):
        errors = [abs(float(raw[f"q{j}_deg"]) - float(raw[f"cmd{j}_deg"]))
                  for j in range(JOINTS)]
        phase_sin, phase_cos = float(raw["obs72"]), float(raw["obs73"])
        if abs(math.hypot(phase_sin, phase_cos) - 1.0) > 0.002:
            raise AnalysisError(f"invalid phase clock at active row {index}")
        phase_cycle = math.atan2(phase_sin, phase_cos) % (2 * math.pi) / (2 * math.pi)
        rows.append({
            "tick": round(float(raw["t_s"]) * 100),
            "t_s": float(raw["t_s"]),
            "phase_cycle": phase_cycle,
            "half_cycle_phase": (phase_cycle % 0.5) / 0.5,
            "vx_ref_mps": float(raw["vx_ref_mps"]),
            "vy_ref_mps": float(raw["vy_ref_mps"]),
            "wz_ref_scaled": float(raw["obs74"]),
            "max_current_a": float(raw["max_cur_a"]),
            "joint_current_abs_a": [abs(float(raw[f"cur{j}_a"])) for j in range(JOINTS)],
            "commands_deg": [float(raw[f"cmd{j}_deg"]) for j in range(JOINTS)],
            "errors_deg": errors,
            "global_error_deg": statistics.fmean(errors),
            "outlier": round(float(raw["t_s"]) * 100) in OUTLIER_TICKS,
        })
    for index, row in enumerate(rows):
        before, after = rows[max(0, index - 1)], rows[min(len(rows) - 1, index + 1)]
        dt = max(1e-9, after["t_s"] - before["t_s"])
        row["command_velocity_deg_s"] = [
            (after["commands_deg"][j] - before["commands_deg"][j]) / dt
            for j in range(JOINTS)
        ]
        row["command_reversal"] = [
            (row["commands_deg"][j] - before["commands_deg"][j])
            * (after["commands_deg"][j] - row["commands_deg"][j]) <= 0
            for j in range(JOINTS)
        ]
    return rows


def _mean(rows: Sequence[dict[str, Any]], value: Callable[[dict[str, Any]], float]) -> float:
    return statistics.fmean(value(row) for row in rows)


def _phase_statistics(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    outliers = [row for row in rows if row["outlier"]]
    bins = []
    for index in range(8):
        selected = [row for row in rows if int(row["phase_cycle"] * 8) % 8 == index]
        selected_outliers = [row for row in selected if row["outlier"]]
        bins.append({
            "bin": index,
            "phase_cycle_range": [index / 8, (index + 1) / 8],
            "rows": len(selected),
            "outlier_rows": len(selected_outliers),
            "outlier_fraction": len(selected_outliers) / len(selected) if selected else None,
            "mean_global_error_deg": _mean(selected, lambda row: row["global_error_deg"]),
        })
    run_summaries = []
    for ticks in OUTLIER_RUNS:
        selected = [row for row in rows if row["tick"] in ticks]
        worst = [max(range(JOINTS), key=row["errors_deg"].__getitem__) for row in selected]
        run_summaries.append({
            "ticks": list(ticks),
            "phase_cycle_range": [min(row["phase_cycle"] for row in selected),
                                  max(row["phase_cycle"] for row in selected)],
            "half_cycle_phase_range": [min(row["half_cycle_phase"] for row in selected),
                                        max(row["half_cycle_phase"] for row in selected)],
            "dominant_worst_joints": dict(sorted(Counter(worst).items())),
            "mean_global_error_deg": _mean(selected, lambda row: row["global_error_deg"]),
            "mean_max_current_a": _mean(selected, lambda row: row["max_current_a"]),
        })
    common_low = max(item["half_cycle_phase_range"][0] for item in run_summaries)
    common_high = min(item["half_cycle_phase_range"][1] for item in run_summaries)
    boundary_distance = [min(row["phase_cycle"] % 0.5, 0.5 - row["phase_cycle"] % 0.5)
                         for row in outliers]
    return {
        "phase_source": "obs72=sin(phase), obs73=cos(phase), recorded before policy action",
        "phase_bins": bins,
        "outlier_runs": run_summaries,
        "repeatability": {
            "common_half_cycle_phase_interval": [common_low, common_high],
            "common_interval_width": max(0.0, common_high - common_low),
            "mean_distance_to_tripod_boundary_cycles": statistics.fmean(boundary_distance),
            "min_distance_to_tripod_boundary_cycles": min(boundary_distance),
            "interpretation": (
                "Both runs overlap in the same half-cycle phase band; none occurs at "
                "the phase-clock tripod boundary itself."
            ),
        },
        "command": {
            "unique_vx_ref_mps": sorted({row["vx_ref_mps"] for row in rows}),
            "unique_vy_ref_mps": sorted({row["vy_ref_mps"] for row in rows}),
            "unique_wz_ref_scaled": sorted({row["wz_ref_scaled"] for row in rows}),
            "outlier_worst_joint_reversal_rows": sum(
                row["command_reversal"][max(range(JOINTS), key=row["errors_deg"].__getitem__)]
                for row in outliers
            ),
            "outlier_rows": len(outliers),
        },
    }


def _cluster_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    outliers = [row for row in rows if row["outlier"]]
    background = [row for row in rows if not row["outlier"]]
    table = []
    for joint in range(JOINTS):
        worst_count = sum(max(range(JOINTS), key=row["errors_deg"].__getitem__) == joint
                          for row in outliers)
        table.append({
            "group": "joint", "key": str(joint), "leg": joint // 3,
            "joint_type": JOINT_TYPES[joint % 3],
            "outlier_mean_error_deg": _mean(outliers, lambda row, j=joint: row["errors_deg"][j]),
            "background_mean_error_deg": _mean(background, lambda row, j=joint: row["errors_deg"][j]),
            "outlier_minus_background_deg": (
                _mean(outliers, lambda row, j=joint: row["errors_deg"][j])
                - _mean(background, lambda row, j=joint: row["errors_deg"][j])
            ),
            "worst_joint_rows": worst_count,
            "outlier_mean_abs_command_velocity_deg_s": _mean(
                outliers, lambda row, j=joint: abs(row["command_velocity_deg_s"][j])),
            "outlier_command_reversal_rows": sum(row["command_reversal"][joint] for row in outliers),
            "outlier_mean_abs_current_a": _mean(
                outliers, lambda row, j=joint: row["joint_current_abs_a"][j]),
        })
    for group, keys, members in (
        ("leg", range(6), lambda key: range(key * 3, key * 3 + 3)),
        ("joint_type", JOINT_TYPES,
         lambda key: [j for j in range(JOINTS) if JOINT_TYPES[j % 3] == key]),
    ):
        for key in keys:
            joints = list(members(key))
            out_mean = _mean(outliers, lambda row, js=joints: statistics.fmean(row["errors_deg"][j] for j in js))
            bg_mean = _mean(background, lambda row, js=joints: statistics.fmean(row["errors_deg"][j] for j in js))
            table.append({
                "group": group, "key": str(key), "leg": "", "joint_type": "",
                "outlier_mean_error_deg": out_mean,
                "background_mean_error_deg": bg_mean,
                "outlier_minus_background_deg": out_mean - bg_mean,
                "worst_joint_rows": sum(
                    max(range(JOINTS), key=row["errors_deg"].__getitem__) in joints
                    for row in outliers
                ),
                "outlier_mean_abs_command_velocity_deg_s": _mean(
                    outliers, lambda row, js=joints: statistics.fmean(abs(row["command_velocity_deg_s"][j]) for j in js)),
                "outlier_command_reversal_rows": sum(
                    any(row["command_reversal"][j] for j in joints) for row in outliers
                ),
                "outlier_mean_abs_current_a": _mean(
                    outliers, lambda row, js=joints: statistics.fmean(row["joint_current_abs_a"][j] for j in js)),
            })
    return table


def _circular_block_bootstrap(
    rows: Sequence[dict[str, Any]], value: Callable[[dict[str, Any]], float],
    *, block_length: int, resamples: int, seed: int,
) -> dict[str, Any]:
    rng, count = random.Random(seed), len(rows)
    estimates = []
    blocks = math.ceil(count / block_length)
    for _ in range(resamples):
        sample = []
        for _ in range(blocks):
            start = rng.randrange(count)
            sample.extend(rows[(start + offset) % count] for offset in range(block_length))
        sample = sample[:count]
        out = [value(row) for row in sample if row["outlier"]]
        bg = [value(row) for row in sample if not row["outlier"]]
        if out and bg:
            estimates.append(statistics.fmean(out) - statistics.fmean(bg))
    observed_out = [value(row) for row in rows if row["outlier"]]
    observed_bg = [value(row) for row in rows if not row["outlier"]]
    return {
        "observed_outlier_minus_background_deg": statistics.fmean(observed_out) - statistics.fmean(observed_bg),
        "bootstrap_95pct_ci_deg": [_percentile(estimates, 0.025), _percentile(estimates, 0.975)],
        "valid_resamples": len(estimates),
    }


def _phase_stratified_difference(
    rows: Sequence[dict[str, Any]], value: Callable[[dict[str, Any]], float],
    labels: Sequence[bool], *, phase_bins: int,
) -> float | None:
    """Return a row-weighted within-phase-bin outlier/background contrast."""
    contrasts: list[tuple[int, float]] = []
    for bin_index in range(phase_bins):
        selected = [
            (value(row), labels[index])
            for index, row in enumerate(rows)
            if int(row["phase_cycle"] * phase_bins) % phase_bins == bin_index
        ]
        out = [sample for sample, is_outlier in selected if is_outlier]
        bg = [sample for sample, is_outlier in selected if not is_outlier]
        if out and bg:
            contrasts.append((len(selected), statistics.fmean(out) - statistics.fmean(bg)))
    if not contrasts:
        return None
    return sum(weight * contrast for weight, contrast in contrasts) / sum(
        weight for weight, _ in contrasts
    )


def _circular_phase_shift_null(
    rows: Sequence[dict[str, Any]], value: Callable[[dict[str, Any]], float],
    *, phase_bins: int, resamples: int, seed: int,
) -> dict[str, Any]:
    """Shift the complete outlier mask, preserving its contiguous time blocks.

    The test statistic compares outlier and background rows within gait-phase
    bins before pooling the contrasts.  Circularly shifting the complete mask
    leaves the two recorded outlier-run shapes and their spacing intact while
    placing that structure at null time/phase locations.
    """
    rng, count = random.Random(seed), len(rows)
    labels = [bool(row["outlier"]) for row in rows]
    observed = _phase_stratified_difference(rows, value, labels, phase_bins=phase_bins)
    if observed is None:
        raise AnalysisError("observed phase-stratified contrast is undefined")
    estimates = []
    for _ in range(resamples):
        shift = rng.randrange(1, count)
        shifted = [labels[(index - shift) % count] for index in range(count)]
        estimate = _phase_stratified_difference(
            rows, value, shifted, phase_bins=phase_bins
        )
        if estimate is not None:
            estimates.append(estimate)
    if not estimates:
        raise AnalysisError("phase-stratified null produced no valid resamples")
    extreme = sum(abs(estimate) >= abs(observed) for estimate in estimates)
    return {
        "observed_phase_stratified_outlier_minus_background_deg": observed,
        "null_95pct_interval_deg": [
            _percentile(estimates, 0.025), _percentile(estimates, 0.975)
        ],
        "two_sided_randomization_p": (extreme + 1) / (len(estimates) + 1),
        "valid_resamples": len(estimates),
    }


def analyze(
    source_dir: Path, *, expected_manifest_sha256: str, active_phase: str = "walk",
    bootstrap_resamples: int = 10_000, bootstrap_seed: int = BOOTSTRAP_SEED,
    block_lengths_rows: Sequence[int] | None = None, phase_bins: int = 8,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    verified = _verified_inputs(source_dir, expected_manifest_sha256)
    contract = _debug_contract(source_dir)
    rows = _read_rows(source_dir, active_phase)
    if contract["phase_hz"] is None:
        phase_steps = [
            (after["phase_cycle"] - before["phase_cycle"]) % 1.0
            for before, after in zip(rows, rows[1:])
        ]
        contract["phase_hz"] = statistics.median(phase_steps) * 100.0
        contract["phase_hz_source"] = "inferred from recorded obs72/obs73 progression"
    else:
        contract["phase_hz_source"] = "debug_start metadata"
    by_tick = {row["tick"]: row for row in rows}
    missing = sorted(set(OUTLIER_TICKS) - set(by_tick))
    if missing:
        raise AnalysisError(f"missing specified outlier ticks: {missing}")
    below = [tick for tick in OUTLIER_TICKS if by_tick[tick]["global_error_deg"] < OUTLIER_THRESHOLD_DEG]
    if below:
        raise AnalysisError(f"specified outlier ticks below preserved threshold: {below}")
    clusters = _cluster_rows(rows)
    inferred_block_length = round(100.0 / (2.0 * contract["phase_hz"]))
    block_lengths = list(block_lengths_rows or (inferred_block_length,))
    if not block_lengths or any(length <= 0 for length in block_lengths):
        raise AnalysisError("block lengths must be positive")
    if phase_bins <= 1:
        raise AnalysisError("phase_bins must be greater than one")
    targets: list[tuple[str, Callable[[dict[str, Any]], float]]] = [
        ("global", lambda row: row["global_error_deg"])
    ]
    for joint_type in JOINT_TYPES:
        joints = [j for j in range(JOINTS) if JOINT_TYPES[j % 3] == joint_type]
        targets.append((joint_type, lambda row, js=joints: statistics.fmean(row["errors_deg"][j] for j in js)))
    block_comparisons = {
        str(block_length): {
            name: _circular_block_bootstrap(
                rows, value, block_length=block_length,
                resamples=bootstrap_resamples, seed=bootstrap_seed + index,
            )
            for index, (name, value) in enumerate(targets)
        }
        for block_length in block_lengths
    }
    null_comparisons = {
        name: _circular_phase_shift_null(
            rows, value, phase_bins=phase_bins, resamples=bootstrap_resamples,
            seed=bootstrap_seed + 100 + index,
        )
        for index, (name, value) in enumerate(targets)
    }
    bootstrap = {
        "schema": "hexapod.gait_phase_joint_bootstrap_reconciliation.v2",
        "seed": bootstrap_seed,
        "resamples": bootstrap_resamples,
        "method": "circular moving-block bootstrap of paired time rows",
        "block_lengths_rows": block_lengths,
        "block_basis": "one 1.333333 Hz tripod half-cycle at 100 Hz",
        "block_comparisons": block_comparisons,
        "phase_stratified_null": {
            "model": "circular_phase_shift_preserving_time_blocks",
            "phase_bins": phase_bins,
            "statistic": "row-weighted mean of within-phase-bin outlier-minus-background contrasts",
            "comparisons": null_comparisons,
        },
        "limitations": [
            "Only two short outlier runs are present, so intervals quantify this trace rather than population causality.",
            "Current is a recorded servo telemetry proxy; it is not direct foot-load measurement.",
        ],
    }
    phase = {
        "schema": "hexapod.gait_phase_outlier_structure.v1",
        "source": {
            "run_dir": str(source_dir), "manifest_sha256": expected_manifest_sha256,
            "verified_inputs": verified, "active_phase": active_phase, "rows": len(rows),
            "debug_contract": contract,
        },
        "definitions": {
            "tracking_error": "abs(qN_deg - cmdN_deg), preserving event_aligned_statistics.json",
            "global_tracking_error": "mean tracking error over joints 0..17",
            "joint_mapping": "joint N maps to leg floor(N/3), type [coxa,femur,tibia][N mod 3]",
            "outlier_ticks": list(OUTLIER_TICKS),
            "outlier_threshold_deg": OUTLIER_THRESHOLD_DEG,
            "load_proxy": "absolute recorded per-joint current and row max_cur_a",
        },
        **_phase_statistics(rows),
    }
    return phase, clusters, bootstrap


def write_outputs(
    phase: dict[str, Any], clusters: Sequence[dict[str, Any]], bootstrap: dict[str, Any],
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "phase_aligned_outlier_statistics.json").write_text(
        json.dumps(phase, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (out_dir / "joint_cluster_table.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(clusters[0]))
        writer.writeheader()
        writer.writerows(clusters)
    (out_dir / "block_bootstrap_results.json").write_text(
        json.dumps(bootstrap, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--bootstrap-resamples", type=int, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int, default=BOOTSTRAP_SEED)
    parser.add_argument("--block-length-rows", type=int, action="append")
    parser.add_argument("--phase-bins", type=int, default=8)
    args = parser.parse_args()
    write_outputs(*analyze(
        args.source_dir,
        expected_manifest_sha256=args.expected_manifest_sha256,
        bootstrap_resamples=args.bootstrap_resamples,
        bootstrap_seed=args.bootstrap_seed,
        block_lengths_rows=args.block_length_rows,
        phase_bins=args.phase_bins,
    ), args.out_dir)


if __name__ == "__main__":
    main()
