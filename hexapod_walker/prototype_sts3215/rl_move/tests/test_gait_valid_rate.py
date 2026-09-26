"""Fast, mechanics-only tests for rl_move.sim.gait_valid_rate.

Pure statistics over hand-built report dicts -- no sim rollout, no
randomization, no artifacts. Per RESEARCH_RULES "Tests": under 5s,
no rollout-ranking bank.
"""
import json
import math

from rl_move.sim.gait_valid_rate import (
    aggregate_counts,
    conditioned_counts_by_difficulty,
    episode_gait_valid_counts,
    fit_difficulty_classifier,
    per_leg_sacrifice_histogram,
    two_proportion_z_test,
    wilson_interval,
)


def _fake_report(gait_valid_flags, sacrificed_legs=None, mode="walk/det"):
    sacrificed_legs = sacrificed_legs or [[] for _ in gait_valid_flags]
    episodes = [
        {"gait_valid": bool(gv), "sacrificed_legs": sac}
        for gv, sac in zip(gait_valid_flags, sacrificed_legs)
    ]
    return {"episodes": {mode: episodes}}


def test_episode_gait_valid_counts_basic():
    report = _fake_report([True, True, False, True, False, False])
    k, n = episode_gait_valid_counts(report, mode="walk/det")
    assert (k, n) == (3, 6)


def test_episode_gait_valid_counts_missing_mode_is_empty():
    report = _fake_report([True, False], mode="walk/det")
    k, n = episode_gait_valid_counts(report, mode="walk/sto")
    assert (k, n) == (0, 0)


def test_aggregate_counts_sums_across_reports():
    r1 = _fake_report([True, False, True])
    r2 = _fake_report([True, True])
    k, n = aggregate_counts([r1, r2], mode="walk/det")
    assert (k, n) == (4, 5)


def test_per_leg_sacrifice_histogram_counts_each_leg_once_per_episode():
    report = _fake_report(
        [False, False, True],
        sacrificed_legs=[[4, 5], [2], []],
    )
    hist = per_leg_sacrifice_histogram(report, mode="walk/det")
    assert hist == {4: 1, 5: 1, 2: 1}


def test_wilson_interval_matches_point_estimate_and_is_bounded():
    p, lo, hi = wilson_interval(14, 24)
    assert math.isclose(p, 14 / 24, rel_tol=1e-9)
    assert 0.0 <= lo <= p <= hi <= 1.0
    # sanity: known Wilson 95% CI for 14/24 is roughly [0.39, 0.75]
    assert 0.35 < lo < 0.45
    assert 0.70 < hi < 0.80


def test_wilson_interval_well_behaved_at_zero_and_full_rate():
    p0, lo0, hi0 = wilson_interval(0, 10)
    assert p0 == 0.0
    assert lo0 == 0.0
    assert hi0 > 0.0  # upper bound is not degenerate at k=0

    p1, lo1, hi1 = wilson_interval(10, 10)
    assert p1 == 1.0
    assert hi1 == 1.0
    assert lo1 < 1.0  # lower bound is not degenerate at k=n


def test_wilson_interval_empty_sample_is_nan():
    p, lo, hi = wilson_interval(0, 0)
    assert math.isnan(p) and math.isnan(lo) and math.isnan(hi)


def test_two_proportion_z_test_identical_rates_not_significant():
    # exactly the parent-vs-child scenario this tool was built for:
    # same k, same n -> z=0, p=1, definitely not significant
    z, p_value = two_proportion_z_test(14, 24, 14, 24)
    assert z == 0.0
    assert math.isclose(p_value, 1.0, abs_tol=1e-9)


def test_two_proportion_z_test_detects_a_real_difference_at_large_n():
    # 30/100 vs 70/100 is a large, obvious effect -- must be significant
    z, p_value = two_proportion_z_test(30, 100, 70, 100)
    assert abs(z) > 5
    assert p_value < 1e-6


def test_two_proportion_z_test_small_n_same_ratio_not_overconfident():
    # 3/6 vs 3/6 (the original fixed-N=6 gate) is exactly as
    # indistinguishable as 14/24 vs 14/24 -- must also read "no
    # evidence of a difference", the same conclusion at a size the
    # original gate actually used.
    z, p_value = two_proportion_z_test(3, 6, 3, 6)
    assert z == 0.0
    assert p_value > 0.05


