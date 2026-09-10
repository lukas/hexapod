#!/usr/bin/env python3
"""Pool this run's per-cycle L2 hip loop widths with every prior run of the
identical protocol hash, and re-state the L2-vs-L5 comparison.

Usage: pool_crossrun.py <out.json> <metrics.json> [<metrics.json> ...]
Each metrics file is an analyze_l2_hysteresis.py output; its run key is taken
from the filename stamp.
"""
import json, re, statistics, sys

OUT = sys.argv[1]
per_run, all_cycles = {}, []
for path in sys.argv[2:]:
    m = json.load(open(path))
    key = (re.search(r"(\d{8}_\d{6})", path) or [None, path])[1]
    widths = [p["hip_loop_deg"] for p in m["pairs"]]
    all_cycles += widths
    per_run[key] = {"n": len(widths),
                    "mean": round(m["hip_loop_deg_mean"], 4),
                    "sd": round(m["hip_loop_deg_sd"], 4),
                    "out_err": round(m["out_err_deg_mean"], 4),
                    "in_err": round(m["in_err_deg_mean"], 4),
                    "block_a": round(m["block_a_mean"], 4),
                    "block_b": round(m["block_b_mean"], 4)}

RES = 0.0879
pooled = {
    "pooled_n_cycles": len(all_cycles),
    "n_runs": len(per_run),
    "pooled_mean_deg": round(statistics.fmean(all_cycles), 4),
    "pooled_sd_deg": round(statistics.stdev(all_cycles), 4),
    "min_deg": round(min(all_cycles), 4),
    "max_deg": round(max(all_cycles), 4),
    "pooled_counts": round(statistics.fmean(all_cycles) / RES, 2),
    "per_run": per_run,
}
json.dump(pooled, open(OUT, "w"), indent=1)
print(json.dumps(pooled, indent=1))
