"""draw_feasibility.py -- walkable/unwalkable DR-draw classifier (standwalk, 2026-09-26).

WHY: CURRENT_TRUTHS 2026-09-26 ~00:2x/~00:5x/~00:6x/~01:1x/~01:4x found,
across 4 independent architecture/seed pairs and up to n=150 fresh draws,
that `gait_valid` at the ceil225/ceil25 DR-ceiling stepping-stones is
statistically INDISTINGUISHABLE between a trained checkpoint and its own
untrained-at-that-ceiling parent (97-98% episode-level identity). That
closed "more training steps" as a lever and named two live options
(standwalk/STATUS.md "Next" item 1): (b) a walkable/unwalkable DR-draw
classifier -- so a future gate can score policy quality only on the
subset of draws that are geometrically/dynamically feasible at all,
instead of a bare fixed-N count dominated by draw hardness -- or (c)
continuous per-step DR sampling. This module builds (b).

Every existing `probe_*` eval_checkpoint report.json already records,
per episode, the actual SAMPLED `randomization` dict (continuous DR
draw values) plus `gait_valid` (bool). Since draw hardness dominates
policy quality on this grid, pooling gait_valid outcomes across many
already-trained/untrained checkpoints at their respective ceilings is
a *valid* dataset for "does the draw alone predict walkability" -- no
new rollout, no new sim mechanics, pure post-hoc statistics over
artifacts that already exist on disk (~1300 walk/det episodes across
23 `probe_*` report files as of 2026-09-26, ~56% gait_valid; see the
CLI output for the live count -- more probe reports accumulate every
cycle this grid runs).

This is a research-analysis tool, not a rollout-ranking bank: it fits
a small numpy-only logistic classifier over the recorded DR draw
vectors and reports held-out cross-validated accuracy/AUC against the
majority-class baseline, plus the top standardized coefficients (which
draw axes move the walkable/unwalkable boundary). No sklearn
dependency (not installed on this image).

Usage (CLI):
    uv run python -m rl_move.sim.draw_feasibility \
        --report 'logs/ckpt_eval/probe_*/*.json' --mode walk/det --k-folds 5

Library:
    from rl_move.sim.draw_feasibility import (
        flatten_randomization, load_dataset, vectorize,
        LogisticClassifier, cross_validate, auc_score,
    )
"""
from __future__ import annotations

import argparse
import glob
import json
import math
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

# Randomization keys that are plain scalars in every observed
# `randomization` dict (see standwalk STATUS.md 2026-09-26 survey).
_SCALAR_KEYS = [
    "mass_scale", "friction_scale", "ground_tilt_deg", "kp_scale_mean",
    "torque_scale", "latency_scale", "deadband_scale", "cmd_drop_prob",
    "zero_bias_max_deg", "start_offset_max_deg", "tipped_roll_deg",
    "rise_rock_roll_deg", "walk_kick_roll_deg", "walk_kick_dur_s",
    "walk_push_peak_nm", "walk_push_dur_s", "walk_push_repeat_period_s",
    "walk_push_start_s", "foot_friction_min", "leg_torque_min",
    "joint_backlash_max_deg", "joint_backlash_load_gain",
    "latency_load_gain_max", "foot_stickslip_gain_max",
    "foot_contact_soft_max", "foot_torsion_soft_min",
]
# Keys that are fixed-length numeric vectors -> expanded to indexed
# scalar features.
_VECTOR_KEYS = {
    "com_offset_mm": ("x", "y", "z"),
    "imu_pos_mm": ("x", "y", "z"),
    "link_scale_range": ("lo", "hi"),
    # Per-leg breakdown (standwalk STATUS 2026-09-26 ~02:1x wiring
    # follow-up): domain_rand.EpisodeRandomization.summary() started
    # recording these two 6-length per-leg vectors alongside the
    # existing whole-robot min/max/max-abs scalars so a future fit can
    # ask "did the SACRIFICED leg also carry this episode's worst
    # per-leg draw" instead of only the whole-robot extreme. Additive
    # only -- old report.json files without these keys still flatten
    # fine (missing key -> absent feature -> vectorize() fills 0.0).
    "link_scale_per_leg": tuple(f"leg{i}" for i in range(6)),
    "joint_zero_bias_deg_per_leg": tuple(f"leg{i}" for i in range(6)),
}
# Booleans stored as python bool.
_BOOL_KEYS = ["zero_drift_cmd_frame"]
# Variable-length lists of indices -> reduced to a count.
_COUNT_KEYS = ["bad_start_joints"]
# Free-text categoricals -> one-hot at dataset-build time (vocabulary
# collected from the pooled data, not hardcoded, since new fault/
# struct_dr categories get added over time).
_CATEGORICAL_KEYS = ["fault", "struct_dr", "struct_dr_story"]


