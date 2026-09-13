"""Compare side-camera foot motion (hexapod2, cam2, 30 fps) with the replayed sim's
foot motion for the same Robot Lab runs.

Hardware timelines come from the vision pod job /data/jobs/simgap/s1_foot_timeline.py
(red boot-tip tracker, same detector as the c5 motion labels); copy its JSONs to
/tmp/simgap/vision/.  Sim timelines come from sysid.simgap.replay_variants npz files.

The camera sees roughly the three near-side boots, so identities are not matched.
Compared statistics are identity-free: fraction of visible feet stationary /
swinging, bout durations of stance and swing per tracked foot, and the fraction of
frames with no swinging foot at all (a 'dead' interval where the gait stalls).

    uv run python -m sysid.simgap.contact_compare --variant baseline
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

VIS = Path("/tmp/simgap/vision")
VAR = Path("/tmp/simgap/variants")
STANCE_MM_S, SWING_MM_S = 30.0, 77.0
LO_PX, HI_PX = 0.7, 1.8


def bouts(states: list[str], want: str, fps: float) -> list[float]:
    out, run = [], 0
    for s in states + ["END"]:
        if s == want:
            run += 1
        else:
            if run:
                out.append(run / fps)
            run = 0
    return out


def hw_stats(js: dict) -> dict:
    fps = js["fps"]; pf = js["per_frame"]
    # drop duplicated frozen frames at the start (cam2 startup duplication)
    start = 0
    for i in range(1, len(pf)):
        if pf[i]["feet"] != pf[i - 1]["feet"] or pf[i]["box"] != pf[i - 1]["box"]:
            start = i; break
    pf = pf[start + 5:]
    vis = np.array([len(p["feet"]) for p in pf]); ns = np.array([p["n_stance"] for p in pf]); nw = np.array([p["n_swing"] for p in pf])
    seen = vis > 0
    # per-track state sequences
    tracks: dict[int, dict[int, str]] = {}
    for p in pf:
        for ti, x, y, v, st in p["feet"]:
            tracks.setdefault(ti, {})[p["f"]] = st
    st_b, sw_b = [], []
    for ti, seq in tracks.items():
        if len(seq) < 15:
            continue
        fs = sorted(seq); states = [seq[f] for f in fs]
        st_b += bouts(states, "stance", fps); sw_b += bouts(states, "swing", fps)
    return {
        "frames": int(len(pf)), "frac_frames_feet_seen": round(float(seen.mean()), 3),
        "mean_visible_feet": round(float(vis[seen].mean()), 2) if seen.any() else None,
        "frac_visible_stationary": round(float(ns[seen].sum() / max(vis[seen].sum(), 1)), 3),
        "frac_visible_swinging": round(float(nw[seen].sum() / max(vis[seen].sum(), 1)), 3),
        "frac_frames_no_swing": round(float(np.mean(nw[seen] == 0)), 3),
        "stance_bout_s_med": round(float(np.median(st_b)), 2) if st_b else None,
        "stance_bout_s_p90": round(float(np.percentile(st_b, 90)), 2) if st_b else None,
        "swing_bout_s_med": round(float(np.median(sw_b)), 2) if sw_b else None,
        "swing_bout_s_p90": round(float(np.percentile(sw_b, 90)), 2) if sw_b else None,
        "n_stance_bouts": len(st_b), "n_swing_bouts": len(sw_b),
    }


def sim_stats(npz: Path) -> dict:
    d = np.load(npz); t = d["t"]; fxyz = d["foot_xyz"]; ff = d["foot_f"]
    dt = np.gradient(t); vel = np.gradient(fxyz, axis=0) / dt[:, None, None]
    sp = np.linalg.norm(vel[:, :, :2], axis=2) * 1000
    fps = 1.0 / float(np.median(np.diff(t)))
    # same +-4-sample median smoothing as the vision tracker, scaled to this tick rate
    from scipy.ndimage import median_filter
    k = max(3, int(round(9 * fps / 30.0)) | 1)
    sp = median_filter(sp, size=(k, 1), mode="nearest")
    stance = sp < STANCE_MM_S; swing = sp > SWING_MM_S
    st_b, sw_b = [], []
    for f in range(6):
        states = ["stance" if a else ("swing" if b else "amb") for a, b in zip(stance[:, f], swing[:, f])]
        st_b += bouts(states, "stance", fps); sw_b += bouts(states, "swing", fps)
    return {
        "ticks": int(len(t)), "frac_stationary": round(float(stance.mean()), 3), "frac_swinging": round(float(swing.mean()), 3),
        "frac_ticks_no_swing": round(float(np.mean(swing.sum(1) == 0)), 3),
        "mean_feet_contact": round(float((ff > 0.05).sum(1).mean()), 2),
        "frac_contact_sliding": round(float(np.mean((ff > 0.05) & swing)), 3),
        "stance_bout_s_med": round(float(np.median(st_b)), 2) if st_b else None,
        "stance_bout_s_p90": round(float(np.percentile(st_b, 90)), 2) if st_b else None,
        "swing_bout_s_med": round(float(np.median(sw_b)), 2) if sw_b else None,
        "swing_bout_s_p90": round(float(np.percentile(sw_b, 90)), 2) if sw_b else None,
        "foot_lift_p95_mm": [round(float(x), 1) for x in np.percentile(fxyz[:, :, 2], 95, axis=0) * 1000],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="baseline")
    a = ap.parse_args(argv)
    out = []
    for vj in sorted(VIS.glob("*.json")):
        run = vj.name.split("__")[0]
        js = json.loads(vj.read_text())
        hw = hw_stats(js)
        sims = sorted((VAR / a.variant).glob(f"{run}__*.npz"))
        sim = sim_stats(sims[0]) if sims else None
        out.append({"run": run, "clip": js["clip"], "hw": hw, "sim": sim, "variant": a.variant})
        print(f"== {run} {js['clip'].split('/')[-1]}")
        print("   hw :", json.dumps(hw))
        print("   sim:", json.dumps(sim))
    Path("/tmp/simgap/contact_compare_%s.json" % a.variant.replace("/", "_")).write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
