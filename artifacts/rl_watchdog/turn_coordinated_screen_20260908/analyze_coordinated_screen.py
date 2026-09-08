"""Frozen-predicate analysis of the 40-branch coordinated-pulse causal screen.

Implements EXACTLY the prespecified decision rules in
turn_coordinated_guidance_20260908/screen_proposal.json: unchanged 5 mrad
actual positive-vector primary + corrected retention, odd>0 direction
support at every qualifying member, matched-phase template repeatability in
BOTH starts for EACH yaw sign, retention on opposite-vector branches, and
the 0.025-first global dose selection. Reports odd/even responses and
clipping. No threshold may be changed here; a failed screen is a STOP for
this proposal, never grounds to refit templates or invent new doses.
"""
import hashlib
import json
import math
from pathlib import Path

D = Path(__file__).resolve().parent
GUID = D.parent / "turn_coordinated_guidance_20260908"

bank = json.loads((D / "full/bank.json").read_text())
frozen = json.loads((GUID / "frozen_templates.json").read_text())
assert hashlib.sha256((GUID / "frozen_templates.json").read_bytes()).hexdigest() \
    == bank["templates_sha256"] == \
    "7014cf633de1e9d22996525ff0465a86819c5865dcb3e0e464996846d1027214"
assert not bank["smoke"]
assert bank["exactness"]["all_match"] and bank["exactness"]["all_pulse_prefixes_match"]
assert bank["baseline_identity_vs_reviewed_bank"]["all_match"]
zeros = [r for r in bank["branches"] if r["signed_amplitude"] is None]
pulses = [r for r in bank["branches"] if r["signed_amplitude"] is not None]
assert len(zeros) == 8 and len(pulses) == 32 and len(bank["baselines"]) == 4

def base_metrics(cell, p):
    return next(b[f"metrics_{p}"] for b in bank["baselines"] if b["cell"] == cell)

def retention(m, b):
    """Corrected retention screen — identical numerics to the reviewed bank."""
    for k in ("fwd_disp_m", "loaded_slip_m", "max_abs_roll_deg", "max_abs_pitch_deg"):
        assert math.isfinite(m[k])
    checks = {"valid": m["valid"], "window_complete": m["window_ticks"] == 80,
              "forward": b["fwd_disp_m"] > 0 and m["fwd_disp_m"] >= .9 * b["fwd_disp_m"],
              "slip": m["loaded_slip_m"] <= 1.25 * b["loaded_slip_m"],
              "roll": m["max_abs_roll_deg"] <= b["max_abs_roll_deg"] + 3,
              "pitch": m["max_abs_pitch_deg"] <= b["max_abs_pitch_deg"] + 3,
              "no_termination": not m["terminated_in_window"],
              "walk_only": m["nonwalk_ticks"] == 0}
    return checks, all(checks.values())

def skey(cell, p):
    return (cell["wz"], cell["phase_offset"], p)

lookup = {(skey(r["cell"], r["branch_tick"]), r["signed_amplitude"]): r for r in pulses}
assert len(lookup) == 32

states = sorted({skey(r["cell"], r["branch_tick"]) for r in pulses})
assert len(states) == 8
rows, per_amp_state = [], {}
for st in states:
    wz, start, p = st
    cell = next(r["cell"] for r in pulses if skey(r["cell"], r["branch_tick"]) == st)
    bm = base_metrics(cell, p)
    for amp in (0.025, 0.05):
        plus, minus = lookup[(st, amp)], lookup[(st, -amp)]
        # Same prefix state => same phase => same selected template.
        assert plus["pulse_selection"]["template_id"] == minus["pulse_selection"]["template_id"]
        assert plus["selected_equals_member_template"] and minus["selected_equals_member_template"]
        g_plus = plus["original_primary_signed_yaw_gain_rad"]
        g_minus = minus["original_primary_signed_yaw_gain_rad"]
        rp_checks, rp = retention(plus["metrics"], bm)
        rm_checks, rm = retention(minus["metrics"], bm)
        row = {
            "wz": wz, "start_phase": start, "branch_tick": p, "amplitude": amp,
            "template_id": plus["pulse_selection"]["template_id"],
            "selection_phase_rad": plus["pulse_selection"]["selection_phase_rad"],
            "G_plus_rad": g_plus, "G_minus_rad": g_minus,
            "odd_rad": (g_plus - g_minus) / 2, "even_rad": (g_plus + g_minus) / 2,
            "endpoint_G_plus_rad": plus["endpoint_signed_yaw_gain_rad"],
            "endpoint_G_minus_rad": minus["endpoint_signed_yaw_gain_rad"],
            "endpoint_odd_rad": (plus["endpoint_signed_yaw_gain_rad"]
                                 - minus["endpoint_signed_yaw_gain_rad"]) / 2,
            "endpoint_even_rad": (plus["endpoint_signed_yaw_gain_rad"]
                                  + minus["endpoint_signed_yaw_gain_rad"]) / 2,
            "clip_hits_plus": plus["clip_hits"], "clip_hits_minus": minus["clip_hits"],
            "retention_plus": rp, "retention_minus": rm,
            "retention_plus_checks": rp_checks, "retention_minus_checks": rm_checks,
            "forward_ratio_plus": plus["metrics"]["fwd_disp_m"] / bm["fwd_disp_m"],
            "forward_ratio_minus": minus["metrics"]["fwd_disp_m"] / bm["fwd_disp_m"],
            "slip_ratio_plus": plus["metrics"]["loaded_slip_m"] / bm["loaded_slip_m"],
            "slip_ratio_minus": minus["metrics"]["loaded_slip_m"] / bm["loaded_slip_m"],
            "loaded_foot_seconds_plus": plus["metrics"]["loaded_foot_seconds"],
            "loaded_foot_seconds_minus": minus["metrics"]["loaded_foot_seconds"],
            "slip_speed_ratio_plus": (plus["metrics"]["loaded_material_mean_speed_m_s"]
                                      / bm["loaded_material_mean_speed_m_s"]),
            "slip_speed_ratio_minus": (minus["metrics"]["loaded_material_mean_speed_m_s"]
                                       / bm["loaded_material_mean_speed_m_s"]),
            # Frozen predicates:
            "primary": bool(plus["metrics"]["valid"] and g_plus >= .005 and rp),
            "direction_support": (g_plus - g_minus) / 2 > 0,
            "stronger_reversal": bool(g_plus >= .005 and g_minus <= -.005),
        }
        rows.append(row)
        per_amp_state[(st, amp)] = row

