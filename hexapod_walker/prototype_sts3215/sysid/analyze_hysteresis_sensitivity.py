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


def _encoder_rows(path: Path, *, leg: str) -> list[tuple[float, float]]:
    joint_offset = int(leg[1:]) * 3
    with path.open(newline="", encoding="utf-8") as stream:
        return [
            (
                float(row[f"q{joint_offset + 1}_deg"]),
                float(row[f"q{joint_offset + 2}_deg"]),
            )
            for row in csv.DictReader(stream)
        ]


def _cycle_loops_with_endpoint_skip(
    path: Path, cycles: list[dict[str, Any]], *, leg: str, endpoint_skip: int
) -> list[dict[str, float]]:
    """Recompute cycle loops after skipping N rows at each dwell arrival."""
    if endpoint_skip < 0:
        raise ValueError("endpoint_skip must be nonnegative")
    rows = _encoder_rows(path, leg=leg)
    values = []
    for cycle in cycles:
        # Stored slices already skip the arrival row once.
        outbound_start, outbound_stop = cycle["outbound_rows"]
        inbound_start, inbound_stop = cycle["inbound_rows"]
        outbound_start += endpoint_skip - 1
        inbound_start += endpoint_skip - 1
        outbound = rows[outbound_start:outbound_stop]
        inbound = rows[inbound_start:inbound_stop]
        if not outbound or len(outbound) != len(inbound):
            raise ValueError("endpoint selection leaves unequal or empty dwells")
        values.append(
            {
                "hip_loop_deg": abs(
                    float(np.mean([row[0] for row in outbound]))
                    - float(np.mean([row[0] for row in inbound]))
                ),
                "knee_loop_deg": abs(
                    float(np.mean([row[1] for row in outbound]))
                    - float(np.mean([row[1] for row in inbound]))
                ),
            }
        )
    return values


def _linear_trend(values: np.ndarray) -> dict[str, Any]:
    """Return an OLS cycle-order slope and a small-sample 95% interval."""
    x = np.arange(len(values), dtype=float)
    slope, intercept = np.polyfit(x, values, 1)
    fitted = intercept + slope * x
    if len(values) <= 2:
        interval = [None, None]
    else:
        residual_variance = float(np.sum((values - fitted) ** 2) / (len(values) - 2))
        standard_error = np.sqrt(residual_variance / float(np.sum((x - x.mean()) ** 2)))
        critical = 2.7764451051977987 if len(values) == 6 else 1.959963984540054
        interval = [
            float(slope - critical * standard_error),
            float(slope + critical * standard_error),
        ]
    return {
        "slope_deg_per_cycle": float(slope),
        "confidence_interval_95_ols": interval,
        "intercept_deg": float(intercept),
    }


