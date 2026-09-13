"""Table of every replay variant in /tmp/simgap/variants: gate counts, rank correlation of
hardware vs sim roll across the 25 runs, roll RMS ratio, feet in contact, per-family medians.

    uv run python -m sysid.simgap.summarize_variants [--md]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

VAR = Path("/tmp/simgap/variants")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--root", type=Path, default=VAR)
    a = ap.parse_args(argv)
    rows = []
    for rj in sorted(a.root.glob("*/result.json")):
        d = json.loads(rj.read_text())
        s = d["summary"]
        if "all" not in s:
            continue
        al, fit, ho = s["all"], s.get("fit", {}), s.get("holdout", {})
        fam = s["per_family"]
        rows.append({
            "variant": d["variant"].replace("series:sysid/simgap/variants/", "series:").replace(".json", ""),
            "n": al["n"], "gate_fit": fit.get("gate"), "gate_hold": ho.get("gate"),
            "rho_peak": al["spearman_peak"], "r_peak": al["pearson_peak"], "rho_rms": al["spearman_rms"],
            "med_sim/hw_peak": al["median_sim_over_hw_peak"], "med_sim/hw_rms": al["median_sim_over_hw_rms"],
            "med_peak_err": al["median_peak_abs_err"], "med_wave": al["median_wave_rmse"], "med_q": al["median_q_rmse"],
            "feet": al["mean_feet_in_contact"],
            "ps200_sim/hw": f"{fam['speed_ps200']['sim_peak_med']}/{fam['speed_ps200']['hw_peak_med']}" if 'speed_ps200' in fam else "",
            "walkteach_sim/hw": f"{fam['walkteach']['sim_peak_med']}/{fam['walkteach']['hw_peak_med']}" if 'walkteach' in fam else "",
            "allhead_sim/hw": f"{fam['allheading_mlp']['sim_peak_med']}/{fam['allheading_mlp']['hw_peak_med']}" if 'allheading_mlp' in fam else "",
            "stotight_sim/hw": f"{fam['stotight45_seed13']['sim_peak_med']}/{fam['stotight45_seed13']['hw_peak_med']}" if 'stotight45_seed13' in fam else "",
            "rlonly_sim/hw": f"{fam['rl_only_widen8_crutchoff_s0']['sim_peak_med']}/{fam['rl_only_widen8_crutchoff_s0']['hw_peak_med']}" if 'rl_only_widen8_crutchoff_s0' in fam else "",
        })
    if not rows:
        print("no results"); return 1
    keys = list(rows[0].keys())
    if a.md:
        print("| " + " | ".join(keys) + " |"); print("|" + "---|" * len(keys))
        for r in rows: print("| " + " | ".join(str(r[k]) for k in keys) + " |")
    else:
        w = {k: max(len(k), *(len(str(r[k])) for r in rows)) for k in keys}
        print("  ".join(k.ljust(w[k]) for k in keys))
        for r in rows: print("  ".join(str(r[k]).ljust(w[k]) for k in keys))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
