"""Gait metrics from the per-tick CSVs both robots already save.

Works on the RL runner CSVs (hexapod2: t_s, phase, roll_deg, pitch_deg,
vx_ref_mps, q{i}_deg, cmd{i}_deg ...), the sysid runner CSVs (hexapod1:
t_s, seg, overrun, cur_a, q{i}_deg, cmd{i}_deg ...) and the sim CSVs written by
`sysid.rollout_policy_csv` (same columns + touch{i} ground truth). Prints, per
file: duration, tick rate, commanded and measured joint amplitude by joint type
(yaw/hip/knee), tracking error, stride frequency from the knee and hip commands,
per-leg knee swing, tilt range when an IMU column exists, current when it exists.

    uv run python -m sysid.gait_metrics FILE.csv [FILE.csv ...] [--phase walk] [--seg 0]
    uv run python -m sysid.gait_metrics FILE.csv --phase walk --footfall [--thr 5] [--diagram] [--cmd]

--phase keeps only rows whose `phase` column equals the value (RL CSVs use
walk/hold/run/tail); --seg keeps only that sysid segment (0 is the first
protocol segment; -1 is the runner's glide/settle). Written 2026-09-11 for the
sim-vs-hardware gait comparison (docs/GAIT_SIM_VS_HARDWARE_2026-09-11.md).

--footfall (2026-09-21) adds the per-leg view that answers "which legs drag,
which hover": foot positions by forward kinematics (`rl_move.body_ik.fk_all_feet`,
robot_abs joints), a ground plane through the lowest feet per tick (absorbs body
tilt without trusting IMU signs), clearance above it, contact = clearance < --thr
mm (5 mm agrees with MuJoCo touch sensors on ~91 % of ticks, 10 mm on ~84 %).
Per leg: duty factor, swings/s, median peak lift per swing, swing duration,
foot travel in the body frame per swing and per stance, and slip = rms deviation
of the planted foot's body-frame velocity from the consensus of all planted feet
(every planted foot should move at minus the body velocity). Body speed from the
stance consensus is reported next to vx_ref so it can be compared with the tag
tracker. --cmd scores the commanded joints instead of the measured ones (policy
intent vs achieved). --diagram prints an ASCII footfall diagram of the first
contiguous segment. Sim CSVs with touch{i} columns also get FK-vs-touch agreement.
See rl_move/sim/REALITY_GAP_REFIT.md "Per-leg footfall view".
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from rl_move.body_ik import fk_all_feet

LEG_NAMES = ["L0 (30deg)", "L1 (90deg)", "L2 (150deg)",
             "L3 (210deg)", "L4 (270deg)", "L5 (330deg)"]
SEGMENT_GAP_S = 0.5     # a gap longer than this splits the selection into segments
MIN_SWING_TICKS = 3     # shorter lift-offs are contact chatter, not swings


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
    # Chassis tilt from the mount-corrected body_* columns only; the raw
    # uncal_*/roll_deg columns are never reported as chassis tilt.
    tilt_ok = False
    for col, name in (("body_roll_deg", "roll_deg"), ("body_pitch_deg", "pitch_deg")):
        if col in d and np.isfinite(d[col]).any():
            out[name] = [round(float(np.nanmin(d[col])), 1), round(float(np.nanmax(d[col])), 1)]
            tilt_ok = True
    if not tilt_ok:
        out["imu_uncalibrated"] = True  # no trustworthy chassis-tilt metric
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


# ---------------------------------------------------------------------------
# Per-leg footfall metrics
# ---------------------------------------------------------------------------

def feet_mm(q_deg: np.ndarray) -> np.ndarray:
    """(N,18) robot_abs degrees -> (N,6,3) foot positions in the body frame, mm."""
    q = np.deg2rad(np.asarray(q_deg, dtype=float))
    return np.stack([fk_all_feet(row) for row in q]) * 1000.0


def ground_clearance(feet: np.ndarray, tol_mm: float = 6.0) -> np.ndarray:
    """Clearance (N,6) of each foot above the plane through the lowest feet.

    Per tick: plane through the three lowest feet, then a least-squares refit
    through every foot within `tol_mm` of it. Feet on the floor define the
    floor in the body frame, so body tilt drops out without any IMU input.
    """
    n = feet.shape[0]
    clear = np.zeros((n, 6))
    for k in range(n):
        p = feet[k]
        A = np.c_[p[:, 0], p[:, 1], np.ones(6)]
        idx = np.argsort(p[:, 2])[:3]
        for _ in range(2):
            coef, *_ = np.linalg.lstsq(A[idx], p[idx, 2], rcond=None)
            dz = p[:, 2] - A @ coef
            idx = np.where(dz < tol_mm)[0]
            if len(idx) < 3:
                idx = np.argsort(p[:, 2])[:3]
        clear[k] = dz
    return clear


def episodes(mask: np.ndarray) -> list[tuple[int, int]]:
    """[(start, end_exclusive)] of True runs."""
    out, start = [], None
    for i, m in enumerate(mask):
        if m and start is None:
            start = i
        elif not m and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(mask)))
    return out


def _smooth(x: np.ndarray, w: int = 5) -> np.ndarray:
    k = np.ones(w) / w
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 0, x)


def _segments(t: np.ndarray) -> list[np.ndarray]:
    cuts = np.where(np.diff(t) > SEGMENT_GAP_S)[0] + 1
    return [s for s in np.split(np.arange(len(t)), cuts) if len(s) > 2 * MIN_SWING_TICKS]


def footfall(d: dict, thr_mm: float = 5.0, use_cmd: bool = False) -> dict:
    """Per-leg duty / lift / swing / stride / slip over every contiguous segment."""
    t = d["t_s"]
    src = "cmd" if use_cmd else "q"
    q = np.stack([d[f"{src}{i}_deg"] for i in range(18)], 1)
    feet = feet_mm(q)
    clear = ground_clearance(feet)
    contact = clear < thr_mm
    vx_ref = d.get("vx_ref_mps")
    acc = {"ticks": 0, "contact_sum": 0.0, "lt3": 0, "six": 0,
           "along": [], "speed": [], "wrong": []}
    legs = [dict(contact=0, swings=0, seconds=0.0, peak=[], swing_s=[], swing_mm=[],
                 stance_mm=[], slip=[]) for _ in range(6)]
    for s in _segments(t):
        ts, ft, cl, ct = t[s], feet[s], clear[s], contact[s]
        dt = np.gradient(ts)
        vel = _smooth(np.gradient(ft[:, :, :2], axis=0) / dt[:, None, None])   # mm/s, body frame
        cons = np.full((len(s), 2), np.nan)
        for k in range(len(s)):
            if ct[k].sum() >= 2:
                cons[k] = np.median(vel[k, ct[k]], axis=0)
        ok = ~np.isnan(cons[:, 0])
        body_v = -cons
        sign = float(np.sign(np.nanmedian(vx_ref[s]))) if vx_ref is not None else 1.0
        sign = sign or 1.0
        acc["ticks"] += len(s)
        acc["contact_sum"] += float(ct.sum())
        acc["lt3"] += int((ct.sum(1) < 3).sum())
        acc["six"] += int((ct.sum(1) == 6).sum())
        acc["speed"] += list(np.hypot(body_v[ok, 0], body_v[ok, 1]))
        acc["along"] += list(body_v[ok, 0] * sign)
        for i in range(6):
            c = ct[:, i]
            L = legs[i]
            L["contact"] += int(c.sum())
            L["seconds"] += float(ts[-1] - ts[0])
            sw = [(a, b) for a, b in episodes(~c) if b - a >= MIN_SWING_TICKS]
            L["swings"] += len(sw)
            L["peak"] += [float(cl[a:b, i].max()) for a, b in sw]
            L["swing_s"] += [float(ts[b - 1] - ts[a]) for a, b in sw]
            L["swing_mm"] += [float(np.linalg.norm(ft[b - 1, i, :2] - ft[a, i, :2])) for a, b in sw]
            L["stance_mm"] += [float(np.linalg.norm(ft[b - 1, i, :2] - ft[a, i, :2]))
                               for a, b in episodes(c) if b - a >= MIN_SWING_TICKS]
            m = c & ok
            if m.any():
                L["slip"] += list(np.linalg.norm(vel[m, i] - cons[m], axis=1))
    med = lambda v: round(float(np.median(v)), 1) if v else None  # noqa: E731
    out = {
        "source": src, "thr_mm": thr_mm, "ticks": acc["ticks"],
        "feet_in_contact_mean": round(acc["contact_sum"] / max(acc["ticks"], 1), 2),
        "frac_lt3_feet": round(acc["lt3"] / max(acc["ticks"], 1), 3),
        "frac_all6_down": round(acc["six"] / max(acc["ticks"], 1), 3),
        # body speed implied by the planted feet; compare with the tag tracker
        "body_speed_from_feet_mm_s": round(float(np.mean(acc["speed"])), 1) if acc["speed"] else None,
        "body_speed_along_cmd_mm_s": round(float(np.mean(acc["along"])), 1) if acc["along"] else None,
        "legs": [],
    }
    for i, L in enumerate(legs):
        out["legs"].append({
            "leg": LEG_NAMES[i],
            "duty": round(L["contact"] / max(acc["ticks"], 1), 3),
            "swings_per_s": round(L["swings"] / L["seconds"], 2) if L["seconds"] else None,
            "lift_mm": med(L["peak"]),
            "swing_s": round(float(np.median(L["swing_s"])), 2) if L["swing_s"] else None,
            "swing_travel_mm": med(L["swing_mm"]),
            "stance_travel_mm": med(L["stance_mm"]),
            "slip_rms_mm_s": round(float(np.sqrt(np.mean(np.square(L["slip"])))), 1) if L["slip"] else None,
        })
    if all(f"touch{i}" in d for i in range(6)):
        touch = np.stack([d[f"touch{i}"] for i in range(6)], 1) > 0.5
        out["touch_agreement"] = round(float((contact == touch).mean()), 3)
        out["touch_duty"] = [round(float(v), 3) for v in touch.mean(0)]
    return out


def footfall_diagram(d: dict, thr_mm: float = 5.0, use_cmd: bool = False,
                     seconds: float = 6.0, ticks_per_char: int = 2) -> str:
    """ASCII footfall diagram of the first contiguous segment: # down, . up, : > 25 mm."""
    t = d["t_s"]
    src = "cmd" if use_cmd else "q"
    segs = _segments(t)
    if not segs:
        return ""
    s = segs[0]
    s = s[: int(seconds / max(float(np.median(np.diff(t[s]))), 1e-3))]
    q = np.stack([d[f"{src}{i}_deg"] for i in range(18)], 1)[s]
    clear = ground_clearance(feet_mm(q))
    lines = [f"footfall ({src}, contact < {thr_mm:g} mm, one char = {ticks_per_char} ticks, "
             f"{t[s[0]]:.1f}..{t[s[-1]]:.1f} s): # down  . up  : > 25 mm"]
    for i in range(6):
        row = "".join("#" if clear[k, i] < thr_mm else (":" if clear[k, i] > 25 else ".")
                      for k in range(0, len(s), ticks_per_char))
        lines.append(f"{LEG_NAMES[i]:12s} {row}")
    return "\n".join(lines)


