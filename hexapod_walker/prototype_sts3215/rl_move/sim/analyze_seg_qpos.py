"""Analysis companion to `eval_modeseq.py --dump-seg-qpos` (09-23,
standwalk composed-session own-DR fall gap, walk/lower analogue of
the rise-pose root-cause diagnostic).

Answers the flagged Next question directly: does the composed
session's REAL state at the walk/lower handoffs (and through a long
randomized walk) actually differ from what each specialist's own
isolated per-episode gate resets into? `--dump-seg-qpos` captures
BOTH halves of that comparison from the identical env.reset() call
(<mode>_cold_reset = the isolated bar's own reset pose,
<mode>_entry = the composed-session carried-over pose restored on
top of it a moment later) plus periodic walk_mid samples, all tagged
by episode. This script pairs them up, per episode, and reports the
delta -- overall and split by whether that episode's walk/lower
segment actually fell (from the matching `--out` report.json) -- so a
FAIL is diagnosed as "off-distribution entry state" (fix = exposure/
curriculum) vs "something else develops mid-segment" (fix =
elsewhere) without guessing.

Usage:
    uv run python -m rl_move.sim.analyze_seg_qpos \\
        --npz logs/.../segstate_dr07_n30.npz \\
        --report logs/.../segstate_dr07_n30_report.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def _seg_mask(seg_arr: np.ndarray, tag: str) -> np.ndarray:
    return seg_arr == tag


def fall_by_ep(report: dict) -> dict[int, dict[str, bool]]:
    """{ep: {"walk": fell?, "lower": fell?}} from an eval_modeseq.py
    --out report.json. A segment counts as "fell" if it has a `fall`
    key (matches the harness's own zero_fall bookkeeping)."""
    out: dict[int, dict[str, bool]] = {}
    for ep_rec in report["episodes"]:
        d = {"walk": False, "lower": False}
        for seg in ep_rec["segments"]:
            if seg.get("mode") in d and seg.get("fall"):
                d[seg["mode"]] = True
        out[ep_rec["ep"]] = d
    return out


def summarize(npz_path: Path, report_path: Path | None) -> dict:
    d = np.load(npz_path, allow_pickle=True)
    seg, ep, t_s = d["seg"], d["ep"], d["t_s"]
    q_deg, qvel = d["q_deg"], d["qvel_rad_s"]
    h_err, roll, pitch = (d["height_err_mm"], d["roll_deg"],
                          d["pitch_deg"])
    fbe = (fall_by_ep(json.loads(report_path.read_text()))
          if report_path is not None else {})

    def pair_deltas(mode: str) -> dict:
        entry_m = _seg_mask(seg, f"{mode}_entry")
        cold_m = _seg_mask(seg, f"{mode}_cold_reset")
        cold_by_ep = {int(e): i for i, e in enumerate(ep[cold_m])}
        rows = []
        for i in np.nonzero(entry_m)[0]:
            e = int(ep[i])
            j = cold_by_ep.get(e)
            if j is None:
                continue
            j_global = np.nonzero(cold_m)[0][j]
            q_delta = np.abs(q_deg[i] - q_deg[j_global])
            qv_delta = np.abs(qvel[i] - qvel[j_global])
            rows.append({
                "ep": e,
                "fell": bool(fbe.get(e, {}).get(mode, False)),
                "height_err_delta_mm": float(
                    (h_err[i] if not np.isnan(h_err[i]) else 0.0)
                    - (h_err[j_global]
                       if not np.isnan(h_err[j_global]) else 0.0)),
                "roll_delta_deg": float(abs(roll[i] - roll[j_global])),
                "pitch_delta_deg": float(
                    abs(pitch[i] - pitch[j_global])),
                "q_deg_max_delta": float(q_delta.max()),
                "q_deg_mean_delta": float(q_delta.mean()),
                "qvel_max_delta": float(qv_delta.max()),
            })
        return rows

    def bucket_stats(rows: list[dict], key: str) -> dict:
        fell = [r[key] for r in rows if r["fell"]]
        ok = [r[key] for r in rows if not r["fell"]]
        return {
            "n_fell": len(fell), "n_ok": len(ok),
            "median_fell": (round(float(np.median(fell)), 2)
                           if fell else None),
            "median_ok": (round(float(np.median(ok)), 2)
                         if ok else None),
        }

    out = {}
    for mode in ("walk", "lower"):
        rows = pair_deltas(mode)
        mode_out = {
            "n_pairs": len(rows),
            "n_fell": sum(1 for r in rows if r["fell"]),
        }
        for metric in ("height_err_delta_mm", "roll_delta_deg",
                      "pitch_delta_deg", "q_deg_max_delta",
                      "q_deg_mean_delta", "qvel_max_delta"):
            mode_out[metric] = bucket_stats(rows, metric)
        out[mode] = mode_out
    # walk_mid drift over the session (composed only, no cold-reset
    # analogue exists mid-segment): does the state at t=45-60s look
    # different from t=0-15s, i.e. does randomization exposure
    # accumulate over the session rather than trip at the handoff?
    mid_m = _seg_mask(seg, "walk_mid")
    if mid_m.any():
        ts = sorted(set(round(float(x), 0) for x in t_s[mid_m]))
        out["walk_mid_by_t"] = {}
        for t in ts:
            m = mid_m & (np.round(t_s, 0) == t)
            out["walk_mid_by_t"][str(t)] = {
                "n": int(m.sum()),
                "roll_deg_med": round(float(np.median(roll[m])), 2),
                "pitch_deg_med": round(float(np.median(pitch[m])), 2),
            }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--npz", type=Path, required=True)
    ap.add_argument("--report", type=Path, default=None,
                    help="matching eval_modeseq.py --out report.json "
                         "(adds the fell-vs-ok split); omit for an "
                         "unsplit summary only")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    result = summarize(args.npz, args.report)
    text = json.dumps(result, indent=1)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
