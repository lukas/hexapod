#!/usr/bin/env python3
"""Extract the plan's per-leg hip-yield timeline from the 50 Hz recorder.

The runner's own /api/feedback polls are ~5 s apart on this bus, so the
plan's t=0/1/2 s hip points and the yield's onset time come from the
robot's own recorder instead. Two record types matter:

  snapshot -- position_deg (18 joints) + IMU roll/pitch, continuous.
  feedback -- position_deg + load_pct + current_a + temperature_c,
              written whenever something does a full-feedback read
              (i.e. once per runner poll).

Reads the recorder JSONL fetched from the robot and the runner's
cycles.json, and writes hold_timeline.json:

  * per cycle, hip angle for all six legs at hold entry and at every
    plan sample point (0,1,2,5,10,15 s),
  * the yield onset time and magnitude per leg, found as the largest
    step in the first seconds of the hold,
  * every non-zero load_pct / current_a seen inside a loaded hold,
    which is the plan's discriminating measurement,
  * IMU roll/pitch range per hold.

Corrupted single samples (the 0x4000-class reads documented on this
bus) are excluded from the angle series by a physical-plausibility
filter and counted separately, never silently dropped.
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
HIP_J = {0: 1, 1: 4, 2: 7, 3: 10, 4: 13, 5: 16}
SAMPLE_POINTS = [0.0, 1.0, 2.0, 5.0, 10.0, 15.0]
# A stance hip lives near +20 deg; anything outside this is a bad read,
# not a pose. The parent run's corruption showed up as +/-180 deg.
HIP_PLAUSIBLE = (-95.0, 115.0)


def load_records(path: pathlib.Path):
    snaps, fbs = [], []
    bad = 0
    with path.open() as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                bad += 1
                continue
            rt = d.get("record_type")
            if rt == "snapshot":
                snaps.append(d)
            elif rt == "feedback":
                fbs.append(d)
    return snaps, fbs, bad


def t_of(rec) -> float | None:
    ns = rec.get("time_unix_ns")
    return None if ns is None else ns / 1e9


def hip_of(rec, leg):
    pos = rec.get("position_deg") or []
    j = HIP_J[leg]
    if j >= len(pos):
        return None
    v = pos[j]
    if v is None:
        return None
    v = float(v)
    if not (HIP_PLAUSIBLE[0] <= v <= HIP_PLAUSIBLE[1]):
        return None  # implausible read
    return v


def nearest(series, target_t, max_gap=1.0):
    """series: list of (t, value). Nearest sample within max_gap."""
    best, bestd = None, None
    for t, v in series:
        d = abs(t - target_t)
        if bestd is None or d < bestd:
            best, bestd = v, d
    if bestd is None or bestd > max_gap:
        return None, bestd
    return best, bestd


def main() -> int:
    tel = HERE / "telemetry.jsonl"
    cyc_path = HERE / "cycles.json"
    if not tel.exists() or not cyc_path.exists():
        print("missing telemetry.jsonl or cycles.json", file=sys.stderr)
        return 1
    snaps, fbs, badlines = load_records(tel)
    run = json.loads(cyc_path.read_text())
    print(f"records: {len(snaps)} snapshot, {len(fbs)} feedback, "
          f"{badlines} unparseable")

    out = {"source_recorder": str(run.get("telemetry_path")),
           "snapshot_records": len(snaps), "feedback_records": len(fbs),
           "hip_plausible_range_deg": list(HIP_PLAUSIBLE),
           "sample_points_s": SAMPLE_POINTS, "cycles": []}

    for cyc in run.get("cycles", []):
        ci = cyc.get("cycle")
        t0 = cyc.get("hold_t0")
        if t0 is None:
            continue
        t_end = t0 + float(run.get("stand_hold_s") or 15)
        entry = {"cycle": ci, "hold_t0_unix": t0}

        # --- dense hip series from snapshots inside the hold ---
        window = [(t_of(s), s) for s in snaps
                  if t_of(s) is not None and t0 - 2.0 <= t_of(s) <= t_end + 2.0]
        window.sort(key=lambda r: r[0])
        entry["snapshots_in_hold"] = len(window)

        per_leg = {}
        implausible = {}
        for leg in range(6):
            ser = []
            nbad = 0
            for t, s in window:
                v = hip_of(s, leg)
                if v is None:
                    nbad += 1
                else:
                    ser.append((t, v))
            implausible[f"L{leg}"] = nbad
            pts = {}
            for sp in SAMPLE_POINTS:
                v, gap = nearest(ser, t0 + sp, max_gap=1.5)
                pts[f"t{sp:g}s"] = (None if v is None
                                    else {"hip_deg": round(v, 2),
                                          "gap_s": round(gap, 3)})
            # yield onset: biggest downward step between consecutive
            # plausible samples in the first 6 s of the hold.
            onset = None
            early = [(t, v) for t, v in ser if t <= t0 + 6.0]
            worst = 0.0
            for (ta, va), (tb, vb) in zip(early, early[1:]):
                drop = va - vb
                if drop > worst:
                    worst, onset = drop, {
                        "t_rel_s": round(tb - t0, 3),
                        "from_deg": round(va, 2), "to_deg": round(vb, 2),
                        "step_deg": round(drop, 2)}
            first = ser[0][1] if ser else None
            last = ser[-1][1] if ser else None
            per_leg[f"L{leg}"] = {
                "samples": len(ser), "implausible_dropped": nbad,
                "hip_at_hold_entry_deg": (None if first is None
                                          else round(first, 2)),
                "hip_at_hold_exit_deg": (None if last is None
                                         else round(last, 2)),
                "total_change_deg": (None if first is None or last is None
                                     else round(last - first, 2)),
                "largest_early_step": onset,
                "sample_points": pts,
            }
        entry["per_leg"] = per_leg
        entry["implausible_hip_reads"] = implausible

        # --- load / current inside the loaded hold (the discriminator) ---
        nonzero_load, nonzero_cur = [], []
        n_fb = 0
        for f in fbs:
            t = t_of(f)
            if t is None or not (t0 <= t <= t_end):
                continue
            n_fb += 1
            for j, v in enumerate(f.get("load_pct") or []):
                if v not in (None, 0, 0.0):
                    nonzero_load.append({"t_rel_s": round(t - t0, 2),
                                         "joint": j, "load_pct": v})
            for j, v in enumerate(f.get("current_a") or []):
                if v not in (None, 0, 0.0):
                    nonzero_cur.append({"t_rel_s": round(t - t0, 2),
                                        "joint": j, "current_a": v})
        entry["feedback_records_in_hold"] = n_fb
        entry["nonzero_load_samples"] = nonzero_load[:200]
        entry["nonzero_current_samples"] = nonzero_cur[:200]
        entry["nonzero_load_count"] = len(nonzero_load)
        entry["nonzero_current_count"] = len(nonzero_cur)

        # --- IMU range across the hold ---
        rolls, pitches = [], []
        for t, s in window:
            imu = s.get("imu") or {}
            r, p = imu.get("roll_deg"), imu.get("pitch_deg")
            # the parent run found interleaved exact-zero IMU dropouts;
            # exclude the exact 0/0 pair rather than average it in.
            if r == 0 and p == 0:
                continue
            if isinstance(r, (int, float)):
                rolls.append(float(r))
            if isinstance(p, (int, float)):
                pitches.append(float(p))
        entry["imu"] = {
            "roll_min_deg": round(min(rolls), 2) if rolls else None,
            "roll_max_deg": round(max(rolls), 2) if rolls else None,
            "pitch_min_deg": round(min(pitches), 2) if pitches else None,
            "pitch_max_deg": round(max(pitches), 2) if pitches else None,
            "samples": len(rolls),
        }
        out["cycles"].append(entry)

        print(f"\n--- cycle {ci}: {len(window)} snapshots in hold, "
              f"{n_fb} feedback records ---")
        for leg in range(6):
            d = per_leg[f"L{leg}"]
            print(f"  L{leg} hip entry={d['hip_at_hold_entry_deg']} "
                  f"exit={d['hip_at_hold_exit_deg']} "
                  f"change={d['total_change_deg']} "
                  f"onset={d['largest_early_step']}")
        print(f"  nonzero load {len(nonzero_load)}, "
              f"nonzero current {len(nonzero_cur)}")
        print(f"  imu {entry['imu']}")

    (HERE / "hold_timeline.json").write_text(json.dumps(out, indent=1))
    print("\nWROTE hold_timeline.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
