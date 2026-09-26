"""Gait-valid RATE + CI instrument for the standwalk ceil225/ceil25 grid.

WHY (CURRENT_TRUTHS 2026-09-26 ~00:2x/~00:5x, standwalk STATUS "Next"#1):
the popup gate's `gait_valid X/6` count on a FIXED 6-episode draw cannot
tell a trained checkpoint from an untrained one at the 2.25deg/0.035pct
(and 2.5deg/0.04pct) DR ceilings -- the discriminator found the ceil20
PARENT, never trained at 2.25, zero-shots the IDENTICAL sacrifice pattern
on the same draws. This module is the "n>=24 rate+CI instead of a fixed-N
count" follow-up the STATUS doc named as unbuilt: it does not run new
rollouts itself (reuse `eval_checkpoint.py --per-mode N --seed S`, already
capable of arbitrary N via its existing CLI -- see `ops.sh evalcmd`), it
turns one or more of that command's `report.json` outputs into a rate with
a Wilson score interval, and -- given two reports (e.g. a trained
candidate vs its own untrained parent evaluated zero-shot on the identical
cfg) -- a plain two-proportion overlap read so a cycle can say "the rate
moved" instead of eyeballing two single-digit fractions.

Usage (from `prototype_sts3215`, after producing report.json files with
`eval_checkpoint.py --per-mode 24 ...`)::

    uv run python -m rl_move.sim.probe_gait_valid_rate \
        logs/ckpt_eval/probe_n24_cont40m_s0/report.json \
        --vs logs/ckpt_eval/probe_n24_ceil20parent_zeroshot/report.json \
        --mode walk/det
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial rate. `n==0` -> (0.0, 1.0)
    (no information, not a divide-by-zero crash)."""
    if n <= 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1.0 + z * z / n
    center = p + z * z / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    lo = (center - spread) / denom
    hi = (center + spread) / denom
    return (max(0.0, lo), min(1.0, hi))


def gait_valid_rate(report: dict, mode: str = "walk/det") -> dict:
    """Extract the gait_valid rate + Wilson CI for one report.json's
    episodes under `mode` (report's own `episodes[mode]` list, each
    episode dict already carrying a `gait_valid` bool)."""
    eps = (report.get("episodes") or {}).get(mode) or []
    n = len(eps)
    successes = sum(1 for e in eps if e.get("gait_valid"))
    lo, hi = wilson_interval(successes, n)
    prog = sorted(e.get("progress_ratio", 0.0) for e in eps)
    prog_med = prog[len(prog) // 2] if prog else 0.0
    return {
        "mode": mode, "n": n, "successes": successes,
        "rate": successes / n if n else 0.0,
        "ci95": (lo, hi), "prog_med": prog_med,
        "checkpoint": report.get("checkpoint"),
    }


def overlap(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """True iff two Wilson intervals overlap (i.e. the two rates are
    NOT distinguishable at ~95% given this sample size)."""
    return a[0] <= b[1] and b[0] <= a[1]


def compare(report_a: dict, report_b: dict, mode: str = "walk/det") -> dict:
    ra = gait_valid_rate(report_a, mode)
    rb = gait_valid_rate(report_b, mode)
    return {
        "a": ra, "b": rb,
        "rate_delta": ra["rate"] - rb["rate"],
        "ci_overlap": overlap(ra["ci95"], rb["ci95"]),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report", type=Path)
    ap.add_argument("--vs", type=Path, default=None,
                     help="a second report.json (e.g. the zero-shot parent) "
                          "to compare against")
    ap.add_argument("--mode", default="walk/det")
    args = ap.parse_args()

    rep_a = json.loads(args.report.read_text())
    if args.vs is None:
        result = gait_valid_rate(rep_a, args.mode)
        print(json.dumps(result, indent=2))
        return
    rep_b = json.loads(args.vs.read_text())
    result = compare(rep_a, rep_b, args.mode)
    print(json.dumps(result, indent=2))
    lo_a, hi_a = result["a"]["ci95"]
    lo_b, hi_b = result["b"]["ci95"]
    print(f"\nA ({args.report.name}): {result['a']['successes']}/{result['a']['n']} "
          f"= {result['a']['rate']:.3f} [{lo_a:.3f}, {hi_a:.3f}]  prog_med={result['a']['prog_med']:.3f}")
    print(f"B ({args.vs.name}): {result['b']['successes']}/{result['b']['n']} "
          f"= {result['b']['rate']:.3f} [{lo_b:.3f}, {hi_b:.3f}]  prog_med={result['b']['prog_med']:.3f}")
    print(f"CI overlap (rates indistinguishable at ~95%): {result['ci_overlap']}")


if __name__ == "__main__":
    main()
