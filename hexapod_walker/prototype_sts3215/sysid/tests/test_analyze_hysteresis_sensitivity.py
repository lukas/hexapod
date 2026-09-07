from pathlib import Path

import numpy as np

from sysid.analyze_hysteresis_sensitivity import (
    analyze_l5_reversal,
    analyze_ordering_comparison,
    analyze_sensitivity,
)
from sysid.tests.test_analyze_hysteresis import _synthetic_trace


def test_sensitivity_enumerates_pairings_bootstraps_and_bounds_quantization(
    tmp_path: Path,
) -> None:
    l2 = _synthetic_trace(
        tmp_path,
        leg=2,
        profile="air",
        amplitudes=[15.0],
        loops=[[(0.4, 0.1), (0.5, 0.1)]],
        dwell_samples=10,
    )
    l5 = _synthetic_trace(
        tmp_path,
        leg=5,
        profile="air",
        amplitudes=[15.0],
        loops=[[(0.8, 0.1), (1.0, 0.1)]],
        dwell_samples=10,
    )

    first = analyze_sensitivity(l2, l5, bootstrap_samples=1000, random_seed=7)
    second = analyze_sensitivity(l2, l5, bootstrap_samples=1000, random_seed=7)

    assert first == second
    assert first["eligible_pairings"]["count"] == 4
    assert first["leave_one_cycle_out"]["count"] == 4
    assert len(first["leave_one_cycle_out"]["all"]) == 4
    assert np.allclose(first["eligible_pairings"]["hip_ratio_range"], [1.6, 2.5])
    assert first["conclusion"] == {
        "hip_ratio_materially_above_one": True,
        "knee_difference_within_encoder_scale": True,
    }
    assert (
        first["encoder_quantization_sensitivity"][
            "hip_loop_l5_over_l2_conservative_interval"
        ][0]
        > 1.0
    )
    offsets = first["dwell_window_offset_sensitivity"]
    assert offsets["offset_range_samples"] == [-5, 5]
    assert [row["offset_samples"] for row in offsets["all"]] == list(range(-5, 6))
    baseline = next(row for row in offsets["all"] if row["offset_samples"] == 0)
    assert np.isclose(
        baseline["hip_loop_l5_over_l2"],
        first["cycle_block_bootstrap"]["hip_loop_l5_over_l2"]["estimate"],
    )
    assert isinstance(offsets["hip_ratio_above_one_at_every_offset"], bool)


def test_ordering_comparison_reports_required_intervals_and_overrun_sensitivity(
    tmp_path: Path,
) -> None:
    l2 = _synthetic_trace(
        tmp_path,
        leg=2,
        profile="air",
        amplitudes=[15.0],
        loops=[[(0.4, 0.2), (0.5, 0.2)]],
        dwell_samples=10,
    )
    l5 = _synthetic_trace(
        tmp_path,
        leg=5,
        profile="air",
        amplitudes=[15.0],
        loops=[[(0.8, 0.2), (1.0, 0.2)]],
        dwell_samples=10,
    )
    first = analyze_ordering_comparison(
        {"forward": (l2, l5), "reverse": (l2, l5)},
        bootstrap_samples=1000,
        random_seed=7,
    )
    second = analyze_ordering_comparison(
        {"forward": (l2, l5), "reverse": (l2, l5)},
        bootstrap_samples=1000,
        random_seed=7,
    )

    assert first == second
    assert first["window_count"] == 4
    assert len(first["per_window_influence"]) == 4
    assert first["hip_ratio_confidence_interval"]["estimate"] == 2.0
    assert first["hip_difference_confidence_interval_deg"]["estimate"] == 0.45
    assert first["knee_ratio_confidence_interval"]["estimate"] == 1.0
    assert first["exclude_windows_adjacent_to_overruns"]["excluded_windows"] == []
    assert first["conclusion"]["hip_ratio_ci_materially_above_one"] is True


def test_l5_reversal_reports_cycles_uncertainty_trends_and_endpoint_sensitivity(
    tmp_path: Path,
) -> None:
    (tmp_path / "parent").mkdir()
    (tmp_path / "reversed").mkdir()
    parent = _synthetic_trace(
        tmp_path / "parent",
        leg=5,
        profile="air",
        amplitudes=[15.0],
        loops=[[(0.8, 0.2), (1.0, 0.3)]],
        dwell_samples=10,
    )
    reversed_trace = _synthetic_trace(
        tmp_path / "reversed",
        leg=5,
        profile="air",
        amplitudes=[15.0],
        loops=[[(0.7, 0.2), (0.9, 0.3)]],
        dwell_samples=10,
    )

    first = analyze_l5_reversal(
        parent, reversed_trace, bootstrap_samples=1000, random_seed=7
    )
    second = analyze_l5_reversal(
        parent, reversed_trace, bootstrap_samples=1000, random_seed=7
    )

    assert first == second
    assert first["cycle_count_per_run"] == 2
    assert len(first["per_cycle"]["parent"]) == 2
    assert np.isclose(first["uncertainty"]["hip"]["reversed_minus_parent_deg"], -0.1)
    assert set(first["cycle_order_trends"]) == {"parent", "reversed"}
    variants = first["endpoint_exclusion_sensitivity"]["variants"]
    assert set(variants) == {
        "include_arrival_endpoint",
        "accepted_exclude_arrival_endpoint",
        "exclude_first_two_rows",
    }
