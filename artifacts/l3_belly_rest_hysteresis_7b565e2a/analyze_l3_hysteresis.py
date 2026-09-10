#!/usr/bin/env python3
"""Per-cycle L3 hip hysteresis from the runner's own synchronized CSV.

Loop width = settled measured hip angle at the SHARED commanded angle
(-47.133 deg, the mid-sweep waypoint the trajectory passes through in both
directions), out-stroke minus in-stroke. "Settled" is the last 1.0 s of each
3.1 s dwell, the same definition the L5 sibling run used, so the legs are
directly comparable.

The dwell structure is derived from the reviewed protocol itself rather than
a hand-written phase map: a dwell is a maximal run of constant commanded hip,
and its stroke direction is set by whether the PREVIOUS extreme was the outer
(-51.14) or inner (-42.96) one.
"""
from __future__ import annotations
import csv, json, statistics, sys

PROTO = sys.argv[1]
CSV = sys.argv[2]
OUT = sys.argv[3]
HIP_J, KNEE_J = 10, 11
SHARED_CMD = -47.133
SETTLE_S = 1.0

proto = json.load(open(PROTO))
hz = float(proto["hz"])
q = proto["segments"][0]["q_deg"]
hip_cmd = [row[HIP_J] for row in q]
knee_cmd = [row[KNEE_J] for row in q]

runs, s = [], 0
for i in range(1, len(hip_cmd) + 1):
    if i == len(hip_cmd) or abs(hip_cmd[i] - hip_cmd[s]) > 1e-9:
        runs.append({"a": s, "b": i - 1, "n": i - s, "hip": hip_cmd[s],
                     "knee": knee_cmd[s]})
        s = i
dwells = [r for r in runs if r["n"] >= 20]           # >= 2 s

OUTER, INNER = -51.14, -42.96
shared, prev_extreme = [], None
for d in dwells:
    if abs(d["hip"] - OUTER) < 0.05:
        prev_extreme = "outer"
    elif abs(d["hip"] - INNER) < 0.05:
        prev_extreme = "inner"
    elif abs(d["hip"] - SHARED_CMD) < 0.05:
        # leaving the outer extreme == the OUT stroke (foot moving outward,
        # hip returning toward zero); leaving the inner == the IN stroke.
        d = dict(d, stroke="out" if prev_extreme == "outer" else "in")
        shared.append(d)

rows = list(csv.DictReader(open(CSV)))
by_tick = {}
for r in rows:
    try:
        by_tick[int(r["tick"] if "tick" in r else r["k"])] = r
    except (KeyError, ValueError):
        pass
if not by_tick:                                       # fall back to order
    by_tick = dict(enumerate(rows))


def col(row, *names):
    for n in names:
        if n in row and row[n] not in ("", None):
            try:
                return float(row[n])
            except ValueError:
                return None
    return None


def settled(d, joint):
    n = int(SETTLE_S * hz)
    vals, cur, load, temp = [], [], [], []
    for k in range(d["b"] - n + 1, d["b"] + 1):
        r = by_tick.get(k)
        if not r:
            continue
        # Runner CSV: q<j>_deg present, cmd<j>_deg command, cur<j>_a per-joint
        # current; load_pct/temp_c are the ACTIVE joint's own full-feedback
        # columns (throttled to ~10 Hz), so they are read unsuffixed.
        v = col(r, f"q{joint}_deg")
        if v is not None:
            vals.append(v)
        c = col(r, f"cur{joint}_a")
        if c is not None:
            cur.append(abs(c))
        # For a whole-body `traj` segment the runner writes joint=-1 and the
        # load_pct/temp_c columns carry the run-level full-feedback reading
        # (throttled to ~10 Hz), not a per-joint one. Read them as such.
        lo = col(r, "load_pct")
        if lo is not None:
            load.append(abs(lo))
        tc = col(r, "temp_c")
        if tc is not None:
            temp.append(tc)
    return {"n": len(vals),
            "deg": statistics.fmean(vals) if vals else None,
            "sd": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
            "cur_a": statistics.fmean(cur) if cur else None,
            "load_pct": statistics.fmean(load) if load else None,
            "temp_c": max(temp) if temp else None}


