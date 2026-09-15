#!/usr/bin/env python3
"""Summarise E2 runs: per-model accuracy vs title-implied label, model agreement,
safety-event counts, latency, and side-by-side text vs the lab's incumbent
Claude 'seen' description.  Usage: python3 e2_report.py [results_dir]"""
import json, sys
from collections import Counter
from pathlib import Path

R = Path(sys.argv[1] if len(sys.argv) > 1 else "/data/results")
sys.path.insert(0, str(Path(__file__).parent))
from e2_classify import COARSE

runs = {}
for p in sorted(R.glob("e2_qwen3vl-*.jsonl")):
    if "smoke" in p.name:
        continue
    rows = [json.loads(l) for l in open(p)]
    runs[p.stem.replace("e2_", "")] = {r["clip"]: r for r in rows if r.get("verdict")}

print("model            clips  exact  coarse  events/clip  hand%  infer_s p50/p90  prompt_tok p50")
for name, d in runs.items():
    rows = list(d.values()); sc = [r for r in rows if r["expected"]]
    ex = sum(r["expected"] == r["verdict"]["primary_activity"] for r in sc)
    co = sum(COARSE[r["expected"]] == COARSE[r["verdict"]["primary_activity"]] for r in sc)
    ev = sum(len(r["verdict"]["safety_events"]) for r in rows) / max(len(rows), 1)
    hand = 100 * sum(r["verdict"]["person_or_hand_in_frame"] for r in rows) / max(len(rows), 1)
    inf = sorted(r["infer_s"] for r in rows); tok = sorted(r["usage"]["prompt_tokens"] for r in rows)
    print(f"{name:16s} {len(rows):5d}  {ex:3d}/{len(sc):<3d} {co:3d}/{len(sc):<3d}   {ev:5.2f}      {hand:4.0f}   "
          f"{inf[len(inf)//2]:5.1f}/{inf[int(len(inf)*.9)]:<5.1f}   {tok[len(tok)//2]}")

names = list(runs)
if len(names) >= 2:
    a, b = runs[names[0]], runs[names[1]]
    common = [c for c in a if c in b]
    agree = sum(a[c]["verdict"]["primary_activity"] == b[c]["verdict"]["primary_activity"] for c in common)
    cagree = sum(COARSE[a[c]["verdict"]["primary_activity"]] == COARSE[b[c]["verdict"]["primary_activity"]] for c in common)
    print(f"\n{names[0]} vs {names[1]}: exact agreement {agree}/{len(common)}, coarse {cagree}/{len(common)}")

for name, d in runs.items():
    rows = list(d.values())
    print(f"\n== {name}: predicted activity distribution")
    for k, v in Counter(r["verdict"]["primary_activity"] for r in rows).most_common():
        print(f"   {k:32s} {v}")
    print(f"== {name}: safety event types")
    for k, v in Counter(e["type"] for r in rows for e in r["verdict"]["safety_events"]).most_common():
        print(f"   {k:32s} {v}")
    print(f"== {name}: outcome")
    for k, v in Counter(r["verdict"]["outcome"] for r in rows).most_common():
        print(f"   {k:32s} {v}")

big = runs.get("qwen3vl-32b") or runs[names[0]]
print("\n== disagreements with title-implied label (32B), title | expected -> got | timeline")
for r in big.values():
    if r["expected"] and r["expected"] != r["verdict"]["primary_activity"]:
        print(f"- {r['clip']} [{r['status']}/{r['review_cls']}] {str(r['title'])[:70]}\n    {r['expected']} -> "
              f"{r['verdict']['primary_activity']} ({r['verdict']['confidence']}): {r['verdict']['timeline'][:220]}")

print("\n== clips where the model reports safety events (32B)")
for r in big.values():
    for e in r["verdict"]["safety_events"]:
        print(f"- {r['clip']} t={e['t_s']}s {e['type']} [{e['severity']}] {e['which_leg_or_side']}: {e['note'][:140]}")

print("\n== incumbent Claude 'seen' vs 32B timeline (wide.mp4 runs)")
for r in big.values():
    if r.get("seen_incumbent"):
        print(f"\n# {r['clip']} {str(r['title'])[:80]}\n  INCUMBENT: {r['seen_incumbent'][:400]}\n  QWEN32B:   {r['verdict']['timeline'][:400]}")
