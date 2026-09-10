"""Commanded-vs-measured hysteresis loop for the L5 hip (j16) and knee (j17).

Discriminator (from the experiment's own rationale): load-dependent position-loop
COMPLIANCE predicts the out-stroke and in-stroke overlaying at matched command;
mechanical BACKLASH/deadband predicts a systematic loop that does not close.

The sweep dwells at hip -51.143 / -47.133 / -42.955 deg. The middle waypoint is
visited on BOTH strokes each cycle, so the out-vs-in difference there measures
the loop width directly. Settled value = mean over the last 1.0 s of each dwell.
"""
import csv, json, statistics, sys

SETTLE_S = 1.0

def load(path):
    rows = []
    for r in csv.DictReader(open(path)):
        try:
            rows.append({
                "t": float(r["t_s"]),
                "c16": float(r["cmd16_deg"]), "q16": float(r["q16_deg"]),
                "c17": float(r["cmd17_deg"]), "q17": float(r["q17_deg"]),
                "cur16": float(r["cur16_a"] or 0), "cur17": float(r["cur17_a"] or 0),
                "load": float(r["load_pct"] or 0), "temp": float(r["temp_c"] or 0)})
        except (ValueError, KeyError):
            continue
    return rows

def dwells(rows, min_s=2.0):
    """Constant-command blocks lasting >= min_s."""
    out, i = [], 0
    while i < len(rows):
        j = i
        while j + 1 < len(rows) and abs(rows[j+1]["c16"] - rows[i]["c16"]) < 1e-6:
            j += 1
        if rows[j]["t"] - rows[i]["t"] >= min_s:
            blk = rows[i:j+1]
            tail = [r for r in blk if r["t"] >= rows[j]["t"] - SETTLE_S]
            out.append({
                "t0": rows[i]["t"], "t1": rows[j]["t"], "n": len(blk),
                "cmd16": rows[i]["c16"], "cmd17": rows[i]["c17"],
                "q16": statistics.fmean(r["q16"] for r in tail),
                "q17": statistics.fmean(r["q17"] for r in tail),
                "q16_sd": (statistics.pstdev([r["q16"] for r in tail])
                           if len(tail) > 1 else 0.0),
                "cur16": max(r["cur16"] for r in blk),
                "cur17": max(r["cur17"] for r in blk),
                "load": max(r["load"] for r in blk)})
        i = j + 1
    return out

def analyse(path, label):
    rows = load(path)
    ds = dwells(rows)
    # sweep dwells only: drop the zero pose and the long entry/exit settles
    sw = [d for d in ds if d["cmd16"] < -40.0 and (d["t1"] - d["t0"]) < 5.0]
    for k, d in enumerate(sw):
        prev = sw[k-1]["cmd16"] if k else None
        d["dir"] = ("out" if prev is not None and d["cmd16"] > prev
                    else "in" if prev is not None else "entry")
    mid = [d for d in sw if abs(d["cmd16"] + 47.133) < 1e-3]
    print(f"\n=== {label} ===  ({len(rows)} ticks, {len(sw)} sweep dwells)")
    print(f"{'t_s':>7} {'dir':>5} {'cmd16':>9} {'meas16':>9} {'err16':>7} "
          f"{'cmd17':>8} {'meas17':>8} {'err17':>7} {'cur16':>6} {'load%':>6}")
    for d in sw:
        print(f"{d['t0']:7.1f} {d['dir']:>5} {d['cmd16']:9.3f} {d['q16']:9.3f} "
              f"{d['q16']-d['cmd16']:7.3f} {d['cmd17']:8.3f} {d['q17']:8.3f} "
              f"{d['q17']-d['cmd17']:7.3f} {d['cur16']:6.3f} {d['load']:6.1f}")
    outs = [d for d in mid if d["dir"] == "out"]
    ins = [d for d in mid if d["dir"] == "in"]
    print(f"\n  midpoint (hip cmd -47.133) visits: {len(outs)} out, {len(ins)} in")
    widths = []
    for k in range(min(len(outs), len(ins))):
        w16 = outs[k]["q16"] - ins[k]["q16"]
        w17 = outs[k]["q17"] - ins[k]["q17"]
        widths.append((w16, w17))
        print(f"    repeat {k+1}: hip loop width {w16:+.3f} deg, "
              f"knee loop width {w17:+.3f} deg")
    if widths:
        h = [w[0] for w in widths]; n = [w[1] for w in widths]
        print(f"  HIP  loop width mean {statistics.fmean(h):+.4f} deg  "
              f"sd {statistics.pstdev(h):.4f}  range {min(h):+.3f}..{max(h):+.3f}")
        print(f"  KNEE loop width mean {statistics.fmean(n):+.4f} deg  "
              f"sd {statistics.pstdev(n):.4f}  range {min(n):+.3f}..{max(n):+.3f}")
    trk16 = max(abs(r["q16"] - r["c16"]) for r in rows)
    trk17 = max(abs(r["q17"] - r["c17"]) for r in rows)
    dwell_trk = max(max(abs(d["q16"]-d["cmd16"]), abs(d["q17"]-d["cmd17"]))
                    for d in sw) if sw else 0
    print(f"  max |cmd-meas| over ALL ticks: hip {trk16:.2f} deg, knee {trk17:.2f} deg")
    print(f"  max settled dwell tracking error: {dwell_trk:.3f} deg (plan bound 5.0)")
    print(f"  peak cur16 {max(r['cur16'] for r in rows):.3f} A, "
          f"cur17 {max(r['cur17'] for r in rows):.3f} A, "
          f"max load {max(r['load'] for r in rows):.1f} %, "
          f"max temp {max(r['temp'] for r in rows):.0f} C")
    return {"label": label, "n_ticks": len(rows), "sweep_dwells": sw,
            "loop_widths": widths,
            "hip_loop_mean": statistics.fmean([w[0] for w in widths]) if widths else None,
            "knee_loop_mean": statistics.fmean([w[1] for w in widths]) if widths else None,
            "max_track_hip": trk16, "max_track_knee": trk17,
            "max_dwell_track": dwell_trk,
            "peak_cur16": max(r["cur16"] for r in rows),
            "peak_cur17": max(r["cur17"] for r in rows),
            "max_load": max(r["load"] for r in rows),
            "max_temp": max(r["temp"] for r in rows)}

res = [analyse(p, l) for p, l in
       [("attempt2.csv", "THIS RUN 2026-09-10T02:09:36Z (hash dbc4d64c333a)"),
        ("prior_l5.csv", "prior 2026-09-06T00:54:45 (same hash)")]]
json.dump(res, open("analysis.json", "w"), indent=1, default=float)
