"""Mechanics-only tests for rl_move.sim.draw_feasibility (standwalk
walkable/unwalkable DR-draw classifier, 2026-09-26). No real report
artifacts, no rollout-ranking bank -- synthetic dicts/arrays only, per
RESEARCH_RULES "Tests" (fast, mechanics, self-contained)."""
from __future__ import annotations

import json

import numpy as np
import pytest

from rl_move.sim.draw_feasibility import (
    LogisticClassifier,
    auc_score,
    cross_validate,
    expand_report_paths,
    flatten_randomization,
    k_fold_indices,
    load_dataset,
    top_features,
    vectorize,
)


def _rand(mass_scale=1.0, friction_scale=1.0, com=(0.0, 0.0, 0.0),
          fault="none", bad_joints=()):
    return {
        "mass_scale": mass_scale,
        "friction_scale": friction_scale,
        "ground_tilt_deg": 0.5,
        "com_offset_mm": list(com),
        "link_scale_range": [0.97, 1.03],
        "zero_drift_cmd_frame": True,
        "bad_start_joints": list(bad_joints),
        "fault": fault,
    }


def test_flatten_randomization_expands_vectors_and_bools_and_counts():
    flat = flatten_randomization(_rand(com=(1.0, 2.0, 3.0), bad_joints=(2, 5)))
    assert flat["mass_scale"] == 1.0
    assert flat["com_offset_mm_x"] == 1.0
    assert flat["com_offset_mm_y"] == 2.0
    assert flat["com_offset_mm_z"] == 3.0
    assert flat["link_scale_range_lo"] == 0.97
    assert flat["link_scale_range_hi"] == pytest.approx(1.03)
    assert flat["zero_drift_cmd_frame"] == 1.0
    assert flat["bad_start_joints_count"] == 2.0
    assert flat["fault=none"] == 1.0
    # an unknown categorical value must not silently disappear as a
    # scalar feature (it's one-hot, not passed through as a number)
    assert "fault" not in flat


def test_flatten_randomization_passes_through_unknown_scalar_keys():
    rand = _rand()
    rand["some_new_dr_axis"] = 3.5
    flat = flatten_randomization(rand)
    assert flat["some_new_dr_axis"] == 3.5


def test_vectorize_fixed_column_order_and_missing_fill():
    rows = [flatten_randomization(_rand(mass_scale=1.1)),
            flatten_randomization(_rand(mass_scale=0.9, com=(1, 0, 0)))]
    X, names = vectorize(rows)
    assert X.shape == (2, len(names))
    # row 0 never saw com_offset_mm_x != 0 -> must fill 0, not drop the column
    assert "com_offset_mm_x" in names
    idx = names.index("com_offset_mm_x")
    assert X[0, idx] == 0.0
    assert X[1, idx] == 1.0
    # a fixed feature_order must reproduce identical columns on new rows
    X2, names2 = vectorize(rows, feature_order=names)
    assert names2 == names
    assert np.array_equal(X, X2)


def test_load_dataset_skips_episodes_missing_fields(tmp_path):
    report = {
        "episodes": {
            "walk/det": [
                {"gait_valid": True, "randomization": _rand(mass_scale=1.0)},
                {"gait_valid": False, "randomization": _rand(mass_scale=1.2)},
                {"gait_valid": True},  # no randomization -> must be skipped
                {"randomization": _rand()},  # no gait_valid -> must be skipped
            ]
        }
    }
    p = tmp_path / "report.json"
    p.write_text(json.dumps(report))
    rows, labels = load_dataset([str(p)])
    assert len(rows) == 2
    assert labels == [True, False]


def test_expand_report_paths_globs_and_dedupes(tmp_path):
    for i in range(3):
        (tmp_path / f"r{i}.json").write_text("{}")
    globbed = expand_report_paths([str(tmp_path / "r*.json")])
    assert len(globbed) == 3
    # passing the same file twice (literal + glob) must not duplicate it
    both = expand_report_paths([str(tmp_path / "r0.json"), str(tmp_path / "r*.json")])
    assert len(both) == 3
    # a glob matching nothing passes through literally (surfaces as a
    # missing-file skip in load_dataset rather than vanishing silently)
    missing = expand_report_paths([str(tmp_path / "nope_*.json")])
    assert missing == [str(tmp_path / "nope_*.json")]


def test_load_dataset_expands_glob_and_pools_multiple_files(tmp_path):
    for i in range(3):
        report = {"episodes": {"walk/det": [
            {"gait_valid": bool(i % 2), "randomization": _rand(mass_scale=1.0 + i * 0.1)}
        ]}}
        (tmp_path / f"r{i}.json").write_text(json.dumps(report))
    rows, labels = load_dataset([str(tmp_path / "r*.json")])
    assert len(rows) == 3
    assert len(labels) == 3


def test_auc_score_perfect_and_chance_and_undefined():
    # perfectly separable scores
    assert auc_score([False, False, True, True], [0.1, 0.2, 0.8, 0.9]) == 1.0
    # perfectly anti-separable
    assert auc_score([False, False, True, True], [0.9, 0.8, 0.2, 0.1]) == 0.0
    # ties -> 0.5-ish contribution, must not crash
    val = auc_score([False, True], [0.5, 0.5])
    assert val == pytest.approx(0.5)
    # single-class -> undefined, must return nan not raise
    assert np.isnan(auc_score([True, True, True], [0.1, 0.5, 0.9]))


def test_k_fold_indices_partition_covers_all_rows_disjointly():
    folds = k_fold_indices(23, 5, seed=1)
    assert len(folds) == 5
    seen = []
    for train_idx, test_idx in folds:
        assert set(train_idx.tolist()).isdisjoint(set(test_idx.tolist()))
        seen.extend(test_idx.tolist())
    assert sorted(seen) == list(range(23))


def test_logistic_classifier_learns_a_separable_synthetic_signal():
    rng = np.random.RandomState(0)
    n = 200
    x = rng.uniform(-2, 2, size=n)
    noise = rng.normal(scale=0.05, size=n)
    y = (x + noise) > 0.0
    X = x.reshape(-1, 1)
    clf = LogisticClassifier(epochs=200).fit(X, y)
    pred = clf.predict(X)
    acc = float(np.mean(pred == y))
    assert acc > 0.95, f"should learn a trivially-separable 1D signal, got acc={acc}"


def test_cross_validate_beats_baseline_on_separable_synthetic_data():
    rng = np.random.RandomState(2)
    n = 300
    x1 = rng.uniform(-2, 2, size=n)
    x2 = rng.normal(size=n)
    y = (x1 - 0.3 * x2) > 0.2
    X = np.column_stack([x1, x2])
    result = cross_validate(X, y, k=5, seed=0)
    assert result["n"] == n
    assert result["cv_accuracy_mean"] > result["baseline_accuracy"]
    assert 0.0 <= result["cv_auc_mean"] <= 1.0


def test_cross_validate_on_pure_noise_does_not_beat_baseline_much():
    rng = np.random.RandomState(3)
    n = 200
    X = rng.normal(size=(n, 5))
    y = rng.uniform(size=n) > 0.5  # label independent of X
    result = cross_validate(X, y, k=5, seed=0)
    # should not wildly exceed the majority baseline on pure noise
    assert result["cv_accuracy_mean"] <= result["baseline_accuracy"] + 0.15


def test_top_features_ranks_by_absolute_magnitude():
    weights = np.array([0.1, -5.0, 2.0, 0.0])
    names = ["a", "b", "c", "d"]
    ranked = top_features(weights, names, n=2)
    assert ranked[0][0] == "b"
    assert ranked[1][0] == "c"
