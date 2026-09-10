#!/usr/bin/env python3
"""Every stop condition preflight_declaration.json declared post-hoc, plus a
check on whether the zero-variance loop width is real or an artifact.

Reads only the run's own synchronized CSV, so every number here is
recomputable from the sealed evidence.
"""
import csv, json, statistics, sys

PROTO, CSVP, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
HIP_J, KNEE_J = 13, 14
SHARED = -47.133
SETTLE_S = 1.0
COUNT_DEG = 0.0879

proto = json.load(open(PROTO))
hz = float(proto["hz"])
rows = list(csv.DictReader(open(CSVP)))
n = len(rows)


def f(r, k):
    v = r.get(k)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# --- declared post-hoc: any measured non-L4 joint off logical zero > 1.0 deg
moving = {HIP_J, KNEE_J}
worst = {"joint": None, "abs_deg": 0.0, "tick": None}
per_joint_max = {}
missing_cells = 0
for i, r in enumerate(rows):
    for j in range(18):
        if j in moving:
            continue
        v = f(r, f"q{j}_deg")
        if v is None:
            missing_cells += 1
            continue
        a = abs(v)
        if a > per_joint_max.get(j, 0.0):
            per_joint_max[j] = a
        if a > worst["abs_deg"]:
            worst = {"joint": j, "abs_deg": round(a, 3), "tick": i}

# --- declared post-hoc: hysteresis growing monotonically across repeats
def settled_at(reversals):
    return reversals

hip_cmd = [row[HIP_J] for row in proto["segments"][0]["q_deg"]]
w = int(SETTLE_S * hz)
# find dwell blocks at the shared commanded waypoint
blocks, cur = [], []
for i, c in enumerate(hip_cmd):
    if abs(c - SHARED) < 1e-3:
        cur.append(i)
    elif cur:
        blocks.append(cur); cur = []
if cur:
    blocks.append(cur)

settled_vals = []
for b in blocks:
    tail = b[-w:]
    vals = [f(rows[i], f"q{HIP_J}_deg") for i in tail if i < n]
    vals = [v for v in vals if v is not None]
    if vals:
        settled_vals.append({"ticks": [tail[0], tail[-1]],
                             "n": len(vals),
                             "unique_values": sorted(set(vals)),
                             "mean": round(statistics.fmean(vals), 4),
                             "sd": round(statistics.pstdev(vals), 4)})

loops = []
for k in range(0, len(settled_vals) - 1, 2):
    loops.append(round(settled_vals[k + 1]["mean"] - settled_vals[k]["mean"], 4))
strictly_monotonic = (len(loops) > 1 and
                      (all(loops[i] < loops[i - 1] for i in range(1, len(loops)))
                       or all(loops[i] > loops[i - 1] for i in range(1, len(loops)))))

# --- currents / load / temperature across the whole window, all 18 joints
peak_cur = {}
for r in rows:
    for j in range(18):
        v = f(r, f"cur{j}_a")
        if v is not None and abs(v) > peak_cur.get(j, 0.0):
            peak_cur[j] = abs(v)
temps = [f(r, "temp_c") for r in rows]
temps = [t for t in temps if t is not None]

def _grid_finding(windows, count_deg):
    """State what the settled windows actually show -- measured, not assumed."""
    if not windows:
        return "no settled window resolved at the shared waypoint"
    single = [w for w in windows if len(w["unique_values"]) == 1]
    resid = [abs(w["mean"] / count_deg - round(w["mean"] / count_deg))
             for w in windows]
    on_grid = [r for r in resid if r <= 0.05]
    return (
        f"{len(single)}/{len(windows)} settled windows hold ONE value across "
        f"all of their 10 Hz samples (sd 0.0); {len(on_grid)}/{len(windows)} "
        f"sit on the encoder-count grid within 0.05 count "
        f"(worst residual {max(resid):.3f} count). "
        + ("Every window is single-valued and on-grid, so the loop widths are "
           "exact count differences rather than averages of a moving joint."
           if len(single) == len(windows) and len(on_grid) == len(windows)
           else "Not every window is single-valued and on-grid, so the loop "
                "widths are NOT purely exact count differences and are "
                "reported as measured means with their own scatter.")
    )


out = {
  "csv": CSVP, "rows": n, "hz": hz,
  "declared_posthoc_checks": {
    "measured_non_L4_joint_departure_gt_1p0_deg": {
      "bound_deg": 1.0,
      "worst": worst,
      "per_joint_max_abs_deg": {str(k): round(v, 3)
                                for k, v in sorted(per_joint_max.items())},
      "missing_measured_cells": missing_cells,
      "verdict": "PASS" if worst["abs_deg"] <= 1.0 else "FAIL",
    },
    "hysteresis_growing_monotonically_across_repeats": {
      "per_cycle_loop_deg": loops,
      "strictly_monotonic": strictly_monotonic,
      "verdict": "PASS (no growth)" if not strictly_monotonic else "FAIL",
    },
  },
  "settled_window_investigation": {
    "question": ("L4 has no prior number, so this asks the question open "
                 "rather than assuming L3's shape: do the settled windows "
                 "each hold a single value on the encoder-count grid (making "
                 "each loop width an exact count difference), or do they "
                 "scatter (making it an average of a moving joint)?"),
    "settled_windows": settled_vals,
    "encoder_resolution_deg_per_count": COUNT_DEG,
    "settled_values_in_counts": {
      "note": _grid_finding(settled_vals, COUNT_DEG),
      "windows": [
        {"ticks": s["ticks"], "deg": s["mean"],
         "counts": round(s["mean"] / COUNT_DEG, 2),
         "nearest_count": round(s["mean"] / COUNT_DEG),
         "residual_counts": round(s["mean"] / COUNT_DEG
                                  - round(s["mean"] / COUNT_DEG), 3)}
        for s in settled_vals
      ],
    },
  },
  "electrical_thermal": {
    "peak_current_a_per_joint": {str(k): round(v, 4)
                                 for k, v in sorted(peak_cur.items())},
    "peak_current_a_any_joint": round(max(peak_cur.values()), 4),
    "per_servo_trip_a": 0.75, "hard_ceiling_a": 3.0,
    "logged_temp_c_max": max(temps) if temps else None,
    "temp_trip_c": 55.0,
  },
}
json.dump(out, open(OUT, "w"), indent=1)
d = out["declared_posthoc_checks"]
print("non-L4 departure :", d["measured_non_L4_joint_departure_gt_1p0_deg"]["verdict"],
      "| worst", d["measured_non_L4_joint_departure_gt_1p0_deg"]["worst"])
print("monotonic growth :", d["hysteresis_growing_monotonically_across_repeats"]["verdict"],
      "| loops", loops)
print("peak current     :", out["electrical_thermal"]["peak_current_a_any_joint"], "A (trip 0.75)")
print("max logged temp  :", out["electrical_thermal"]["logged_temp_c_max"], "C (trip 55)")
print()
print(f"settled windows at the shared waypoint (hip q{HIP_J}_deg):")
for i, s in enumerate(settled_vals):
    print(f"  {i:2d} ticks {s['ticks']} n={s['n']} unique={s['unique_values']} mean={s['mean']}")
