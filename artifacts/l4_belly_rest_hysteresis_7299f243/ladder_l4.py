#!/usr/bin/env python3
"""Place L4 on the ladder and apply the SAME adjacent-spacing test L3 used.

Usage: ladder_l4.py <l4_loop_metrics.json> <l4_posthoc.json> <out.json>

The five prior legs' values are the plan's own reporting.compare_against list.
L4's number comes from this run's measured metrics, never from a constant.
"""
import json, statistics, sys, datetime

MET, POST, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
CD = 0.0879                      # deg per encoder count

met = json.load(open(MET))
post = json.load(open(POST))

# --- L4 from this run
loops = [p["hip_loop_deg"] for p in met["pairs"]]
l4_mean = statistics.fmean(loops)
l4_sd = statistics.pstdev(loops) if len(loops) > 1 else 0.0
# settled value = the modal/repeated per-cycle value when the windows are
# single-valued and on-grid; otherwise fall back to the mean.
uniq = sorted(set(round(v, 4) for v in loops))
mode_val = max(uniq, key=lambda v: sum(1 for x in loops if round(x, 4) == v))
mode_n = sum(1 for x in loops if round(x, 4) == mode_val)
grid = post["settled_window_investigation"]["settled_values_in_counts"]
single_valued = all(len(w["unique_values"]) == 1
                    for w in post["settled_window_investigation"]["settled_windows"])
on_grid = all(abs(w["residual_counts"]) <= 0.05 for w in grid["windows"])
settled = mode_val if (single_valued and mode_n >= 4) else round(l4_mean, 4)

PRIOR = [("L1", -0.330), ("L2", -0.4357), ("L3", -0.703),
         ("L5", -0.832), ("L0", -0.967)]
rows = PRIOR + [("L4", settled)]
rows.sort(key=lambda r: -r[1])            # least negative first
ladder = [{"leg": n, "deg": round(v, 4), "counts": round(v / CD, 3)}
          for n, v in rows]
gaps = [{"pair": f"{ladder[i]['leg']}->{ladder[i+1]['leg']}",
         "deg": round(abs(ladder[i+1]['deg'] - ladder[i]['deg']), 4),
         "counts": round(abs(ladder[i+1]['counts'] - ladder[i]['counts']), 3)}
        for i in range(len(ladder) - 1)]

# --- the adjacent-spacing test, exactly as L3 applied it
idx = next(i for i, r in enumerate(ladder) if r["leg"] == "L4")
neigh = []
if idx > 0:
    neigh.append((ladder[idx-1]["leg"],
                  abs(ladder[idx]["counts"] - ladder[idx-1]["counts"])))
if idx < len(ladder) - 1:
    neigh.append((ladder[idx+1]["leg"],
                  abs(ladder[idx+1]["counts"] - ladder[idx]["counts"])))
nearest, nearest_d = min(neigh, key=lambda t: t[1])
# reference spacings: the accepted-as-one-bracket internal spacings
ref = {g["pair"]: g["counts"] for g in gaps}
biggest = max(gaps, key=lambda g: g["counts"])

out = {
 "experiment_id": "7299f24343654f9893274d4328b277ad",
 "generated_utc": datetime.datetime.now(datetime.timezone.utc)
                  .isoformat().replace("+00:00", "Z"),
 "encoder_resolution_deg_per_count": CD,
 "loop_definition": met.get("shared_commanded_hip_deg"),
 "L4_this_run": {
   "n_cycles": len(loops), "per_cycle_loop_deg": loops,
   "per_cycle_loop_counts": [round(v / CD, 2) for v in loops],
   "mean": round(l4_mean, 4), "sd": round(l4_sd, 4),
   "mean_counts": round(l4_mean / CD, 3),
   "settled_value_deg": settled, "settled_counts": round(settled / CD, 3),
   "settled_is_exact_count": round(settled / CD, 2),
   "all_settled_windows_single_valued": single_valued,
   "all_settled_windows_on_count_grid": on_grid,
   "modal_cycle_value_deg": mode_val, "modal_cycle_count": mode_n},
 "ladder_all_six_legs": ladder,
 "adjacent_gaps": gaps,
 "adjacent_spacing_test": {
   "method": ("the identical test L3 used: compare L4's distance to its nearest "
              "neighbour against that neighbour's own bracket-internal spacing. "
              "If L4 sits closer to a bracket than the bracket's members sit to "
              "each other, the same standard that groups them groups L4 too."),
   "L4_nearest_neighbour": nearest,
   "L4_distance_to_nearest_counts": round(nearest_d, 3),
   "reference_internal_spacings_counts": ref,
   "largest_discontinuity": biggest},
 "notes": []}
json.dump(out, open(OUT, "w"), indent=1)
print(json.dumps({k: out[k] for k in
                  ("L4_this_run", "ladder_all_six_legs", "adjacent_gaps",
                   "adjacent_spacing_test")}, indent=1))