def analyze_l5_reversal(
    parent_path: Path | str,
    reversed_path: Path | str,
    *,
    bootstrap_samples: int = 10_000,
    random_seed: int = 54_072,
) -> dict[str, Any]:
    """Compare L5 cycle loops before and after temporal-order reversal."""
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be positive")
    paths = {"parent": Path(parent_path), "reversed": Path(reversed_path)}
    analyzed = {
        label: analyze_hysteresis(path, leg="L5") for label, path in paths.items()
    }
    if any(item["method"] != METHOD for item in analyzed.values()):
        raise ValueError("hysteresis analyzer method mismatch")
    cycles = {label: _cycles(item) for label, item in analyzed.items()}
    if len(cycles["parent"]) != len(cycles["reversed"]):
        raise ValueError("parent and reversed traces need equal eligible cycle counts")

    endpoint_variants: dict[str, Any] = {}
    variant_values: dict[str, dict[str, list[dict[str, float]]]] = {}
    for label, skip in (
        ("include_arrival_endpoint", 0),
        ("accepted_exclude_arrival_endpoint", 1),
        ("exclude_first_two_rows", 2),
    ):
        values = {
            run: _cycle_loops_with_endpoint_skip(
                paths[run], cycles[run], leg="L5", endpoint_skip=skip
            )
            for run in paths
        }
        variant_values[label] = values
        endpoint_variants[label] = {
            run: {
                joint: float(np.mean([row[f"{joint}_loop_deg"] for row in values[run]]))
                for joint in ("hip", "knee")
            }
            for run in paths
        }
        endpoint_variants[label]["reversed_minus_parent_deg"] = {
            joint: endpoint_variants[label]["reversed"][joint]
            - endpoint_variants[label]["parent"][joint]
            for joint in ("hip", "knee")
        }

    accepted = variant_values["accepted_exclude_arrival_endpoint"]
    arrays = {
        run: {
            joint: np.asarray([row[f"{joint}_loop_deg"] for row in accepted[run]])
            for joint in ("hip", "knee")
        }
        for run in paths
    }
    rng = np.random.default_rng(random_seed)
    n = len(cycles["parent"])
    independent_indices = {
        run: rng.integers(0, n, size=(bootstrap_samples, n)) for run in paths
    }
    paired_indices = rng.integers(0, n, size=(bootstrap_samples, n))
    uncertainty: dict[str, Any] = {}
    for joint in ("hip", "knee"):
        parent_draws = arrays["parent"][joint][independent_indices["parent"]].mean(
            axis=1
        )
        reversed_draws = arrays["reversed"][joint][
            independent_indices["reversed"]
        ].mean(axis=1)
        independent_delta = reversed_draws - parent_draws
        paired_delta = (
            arrays["reversed"][joint][paired_indices]
            - arrays["parent"][joint][paired_indices]
        ).mean(axis=1)
        uncertainty[joint] = {
            "parent_mean_deg": float(arrays["parent"][joint].mean()),
            "parent_mean_ci_95_percentile": _percentile_interval(parent_draws),
            "reversed_mean_deg": float(arrays["reversed"][joint].mean()),
            "reversed_mean_ci_95_percentile": _percentile_interval(reversed_draws),
            "reversed_minus_parent_deg": float(
                arrays["reversed"][joint].mean() - arrays["parent"][joint].mean()
            ),
            "independent_cycle_block_ci_95_percentile": _percentile_interval(
                independent_delta
            ),
            "matched_cycle_index_ci_95_percentile": _percentile_interval(paired_delta),
        }

    return {
        "schema": "hexapod.sysid.l5_reversal_uncertainty.v1",
        "method": METHOD,
        "bootstrap": {
            "samples": bootstrap_samples,
            "random_seed": random_seed,
            "confidence_level": 0.95,
            "primary_unit": "cycle",
        },
        "inputs": {
            label: {"filename": path.name, "sha256": _sha256(path)}
            for label, path in paths.items()
        },
        "cycle_count_per_run": n,
        "per_cycle": {
            run: [
                {"cycle_index": index, **row} for index, row in enumerate(accepted[run])
            ]
            for run in paths
        },
        "uncertainty": uncertainty,
        "cycle_order_trends": {
            run: {joint: _linear_trend(arrays[run][joint]) for joint in ("hip", "knee")}
            for run in paths
        },
        "endpoint_exclusion_sensitivity": {
            "interpretation": "Compare retaining the arrival endpoint, the accepted one-row exclusion, and excluding two arrival rows while retaining each remaining dwell.",
            "variants": endpoint_variants,
            "hip_delta_range_deg": [
                min(
                    row["reversed_minus_parent_deg"]["hip"]
                    for row in endpoint_variants.values()
                ),
                max(
                    row["reversed_minus_parent_deg"]["hip"]
                    for row in endpoint_variants.values()
                ),
            ],
            "knee_delta_range_deg": [
                min(
                    row["reversed_minus_parent_deg"]["knee"]
                    for row in endpoint_variants.values()
                ),
                max(
                    row["reversed_minus_parent_deg"]["knee"]
                    for row in endpoint_variants.values()
                ),
            ],
        },
    }