# Repeatability: at ONE global amplitude, for EACH yaw sign, at least one
# matched-phase template must meet primary+direction in BOTH starts, and a
# qualifying template also requires retention on its opposite-vector branches.
def template_state(t, member):
    wz = 0.15 * t["wz_sign"]
    return (wz, member["start_phase"], member["branch_tick"])

qualification = {}
for amp in (0.025, 0.05):
    per_template = {}
    for t in frozen["templates"]:
        members = [per_amp_state[(template_state(t, m), amp)] for m in t["members"]]
        assert all(r["template_id"] == t["template_id"] for r in members)
        per_template[t["template_id"]] = {
            "wz_sign": t["wz_sign"],
            "members_primary": [r["primary"] for r in members],
            "members_direction": [r["direction_support"] for r in members],
            "members_opposite_retention": [r["retention_minus"] for r in members],
            "qualifies": all(r["primary"] and r["direction_support"]
                             and r["retention_minus"] for r in members),
        }
    qualification[str(amp)] = {
        "per_template": per_template,
        "wz_pos_supported": any(v["qualifies"] for v in per_template.values() if v["wz_sign"] == 1),
        "wz_neg_supported": any(v["qualifies"] for v in per_template.values() if v["wz_sign"] == -1),
    }
    qualification[str(amp)]["global_qualifies"] = (
        qualification[str(amp)]["wz_pos_supported"]
        and qualification[str(amp)]["wz_neg_supported"])

if qualification["0.025"]["global_qualifies"]:
    chosen, verdict = 0.025, "PASS"
elif qualification["0.05"]["global_qualifies"]:
    chosen, verdict = 0.05, "PASS"
else:
    chosen, verdict = None, "STOP"

mrad = lambda x: round(1000 * x, 4)
summary = {
    "screen_bank_sha256": hashlib.sha256((D / "full/bank.json").read_bytes()).hexdigest(),
    "branches": 40, "pulse_branches": 32, "zero_controls": 8,
    "zero_parity_all_match": bank["exactness"]["all_match"],
    "baseline_identity_vs_reviewed_bank": True,
    "primary_5mrad_positive_vector_passes": sum(r["primary"] for r in rows),
    "direction_support_count": sum(r["direction_support"] for r in rows),
    "stronger_reversal_count": sum(r["stronger_reversal"] for r in rows),
    "G_plus_range_mrad": [mrad(min(r["G_plus_rad"] for r in rows)),
                          mrad(max(r["G_plus_rad"] for r in rows))],
    "G_minus_range_mrad": [mrad(min(r["G_minus_rad"] for r in rows)),
                           mrad(max(r["G_minus_rad"] for r in rows))],
    "odd_range_mrad": [mrad(min(r["odd_rad"] for r in rows)),
                       mrad(max(r["odd_rad"] for r in rows))],
    "even_range_mrad": [mrad(min(r["even_rad"] for r in rows)),
                        mrad(max(r["even_rad"] for r in rows))],
    "endpoint_odd_range_mrad": [mrad(min(r["endpoint_odd_rad"] for r in rows)),
                                mrad(max(r["endpoint_odd_rad"] for r in rows))],
    "total_clip_hits": sum(r["clip_hits_plus"] + r["clip_hits_minus"] for r in rows),
    "retention_passes": sum(r["retention_plus"] + r["retention_minus"] for r in rows),
    "forward_ratio_range": [min(min(r["forward_ratio_plus"], r["forward_ratio_minus"]) for r in rows),
                            max(max(r["forward_ratio_plus"], r["forward_ratio_minus"]) for r in rows)],
    "slip_ratio_range": [min(min(r["slip_ratio_plus"], r["slip_ratio_minus"]) for r in rows),
                         max(max(r["slip_ratio_plus"], r["slip_ratio_minus"]) for r in rows)],
    "qualification": qualification,
    "chosen_global_dose": chosen, "screen_verdict": verdict,
    "linear_prediction_note": "Central-secant sums 5.247-12.427 mrad were heuristics, not authority bounds; even residues 6.23-11.66 mrad comparable by design.",
    "scope": "Frozen coordinated pulse class on eight discovery states only. PASS licenses ONLY the frozen quarter-phase/straight holdouts. STOP closes this finite proposal; it does not close longer, recurring, closed-loop or learned steering mechanisms. No PPO either way.",
    "state_rows": rows,
}
(D / "screen_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
print(json.dumps({k: v for k, v in summary.items() if k != "state_rows"}, indent=2))
