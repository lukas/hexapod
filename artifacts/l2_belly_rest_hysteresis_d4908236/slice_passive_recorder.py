#!/usr/bin/env python3
"""Slice the passive 50 Hz recorder to the d4908236 motion window and
summarise what it independently establishes.

This matters for two of the saved plan's requirements that the runner's own
CSV cannot meet on its own:
  * `telemetry.record_fields` asks for load_pct and temp_c for ALL 18 joints;
    the runner CSV carries per-joint goal/present/current but only a single
    whole-robot temp_c/load_pct column.  The recorder's `feedback` records
    carry all 18 per joint, plus raw `pos_counts` in `snapshot.servo_reports`.
  * chassis tilt.  The runner deliberately does not poll /api/feedback during
    motion (a ~5 s full-bus scan starved the L5 sibling's first attempt), so
    tilt was previously reported as post-hoc only.  The recorder is PASSIVE --
    it adds no bus reads -- and its snapshots carry the IMU, so tilt can be
    checked across the whole window from a bus-free record.
"""
import json, sys

SRC, OUT_SLICE, OUT_SUM = sys.argv[1], sys.argv[2], sys.argv[3]
T0, T1 = sys.argv[4], sys.argv[5]
KEEP = {"feedback", "snapshot", "marker", "positions", "sync_write"}

n = {"feedback": 0, "snapshot": 0, "marker": 0, "positions": 0, "sync_write": 0}
load = [0.0] * 18
temp = [0] * 18
cur = [0.0] * 18
volt_min = 99.0
roll = []
pitch = []
missing = []
counts_seen = 0
none_slots = [0] * 18
first = last = None
markers = []

with open(OUT_SLICE, "w") as out:
    for line in open(SRC):
        try:
            r = json.loads(line)
        except Exception:
            continue
        ts = r.get("ts") or ""
        if not (T0 <= ts <= T1):
            continue
        rt = r.get("record_type")
        if rt not in KEEP:
            continue
        n[rt] += 1
        first = first or ts
        last = ts
        out.write(json.dumps(r) + "\n")
        if rt == "feedback":
            # A servo that did not answer this particular scan leaves None in
            # its slot; that is telemetry noise, counted below, not a value.
            for j in range(18):
                lv, tv, cv = (r["load_pct"][j], r["temperature_c"][j],
                              r["current_a"][j])
                if lv is None or tv is None or cv is None:
                    none_slots[j] += 1
                    continue
                load[j] = max(load[j], abs(float(lv)))
                temp[j] = max(temp[j], int(tv))
                cur[j] = max(cur[j], float(cv))
            vs = [float(v) for v in r["voltage_v"] if v is not None]
            if vs:
                volt_min = min(volt_min, min(vs))
        elif rt == "snapshot":
            miss = r.get("missing_servo_ids") or []
            if miss:
                missing.append({"ts": ts, "missing": miss})
            imu = r.get("imu") or {}
            if imu.get("roll_deg") is not None:
                roll.append(float(imu["roll_deg"]))
                pitch.append(float(imu["pitch_deg"]))
            if r.get("servo_reports"):
                counts_seen += 1
        elif rt == "marker":
            markers.append({"ts": ts, "label": r.get("label")})

summary = {
    "window": {"from": T0, "to": T1, "first_record": first, "last_record": last},
    "record_counts": n,
    "per_joint_max_load_pct": [round(v, 2) for v in load],
    "per_joint_max_temp_c": temp,
    "per_joint_max_current_a": [round(v, 4) for v in cur],
    "min_bus_voltage_v": round(volt_min, 2),
    "feedback_none_slots_per_joint": none_slots,
    "snapshots_with_raw_counts": counts_seen,
    "snapshots_with_missing_servos": len(missing),
    "missing_servo_events": missing[:20],
    "imu_samples": len(roll),
    "imu_roll_deg": ({"min": round(min(roll), 2), "max": round(max(roll), 2)}
                     if roll else None),
    "imu_pitch_deg": ({"min": round(min(pitch), 2), "max": round(max(pitch), 2)}
                      if pitch else None),
    "tilt_stop_deg": 10.0,
    "markers": markers,
}
json.dump(summary, open(OUT_SUM, "w"), indent=1)
print(json.dumps({k: v for k, v in summary.items()
                  if k != "missing_servo_events"}, indent=1))
