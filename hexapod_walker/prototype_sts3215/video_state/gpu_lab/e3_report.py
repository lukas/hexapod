#!/usr/bin/env python3
"""Summarise an E3 run: realtime factor, per-clip event timelines, event type counts."""
import json, sys
from collections import Counter
path = sys.argv[1] if len(sys.argv) > 1 else "/data/results/e3_qwen3vl-32b.jsonl"
rows = [json.loads(l) for l in open(path)]
tot_video = sum(r["duration_s"] for r in rows); tot_wall = sum(r["wall_s"] for r in rows)
wins = [w for r in rows for w in r["windows"] if w["verdict"]]
lat = sorted(w["infer_s"] for w in wins)
print(f"{len(rows)} clips, {tot_video/60:.1f} min of video, {len(wins)} windows, wall {tot_wall/60:.1f} min "
      f"-> {tot_wall/tot_video:.2f}x realtime sequential; per-window p50 {lat[len(lat)//2]:.1f}s p90 {lat[int(len(lat)*.9)]:.1f}s")
print("event types:", Counter(e["type"] for r in rows for e in r["events"]).most_common())
print("risk max per clip:", Counter(r["risk_max"] for r in rows))
print("end states:", Counter(s for r in rows for s in r["states"]).most_common(8))
for r in rows:
    print(f"\n# {r['clip']}  [{r['duration_s']:.0f}s, {r['n_windows']} windows, risk {r['risk_max']}]  {str(r['title'])[:80]}")
    print("  states:", " > ".join(s or "?" for s in r["states"]))
    for e in r["events"]:
        print(f"  t={e['t_s']:>6.1f} {e['type']:28s} {e['severity']:6s} {e['note'][:110]}")
