"""Preregistered analysis of the action-response bank (no post-hoc knobs).

Implements exactly prereg_spec.json 'preregistered_criteria'. Usage:
  python3 analyze_bank.py bank.json ranking.json
"""
import json
import math
import sys

EFFECT_RAD = 0.005
FWD_KEEP = 0.90
SLIP_KEEP = 1.25
TILT_ALLOW = 3.0
PHASE_MATCH = 0.6


def circ(a, b):
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def main(bank_path, out_path):
    bank = json.load(open(bank_path))
    assert bank["exactness"]["all_match"], "exactness gate failed; no analysis"
    base_by = {}
    for b in bank["baselines"]:
        c = b["cell"]
        for p in (b["p1"], b["p2"]):
            base_by[(c["wz"], c["phase_offset"], p)] = {
                "m": b[f"metrics_{p}"], "phase": b[f"phase_{'p1' if p == b['p1'] else 'p2'}"]}
    rows = []
    for br in bank["branches"]:
        if br["joint"] is None:
            continue
        c = br["cell"]
        key = (c["wz"], c["phase_offset"], br["branch_tick"])
        bm = base_by[key]["m"]
        m = br["metrics"]
        sgn = 1.0 if c["wz"] > 0 else -1.0
        gain = sgn * (m["d_yaw_rad"] - bm["d_yaw_rad"])
        ret = {
            "fwd": m["fwd_disp_m"] >= FWD_KEEP * bm["fwd_disp_m"] and bm["fwd_disp_m"] > 0,
            "slip": m["loaded_slip_m"] <= SLIP_KEEP * bm["loaded_slip_m"],
            "term": not m["terminated_in_window"],
            "roll": m["max_abs_roll_deg"] <= bm["max_abs_roll_deg"] + TILT_ALLOW,
            "pitch": m["max_abs_pitch_deg"] <= bm["max_abs_pitch_deg"] + TILT_ALLOW,
            "walk": m["nonwalk_ticks"] == 0,
        }
        rows.append({
            "wz": c["wz"], "start": c["phase_offset"], "p": br["branch_tick"],
            "phase": m["phase_at_branch"], "joint": br["joint"],
            "sign": 1 if br["pulse_delta"] > 0 else -1,
            "yaw_gain_cmd_dir_rad": round(gain, 6),
            "d_yaw": round(m["d_yaw_rad"], 6),
            "base_d_yaw": round(bm["d_yaw_rad"], 6),
            "fwd_ratio": round(m["fwd_disp_m"] / bm["fwd_disp_m"], 4) if bm["fwd_disp_m"] else None,
            "slip_ratio": round(m["loaded_slip_m"] / bm["loaded_slip_m"], 4),
            "clip_hits": br["clip_hits"],
            "effect": gain >= EFFECT_RAD,
            "retention": all(ret.values()), "retention_detail": ret,
            "qualifies": gain >= EFFECT_RAD and all(ret.values()),
        })
    # matched-phase pairs across starts, per wz sign
    quals = {}
    for wz in (0.15, -0.15):
        states0 = sorted({(r["start"], r["p"], r["phase"]) for r in rows
                          if r["wz"] == wz and r["start"] == 0.0})
        statesP = sorted({(r["start"], r["p"], r["phase"]) for r in rows
                          if r["wz"] == wz and r["start"] != 0.0})
        pairs = [(a, b) for a in states0 for b in statesP
                 if circ(a[2], b[2]) < PHASE_MATCH]
        qual_js = []
        for j in range(18):
            for s in (1, -1):
                for a, b in pairs:
                    ra = next(r for r in rows if r["wz"] == wz and r["start"] == a[0]
                              and r["p"] == a[1] and r["joint"] == j and r["sign"] == s)
                    rb = next(r for r in rows if r["wz"] == wz and r["start"] == b[0]
                              and r["p"] == b[1] and r["joint"] == j and r["sign"] == s)
                    if ra["qualifies"] and rb["qualifies"]:
                        qual_js.append({"joint": j, "sign": s,
                                        "pair_phases": [a[2], b[2]],
                                        "gains": [ra["yaw_gain_cmd_dir_rad"],
                                                  rb["yaw_gain_cmd_dir_rad"]]})
        quals[str(wz)] = {"matched_pairs": [[list(a), list(b)] for a, b in pairs],
                          "qualifying": qual_js}
    both = bool(quals["0.15"]["qualifying"]) and bool(quals["-0.15"]["qualifying"])
    rows.sort(key=lambda r: -r["yaw_gain_cmd_dir_rad"])
    out = {
        "prereg_effect_rad": EFFECT_RAD,
        "n_pulse_branches": len(rows),
        "n_effect": sum(r["effect"] for r in rows),
        "n_retention": sum(r["retention"] for r in rows),
        "n_qualify": sum(r["qualifies"] for r in rows),
        "both_signs_qualification": both,
        "per_sign": quals,
        "ranking": rows,
    }
    json.dump(out, open(out_path, "w"), indent=1)
    print(f"branches={len(rows)} effect>= {EFFECT_RAD}: {out['n_effect']}  "
          f"retention: {out['n_retention']}  qualify: {out['n_qualify']}  "
          f"BOTH-SIGNS: {both}")
    for r in rows[:12]:
        print(f"  wz={r['wz']:+.2f} start={r['start']:.2f} p={r['p']} j={r['joint']:2d} "
              f"s={r['sign']:+d} gain={r['yaw_gain_cmd_dir_rad']:+.4f} "
              f"fwd={r['fwd_ratio']} slip={r['slip_ratio']} "
              f"eff={r['effect']} ret={r['retention']}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
