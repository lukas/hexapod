"""gait_valid_rate.py -- DR-ceiling rate+CI aggregator (standwalk, 2026-09-26).

WHY: the ceil225/ceil25 stepping-stone grid's own gate scored
gait_valid as a bare fixed-N count (N=6, later N=24) over a FIXED
held-out episode-seed set. CURRENT_TRUTHS 2026-09-26 ~00:2x/~00:5x
found that at both 2.25deg/0.035pct and 2.5deg/0.04pct ceilings, a
TRAINED checkpoint and its UNTRAINED parent (evaluated zero-shot at
the same ceiling for the first time) produce statistically
indistinguishable gait_valid counts and per-leg sacrifice histograms
-- the fixed-N draws, not the policy, dominate the signal. A bare
count/N cannot say whether that indistinguishability is real (no
effect) or just imprecise (N too small to resolve a real effect).

This module is the fix named in that entry: turn "N/M" into a rate
with a confidence interval, and turn "checkpoint A's N/M vs checkpoint
B's N'/M'" into an actual two-proportion significance test, so a
future arm can say "trained changed the rate, CI excludes zero" or
"no evidence of a difference at this N" instead of eyeballing two raw
counts. Pure stats over already-produced eval_checkpoint report.json
files -- no new sim mechanics, no new randomization, no rollout.

Usage (CLI):
    uv run python -m rl_move.sim.gait_valid_rate \
        --report logs/ckpt_eval/<child>/report.json \
        --report logs/ckpt_eval/<parent>/report.json \
        --mode walk/det

Library:
    from rl_move.sim.gait_valid_rate import (
        episode_gait_valid_counts, wilson_interval, two_proportion_z_test,
    )
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterable, Sequence


def episode_gait_valid_counts(report: dict, mode: str = "walk/det") -> tuple[int, int]:
    """Return (k, n): number of gait_valid episodes and total episodes
    for `mode` in a single eval_checkpoint report.json dict."""
    episodes = report.get("episodes", {})
    eps = episodes.get(mode, [])
    n = len(eps)
    k = sum(1 for e in eps if e.get("gait_valid"))
    return k, n


def aggregate_counts(reports: Iterable[dict], mode: str = "walk/det") -> tuple[int, int]:
    """Sum (k, n) across multiple report dicts (e.g. several reseeds of
    the same checkpoint) -- more episodes, same underlying question."""
    k_total = 0
    n_total = 0
    for report in reports:
        k, n = episode_gait_valid_counts(report, mode=mode)
        k_total += k
        n_total += n
    return k_total, n_total


def per_leg_sacrifice_histogram(report: dict, mode: str = "walk/det") -> dict[int, int]:
    """Count how many episodes sacrifice each leg index, for `mode`."""
    hist: dict[int, int] = {}
    for ep in report.get("episodes", {}).get(mode, []):
        for leg in ep.get("sacrificed_legs", []) or []:
            hist[leg] = hist.get(leg, 0) + 1
    return hist


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Wilson score interval for a binomial rate k/n. Returns
    (point_rate, lo, hi). z=1.96 -> ~95% CI. Well-behaved at k=0 or
    k=n (unlike the naive normal-approximation interval), which matters
    here since small-N ceiling arms often sit near the edges."""
    if n <= 0:
        return (float("nan"), float("nan"), float("nan"))
    p = k / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p) / n) + (z * z / (4 * n * n)))) / denom
    lo = max(0.0, center - half)
    hi = min(1.0, center + half)
    return (p, lo, hi)


def two_proportion_z_test(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float]:
    """Pooled two-proportion z-test. Returns (z, two_sided_p). NaN if
    either sample is empty or the pooled variance is degenerate (both
    counts identical and at 0 or n, e.g. all-zero vs all-zero)."""
    if n1 <= 0 or n2 <= 0:
        return (float("nan"), float("nan"))
    p1 = k1 / n1
    p2 = k2 / n2
    p_pool = (k1 + k2) / (n1 + n2)
    var = p_pool * (1 - p_pool) * (1.0 / n1 + 1.0 / n2)
    if var <= 0:
        return (0.0, 1.0) if p1 == p2 else (float("inf"), 0.0)
    z = (p1 - p2) / math.sqrt(var)
    # two-sided p-value from the standard normal survival function
    p_value = math.erfc(abs(z) / math.sqrt(2.0))
    return (z, p_value)


def _load(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def compare_reports(
    paths: Sequence[Path],
    mode: str = "walk/det",
    labels: Sequence[str] | None = None,
) -> str:
    """Human-readable rate+CI for each report plus every pairwise
    two-proportion z-test. This is what the CLI prints and what a
    future arm's triage should read instead of raw N/M counts."""
    labels = list(labels) if labels else [str(p) for p in paths]
    reports = [_load(p) for p in paths]
    counts = [episode_gait_valid_counts(r, mode=mode) for r in reports]
    lines = [f"gait_valid_rate mode={mode}"]
    for label, (k, n) in zip(labels, counts):
        p, lo, hi = wilson_interval(k, n)
        lines.append(f"  {label}: {k}/{n} = {p:.3f}  95% CI [{lo:.3f}, {hi:.3f}]")
    if len(paths) >= 2:
        lines.append("  pairwise two-proportion z-tests (H0: same rate):")
        for i in range(len(paths)):
            for j in range(i + 1, len(paths)):
                k1, n1 = counts[i]
                k2, n2 = counts[j]
                z, p_value = two_proportion_z_test(k1, n1, k2, n2)
                sig = "SIGNIFICANT (p<0.05)" if p_value < 0.05 else "no evidence of a difference"
                lines.append(
                    f"    {labels[i]} vs {labels[j]}: z={z:.3f} p={p_value:.4f} -> {sig}"
                )
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="append", required=True, type=Path,
                     help="path to an eval_checkpoint report.json; repeat for each checkpoint/arm to compare")
    ap.add_argument("--label", action="append", default=None,
                     help="optional label per --report, same order/count")
    ap.add_argument("--mode", default="walk/det",
                     help="episode-group key inside report['episodes'], e.g. walk/det, walk/sto")
    args = ap.parse_args()
    print(compare_reports(args.report, mode=args.mode, labels=args.label))


if __name__ == "__main__":
    main()
