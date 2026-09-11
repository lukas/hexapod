"""Gait metrics from the per-tick CSVs both robots already save.

Works on the RL runner CSVs (hexapod2: t_s, phase, roll_deg, pitch_deg,
vx_ref_mps, q{i}_deg, cmd{i}_deg ...) and the sysid runner CSVs (hexapod1:
t_s, seg, overrun, cur_a, q{i}_deg, cmd{i}_deg ...). Prints, per file: duration,
tick rate, commanded and measured joint amplitude by joint type (yaw/hip/knee),
tracking error, stride frequency from the knee and hip commands, per-leg knee
swing, tilt range when an IMU column exists, current when it exists.

    uv run python -m sysid.gait_metrics FILE.csv [FILE.csv ...] [--phase walk] [--seg 0]

--phase keeps only rows whose `phase` column equals the value (RL CSVs use
walk/hold/run/tail); --seg keeps only that sysid segment (0 is the first
protocol segment; -1 is the runner's glide/settle). Written 2026-09-11 for the
sim-vs-hardware gait comparison (docs/GAIT_SIM_VS_HARDWARE_2026-09-11.md).
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np


def load(path: Path) -> dict:
    with open(path) as fh:
        rd = csv.DictReader(fh)
        rows = list(rd)
    out = {}
    for k in rd.fieldnames or []:
        try:
            out[k] = np.array([float(r[k]) if r[k] not in ("", None) else np.nan for r in rows])
        except ValueError:
            out[k] = np.array([r[k] for r in rows])
    return out


def dominant_hz(t: np.ndarray, x: np.ndarray, floor_hz: float = 0.05) -> float:
    x = x - np.nanmean(x)
    if len(x) < 32:
        return float("nan")
    dt = float(np.median(np.diff(t)))
    f = np.fft.rfftfreq(len(x), dt)
    p = np.abs(np.fft.rfft(x))
    p[f < floor_hz] = 0
    return float(f[p.argmax()])


def metrics(d: dict) -> dict:
    t = d["t_s"]
    dur = float(t[-1] - t[0])
    q = np.stack([d[f"q{i}_deg"] for i in range(18)], 1)
    c = np.stack([d[f"cmd{i}_deg"] for i in range(18)], 1)
    err = np.abs(c - q)
    camp = np.nanmax(c, 0) - np.nanmin(c, 0)
    qamp = np.nanmax(q, 0) - np.nanmin(q, 0)
    by = lambda a, k: round(float(a[k::3].mean()), 1)  # noqa: E731  joint k of each leg: 0 yaw, 1 hip, 2 knee
    out = {
        "rows": int(len(t)), "dur_s": round(dur, 1), "tick_hz": round(len(t) / dur, 1) if dur else None,
        "cmd_amp_deg": {"yaw": by(camp, 0), "hip": by(camp, 1), "knee": by(camp, 2)},
        "meas_amp_deg": {"yaw": by(qamp, 0), "hip": by(qamp, 1), "knee": by(qamp, 2)},
        "track_err_deg": {"mean": round(float(np.nanmean(err)), 1), "max": round(float(np.nanmax(err)), 1)},
        "stride_hz": {"knee": round(float(np.nanmedian([dominant_hz(t, c[:, i]) for i in range(2, 18, 3)])), 3),
                      "hip": round(float(np.nanmedian([dominant_hz(t, c[:, i]) for i in range(1, 18, 3)])), 3)},
        "knee_cmd_amp_per_leg": [round(float(a), 1) for a in camp[2::3]],
        "hip_cmd_amp_per_leg": [round(float(a), 1) for a in camp[1::3]],
    }
    for col, name in (("roll_deg", "roll_deg"), ("pitch_deg", "pitch_deg")):
        if col in d:
            out[name] = [round(float(np.nanmin(d[col])), 1), round(float(np.nanmax(d[col])), 1)]
    if "gyro_z_dps" in d:
        out["gyro_z_rms_dps"] = round(float(np.sqrt(np.nanmean(d["gyro_z_dps"] ** 2))), 1)
    if "vx_ref_mps" in d:
        out["vx_ref_mps"] = [round(float(np.nanmin(d["vx_ref_mps"])), 3), round(float(np.nanmax(d["vx_ref_mps"])), 3)]
    if "max_cur_a" in d:
        out["max_cur_a"] = round(float(np.nanmax(d["max_cur_a"])), 2)
    if "cur_a" in d:
        out["cur_a"] = {"max": round(float(np.nanmax(d["cur_a"])), 2), "mean": round(float(np.nanmean(d["cur_a"])), 2)}
    if "overrun" in d:
        out["overruns"] = int(np.nansum(d["overrun"]))
    return out


def select(d: dict, phase: str | None, seg: str | None) -> dict:
    m = np.ones(len(d["t_s"]), bool)
    if phase and "phase" in d and d["phase"].dtype.kind in "US":
        m &= d["phase"] == phase
    if seg is not None and "seg" in d:
        m &= (d["seg"] == seg) if d["seg"].dtype.kind in "US" else (d["seg"] == float(seg))
    return {k: v[m] for k, v in d.items()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("csv", nargs="+", type=Path)
    ap.add_argument("--phase", default=None, help="keep rows with this phase (RL CSVs: walk, run)")
    ap.add_argument("--seg", default=None, help="keep this sysid segment (0 = first protocol segment)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    for p in a.csv:
        d = select(load(p), a.phase, a.seg)
        if len(d["t_s"]) < 2:
            print(f"{p.name}: no rows after selection")
            continue
        m = metrics(d)
        if a.json:
            print(json.dumps({"file": str(p), **m}))
        else:
            print(f"== {p.name}")
            for k, v in m.items():
                print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
