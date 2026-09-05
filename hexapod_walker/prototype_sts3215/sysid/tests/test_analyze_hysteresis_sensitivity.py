from pathlib import Path

import numpy as np

from sysid.analyze_hysteresis_sensitivity import analyze_sensitivity
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
