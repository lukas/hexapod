"""Sensitivity analysis for two matched-dwell hysteresis traces.

This keeps the accepted dwell extraction in :mod:`sysid.analyze_hysteresis`
and asks how the between-leg comparison changes across every extracted cycle,
cycle-block resampling, and one STS3215 encoder count of quantization error.
"""

from __future__ import annotations

import argparse
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
    parser.add_argument("l2_trace", type=Path)
    parser.add_argument("l5_trace", type=Path)
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--random-seed", type=int, default=83_869)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
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
