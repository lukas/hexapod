"""Reproduce and seal the ordering-level hysteresis sensitivity analysis."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from .analyze_hysteresis_sensitivity import METHOD, analyze_ordering_comparison


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def _compare(
    expected: Any, actual: Any, *, tolerance: float, path: str = "$"
) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(expected.keys() | actual.keys()):
            child = f"{path}.{key}"
            if key not in expected or key not in actual:
                mismatches.append(
                    {
                        "path": child,
                        "expected": expected.get(key),
                        "actual": actual.get(key),
                    }
                )
            else:
                mismatches.extend(
                    _compare(
                        expected[key], actual[key], tolerance=tolerance, path=child
                    )
                )
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            mismatches.append(
                {
                    "path": path,
                    "expected_length": len(expected),
                    "actual_length": len(actual),
                }
            )
        for index, (left, right) in enumerate(zip(expected, actual)):
            mismatches.extend(
                _compare(left, right, tolerance=tolerance, path=f"{path}[{index}]")
            )
    elif (
        isinstance(expected, (int, float))
        and not isinstance(expected, bool)
        and isinstance(actual, (int, float))
        and not isinstance(actual, bool)
    ):
        if abs(float(expected) - float(actual)) > tolerance:
            mismatches.append({"path": path, "expected": expected, "actual": actual})
    elif expected != actual:
        mismatches.append({"path": path, "expected": expected, "actual": actual})
    return mismatches


def replay(
    dataset_dir: Path, out_dir: Path, *, tolerance: float = 1e-9
) -> dict[str, Any]:
    reference_path = dataset_dir / "bootstrap_overrun_sensitivity.json"
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    if reference["method"] != METHOD:
        raise ValueError(f"analysis method mismatch: {reference['method']} != {METHOD}")

    paths = {
        ordering: {
            leg: dataset_dir / ordering / reference["inputs"][ordering][leg]["filename"]
            for leg in ("L2", "L5")
        }
        for ordering in ("forward", "reverse")
    }
    verified_inputs = []
    for ordering, legs in paths.items():
        for leg, path in legs.items():
            expected = reference["inputs"][ordering][leg]["sha256"]
            actual = _sha256(path)
            verified_inputs.append(
                {
                    "ordering": ordering,
                    "leg": leg,
                    "path": str(path),
                    "expected_sha256": expected,
                    "actual_sha256": actual,
                    "matches": actual == expected,
                }
            )
    if not all(row["matches"] for row in verified_inputs):
        raise ValueError(
            "one or more input trace hashes do not match the sealed reference"
        )

    computed = analyze_ordering_comparison(
        {ordering: (legs["L2"], legs["L5"]) for ordering, legs in paths.items()},
        bootstrap_samples=reference["bootstrap"]["samples"],
        random_seed=reference["bootstrap"]["random_seed"],
    )
    mismatches = _compare(reference, computed, tolerance=tolerance)

    repo_root = Path(_git("rev-parse", "--show-toplevel", cwd=dataset_dir))
    implementation_path = Path(__file__).with_name("analyze_hysteresis_sensitivity.py")
    base_analyzer_path = Path(__file__).with_name("analyze_hysteresis.py")
    implementation = {
        "schema": "hexapod.sysid.analysis_implementation_revision.v1",
        "git_commit": _git("rev-parse", "HEAD", cwd=repo_root),
        "git_branch": _git("branch", "--show-current", cwd=repo_root),
        "git_tree_clean": not bool(_git("status", "--porcelain", cwd=repo_root)),
        "analysis_method": METHOD,
        "bootstrap": computed["bootstrap"],
        "numeric_tolerance": tolerance,
        "implementations": [
            {
                "path": str(implementation_path.relative_to(repo_root)),
                "sha256": _sha256(implementation_path),
            },
            {
                "path": str(base_analyzer_path.relative_to(repo_root)),
                "sha256": _sha256(base_analyzer_path),
            },
        ],
        "runtime": {"numpy_version": __import__("numpy").__version__},
    }
    provenance = {
        "schema": "hexapod.sysid.per_window_provenance.v1",
        "analysis_method": METHOD,
        "verified_inputs": verified_inputs,
        "windows": computed["windows"],
    }
    comparison = {
        "schema": "hexapod.sysid.reproducibility_comparison.v1",
        "reference": str(reference_path),
        "reference_sha256": _sha256(reference_path),
        "numeric_tolerance": tolerance,
        "exact_structure_compared": True,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "reproduced": not mismatches,
        "checks": {
            "verify_input_sha256": True,
            "recompute_windows": computed["windows"] == reference["windows"],
            "compare_orderings": computed["compare_orderings"]
            == reference["compare_orderings"],
            "leave_one_window_out": computed["per_window_influence"]
            == reference["per_window_influence"],
            "exclude_windows_adjacent_to_overruns": computed[
                "exclude_windows_adjacent_to_overruns"
            ]
            == reference["exclude_windows_adjacent_to_overruns"],
        },
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "computed_metrics.json": computed,
        "per_window_provenance.json": provenance,
        "implementation_revision.json": implementation,
        "comparison_to_bootstrap_overrun_sensitivity.json": comparison,
    }
    for filename, payload in outputs.items():
        (out_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return comparison


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset_dir", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--numeric-tolerance", type=float, default=1e-9)
    args = parser.parse_args()
    comparison = replay(
        args.dataset_dir.resolve(),
        args.out_dir.resolve(),
        tolerance=args.numeric_tolerance,
    )
    print(json.dumps(comparison, indent=2, sort_keys=True))
    if not comparison["reproduced"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