def _dwell_offset_sensitivity(
    paths: dict[str, Path],
    cycles: dict[str, list[dict[str, Any]]],
    *,
    minimum_offset: int = -5,
    maximum_offset: int = 5,
) -> dict[str, Any]:
    """Shift both matched dwell slices while preserving their sample count."""
    encoder_rows = {leg: _encoder_rows(path, leg=leg) for leg, path in paths.items()}
    offsets = []
    for offset in range(minimum_offset, maximum_offset + 1):
        means: dict[str, dict[str, float]] = {}
        per_cycle: dict[str, list[dict[str, float]]] = {}
        for leg in ("L2", "L5"):
            values = []
            for cycle in cycles[leg]:
                outbound_start, outbound_stop = cycle["outbound_rows"]
                inbound_start, inbound_stop = cycle["inbound_rows"]
                outbound = encoder_rows[leg][
                    outbound_start + offset : outbound_stop + offset
                ]
                inbound = encoder_rows[leg][
                    inbound_start + offset : inbound_stop + offset
                ]
                if len(outbound) != len(inbound) or not outbound:
                    raise ValueError(
                        f"{leg}: offset {offset} leaves an incomplete dwell"
                    )
                values.append(
                    {
                        "hip_loop_deg": abs(
                            float(np.mean([row[0] for row in outbound]))
                            - float(np.mean([row[0] for row in inbound]))
                        ),
                        "knee_loop_deg": abs(
                            float(np.mean([row[1] for row in outbound]))
                            - float(np.mean([row[1] for row in inbound]))
                        ),
                    }
                )
            per_cycle[leg] = values
            means[leg] = {
                joint: float(np.mean([row[f"{joint}_loop_deg"] for row in values]))
                for joint in ("hip", "knee")
            }
        offsets.append(
            {
                "offset_samples": offset,
                "mean_loops_deg": means,
                "hip_loop_l5_over_l2": means["L5"]["hip"] / means["L2"]["hip"],
                "knee_loop_difference_l5_minus_l2_deg": (
                    means["L5"]["knee"] - means["L2"]["knee"]
                ),
                "per_cycle": per_cycle,
            }
        )
    hip_ratios = [row["hip_loop_l5_over_l2"] for row in offsets]
    knee_differences = [row["knee_loop_difference_l5_minus_l2_deg"] for row in offsets]
    return {
        "offset_range_samples": [minimum_offset, maximum_offset],
        "window_samples_preserved": True,
        "interpretation": (
            "Both outbound and inbound accepted dwell slices are shifted by the "
            "same integer offset without changing their length. Negative and "
            "positive extremes intentionally admit up to five neighboring samples."
        ),
        "all": offsets,
        "hip_ratio_range": [min(hip_ratios), max(hip_ratios)],
        "knee_difference_deg_range": [min(knee_differences), max(knee_differences)],
        "hip_ratio_above_one_at_every_offset": min(hip_ratios) > 1.0,
    }


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
            windows[index] for index in rng.integers(0, len(windows), len(windows))
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
        for index, (l2_cycle, l5_cycle) in enumerate(zip(cycles["L2"], cycles["L5"])):
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

    bootstrap = _bootstrap_metrics(windows, samples=bootstrap_samples, seed=random_seed)
    baseline = _metric_estimates(windows)
    leave_one_out = []
    for omitted, window in enumerate(windows):
        estimates = _metric_estimates(windows[:omitted] + windows[omitted + 1 :])
        leave_one_out.append(
            {
                "ordering": window["ordering"],
                "window_index": window["window_index"],
                "estimates": estimates,
                "influence_from_full_estimate": {
                    name: estimates[name] - baseline[name] for name in estimates
                },
            }
        )
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
                bootstrap["hip_ratio"]["confidence_interval_95_percentile"][0] > 1.0
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

    leave_one_out = []
    for omitted_leg in ("L2", "L5"):
        for omitted_cycle in range(len(cycles[omitted_leg])):
            retained = {
                leg: {
                    joint: (
                        np.delete(values, omitted_cycle)
                        if leg == omitted_leg
                        else values
                    )
                    for joint, values in joints.items()
                }
                for leg, joints in arrays.items()
            }
            leave_one_out.append(
                {
                    "omitted_leg": omitted_leg,
                    "omitted_cycle_index": omitted_cycle,
                    "hip_loop_l5_over_l2": float(
                        retained["L5"]["hip"].mean() / retained["L2"]["hip"].mean()
                    ),
                    "knee_loop_difference_l5_minus_l2_deg": float(
                        retained["L5"]["knee"].mean() - retained["L2"]["knee"].mean()
                    ),
                }
            )

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

    dwell_offsets = _dwell_offset_sensitivity({"L2": l2_path, "L5": l5_path}, cycles)

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
        "leave_one_cycle_out": {
            "count": len(leave_one_out),
            "all": leave_one_out,
            "hip_ratio_range": [
                min(row["hip_loop_l5_over_l2"] for row in leave_one_out),
                max(row["hip_loop_l5_over_l2"] for row in leave_one_out),
            ],
            "knee_difference_deg_range": [
                min(
                    row["knee_loop_difference_l5_minus_l2_deg"] for row in leave_one_out
                ),
                max(
                    row["knee_loop_difference_l5_minus_l2_deg"] for row in leave_one_out
                ),
            ],
        },
        "cycle_block_bootstrap": bootstrap,
        "dwell_window_offset_sensitivity": dwell_offsets,
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
    parser.add_argument(
        "--l5-reversal",
        nargs=2,
        metavar=("PARENT_L5", "REVERSED_L5"),
        help="compare matched L5 cycles before and after temporal reversal",
    )
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--random-seed", type=int, default=83_869)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.l5_reversal:
        if args.ordering or args.l2_trace or args.l5_trace:
            parser.error("--l5-reversal cannot be combined with other traces")
        result = analyze_l5_reversal(
            *args.l5_reversal,
            bootstrap_samples=args.bootstrap_samples,
            random_seed=args.random_seed,
        )
    elif args.ordering:
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