def format_footfall(f: dict) -> str:
    hdr = (f"  footfall [{f['source']}, {f['thr_mm']:g} mm]: feet down {f['feet_in_contact_mean']}, "
           f"<3 down {f['frac_lt3_feet']*100:.0f}%, all 6 down {f['frac_all6_down']*100:.0f}%, "
           f"body speed from feet {f['body_speed_from_feet_mm_s']} mm/s "
           f"(along cmd {f['body_speed_along_cmd_mm_s']})")
    if "touch_agreement" in f:
        hdr += f", FK vs touch agreement {f['touch_agreement']*100:.0f}%"
    rows = [hdr, f"  {'leg':12s} {'duty':>5s} {'sw/s':>5s} {'lift':>5s} {'swing_s':>7s} {'swing_mm':>8s} {'stance_mm':>9s} {'slip':>5s}"]
    for L in f["legs"]:
        g = lambda k, w, p: (f"{L[k]:{w}.{p}f}" if L[k] is not None else " " * (w - 1) + "-")  # noqa: E731
        rows.append(f"  {L['leg']:12s} {g('duty',5,2)} {g('swings_per_s',5,2)} {g('lift_mm',5,1)} "
                    f"{g('swing_s',7,2)} {g('swing_travel_mm',8,1)} {g('stance_travel_mm',9,1)} {g('slip_rms_mm_s',5,0)}")
    return "\n".join(rows)


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
    ap.add_argument("--footfall", action="store_true", help="per-leg duty/lift/swing/stride/slip from foot kinematics")
    ap.add_argument("--thr", type=float, default=5.0, help="contact threshold, mm above the ground plane (default 5)")
    ap.add_argument("--cmd", action="store_true", help="score the commanded joints instead of the measured ones")
    ap.add_argument("--diagram", action="store_true", help="ASCII footfall diagram of the first segment")
    a = ap.parse_args(argv)
    for p in a.csv:
        d = select(load(p), a.phase, a.seg)
        if len(d["t_s"]) < 2:
            print(f"{p.name}: no rows after selection")
            continue
        m = metrics(d)
        if a.footfall or a.diagram:
            m["footfall"] = footfall(d, a.thr, a.cmd)
        if a.json:
            print(json.dumps({"file": str(p), **m}))
            continue
        print(f"== {p.name}")
        for k, v in m.items():
            if k == "footfall":
                print(format_footfall(v))
            else:
                print(f"  {k}: {v}")
        if a.diagram:
            print(footfall_diagram(d, a.thr, a.cmd))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
