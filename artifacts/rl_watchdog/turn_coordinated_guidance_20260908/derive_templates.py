"""Reproduce a frozen proposal from completed single-axis measurements. No simulation."""
import json,math,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent
p=D/"single_joint_inputs.json";data=json.loads(p.read_text());states=data["states"]
def cd(a,b): return abs((a-b+math.pi)%(2*math.pi)-math.pi)
def sign(x): return 1 if x>0 else -1 if x<0 else 0
for r in states:
 s=sign(r["cell"]["wz"]);plus=r["yaw_plus_rad"];minus=r["yaw_minus_rad"];base=r["baseline_yaw_rad"]
 r["central_secant"]=[s*(a-b)/.1 for a,b in zip(plus,minus)]
 r["even_axis_residue_rad"]=[s*((a+b)/2-base) for a,b in zip(plus,minus)]
 r["state_specific_linear_sum_mrad"]=50*sum(abs(x) for x in r["central_secant"])
 r["sum_abs_even_axis_residue_mrad"]=1000*sum(abs(x) for x in r["even_axis_residue_rad"])
templates=[]
for wz in [-.15,.15]:
 group=[r for r in states if r["cell"]["wz"]==wz]
 pairs=[]
 for a in [r for r in group if r["cell"]["phase_offset"]==0]:
  z=min([r for r in group if r["cell"]["phase_offset"]!=0],key=lambda r:cd(r["phase_rad"],a["phase_rad"]))
  assert cd(a["phase_rad"],z["phase_rad"])<.6
  phase=math.atan2(math.sin(a["phase_rad"])+math.sin(z["phase_rad"]),math.cos(a["phase_rad"])+math.cos(z["phase_rad"]))%(2*math.pi)
  j=[(x+y)/2 for x,y in zip(a["central_secant"],z["central_secant"])]
  v=[sign(x) for x in j]
  pairs.append({"wz_sign":sign(wz),"phase_center_rad":phase,"mean_central_secant":j,"unit_box_vector":v,"sign_agreement_of_members":sum(sign(x)==sign(y) for x,y in zip(a["central_secant"],z["central_secant"])),"members":[{"start_phase":r["cell"]["phase_offset"],"branch_tick":r["branch_tick"],"actual_phase_rad":r["phase_rad"],"linear_prediction_mrad_at_0p05":50*sum(x*y for x,y in zip(r["central_secant"],v))} for r in [a,z]],"delta_at_0p025":[.025*x for x in v],"delta_at_0p05":[.05*x for x in v],"l2_norm_0p05":.05*math.sqrt(sum(x*x for x in v)),"l1_norm_0p05":.05*sum(abs(x) for x in v)})
 for i,t in enumerate(sorted(pairs,key=lambda t:t["phase_center_rad"])):
  t["phase_index"]=i;t["template_id"]=f"wz_{'pos' if wz>0 else 'neg'}_phase{i}";templates.append(t)
out={"schema":"hexapod.coordinated_pulse_templates.proposal.v1","input_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"source_bank_sha256":data["source_bank_sha256"],"status":"FROZEN_PROPOSAL_NO_NEW_SIMULATION","frozen_assets":{k:data[k] for k in ("frozen_checkpoint_sha256","frozen_xml_sha256","cfg_json_sha256","prereg_spec_sha256")},"mapping":{"command_domain":"vx=.08, wz=+.15 or-.15 only; exact wz=0 gives all-zero vector","phase_rule":"wrap actual observed env._phase into[0,2pi); among the two centers for sign(wz), select minimum circular distance; if distances differ by<=1e-12rad, choose lower phase_index","pulse_rule":"Choose template once at burst start and hold that vector for exactly5controlticks; then75unchanged policyticks. Do not reselect inside a burst.","out_of_domain":"No assertion or deployment outside tested commands; no start-label/tick-index lookup in vector selection."},"templates":templates,"derivation":"central secant sign(wz)*(yaw(+.05)-yaw(-.05))/.1; arithmetic mean across matched phases of two starts; sign(mean) perjoint (exact zero→0)","limitations":["Finite central secant over closed-loop80tickresponse; not infinitesimalJacobian or authority bound.","18joint dose has sqrt18 timesL2norm and18times squarednorm of equal-component singleaxis pulse.","Sum absolute evenaxis residues is comparable to linear prediction; neither even nor odd responses may be superposed.","Templates use measured discovery states. Same-state results are not validation or PPOauthorization."]}
(D/"frozen_templates.json").write_text(json.dumps(out,indent=2)+"\n")
(D/"derivation_details.json").write_text(json.dumps(states,indent=2)+"\n")
print("four templates; common-vector linear predictions mrad",min(m["linear_prediction_mrad_at_0p05"] for t in templates for m in t["members"]),max(m["linear_prediction_mrad_at_0p05"] for t in templates for m in t["members"]))