def test_two_proportion_z_test_empty_sample_is_nan():
    z, p_value = two_proportion_z_test(0, 0, 5, 10)
    assert math.isnan(z) and math.isnan(p_value)


def _rand(mass_scale=1.0, zero_bias_max_deg=0.0):
    return {"mass_scale": mass_scale, "zero_bias_max_deg": zero_bias_max_deg}


def _write_report(path, mass_scales, gait_valid_flags, mode="walk/det"):
    episodes = [
        {"gait_valid": bool(gv), "randomization": _rand(mass_scale=m)}
        for m, gv in zip(mass_scales, gait_valid_flags)
    ]
    path.write_text(json.dumps({"episodes": {mode: episodes}}))


def test_fit_difficulty_classifier_learns_a_separable_fit_pool(tmp_path):
    # a clean fit pool: low mass_scale -> gait_valid, high -> not.
    p = tmp_path / "fit.json"
    _write_report(
        p,
        mass_scales=[0.8, 0.85, 0.9, 1.1, 1.15, 1.2],
        gait_valid_flags=[True, True, True, False, False, False],
    )
    clf, feature_order = fit_difficulty_classifier([str(p)], mode="walk/det")
    assert "mass_scale" in feature_order
    # sanity: the fitted classifier should score an easy draw higher
    # than a hard one along the same axis it was fit on.
    import numpy as np
    from rl_move.sim.draw_feasibility import vectorize
    X, _ = vectorize(
        [{"mass_scale": 0.8}, {"mass_scale": 1.2}], feature_order=feature_order)
    proba = clf.predict_proba(X)
    assert proba[0] > proba[1]


def test_conditioned_counts_by_difficulty_splits_easy_and_hard(tmp_path):
    fit_p = tmp_path / "fit.json"
    _write_report(
        fit_p,
        mass_scales=[0.8, 0.85, 0.9, 1.1, 1.15, 1.2],
        gait_valid_flags=[True, True, True, False, False, False],
    )
    clf, feature_order = fit_difficulty_classifier([str(fit_p)], mode="walk/det")

    target_p = tmp_path / "target.json"
    _write_report(
        target_p,
        mass_scales=[0.82, 0.88, 1.12, 1.18],
        gait_valid_flags=[True, True, False, False],
    )
    target = json.loads(target_p.read_text())
    (easy_k, easy_n), (hard_k, hard_n) = conditioned_counts_by_difficulty(
        target, clf, feature_order, mode="walk/det")
    # the two low-mass_scale episodes should land predicted-easy and
    # actually be gait_valid; the two high-mass_scale ones predicted-hard.
    assert easy_n == 2 and easy_k == 2
    assert hard_n == 2 and hard_k == 0


def test_conditioned_counts_by_difficulty_skips_episodes_missing_randomization(tmp_path):
    fit_p = tmp_path / "fit.json"
    _write_report(
        fit_p, mass_scales=[0.8, 1.2], gait_valid_flags=[True, False])
    clf, feature_order = fit_difficulty_classifier([str(fit_p)], mode="walk/det")
    report = {"episodes": {"walk/det": [
        {"gait_valid": True},  # no randomization -> skipped
        {"randomization": _rand(0.8)},  # no gait_valid -> skipped
        {"gait_valid": True, "randomization": _rand(0.8)},
    ]}}
    (easy_k, easy_n), (hard_k, hard_n) = conditioned_counts_by_difficulty(
        report, clf, feature_order, mode="walk/det")
    assert easy_n + hard_n == 1


def test_conditioned_counts_by_difficulty_empty_report_is_zero(tmp_path):
    fit_p = tmp_path / "fit.json"
    _write_report(fit_p, mass_scales=[0.8, 1.2], gait_valid_flags=[True, False])
    clf, feature_order = fit_difficulty_classifier([str(fit_p)], mode="walk/det")
    (easy_k, easy_n), (hard_k, hard_n) = conditioned_counts_by_difficulty(
        {"episodes": {}}, clf, feature_order, mode="walk/det")
    assert (easy_k, easy_n) == (0, 0)
    assert (hard_k, hard_n) == (0, 0)
