"""Post-execution read-only audit of the frozen finite assay; no rollout or fitting."""
from pathlib import Path
import hashlib, json, math
import numpy as np

HERE=Path(__file__).resolve().parent
OUT=HERE/"full_recovered"
read=lambda f:json.loads((OUT/f).read_text())
rows=read("state_results.json")
zeros=read("zero_controls_frozen.json")
pulses=read("pulse_branches.json")
baselines=read("baselines_frozen.json")
straight=read("straight_zero_off.json")
summary=read("summary.json")
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
reg=json.loads((HERE/"PREREGISTRATION.json").read_text())
recovery=json.loads((HERE/"recovery_pins.json").read_text())
assert sha(HERE/"PROPOSAL_SOURCE.md")==reg["protocol_sha256"]
assert sha(HERE/"probe_support_yaw.py")==read("execution_manifest.json")["script_sha256"]
for f,h in recovery["initial_attempt_sha256"].items():
    assert sha(HERE/"initial_attempt"/f)==h
for f in ["baselines_frozen.json","selected_states_frozen.json"]:
    assert (OUT/f).read_bytes()==(HERE/"initial_attempt"/f).read_bytes()
for b in baselines:
    f="traces/"+b["trace_file"]
    assert (OUT/f).read_bytes()==(HERE/"initial_attempt"/f).read_bytes()
expected={(r,ph,w,t) for r in (1,2) for ph in (0,1) for w in (.15,-.15) for t in (0,1)}
assert {(r["cell"]["reset_seed"],r["cell"]["phase_index"],r["cell"]["wz"],r["target_index"]) for r in rows}==expected
assert len(rows)==16 and len(zeros)==16 and len(pulses)==32 and len(straight["rollouts"])==8
assert all(r["zero_parity"] for r in zeros)
assert all(r["prefix_parity"] and r["vector_parity"] for r in pulses)
assert all(r["parity"] for r in straight["pairs"])
zmap={(r["cell"]["reset_seed"],r["cell"]["phase_index"],r["cell"]["wz"],r["p"]):r for r in zeros}
def key(r):return (r["cell"]["reset_seed"],r["cell"]["phase_index"],r["cell"]["wz"],r["p"])
records=[]
for p in pulses:
    z=zmap[key(p)]
    m,b=p["metrics"],z["metrics"]
    checks=dict(full_window=m["valid"] and b["valid"] and m["window_ticks"]==80,
      positive_baseline_forward=b["fwd_disp_m"]>0,
      forward=m["fwd_disp_m"]>=.9*b["fwd_disp_m"],
      slip=m["loaded_slip_m"]<=1.25*b["loaded_slip_m"],
      roll=m["max_abs_roll_deg"]<=b["max_abs_roll_deg"]+3,
      pitch=m["max_abs_pitch_deg"]<=b["max_abs_pitch_deg"]+3,
      all_walking=m["nonwalk_ticks"]==0,
      no_termination=not m["terminated_in_window"] and not p["fell"] and not p["term_reason"])
    c=p["controller_state"]["controller"]
    assert c["private_observation_live_parity"]
    assert len(c["support"])==3 and c["support_rank"]==2
    assert all(c["leg_ranks"][str(i)]==3 for i in c["support"])
    records.append(dict(id=p["id"],checks=checks,retention=all(checks.values()),
      forward_ratio=m["fwd_disp_m"]/b["fwd_disp_m"],
      loaded_slip_ratio=m["loaded_slip_m"]/b["loaded_slip_m"],
      roll_increase_deg=m["max_abs_roll_deg"]-b["max_abs_roll_deg"],
      pitch_increase_deg=m["max_abs_pitch_deg"]-b["max_abs_pitch_deg"],
      loaded_per_foot_seconds=m["loaded_per_foot_seconds"],
      loaded_material_per_foot_m=m["loaded_material_per_foot_m"]))
assert all(r["retention"] for r in records)
requested=[abs(v) for p in pulses for d in p["controller_state"]["doses"] for v in d["requested"]]
applied=[abs(v) for p in pulses for d in p["controller_state"]["doses"] for v in d["applied"]]
assert len(pulses)*5==sum(len(p["controller_state"]["doses"]) for p in pulses)
assert max(requested)<=.05+1e-15
gp=np.array([r["Gplus_rad"] for r in rows])*1000
gm=np.array([r["Gminus_rad"] for r in rows])*1000
odd=np.array([r["odd_rad"] for r in rows])*1000
even=np.array([r["even_rad"] for r in rows])*1000
stats=lambda a:dict(min=float(min(a)),max=float(max(a)),mean=float(np.mean(a)),median=float(np.median(a)))
audit=dict(status="COMPLETE",decision="STOP",protocol_sha256=reg["protocol_sha256"],
  fixed_state_matrix_verified=True,immutable_baselines_and_selections_verified=True,
  runner_hash_matches_execution=True,baseline_count=8,branch_slots=48,branch_count=48,
  straight_rollouts=8,available_states=16,unavailable_states=0,qualifying_states=0,
  positive_gain_mrad=stats(gp),negative_gain_mrad=stats(gm),odd_mrad=stats(odd),even_mrad=stats(even),
  positive_odd_count=int(sum(odd>0)),corrected_retention_count=sum(r["retention"] for r in records),
  clipping_count=sum(d["clip_hits"] for p in pulses for d in p["controller_state"]["doses"]),
  maximum_requested_coordinate_dose=max(requested),maximum_float32_applied_coordinate_dose=max(applied),
  per_state_l1=stats([r["controller"]["l1"] for r in rows]),
  per_state_l2=stats([r["controller"]["l2"] for r in rows]),
  forward_ratio=stats([r["forward_ratio"] for r in records]),
  loaded_slip_ratio=stats([r["loaded_slip_ratio"] for r in records]),
  roll_increase_deg=stats([r["roll_increase_deg"] for r in records]),
  pitch_increase_deg=stats([r["pitch_increase_deg"] for r in records]),
  loaded_per_foot_seconds_min_by_leg=np.min([r["loaded_per_foot_seconds"] for r in records],axis=0).tolist(),
  loaded_per_foot_seconds_max_by_leg=np.max([r["loaded_per_foot_seconds"] for r in records],axis=0).tolist(),
  support_mask_counts={str(mask):sum(r["controller"]["support"]==list(mask) for r in rows) for mask in [(0,2,4),(1,3,5)]},
  private_observation_live_parity_count=sum(r["controller_state"]["controller"]["private_observation_live_parity"] for r in zeros+pulses),
  zero_parity_count=16,pulse_prefix_vector_parity_count=32,straight_fulltrace_endpoint_parity_count=4,
  pulse_termination_count=sum(p["fell"] or bool(p["term_reason"]) for p in pulses),
  all_rollout_termination_count=sum(p["fell"] or bool(p["term_reason"]) for p in baselines+zeros+pulses+straight["rollouts"]),
  baseline_trace_files=8,total_trace_files=len(list((OUT/"traces").glob("*.npz"))),
  motor_current_trace_status="UNAVAILABLE: frozen helper did not export current time series; no current-health inference or response rerun.",
  branch_retention=records,no_response_fit=True,no_PPO=True)
(OUT/"post_execution_audit.json").write_text(json.dumps(audit,indent=2,allow_nan=False)+"\n")
print(json.dumps({k:v for k,v in audit.items() if k!="branch_retention"},indent=2))