def flatten_randomization(rand: dict) -> dict[str, float]:
    """Turn one episode's `randomization` dict into a flat
    name -> float feature dict. Missing keys are simply absent (the
    caller/vectorizer fills a default); unknown extra keys that are
    plain scalars are passed through so a new DR axis shows up
    automatically instead of being silently dropped."""
    out: dict[str, float] = {}
    seen = set()
    for k in _SCALAR_KEYS:
        if k in rand and isinstance(rand[k], (int, float)):
            out[k] = float(rand[k])
            seen.add(k)
    for k, suffixes in _VECTOR_KEYS.items():
        v = rand.get(k)
        if isinstance(v, (list, tuple)) and len(v) == len(suffixes):
            for suf, val in zip(suffixes, v):
                out[f"{k}_{suf}"] = float(val)
        seen.add(k)
    for k in _BOOL_KEYS:
        if k in rand:
            out[k] = float(bool(rand[k]))
            seen.add(k)
    for k in _COUNT_KEYS:
        v = rand.get(k)
        if isinstance(v, (list, tuple)):
            out[f"{k}_count"] = float(len(v))
        seen.add(k)
    for k in _CATEGORICAL_KEYS:
        v = rand.get(k)
        if isinstance(v, str):
            out[f"{k}={v}"] = 1.0
        seen.add(k)
    # pass through any plain-scalar key this survey didn't already know
    # about, so a newly-added DR axis is visible rather than silently lost.
    for k, v in rand.items():
        if k in seen:
            continue
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out[k] = float(v)
    return out


def expand_report_paths(report_paths: Sequence[str]) -> list[str]:
    """Expand a mix of literal paths and glob patterns into a sorted,
    de-duplicated list of concrete file paths (globs that match
    nothing pass through literally, so a typo'd literal path still
    surfaces as a missing-file skip rather than vanishing silently)."""
    paths: list[str] = []
    for p in report_paths:
        matches = sorted(glob.glob(p))
        paths.extend(matches if matches else [p])
    seen: set[str] = set()
    out = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def load_dataset(
    report_paths: Sequence[str], mode: str = "walk/det"
) -> tuple[list[dict[str, float]], list[bool]]:
    """Load and pool episodes from one or more eval_checkpoint
    report.json files (or glob patterns). Returns (rows, labels) where
    each row is a flattened randomization dict and each label is the
    episode's `gait_valid` bool. Episodes lacking either field are
    skipped (never invented)."""
    paths = expand_report_paths(report_paths)
    rows: list[dict[str, float]] = []
    labels: list[bool] = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            continue
        with open(path) as f:
            report = json.load(f)
        for ep in report.get("episodes", {}).get(mode, []):
            rand = ep.get("randomization")
            if not rand or "gait_valid" not in ep:
                continue
            rows.append(flatten_randomization(rand))
            labels.append(bool(ep["gait_valid"]))
    return rows, labels


def vectorize(
    rows: Sequence[dict[str, float]], feature_order: Sequence[str] | None = None
) -> tuple[np.ndarray, list[str]]:
    """Build a dense (n_rows, n_features) matrix from flattened feature
    dicts. `feature_order` fixes the column set/order (e.g. for
    predicting on new rows with the same schema as training); if None
    it is the sorted union of all keys seen, missing keys fill 0.0."""
    if feature_order is None:
        keys: set[str] = set()
        for r in rows:
            keys.update(r.keys())
        feature_order = sorted(keys)
    X = np.zeros((len(rows), len(feature_order)), dtype=np.float64)
    for i, r in enumerate(rows):
        for j, k in enumerate(feature_order):
            X[i, j] = r.get(k, 0.0)
    return X, list(feature_order)


