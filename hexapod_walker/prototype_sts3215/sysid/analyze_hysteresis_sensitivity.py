"""Sensitivity analysis for two matched-dwell hysteresis traces.

This keeps the accepted dwell extraction in :mod:`sysid.analyze_hysteresis`
and asks how the between-leg comparison changes across every extracted cycle,
cycle-block resampling, and one STS3215 encoder count of quantization error.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from .analyze_hysteresis import analyze_hysteresis

METHOD = "matched_midpoint_dwells_excluding_arrival_endpoint_v1"
ENCODER_COUNT_DEG = 360.0 / 4096.0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cycles(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        cycle for condition in result["conditions"] for cycle in condition["cycles"]
    ]


def _percentile_interval(values: np.ndarray) -> list[float]:
    return [float(value) for value in np.percentile(values, [2.5, 97.5])]


def _overrun_rows(path: Path) -> list[int]:
    """Return zero-based CSV row indexes whose hardware tick overran."""
    with path.open(newline="", encoding="utf-8") as stream:
        return [
            index
            for index, row in enumerate(csv.DictReader(stream))
            if int(row.get("overrun") or 0) != 0
        ]


def _window_has_adjacent_overrun(cycle: dict[str, Any], rows: list[int]) -> bool:
    """Test overruns in the complete base-mid-peak-mid-base window."""
    dwell = int(cycle["dwell_samples_per_side"])
    start = int(cycle["outbound_rows"][0]) - dwell - 1
    stop = int(cycle["inbound_rows"][1]) + dwell + 1
    return any(start <= row < stop for row in rows)


def _metric_estimates(windows: list[dict[str, Any]]) -> dict[str, float]:
    if not windows:
        raise ValueError("at least one complete interior window is required")
    means = {
        leg: {
            joint: float(np.mean([row[leg][joint] for row in windows]))
            for joint in ("hip", "knee")
        }
        for leg in ("L2", "L5")
    }
    if means["L2"]["hip"] <= 0 or means["L2"]["knee"] <= 0:
        raise ValueError("L2 loop means must be positive for ratio analysis")
    return {
        "hip_ratio": means["L5"]["hip"] / means["L2"]["hip"],
        "hip_difference_deg": means["L5"]["hip"] - means["L2"]["hip"],
        "knee_ratio": means["L5"]["knee"] / means["L2"]["knee"],
    }


def _bootstrap_metrics(
    windows: list[dict[str, Any]], *, samples: int, seed: int
) -> dict[str, dict[str, Any]]:
    rng = np.random.default_rng(seed)
    names = _metric_estimates(windows)
    values = {name: np.empty(samples) for name in names}
    for draw in range(samples):
        selected = [
            windows[index]
            for index in rng.integers(0, len(windows), len(windows))
        ]
        for name, value in _metric_estimates(selected).items():
            values[name][draw] = value
    return {
        name: {
            "estimate": names[name],
            "confidence_interval_95_percentile": _percentile_interval(draws),
        }
        for name, draws in values.items()
    }


def analyze_ordering_comparison(
    orderings: dict[str, tuple[Path | str, Path | str]],
    *,
    bootstrap_samples: int = 10_000,
    random_seed: int = 9_052_026,
) -> dict[str, Any]:
    """Replay matched windows across orderings with timing sensitivity."""
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be positive")
    if not orderings:
        raise ValueError("at least one ordering is required")

    windows: list[dict[str, Any]] = []
    inputs: dict[str, Any] = {}
    per_ordering: dict[str, Any] = {}
    for label, paths in orderings.items():
        l2_path, l5_path = (Path(path) for path in paths)
        analyzed = {
            "L2": analyze_hysteresis(l2_path, leg="L2"),
            "L5": analyze_hysteresis(l5_path, leg="L5"),
        }
        cycles = {leg: _cycles(result) for leg, result in analyzed.items()}
        if len(cycles["L2"]) != len(cycles["L5"]):
            raise ValueError(f"{label}: L2/L5 eligible window counts differ")
        l5_overruns = _overrun_rows(l5_path)
        order_windows = []
        for index, (l2_cycle, l5_cycle) in enumerate(
            zip(cycles["L2"], cycles["L5"])
        ):
            row = {
                "ordering": label,
                "window_index": index,
                "L2": {
                    "hip": float(l2_cycle["hip_loop_deg"]),
                    "knee": float(l2_cycle["knee_loop_deg"]),
                },
                "L5": {
                    "hip": float(l5_cycle["hip_loop_deg"]),
                    "knee": float(l5_cycle["knee_loop_deg"]),
                },
                "l5_overrun_adjacent": _window_has_adjacent_overrun(
                    l5_cycle, l5_overruns
                ),
                "l5_outbound_rows": l5_cycle["outbound_rows"],
                "l5_inbound_rows": l5_cycle["inbound_rows"],
            }
            row["metrics"] = _metric_estimates([row])
            order_windows.append(row)
            windows.append(row)
        inputs[label] = {
            "L2": {"filename": l2_path.name, "sha256": _sha256(l2_path)},
            "L5": {"filename": l5_path.name, "sha256": _sha256(l5_path)},
        }
        per_ordering[label] = {
            "window_count": len(order_windows),
            "l5_overrun_rows": l5_overruns,
            "metrics": _metric_estimates(order_windows),
        }

    bootstrap = _bootstrap_metrics(
        windows, samples=bootstrap_samples, seed=random_seed
    )
    baseline = _metric_estimates(windows)
    leave_one_out = []
    for omitted, window in enumerate(windows):
        estimates = _metric_estimates(windows[:omitted] + windows[omitted + 1 :])
        leave_one_out.append({
            "ordering": window["ordering"],
            "window_index": window["window_index"],
            "estimates": estimates,
            "influence_from_full_estimate": {
                name: estimates[name] - baseline[name] for name in estimates
            },
        })
    timing_clean = [row for row in windows if not row["l5_overrun_adjacent"]]
    timing_excluded = [
        {"ordering": row["ordering"], "window_index": row["window_index"]}
        for row in windows
        if row["l5_overrun_adjacent"]
    ]
    timing_metrics = _metric_estimates(timing_clean)
    return {
        "schema": "hexapod.sysid.hysteresis_ordering_sensitivity.v1",
        "method": METHOD,
        "bootstrap": {
            "samples": bootstrap_samples,
            "random_seed": random_seed,
            "confidence_level": 0.95,
            "unit": "complete_interior_window",
        },
        "inputs": inputs,
        "window_count": len(windows),
        "hip_ratio_confidence_interval": bootstrap["hip_ratio"],
        "hip_difference_confidence_interval_deg": bootstrap["hip_difference_deg"],
        "knee_ratio_confidence_interval": bootstrap["knee_ratio"],
        "per_window_influence": leave_one_out,
        "windows": windows,
        "compare_orderings": per_ordering,
        "exclude_windows_adjacent_to_overruns": {
            "criterion": (
                "L5 overrun within the complete base-midpoint-peak-midpoint-base "
                "window, reconstructed by expanding the accepted midpoint slices "
                "by one dwell on each side"
            ),
            "excluded_windows": timing_excluded,
            "retained_window_count": len(timing_clean),
            "metrics": timing_metrics,
        },
        "conclusion": {
            "hip_ratio_ci_materially_above_one": (
                bootstrap["hip_ratio"]["confidence_interval_95_percentile"][0]
                > 1.0
            ),
            "hip_ratio_remains_above_one_without_overrun_adjacent_windows": (
                timing_metrics["hip_ratio"] > 1.0
            ),
        },
    }


def analyze_sensitivity(
    l2_path: Path | str,
    l5_path: Path | str,
    *,
    bootstrap_samples: int = 10_000,
    random_seed: int = 83_869,
) -> dict[str, Any]:
    """Compare all eligible L2/L5 cycles and quantify sampling uncertainty."""
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be positive")
    l2_path, l5_path = Path(l2_path), Path(l5_path)
    analyzed = {
        "L2": analyze_hysteresis(l2_path, leg="L2"),
        "L5": analyze_hysteresis(l5_path, leg="L5"),
    }
    if any(item["method"] != METHOD for item in analyzed.values()):
        raise ValueError("hysteresis analyzer method mismatch")

    cycles = {leg: _cycles(result) for leg, result in analyzed.items()}
    arrays = {
        leg: {
            joint: np.asarray([cycle[f"{joint}_loop_deg"] for cycle in rows])
            for joint in ("hip", "knee")
        }
        for leg, rows in cycles.items()
    }
    if any(len(rows) < 2 for rows in cycles.values()):
        raise ValueError("each leg needs at least two eligible cycles")
    if np.any(arrays["L2"]["hip"] <= 0):
        raise ValueError("L2 hip loops must be positive for ratio analysis")

    pairings = []
    for l2_index, l2_cycle in enumerate(cycles["L2"]):
        for l5_index, l5_cycle in enumerate(cycles["L5"]):
            pairings.append(
                {
                    "l2_cycle_index": l2_index,
                    "l5_cycle_index": l5_index,
                    "hip_loop_l5_over_l2": (
                        l5_cycle["hip_loop_deg"] / l2_cycle["hip_loop_deg"]
                    ),
                    "knee_loop_difference_l5_minus_l2_deg": (
                        l5_cycle["knee_loop_deg"] - l2_cycle["knee_loop_deg"]
                    ),
                }
            )

    rng = np.random.default_rng(random_seed)
    bootstrap = {}
    draws: dict[str, dict[str, np.ndarray]] = {}
    for leg in ("L2", "L5"):
        count = len(cycles[leg])
        indices = rng.integers(0, count, size=(bootstrap_samples, count))
        draws[leg] = {
            joint: arrays[leg][joint][indices].mean(axis=1) for joint in ("hip", "knee")
        }
    boot_ratio = draws["L5"]["hip"] / draws["L2"]["hip"]
    boot_knee_difference = draws["L5"]["knee"] - draws["L2"]["knee"]
    bootstrap["hip_loop_l5_over_l2"] = {
        "estimate": float(arrays["L5"]["hip"].mean() / arrays["L2"]["hip"].mean()),
        "confidence_interval_95_percentile": _percentile_interval(boot_ratio),
    }
    bootstrap["knee_loop_difference_l5_minus_l2_deg"] = {
        "estimate": float(arrays["L5"]["knee"].mean() - arrays["L2"]["knee"].mean()),
        "confidence_interval_95_percentile": _percentile_interval(boot_knee_difference),
    }

    # Each loop is the absolute difference of two plateau means. Treat each
    # plateau's unknown encoder rounding offset as bounded by half a count.
    # Therefore one loop can move by at most one count. The resulting bounds
    # are conservative and do not assume independent sample-level rounding.
    mean_loops = {
        leg: {joint: float(values.mean()) for joint, values in joints.items()}
        for leg, joints in arrays.items()
    }
    q = ENCODER_COUNT_DEG
    l2_hip_low = max(0.0, mean_loops["L2"]["hip"] - q)
    l2_hip_high = mean_loops["L2"]["hip"] + q
    l5_hip_low = max(0.0, mean_loops["L5"]["hip"] - q)
    l5_hip_high = mean_loops["L5"]["hip"] + q
    quantization = {
        "encoder_count_deg": q,
        "assumption": (
            "Each outbound and inbound plateau mean has an unknown rounding "
            "offset bounded by half an encoder count; each absolute loop is "
            "therefore bounded by plus or minus one count."
        ),
        "hip_loop_l5_over_l2_conservative_interval": [
            l5_hip_low / l2_hip_high,
            l5_hip_high / l2_hip_low,
        ],
        "knee_loop_difference_l5_minus_l2_deg_conservative_interval": [
            mean_loops["L5"]["knee"] - mean_loops["L2"]["knee"] - 2 * q,
            mean_loops["L5"]["knee"] - mean_loops["L2"]["knee"] + 2 * q,
        ],
    }

    pairing_ratios = np.asarray([row["hip_loop_l5_over_l2"] for row in pairings])
    pairing_knee = np.asarray(
        [row["knee_loop_difference_l5_minus_l2_deg"] for row in pairings]
    )
    return {
        "schema": "hexapod.sysid.hysteresis_sensitivity.v1",
        "method": METHOD,
        "random_seed": random_seed,
        "bootstrap_samples": bootstrap_samples,
        "inputs": {
            "L2": {"filename": l2_path.name, "sha256": _sha256(l2_path)},
            "L5": {"filename": l5_path.name, "sha256": _sha256(l5_path)},
        },
        "eligible_cycles": {
            leg: {
                "count": len(rows),
                "hip_loop_deg": arrays[leg]["hip"].tolist(),
                "knee_loop_deg": arrays[leg]["knee"].tolist(),
                "outbound_rows": [row["outbound_rows"] for row in rows],
                "inbound_rows": [row["inbound_rows"] for row in rows],
            }
            for leg, rows in cycles.items()
        },
        "eligible_pairings": {
            "count": len(pairings),
            "hip_ratio_range": [
                float(pairing_ratios.min()),
                float(pairing_ratios.max()),
            ],
            "knee_difference_deg_range": [
                float(pairing_knee.min()),
                float(pairing_knee.max()),
            ],
            "all": pairings,
        },
        "cycle_block_bootstrap": bootstrap,
        "encoder_quantization_sensitivity": quantization,
        "conclusion": {
            "hip_ratio_materially_above_one": bool(
                bootstrap["hip_loop_l5_over_l2"]["confidence_interval_95_percentile"][0]
                > 1.0
                and quantization["hip_loop_l5_over_l2_conservative_interval"][0] > 1.0
            ),
            "knee_difference_within_encoder_scale": bool(
                abs(bootstrap["knee_loop_difference_l5_minus_l2_deg"]["estimate"]) <= q
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("l2_trace", type=Path, nargs="?")
    parser.add_argument("l5_trace", type=Path, nargs="?")
    parser.add_argument(
        "--ordering",
        nargs=3,
        action="append",
        metavar=("LABEL", "L2", "L5"),
        help="compare one or more named L2/L5 trace orderings",
    )
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--random-seed", type=int, default=83_869)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.ordering:
        if args.l2_trace or args.l5_trace:
            parser.error("positional traces cannot be combined with --ordering")
        result = analyze_ordering_comparison(
            {label: (l2, l5) for label, l2, l5 in args.ordering},
            bootstrap_samples=args.bootstrap_samples,
            random_seed=args.random_seed,
        )
    else:
        if args.l2_trace is None or args.l5_trace is None:
            parser.error("provide L2 and L5 traces, or one or more --ordering groups")
        result = analyze_sensitivity(
            args.l2_trace,
            args.l5_trace,
            bootstrap_samples=args.bootstrap_samples,
            random_seed=args.random_seed,
        )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
