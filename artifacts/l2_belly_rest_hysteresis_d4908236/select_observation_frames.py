#!/usr/bin/env python3
"""Select the plan's stamped observation frames from the continuous record.

The saved plan asks for frames on cameras 0, 1 and 2 at `pre_run`, at EVERY
REVERSAL and at `post_run`, each carrying its ACTUAL capture time
(`frame_actual_timestamp_required: true`), plus a dedup check.

A reversal is where the hip sweep changes direction -- the dwells at the two
extremes of the protocol's own commanded hip path (outer and inner), derived
from the reviewed protocol rather than a hand-written phase map.  Target wall
times come from the `protocol_tick0` marker, and for each target the nearest
actual frame on each camera is selected from `run/frame_index.jsonl`, which
already carries every frame's own capture time and sha256.
"""
import json, shutil, os, sys

PROTO, OUT = sys.argv[1], "observation_frames"
HIP_J = 7
proto = json.load(open(PROTO))
hz = float(proto["hz"])
hip = [t[HIP_J] for t in proto["segments"][0]["q_deg"]]

# maximal runs of constant commanded hip, >= 2 s, same rule the analysis uses
runs, s = [], 0
for i in range(1, len(hip) + 1):
    if i == len(hip) or abs(hip[i] - hip[s]) > 1e-9:
        runs.append({"a": s, "b": i - 1, "n": i - s, "hip": hip[s]})
        s = i
dwells = [r for r in runs if r["n"] >= 20]

# A reversal is a dwell where the commanded hip path turns around, i.e. a
# LOCAL EXTREMUM of the dwell sequence.  Detecting it this way rather than by
# hard-coding the extreme angles is what makes it correct: the sweep has THREE
# plateau levels (outer -51.14, shared -47.13, inner -42.95) plus a full return
# to logical zero mid-run, and the shared -47.13 dwells are passed through in
# both directions, so they are measurement waypoints, NOT reversals.
TOL = 0.05

# Merge consecutive dwells that sit at the SAME commanded level first.  The
# outer turnaround is sometimes split into a short dwell plus the adjacent long
# plateau (e.g. 58.9-61.9 s at -51.1413 followed by 62.0-69.9 s at -51.1427);
# without merging, neither half is a strict local extremum and a real reversal
# is missed.
merged = []
for d in dwells:
    if merged and abs(d["hip"] - merged[-1]["hip"]) < TOL:
        merged[-1] = {"a": merged[-1]["a"], "b": d["b"],
                      "n": d["b"] - merged[-1]["a"] + 1, "hip": merged[-1]["hip"]}
    else:
        merged.append(dict(d))
dwells = merged

def _kind(i):
    h = dwells[i]["hip"]
    prev_h = dwells[i - 1]["hip"] if i > 0 else None
    next_h = dwells[i + 1]["hip"] if i + 1 < len(dwells) else None
    if prev_h is None or next_h is None:
        return "endpoint"
    if h < prev_h - TOL and h < next_h - TOL:
        return "outer"          # deepest hip angle: the outward turnaround
    if h > prev_h + TOL and h > next_h + TOL:
        return "zero_return" if abs(h) < TOL else "inner"
    return None

reversals = []
for i, d in enumerate(dwells):
    k = _kind(i)
    if k in ("outer", "inner", "zero_return"):
        reversals.append(dict(d, kind=k))

markers = {m["label"]: m["t"] for m in json.load(open("markers.json"))}
t0 = markers["protocol_tick0"]

targets = [{"label": "pre_run", "t": markers["d4908236_pre_run"]}]
for k, d in enumerate(reversals, 1):
    mid = (d["a"] + d["b"]) / 2.0 / hz
    targets.append({"label": f"reversal_{k:02d}_{d['kind']}",
                    "t": t0 + mid, "protocol_t_s": round(mid, 2),
                    "commanded_hip_deg": round(d["hip"], 3),
                    "kind": d["kind"]})
targets.append({"label": "post_run", "t": markers["d4908236_post_run"]})

frames = [json.loads(l) for l in open("run/frame_index.jsonl")]
frames = [f for f in frames if "error" not in f]
by_cam = {}
for f in frames:
    by_cam.setdefault(f["cam"], []).append(f)
for v in by_cam.values():
    v.sort(key=lambda f: f["t"])

os.makedirs(OUT, exist_ok=True)
man, offsets = [], []
for tg in targets:
    entry = {k: v for k, v in tg.items() if k != "t"}
    entry["target_utc"] = tg["t"]
    entry["cameras"] = {}
    for cam, fs in by_cam.items():
        best = min(fs, key=lambda f: abs(f["t"] - tg["t"]))
        off = round(best["t"] - tg["t"], 3)
        offsets.append(abs(off))
        name = f"{tg['label']}_{cam}.jpg"
        shutil.copy(best["path"], os.path.join(OUT, name))
        entry["cameras"][cam] = {
            "file": f"{OUT}/{name}",
            "actual_capture_utc": best["t"],
            "offset_from_target_s": off,
            "sha256": best["sha256"],
            "source_frame": best["path"]}
    man.append(entry)

shas = [c["sha256"] for e in man for c in e["cameras"].values()]
rep = {
 "requirement": ("observation_frames [pre_run, each_reversal, post_run] on "
                 "cameras 0/1/2, frame_actual_timestamp_required, "
                 "frame_dedup_check"),
 "reversal_definition": (
   "local extrema of the reviewed protocol's own commanded hip dwell sequence. "
   "The sweep has three plateau levels plus a mid-run full return to logical "
   "zero; the shared -47.13 deg waypoint is passed through in BOTH directions "
   "and is a measurement point, not a reversal, so it is excluded."),
 "reversal_kinds": {k: sum(1 for r in reversals if r["kind"] == k)
                    for k in ("outer", "inner", "zero_return")},
 "n_targets": len(targets), "n_reversals": len(reversals),
 "n_frames_selected": len(shas),
 "max_offset_from_target_s": round(max(offsets), 3),
 "median_offset_from_target_s": round(sorted(offsets)[len(offsets)//2], 3),
 "distinct_sha256": len(set(shas)),
 "all_distinct": len(set(shas)) == len(shas),
 "note": ("Selected from the continuous 252-frame-per-camera record, whose "
          "sampling period is ~0.695 s, so the offsets below are bounded by "
          "half that. Each entry carries the frame's OWN capture time, not the "
          "target time. Low exposure applies here as everywhere in this run: "
          "these frames document coverage and chassis stillness at each "
          "reversal, not obstacle discrimination."),
 "targets": man,
}
json.dump(rep, open("observation_frames.json", "w"), indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != "targets"}, indent=1))
for e in man:
    print(f"  {e['label']:<28} "
          f"offsets {[e['cameras'][c]['offset_from_target_s'] for c in sorted(e['cameras'])]}")