def _standardize(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std[std < 1e-9] = 1.0
    return (X - mean) / std, mean, std


class LogisticClassifier:
    """Minimal L2-regularized logistic regression, numpy-only (no
    sklearn on this image). Deterministic gradient descent, small
    enough to fit thousands of rows / dozens of features in well
    under a second."""

    def __init__(self, l2: float = 1e-2, lr: float = 0.5, epochs: int = 300):
        self.l2 = l2
        self.lr = lr
        self.epochs = epochs
        self.weights: np.ndarray | None = None
        self.bias: float = 0.0
        self._mean: np.ndarray | None = None
        self._std: np.ndarray | None = None

    def fit(self, X: np.ndarray, y: Sequence[bool]) -> "LogisticClassifier":
        Xs, mean, std = _standardize(np.asarray(X, dtype=np.float64))
        self._mean, self._std = mean, std
        n, d = Xs.shape
        yv = np.asarray(y, dtype=np.float64)
        w = np.zeros(d)
        b = 0.0
        for _ in range(self.epochs):
            z = Xs @ w + b
            p = 1.0 / (1.0 + np.exp(-z))
            grad_w = Xs.T @ (p - yv) / n + self.l2 * w
            grad_b = float(np.mean(p - yv))
            w -= self.lr * grad_w
            b -= self.lr * grad_b
        self.weights = w
        self.bias = b
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        assert self.weights is not None, "call fit() first"
        Xs = (np.asarray(X, dtype=np.float64) - self._mean) / self._std
        z = Xs @ self.weights + self.bias
        return 1.0 / (1.0 + np.exp(-z))

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        return self.predict_proba(X) >= threshold

    def to_dict(self, feature_order: Sequence[str]) -> dict:
        """Serialize fitted weights + the exact standardization stats
        + the feature column order, so a consumer (e.g. a training-
        time DR-draw curriculum) can score a NEW single draw without
        refitting or re-pooling report.json files. Raises if unfit
        (a persisted model must be a real fit, never a stub)."""
        assert self.weights is not None, "call fit() first"
        return {
            "feature_order": list(feature_order),
            "weights": [float(w) for w in self.weights],
            "bias": float(self.bias),
            "mean": [float(v) for v in self._mean],
            "std": [float(v) for v in self._std],
            "l2": self.l2, "lr": self.lr, "epochs": self.epochs,
        }

    @classmethod
    def from_dict(cls, d: dict) -> tuple["LogisticClassifier", list[str]]:
        """Inverse of `to_dict` -- returns (classifier, feature_order)
        ready for `predict_proba_one`/`predict_proba` without calling
        `fit()` again."""
        clf = cls(l2=float(d.get("l2", 1e-2)), lr=float(d.get("lr", 0.5)),
                   epochs=int(d.get("epochs", 300)))
        clf.weights = np.asarray(d["weights"], dtype=np.float64)
        clf.bias = float(d["bias"])
        clf._mean = np.asarray(d["mean"], dtype=np.float64)
        clf._std = np.asarray(d["std"], dtype=np.float64)
        return clf, list(d["feature_order"])


def save_model(path: str, clf: LogisticClassifier,
               feature_order: Sequence[str]) -> None:
    """Persist a fitted classifier to a small JSON file (standwalk
    difficulty-curriculum consumer, `dr.difficulty_model_path`)."""
    with open(path, "w") as f:
        json.dump(clf.to_dict(feature_order), f, indent=1)


def load_model(path: str) -> tuple[LogisticClassifier, list[str]]:
    """Load a classifier persisted by `save_model`."""
    with open(path) as f:
        d = json.load(f)
    return LogisticClassifier.from_dict(d)


def predict_proba_one(rand: dict, clf: LogisticClassifier,
                       feature_order: Sequence[str]) -> float:
    """Score ONE episode's raw `randomization`/`summary()` dict
    against a persisted model -- the exact `flatten_randomization` ->
    `vectorize` pipeline `load_dataset`/`_main` use for training,
    applied to a single new row with the model's OWN fixed feature
    column order (unknown/missing keys fill 0.0, same convention as
    `vectorize`'s `feature_order` argument)."""
    row = flatten_randomization(rand)
    X, _ = vectorize([row], feature_order=feature_order)
    return float(clf.predict_proba(X)[0])


def auc_score(y_true: Sequence[bool], scores: Sequence[float]) -> float:
    """Rank-based (Mann-Whitney U) AUC, no sklearn needed. Returns
    nan if either class is empty (undefined)."""
    y = np.asarray(y_true, dtype=bool)
    s = np.asarray(scores, dtype=np.float64)
    n_pos = int(y.sum())
    n_neg = len(y) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s), dtype=np.float64)
    # average ranks for ties
    sorted_s = s[order]
    i = 0
    rank = 1
    while i < len(sorted_s):
        j = i
        while j + 1 < len(sorted_s) and sorted_s[j + 1] == sorted_s[i]:
            j += 1
        avg_rank = (rank + (rank + (j - i))) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        rank += (j - i + 1)
        i = j + 1
    sum_ranks_pos = ranks[y].sum()
    u = sum_ranks_pos - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