cycles, out_s, in_s = [], [], []
for d in shared:
    hip = settled(d, HIP_J)
    knee = settled(d, KNEE_J)
    rec = {"ticks": [d["a"], d["b"]], "t_s": round(d["a"] / hz, 1),
           "stroke": d["stroke"], "cmd_hip_deg": d["hip"],
           "cmd_knee_deg": d["knee"], "hip": hip, "knee": knee,
           "hip_err_deg": (None if hip["deg"] is None
                           else round(hip["deg"] - d["hip"], 4))}
    cycles.append(rec)
    (out_s if d["stroke"] == "out" else in_s).append(rec)

pairs = []
for i, (o, n) in enumerate(zip(out_s, in_s), start=1):
    if o["hip"]["deg"] is None or n["hip"]["deg"] is None:
        continue
    pairs.append({
        "repeat": i,
        "out_t_s": o["t_s"], "in_t_s": n["t_s"],
        "hip_loop_deg": round(o["hip"]["deg"] - n["hip"]["deg"], 4),
        "knee_loop_deg": (round(o["knee"]["deg"] - n["knee"]["deg"], 4)
                          if o["knee"]["deg"] is not None
                          and n["knee"]["deg"] is not None else None),
        "out_err_deg": o["hip_err_deg"], "in_err_deg": n["hip_err_deg"],
        "out_cur_a": o["hip"]["cur_a"], "in_cur_a": n["hip"]["cur_a"],
        "out_load_pct": o["hip"]["load_pct"], "in_load_pct": n["hip"]["load_pct"],
    })

loops = [p["hip_loop_deg"] for p in pairs]
res = {
    "protocol": proto["name"], "hz": hz,
    "shared_commanded_hip_deg": SHARED_CMD,
    "settle_window_s": SETTLE_S,
    "moving_leg": "L3", "hip_joint": HIP_J, "knee_joint": KNEE_J,
    "encoder_resolution_deg_per_count": 0.0879,
    "repeats": len(pairs),
    "hip_loop_deg_mean": round(statistics.fmean(loops), 4) if loops else None,
    "hip_loop_deg_sd": round(statistics.pstdev(loops), 4) if len(loops) > 1 else None,
    "hip_loop_deg_min": min(loops) if loops else None,
    "hip_loop_deg_max": max(loops) if loops else None,
    "hip_loop_counts_mean": (round(statistics.fmean(loops) / 0.0879, 2)
                             if loops else None),
    "out_err_deg_mean": (round(statistics.fmean(
        [p["out_err_deg"] for p in pairs]), 4) if pairs else None),
    "in_err_deg_mean": (round(statistics.fmean(
        [p["in_err_deg"] for p in pairs]), 4) if pairs else None),
    "block_a_mean": (round(statistics.fmean(loops[:3]), 4)
                     if len(loops) >= 3 else None),
    "block_b_mean": (round(statistics.fmean(loops[3:]), 4)
                     if len(loops) > 3 else None),
    "pairs": pairs, "dwells": cycles,
}
json.dump(res, open(OUT, "w"), indent=1)
print(json.dumps({k: v for k, v in res.items()
                  if k not in ("pairs", "dwells")}, indent=1))
print("\nper repeat:")
for p in pairs:
    print(f"  {p['repeat']}  loop {p['hip_loop_deg']:+.3f} deg  "
          f"knee {p['knee_loop_deg']:+.3f}  out_err {p['out_err_deg']:+.3f} "
          f"in_err {p['in_err_deg']:+.3f}  "
          f"cur out {p['out_cur_a']} in {p['in_cur_a']}  "
          f"load out {p['out_load_pct']} in {p['in_load_pct']}")
