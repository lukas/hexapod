#!/usr/bin/env python3
"""Post-hoc verification of the d4908236 terminal run against the saved plan.

Reads the runner's own synchronized CSV and checks, per tick:
  * every non-L2 joint stayed at absolute logical zero (the plan's
    "chassis does not stand / other five legs at belly-rest zero");
  * L2 hip/knee tracking against the commanded angle (plan stop: >5 deg
    outside a commanded fast re-pose ramp);
  * per-servo current and temperature against the plan's stop bounds;
  * the commanded and measured L2 foot depth against the floor, through the
    robot's own forward kinematics, so foot clearance is stated rather than
    assumed.
"""
import csv, json, os, sys

# Use the ROBOT'S OWN forward kinematics rather than a hand-copied formula.
# A hand-copy of this got the knee convention wrong on the first pass here
# (k = hip + knee instead of k = knee), which silently turned a -15 mm
# commanded foot depth into +113 mm -- exactly the kind of quiet sign error
# that would make a clearance claim meaningless.
_PROTO_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "hexapod_walker", "prototype_sts3215")
for _sub in ("linux_control", "motor_setup"):   # geometry_plant imports feetech_bus
    sys.path.insert(0, os.path.abspath(os.path.join(_PROTO_DIR, _sub)))
from geometry_plant import (foot_z_mm, foot_r_mm,      # noqa: E402
                            COXA_MM, FEMUR_MM, TIBIA_MM)

HIP_J, KNEE_J = 7, 8
L5_CONTACT_ONSET_Z_MM = -80.95     # measured on L5 in sealed b289e536


def col(row, *names):
    for n in names:
        if n in row and row[n] not in ("", None):
            try:
                return float(row[n])
            except ValueError:
                return None
    return None


proto = json.load(open(sys.argv[1]))
rows = list(csv.DictReader(open(sys.argv[2])))
out_path = sys.argv[3]
q = proto["segments"][0]["q_deg"]

stationary, tracking = {}, {}
for j in range(18):
    cmd = [t[j] for t in q]
    meas = [col(r, f"q{j}_deg") for r in rows]
    meas = [v for v in meas if v is not None]
    if not meas:
        continue
    if j in (HIP_J, KNEE_J):
        errs = []
        for i, r in enumerate(rows):
            v = col(r, f"q{j}_deg")
            c = col(r, f"cmd{j}_deg")
            if c is None and i < len(cmd):
                c = cmd[i]
            if v is not None and c is not None:
                errs.append(abs(v - c))
        tracking[j] = {"max": round(max(errs), 3),
                       "over5deg_ticks": sum(1 for e in errs if e > 5.0),
                       "ticks": len(errs)}
    else:
        stationary[j] = {"cmd_span": round(max(cmd) - min(cmd), 4),
                         "meas_span": round(max(meas) - min(meas), 4),
                         "meas_max_abs": round(max(abs(v) for v in meas), 3)}

cur_max, temp_max = {}, {}
for j in range(18):
    cs = [col(r, f"cur{j}_a") for r in rows]
    cs = [v for v in cs if v is not None]
    ts = [col(r, f"temp{j}_c") for r in rows]
    ts = [v for v in ts if v is not None]
    if cs:
        cur_max[j] = round(max(cs), 4)
    if ts:
        temp_max[j] = max(ts)

cz = [foot_z_mm(t[HIP_J], t[KNEE_J]) for t in q]
cr = [foot_r_mm(t[HIP_J], t[KNEE_J]) for t in q]
mz, mr = [], []
for r in rows:
    h, k = col(r, f"q{HIP_J}_deg"), col(r, f"q{KNEE_J}_deg")
    if h is not None and k is not None:
        mz.append(foot_z_mm(h, k)); mr.append(foot_r_mm(h, k))

rep = {
    "kinematics_source": "linux_control/geometry_plant.py "
                          f"(coxa {COXA_MM}, femur {FEMUR_MM}, tibia {TIBIA_MM} mm)",
    "ticks_in_csv": len(rows),
    "protocol_ticks": len(q),
    "stationary_joints": stationary,
    "tracking_deg": tracking,
    "peak_current_a": max(cur_max.values()) if cur_max else None,
    "peak_current_joint": (max(cur_max, key=cur_max.get) if cur_max else None),
    "max_temp_c": max(temp_max.values()) if temp_max else None,
    "commanded_foot_z_mm": {"min": round(min(cz), 2), "max": round(max(cz), 2)},
    "commanded_foot_r_mm": {"min": round(min(cr), 2), "max": round(max(cr), 2)},
    "measured_foot_z_mm": ({"min": round(min(mz), 2), "max": round(max(mz), 2)}
                           if mz else None),
    "measured_foot_r_mm": ({"min": round(min(mr), 2), "max": round(max(mr), 2)}
                           if mr else None),
    "l5_measured_contact_onset_foot_z_mm": L5_CONTACT_ONSET_Z_MM,
    "deepest_measured_margin_mm": (round(min(mz) - L5_CONTACT_ONSET_Z_MM, 2)
                                   if mz else None),
    "floor_clearance_caveat": (
        "L2 has no ground-contact ramp of its own on this robot; the contact "
        "onset is INFERRED from L5's measured -80.95 mm by symmetry (identical "
        "link lengths, identical belly-rest chassis attitude), not measured."),
    "protocol_stop_bounds": {
        "current_stop_a": proto.get("max_current_a"),
        "current_trip_polls": proto.get("current_trip_polls"),
        "hard_current_a": proto.get("hard_current_a"),
        "soft_torque": proto.get("soft_torque"),
    },
}
json.dump(rep, open(out_path, "w"), indent=1)
print(json.dumps({k: v for k, v in rep.items()
                  if k != "stationary_joints"}, indent=1))
print("stationary max |deg| over all 16 non-L2 joints:",
      max(v["meas_max_abs"] for v in stationary.values()))
print("stationary max commanded span:",
      max(v["cmd_span"] for v in stationary.values()))
