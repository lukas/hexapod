"""Hexapod 1 vs hexapod 2 on the same RL gaits, from what each lab run recorded.

hexapod 2: the 2026-09-11 grid session, one lab import per gait step
(`<stamp>_<label>.json` with speed_mm_s, heading_change_deg, seconds,
stop_reason; tilt from the rl_drive_*.csv next to it).
hexapod 1: Robot Lab v2 walk runs whose walk_summary.json carries rl_policy
(camera-measured net speed, drift, tilt, current, the runner's drive stats).

    /Users/lukas/hexapod/.venv/bin/python -m sysid.rl_gait_compare \
        --lab-dir "$HOME/Library/Application Support/Hexapod Lab/v2" --out docs/RL_GAITS_HEXAPOD1_VS_HEXAPOD2_2026-09-12.md
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path

POLICY_SHORT = {
    "walkteach_allhead_acq12m_100hz.json": "walkteach 100 Hz",
    "walk_allheading_mlp_singleframe_acq1_stdanneal.json": "allheading 100 Hz",
    "cap29_stdwalklo_hi_100hz.json": "cap29 standwalk 100 Hz",
    "walkscratch_rlonly_widen8_crutchoff_s0_warmadapt_50hz_acq1.json": "RL-only s0 50 Hz",
    "amp_phasehz11_s29_25hz.json": "AMP 25 Hz",
    "stotight45_seed13_25hz.json": "stotight45 25 Hz",
    "dep_tip1_25hz.json": "dep_tip1 25 Hz",
    "speed50hz_stride_ps200_lift14_massfix_sr105_acq10m.json": "speed ps200 50 Hz",
    "scripted gait 1": "scripted gait 1",
}


def tilt_from_csv(path: Path) -> tuple[float | None, float | None]:
    try:
        with open(path) as fh:
            rows = list(csv.DictReader(fh))
    except OSError:
        return None, None
    t = [math.hypot(float(r.get("roll_deg") or 0), float(r.get("pitch_deg") or 0)) for r in rows
         if (r.get("phase") or "walk") in ("walk", "run", "drive", "")]
    if not t:
        return None, None
    return round(max(t), 1), round(math.sqrt(sum(v * v for v in t) / len(t)), 1)


def hexapod2_rows(con) -> list[dict]:
    out = []
    for r in con.execute("SELECT id, run_dir, started_at FROM runs WHERE robot='hexapod2' AND run_dir IS NOT NULL"):
        rd = Path(r["run_dir"])
        for j in rd.glob("*.json"):
            try:
                d = json.loads(j.read_text())
            except ValueError:
                continue
            if not isinstance(d, dict) or "speed_mm_s" not in d or not d.get("policy"):
                continue
            cmd = d.get("cmd") or {}
            vx = float(cmd.get("vx") or 0)
            tilt_max, tilt_rms = None, None
            csvs = sorted(rd.glob("rl_drive_*.csv"))
            if csvs:
                tilt_max, tilt_rms = tilt_from_csv(csvs[0])
            out.append({"robot": "hexapod2", "run": r["id"], "policy": d["policy"], "label": d.get("label"),
                        "cmd_mm_s": round(vx if abs(vx) > 5 else vx * 1000, 0), "seconds": d.get("seconds"),
                        "speed_mm_s": d.get("speed_mm_s"), "heading_change_deg": d.get("heading_change_deg"),
                        "stop": d.get("stop_reason"), "tilt_max": tilt_max, "tilt_rms": tilt_rms,
                        "service_ms": ((d.get("drive") or {}).get("mean_service_ms")), "overruns": (d.get("drive") or {}).get("overruns")})
    return out


def hexapod1_rows(con) -> list[dict]:
    out = []
    for r in con.execute("SELECT id, run_dir, started_at, status FROM runs WHERE robot='hexapod1' AND run_dir IS NOT NULL AND started_at >= '2026-09-12'"):
        ws = Path(r["run_dir"]) / "walk_summary.json"
        if not ws.exists():
            continue
        s = json.loads(ws.read_text())
        policy = s.get("rl_policy") or "scripted gait 1"
        for leg in s.get("legs") or []:
            if "path_speed_mm_s" not in leg:
                # Before the 2026-09-12 metric fix the speed was the fused-marker path length
                # (camera 0's weak calibration made a 30 mm/s walk read 250 mm/s); not comparable.
                continue
            drv = leg.get("drive") or {}
            out.append({"robot": "hexapod1", "run": r["id"], "policy": policy, "label": leg["leg"],
                        "cmd_mm_s": leg.get("vx_mm_s"), "seconds": leg.get("seconds"), "speed_mm_s": leg.get("mean_speed_mm_s"),
                        "heading_change_deg": leg.get("heading_change_deg"), "drift_deg": leg.get("drift_deg"),
                        "stop": leg.get("stopped") if not leg.get("fatal") else leg.get("fatal"),
                        "tilt_max": leg.get("tilt_max_deg"), "tilt_rms": leg.get("tilt_rms_deg"),
                        "current_a": leg.get("current_total_mean_a"), "hottest_c": leg.get("hottest_c"),
                        "service_ms": drv.get("mean_service_ms"), "overruns": drv.get("overruns"),
                        "aborted": s.get("aborted"), "status": r["status"]})
    return out


def fmt(v, nd=1):
    if v is None or v == "":
        return "-"
    return f"{v:.{nd}f}" if isinstance(v, float) else str(v)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lab-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    con = sqlite3.connect(str(a.lab_dir / "lab2.sqlite3"))
    con.row_factory = sqlite3.Row
    h2, h1 = hexapod2_rows(con), hexapod1_rows(con)
    by_policy: dict[str, dict[str, list]] = defaultdict(lambda: {"hexapod1": [], "hexapod2": []})
    for row in h1 + h2:
        by_policy[row["policy"]][row["robot"]].append(row)
    lines = ["# RL gaits: hexapod 1 vs hexapod 2 (2026-09-12)", "",
             "Same policy files, same commanded speeds. hexapod 2's numbers are its 2026-09-11 tag-grid session "
             "(floor camera, 2 fps fixes, straight-line speed). hexapod 1's are Robot Lab v2 walk runs on 2026-09-12 "
             "(camera 1, net start-to-end speed over the leg, out and back). Speed is the camera's, not the command.", "",
             "| gait | robot | cmd mm/s | measured mm/s | heading change deg | tilt max / rms deg | stop | runs |", "|---|---|---:|---:|---:|---|---|---|"]
    for policy in sorted(by_policy, key=lambda p: POLICY_SHORT.get(p, p)):
        for robot in ("hexapod1", "hexapod2"):
            rows = by_policy[policy][robot]
            if not rows:
                lines.append(f"| {POLICY_SHORT.get(policy, policy)} | {robot} | - | not run | - | - | - | 0 |")
                continue
            speeds = [r["speed_mm_s"] for r in rows if isinstance(r["speed_mm_s"], (int, float))]
            heads = [r["heading_change_deg"] for r in rows if isinstance(r["heading_change_deg"], (int, float))]
            tmax = [r["tilt_max"] for r in rows if isinstance(r["tilt_max"], (int, float))]
            trms = [r["tilt_rms"] for r in rows if isinstance(r["tilt_rms"], (int, float))]
            cmds = sorted({abs(r["cmd_mm_s"]) for r in rows if isinstance(r["cmd_mm_s"], (int, float))})
            stops = sorted({str(r["stop"])[:30] for r in rows})
            sp = f"{min(speeds):.1f}-{max(speeds):.1f}" if len(speeds) > 1 else (fmt(speeds[0]) if speeds else "-")
            hd = f"{min(heads):+.0f}..{max(heads):+.0f}" if len(heads) > 1 else (fmt(heads[0]) if heads else "-")
            tl = (f"{max(tmax):.1f}" if tmax else "-") + " / " + (f"{max(trms):.1f}" if trms else "-")
            lines.append(f"| {POLICY_SHORT.get(policy, policy)} | {robot} | {', '.join(f'{c:.0f}' for c in cmds)} | {sp} | {hd} | {tl} | {'; '.join(stops)} | {len(rows)} |")
    lines += ["", "## Every leg", "", "| robot | run | gait | leg | cmd | s | mm/s | heading | drift | tilt max/rms | current A | hottest C | service ms | overruns | stop |", "|---|---|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|"]
    for row in sorted(h1 + h2, key=lambda r: (POLICY_SHORT.get(r["policy"], r["policy"]), r["robot"], str(r["label"]))):
        lines.append(f"| {row['robot']} | {row['run']} | {POLICY_SHORT.get(row['policy'], row['policy'])} | {row.get('label')} | {fmt(row.get('cmd_mm_s'), 0)} | "
                     f"{fmt(row.get('seconds'))} | {fmt(row.get('speed_mm_s'))} | {fmt(row.get('heading_change_deg'))} | {fmt(row.get('drift_deg'))} | "
                     f"{fmt(row.get('tilt_max'))}/{fmt(row.get('tilt_rms'))} | {fmt(row.get('current_a'), 2)} | {fmt(row.get('hottest_c'), 0)} | "
                     f"{fmt(row.get('service_ms'))} | {fmt(row.get('overruns'), 0)} | {str(row.get('stop'))[:40]} |")
    a.out.write_text("\n".join(lines) + "\n")
    print(f"{len(h1)} hexapod1 legs, {len(h2)} hexapod2 steps -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
