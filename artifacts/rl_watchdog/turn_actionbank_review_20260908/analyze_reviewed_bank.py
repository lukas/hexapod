"""Summarize unchanged primary and explicitly post-review retention screens."""
import json, math
from pathlib import Path
D=Path(__file__).resolve().parent
bank=json.loads((D/"full/bank.json").read_text())
owner=json.loads((D/"owner_bank.json").read_text())
assert bank["exactness"]["all_match"] and bank["exactness"]["all_pulse_prefixes_match"]
assert bank["original_comparison"]["all_match"]
assert len(bank["branches"])==296
pulses=[r for r in bank["branches"] if r["joint"] is not None]
assert len(pulses)==288

def find_base(bases, cell, p):
    return next(b[f"metrics_{p}"] for b in bases if b["cell"]==cell)

def screen(r,b):
    vals=[r[k] for k in ("fwd_disp_m","loaded_slip_m","max_abs_roll_deg","max_abs_pitch_deg")]
    assert all(math.isfinite(v) for v in vals)
    checks={"valid":r.get("valid",True), "forward": b["fwd_disp_m"]>0 and r["fwd_disp_m"]>=.9*b["fwd_disp_m"],
            "slip":r["loaded_slip_m"]<=1.25*b["loaded_slip_m"],
            "roll":r["max_abs_roll_deg"]<=b["max_abs_roll_deg"]+3,
            "pitch":r["max_abs_pitch_deg"]<=b["max_abs_pitch_deg"]+3,
            "no_termination":not r["terminated_in_window"],"walk_only":r["nonwalk_ticks"]==0}
    return checks, all(checks.values())

corrected_pass=owner_pass=0
rows=[]
for r in pulses:
    p=r["branch_tick"]; b=find_base(bank["baselines"],r["cell"],p)
    old_b=find_base(owner["baselines"],r["cell"],p)
    checks,passed=screen(r["metrics"],b)
    old_checks,old_pass=screen(r["owner_original_metrics"],old_b)
    corrected_pass+=passed; owner_pass+=old_pass
    rows.append({"cell":r["cell"],"branch_tick":p,"joint":r["joint"],"pulse_delta":r["pulse_delta"],
                 "original_primary_signed_yaw_gain_rad":r["original_primary_signed_yaw_gain_rad"],
                 "endpoint_signed_yaw_gain_rad":math.copysign(1,r["cell"]["wz"])*(r["metrics"]["endpoint_d_yaw_rad"]-b["endpoint_d_yaw_rad"]),
                 "corrected_retention":checks,"corrected_retention_pass":passed,"owner_original_retention_pass":old_pass,
                 "forward_ratio":r["metrics"]["fwd_disp_m"]/b["fwd_disp_m"],
                 "material_slip_distance_ratio":r["metrics"]["loaded_slip_m"]/b["loaded_slip_m"],
                 "loaded_foot_seconds":r["metrics"]["loaded_foot_seconds"],
                 "loaded_foot_seconds_ratio":r["metrics"]["loaded_foot_seconds"]/b["loaded_foot_seconds"],
                 "material_slip_speed_ratio":r["metrics"]["loaded_material_mean_speed_m_s"]/b["loaded_material_mean_speed_m_s"]})
base_rows=[]
for b in bank["baselines"]:
    for p in (b["p1"],b["p2"]):
        m=b[f"metrics_{p}"]
        base_rows.append({"cell":b["cell"],"branch_tick":p,"phase_rad":m["phase_at_branch"],
                         **{k:m[k] for k in ("d_yaw_rad","endpoint_d_yaw_rad","fwd_disp_m","legacy_initial_heading_fwd_disp_m","loaded_slip_m","legacy_pad_center_touch_slip_m","loaded_material_mean_speed_m_s","loaded_foot_seconds","max_abs_roll_deg","max_abs_pitch_deg","nonwalk_ticks","terminated_in_window")}})
summary={"review_bank_sha256":__import__("hashlib").sha256((D/"full/bank.json").read_bytes()).hexdigest(),
         "branches":296,"pulse_branches":288,"zero_parity":bank["exactness"],
         "original_trajectory_comparison_all_match":bank["original_comparison"]["all_match"],
         "primary_5mrad_passes":sum(r["original_primary_effect_pass"] for r in pulses),
         "primary_gain_range_rad":[min(r["original_primary_signed_yaw_gain_rad"] for r in rows),max(r["original_primary_signed_yaw_gain_rad"] for r in rows)],
         "endpoint_gain_range_rad":[min(r["endpoint_signed_yaw_gain_rad"] for r in rows),max(r["endpoint_signed_yaw_gain_rad"] for r in rows)],
         "owner_original_proxy_retention_passes":owner_pass,"postreview_corrected_retention_passes":corrected_pass,
         "postreview_failed_branches":[r for r in rows if not r["corrected_retention_pass"]],
         "forward_ratio_range":[min(r["forward_ratio"] for r in rows),max(r["forward_ratio"] for r in rows)],
         "material_slip_distance_ratio_range":[min(r["material_slip_distance_ratio"] for r in rows),max(r["material_slip_distance_ratio"] for r in rows)],
         "material_slip_speed_ratio_range":[min(r["material_slip_speed_ratio"] for r in rows),max(r["material_slip_speed_ratio"] for r in rows)],
         "loaded_foot_seconds_range":[min(r["loaded_foot_seconds"] for r in rows),max(r["loaded_foot_seconds"] for r in rows)],
         "loaded_foot_seconds_ratio_range":[min(r["loaded_foot_seconds_ratio"] for r in rows),max(r["loaded_foot_seconds_ratio"] for r in rows)],
         "clip_hits":sum(r["clip_hits"] for r in pulses),"wall_s":bank["wall_s"],"baseline_rows":base_rows,
         "scope":"Original 5 mrad primary unchanged. Corrected retention is explicitly post-review; no threshold change, no PPO justification, finite pulse class only."}
(D/"review_summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
(D/"branch_retention_comparison.json").write_text(json.dumps(rows,indent=1,allow_nan=False)+"\n")
print(json.dumps({k:v for k,v in summary.items() if k not in ("zero_parity","baseline_rows","postreview_failed_branches")},indent=2))