def k_fold_indices(n: int, k: int, seed: int = 0) -> list[tuple[np.ndarray, np.ndarray]]:
    """Deterministic k-fold split (train_idx, test_idx) pairs."""
    rng = np.random.RandomState(seed)
    idx = np.arange(n)
    rng.shuffle(idx)
    folds = np.array_split(idx, k)
    out = []
    for i in range(k):
        test_idx = folds[i]
        train_idx = np.concatenate([folds[j] for j in range(k) if j != i])
        out.append((train_idx, test_idx))
    return out


def cross_validate(
    X: np.ndarray, y: Sequence[bool], k: int = 5, seed: int = 0, **clf_kwargs
) -> dict:
    """k-fold cross-validated accuracy/AUC for LogisticClassifier vs
    the majority-class baseline accuracy. Returns a plain dict so it's
    trivially JSON-serializable/printable."""
    yv = np.asarray(y, dtype=bool)
    n = len(yv)
    k = max(2, min(k, n))
    accs = []
    aucs = []
    for train_idx, test_idx in k_fold_indices(n, k, seed=seed):
        clf = LogisticClassifier(**clf_kwargs).fit(X[train_idx], yv[train_idx])
        proba = clf.predict_proba(X[test_idx])
        pred = proba >= 0.5
        accs.append(float(np.mean(pred == yv[test_idx])))
        aucs.append(auc_score(yv[test_idx], proba))
    majority = max(float(yv.mean()), 1.0 - float(yv.mean()))
    return {
        "n": n,
        "k_folds": k,
        "base_rate": float(yv.mean()),
        "baseline_accuracy": majority,
        "cv_accuracy_mean": float(np.mean(accs)),
        "cv_accuracy_per_fold": accs,
        "cv_auc_mean": float(np.nanmean(aucs)),
        "cv_auc_per_fold": aucs,
    }


def top_features(
    weights: np.ndarray, feature_names: Sequence[str], n: int = 10
) -> list[tuple[str, float]]:
    """Standardized-coefficient magnitude ranking (largest |weight|
    first) -- which draw axes move the walkable/unwalkable boundary
    most, given standardized inputs."""
    order = np.argsort(-np.abs(weights))[:n]
    return [(feature_names[i], float(weights[i])) for i in order]


def _main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="append", required=True,
                     help="report.json path or glob, repeatable")
    ap.add_argument("--mode", default="walk/det")
    ap.add_argument("--k-folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--top-n", type=int, default=12)
    ap.add_argument("--save-model", default=None,
                     help="persist the fitted classifier + feature "
                          "order to this JSON path (see save_model)")
    args = ap.parse_args()

    n_files = len(expand_report_paths(args.report))
    rows, labels = load_dataset(args.report, mode=args.mode)
    if not rows:
        raise SystemExit(f"no episodes with randomization+gait_valid found for mode={args.mode}")
    X, feature_names = vectorize(rows)
    print(f"pooled {len(rows)} episodes from {n_files} report file(s), "
          f"{len(feature_names)} draw features, base rate gait_valid="
          f"{np.mean(labels):.3f}")

    result = cross_validate(X, labels, k=args.k_folds, seed=args.seed)
    print(f"{args.k_folds}-fold CV accuracy: {result['cv_accuracy_mean']:.3f} "
          f"(baseline/majority-class: {result['baseline_accuracy']:.3f})  "
          f"CV AUC: {result['cv_auc_mean']:.3f}")

    clf = LogisticClassifier().fit(X, labels)
    print(f"\ntop {args.top_n} draw axes by |standardized coefficient| "
          f"(fit on all {len(rows)} episodes):")
    for name, w in top_features(clf.weights, feature_names, n=args.top_n):
        direction = "raises" if w > 0 else "lowers"
        print(f"  {name:32s} {w:+.3f}  ({direction} P(gait_valid))")

    if args.save_model:
        save_model(args.save_model, clf, feature_names)
        print(f"\nsaved model ({len(feature_names)} features) to "
              f"{args.save_model}")


if __name__ == "__main__":
    _main()
