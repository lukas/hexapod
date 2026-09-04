"""audit_dr_hold_correlate.py — correlate the per-episode DR draw
against a fired termination reason.

WHY (standwalk STATUS Next#1, 2026-09-04): the mlcontprice dose-bracket
dig-in closed with k=8 as the adopted `hold_min_load` ceiling recipe --
better than k=0/2/16, but still firing on SOME own-DR episodes (the
mlcontprice2 dig-in's own read: 4.2% combined rate at k=8, non-zero).
The next lever isn't another dose point (bracketed both directions,
09-04 ~16:3x) -- it's finding WHICH randomized axis the k=8 price still
under-covers. `eval_checkpoint.run_episode` now persists
`ep["randomization"]` (this same cycle's landing, additive field, see
`test_eval_checkpoint_randomization_field.py`) -- this tool is the
consumer: split a report.json's episodes by whether they fired the
named termination reason, and compare the sampled DR fields between
the two groups (median + a plain standardized-mean-difference "d" so a
skim can spot which axis actually separates the groups instead of
eyeballing a raw episode dump).

Pure function (`correlate`) + thin CLI, same shape as
`audit_over_current.py`. Numeric scalar fields only (mass_scale,
friction_scale, kp_scale_mean, torque_scale, latency_scale,
deadband_scale, cmd_drop_prob, ground_tilt_deg, zero_bias_max_deg,
start_offset_max_deg, tipped_roll_deg, rise_rock_roll_deg,
walk_kick_roll_deg, walk_kick_dur_s, walk_push_peak_nm,
walk_push_dur_s); `fault` (categorical) is reported as fired/clean
counts per fault_mode instead of a numeric d.

Usage:
    uv run python -m rl_move.sim.audit_dr_hold_correlate \
        logs/ckpt_eval/<run>_cmdstress/owndr/report.json \
        [more_report.json ...] [--reason hold_min_load] [--json out.json]

n<2 in either group is reported (not hidden) but flagged low-n --
this is a triage instrument, not a statistical test with a p-value.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

NUMERIC_FIELDS = (
    "mass_scale", "friction_scale", "ground_tilt_deg", "kp_scale_mean",
    "torque_scale", "latency_scale", "deadband_scale", "cmd_drop_prob",
    "zero_bias_max_deg", "start_offset_max_deg", "tipped_roll_deg",
    "rise_rock_roll_deg", "walk_kick_roll_deg", "walk_kick_dur_s",
    "walk_push_peak_nm", "walk_push_dur_s",
)


def _episodes(report: dict):
    for label, eps in (report.get("episodes") or {}).items():
        for ep in eps:
            yield label, ep


def load_episodes(paths: list[Path]) -> list[dict]:
    """Every episode (any label) across every report.json path that
    carries a `randomization` draw -- episodes without one (DR-off
    passes, or pre-this-change report.json files) are silently
    skipped, never crashed on."""
    out = []
    for p in paths:
        report = json.loads(Path(p).read_text())
        for _label, ep in _episodes(report):
            if ep.get("randomization") is not None:
                out.append(ep)
    return out


def _std_mean_diff(fired: list[float], clean: list[float]) -> float | None:
    """Plain (not pooled-variance-corrected) standardized mean
    difference: (mean(fired) - mean(clean)) / std(clean or fired,
    whichever is nonzero) -- a skim signal, not a formal Cohen's d;
    None when either group is empty or both are constant."""
    if not fired or not clean:
        return None
    mf, mc = statistics.fmean(fired), statistics.fmean(clean)
    pooled = clean + fired
    if len(pooled) < 2:
        return None
    sd = statistics.pstdev(pooled)
    if sd < 1e-9:
        return None
    return (mf - mc) / sd


def correlate(episodes: list[dict], *, reason: str) -> dict:
    """Pure function: episodes (each carrying `term_reason` +
    `randomization`) -> per-field fired-vs-clean comparison."""
    fired = [e for e in episodes if e.get("term_reason") == reason]
    clean = [e for e in episodes if e.get("term_reason") != reason]
    out: dict = {
        "reason": reason, "n_fired": len(fired), "n_clean": len(clean),
        "low_n_warning": len(fired) < 2 or len(clean) < 2,
        "fields": {},
    }
    for field in NUMERIC_FIELDS:
        fv = [e["randomization"][field] for e in fired
              if field in e.get("randomization", {})]
        cv = [e["randomization"][field] for e in clean
              if field in e.get("randomization", {})]
        if not fv and not cv:
            continue
        out["fields"][field] = {
            "fired_median": round(statistics.median(fv), 4) if fv else None,
            "clean_median": round(statistics.median(cv), 4) if cv else None,
            "std_mean_diff": (round(d, 3) if (d := _std_mean_diff(fv, cv))
                              is not None else None),
        }
    # Categorical: fault mode counts per group.
    fault_fired: dict[str, int] = {}
    fault_clean: dict[str, int] = {}
    for e, bucket in ((e, fault_fired) for e in fired):
        m = e.get("randomization", {}).get("fault", "none")
        bucket[m] = bucket.get(m, 0) + 1
    for e, bucket in ((e, fault_clean) for e in clean):
        m = e.get("randomization", {}).get("fault", "none")
        bucket[m] = bucket.get(m, 0) + 1
    out["fault_fired_counts"] = fault_fired
    out["fault_clean_counts"] = fault_clean
    # Ranked by |std_mean_diff|, biggest separation first -- the skim.
    ranked = sorted(
        (f for f in out["fields"].items() if f[1]["std_mean_diff"] is not None),
        key=lambda kv: abs(kv[1]["std_mean_diff"]), reverse=True)
    out["ranked_fields"] = [k for k, _v in ranked]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("reports", nargs="+", type=Path)
    ap.add_argument("--reason", default="hold_min_load")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args(argv)

    episodes = load_episodes(args.reports)
    result = correlate(episodes, reason=args.reason)
    text = json.dumps(result, indent=1)
    print(text)
    if args.json:
        args.json.write_text(text)
        print(f"[audit-dr-hold] wrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
