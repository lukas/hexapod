"""Finite preregistered capped-L2 allocation assay. Import is pure; no training."""
from __future__ import annotations
import os
for _key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS",
             "NUMEXPR_NUM_THREADS","VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_key,"1")
import argparse, hashlib, importlib.util, json, math, shutil, sys, time, traceback
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np

HERE=Path(__file__).resolve().parent
PROTO=Path(os.environ.get("HEXAPOD_PROTOTYPE_ROOT",Path.cwd())).resolve()
CAP=.05
RHO=math.sqrt(18)*.025
BASE=None
TRACE_KEYS=("yaw","xy","vx","phase","contact","pad_xy","roll","pitch",
            "endpoint_yaw","material_slip","loaded_time","body_forward")

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read(p):
    return json.loads(Path(p).read_text())

def dump(p,obj):
    Path(p).write_text(json.dumps(obj,indent=2,allow_nan=False)+"\n")

def capped_allocation(g):
    a=np.asarray(g,dtype=float)
    if a.shape!=(18,) or not np.isfinite(a).all():
        raise ValueError("expected finite 18-coordinate source secant")
    nz=[abs(float(x)) for x in a if x!=0]
    if not nz or len(nz)*CAP*CAP < RHO*RHO:
        raise ValueError("source cannot reach fixed L2 budget")
    lo,hi=0.,CAP/min(nz)
    for _ in range(100):
        mid=(lo+hi)/2
        if sum(min(CAP,mid*abs(float(x)))**2 for x in a)<RHO*RHO:
            lo=mid
        else:
            hi=mid
    lam=(lo+hi)/2
    return np.array([math.copysign(min(CAP,lam*abs(float(x))),x)
                     if x else 0. for x in a])

def choose_template(templates,wz,phase):
    if wz==0:
        return None
    if wz not in (-.15,.15) or not math.isfinite(float(phase)):
        raise ValueError("mapping outside frozen command/phase domain")
    sign=1 if wz>0 else -1
    selected=[t for t in templates if t["wz_sign"]==sign]
    if len(selected)!=2:
        raise ValueError("mapping must contain exactly two phase centers per sign")
    distance=lambda t:abs((float(phase)-t["phase_center_rad"]+math.pi)%(2*math.pi)-math.pi)
    selected.sort(key=lambda t:(distance(t),t["phase_index"]))
    if abs(distance(selected[0])-distance(selected[1]))<=1e-12:
        return min(selected,key=lambda t:t["phase_index"])
    return selected[0]

def select_tick(phase_trace,P,target):
    lo,hi=P+10,P+25
    if len(phase_trace)<hi:
        return None
    if not math.isfinite(float(target)):
        raise ValueError("nonfinite fixed phase target")
    if not all(math.isfinite(float(phase_trace[n-1])) for n in range(lo,hi+1)):
        raise ValueError("incomplete finite phase-selection window")
    return min(range(lo,hi+1),key=lambda n:(
        abs((float(phase_trace[n-1])-target+math.pi)%(2*math.pi)-math.pi),n))

def finite_metrics(m):
    keys=("d_yaw_rad","fwd_disp_m","loaded_slip_m","max_abs_roll_deg",
          "max_abs_pitch_deg","window_ticks","nonwalk_ticks")
    try:
        return bool(m is not None and all(math.isfinite(float(m[k])) for k in keys)
                    and "valid" in m and "terminated_in_window" in m)
    except (KeyError,TypeError,ValueError):
        return False

def retention(m,b,window_ticks=80):
    if not finite_metrics(m) or not finite_metrics(b):
        return False
    return bool(m["valid"] and b["valid"]
        and m["window_ticks"]==b["window_ticks"]==window_ticks
        and b["fwd_disp_m"]>0
        and m["fwd_disp_m"]>=.9*b["fwd_disp_m"]
        and m["loaded_slip_m"]<=1.25*b["loaded_slip_m"]
        and m["max_abs_roll_deg"]<=b["max_abs_roll_deg"]+3
        and m["max_abs_pitch_deg"]<=b["max_abs_pitch_deg"]+3
        and not m["terminated_in_window"] and m["nonwalk_ticks"]==0)

def allocation_state_pass(candidate_plus,candidate_minus,box_plus,baseline,wz,clip_hits=0):
    if wz not in (-.15,.15):
        raise ValueError("unknown yaw command")
    sign=math.copysign(1,wz)
    gain=lambda m:sign*(m["d_yaw_rad"]-baseline["d_yaw_rad"]) if (
        finite_metrics(m) and finite_metrics(baseline)) else None
    gp,gm,gb=map(gain,(candidate_plus,candidate_minus,box_plus))
    odd=None if gp is None or gm is None else (gp-gm)/2
    even=None if gp is None or gm is None else (gp+gm)/2
    rp=retention(candidate_plus,baseline)
    rn=retention(candidate_minus,baseline)
    complete=bool(finite_metrics(box_plus) and box_plus["valid"]
                  and box_plus["window_ticks"]==80)
    authority=bool(gp is not None and gp>=.005 and odd is not None and odd>0 and rp and rn)
    advantage=None if gp is None or gb is None or not complete else gp-gb
    return dict(Gplus_rad=gp,Gminus_rad=gm,Gbox_plus_rad=gb,
                odd_rad=odd,even_rad=even,paired_advantage_rad=advantage,
                positive_retention=rp,negative_retention=rn,
                comparator_complete=complete,authority=authority,
                allocation=bool(authority and complete and advantage>0 and clip_hits==0))

def load_base():
    global BASE
    if BASE is None:
        path=Path(os.environ["MAGNITUDE_REVIEWED_HELPER"]).resolve()
        if sha(path)!=read(HERE/"PREREGISTRATION.json")["frozen_helper_sha256"]:
            raise RuntimeError("reviewed helper hash mismatch")
        spec=importlib.util.spec_from_file_location("magnitude_frozen_helper",path)
        BASE=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=BASE
        spec.loader.exec_module(BASE)
    return BASE

def frozen_templates():
    ts=read(HERE/"frozen_vectors.json")["templates"]
    for t in ts:
        u=capped_allocation(t["mean_central_secant"])
        if not np.array_equal(u,t["candidate_vector"]):
            raise RuntimeError("derived allocation differs from frozen vector")
        b=.025*np.sign(t["mean_central_secant"])
        if not np.array_equal(b,t["comparator_vector"]):
            raise RuntimeError("sign-box comparator differs from frozen vector")
        if not math.isclose(float(np.linalg.norm(u)),RHO,rel_tol=0,abs_tol=1e-14):
            raise RuntimeError("candidate L2 mismatch")
    return ts

def trace_hash(tr):
    h=hashlib.sha256()
    for key in TRACE_KEYS:
        h.update(np.ascontiguousarray(tr[key]).tobytes())
    h.update(json.dumps(tr["modes"]).encode())
    return h.hexdigest()

class WrappedPredictor:
    def __init__(self,model,env,job,state,templates):
        self.model,self.env,self.job,self.state=model,env,job,state
        self.templates,self.index,self.vector=templates,0,np.zeros(18)
    def __getattr__(self,name):
        return getattr(self.model,name)
    def predict(self,obs,deterministic=True):
        p,mode=self.job.get("p"),self.job["mode"]
        if mode in ("straight_candidate","straight_comparator"):
            if choose_template(self.templates,0.,None) is not None:
                raise RuntimeError("zero command did not switch mapping off")
            self.state["zero_off_checked_ticks"]+=1
        if p is not None and self.index==p:
            t=choose_template(self.templates,self.job["cell"]["wz"],self.env._phase)
            self.state["mapping"]={k:t[k] for k in ("template_id","phase_index","phase_center_rad")}
            self.state["mapping"]["actual_phase_rad"]=float(self.env._phase)
            self.state["candidate_vector"]=t["candidate_vector"]
            self.state["comparator_vector"]=t["comparator_vector"]
            self.vector=np.array(t["candidate_vector"] if mode.startswith("candidate")
                                 else t["comparator_vector"])
        act,hidden=self.model.predict(obs,deterministic=deterministic)
        if p is not None and p<=self.index<p+5 and mode!="zero":
            delta=self.vector*(1 if mode.endswith("_plus") else -1)
            raw=np.asarray(act,dtype=np.float32).copy()+delta
            clipped=np.clip(raw,self.env.action_space.low,self.env.action_space.high)
            changed=clipped.astype(np.float32)
            self.state["doses"].append(dict(tick=self.index,requested=delta.tolist(),
                applied=(changed-np.asarray(act)).tolist(),
                clip_hits=int(np.count_nonzero(raw!=clipped))))
            act=changed
        self.index+=1
        return act,hidden

def current_summary(values):
    valid=[np.array(x,dtype=float) for x in values if x is not None]
    if not valid:
        return dict(status="UNAVAILABLE",samples=0)
    flat=np.abs(np.concatenate(valid))
    return dict(status="COMPLETE" if len(valid)==len(values) else "PARTIAL",
                samples=len(valid),total_ticks=len(values),mean_a=float(np.mean(flat)),
                p95_a=float(np.percentile(flat,95)),max_a=float(np.max(flat)),
                uncalibrated_simulated_estimate=True)

def run_one(job):
    base=load_base()
    templates=frozen_templates()
    state=dict(doses=[],zero_off_checked_ticks=0)
    current=[]
    original_fresh=base._fresh_env
    original_settle=base.SETTLE_TICK
    def fresh(*args,**kwargs):
        env,model,obs,onehot=original_fresh(*args,**kwargs)
        if (getattr(env,"_cart_foot_active",False)
            or getattr(env,"_joint_action_box_active",False)
            or getattr(env,"_joint_action_bias_active",False)):
            raise RuntimeError("frozen affine assisted decoder inactive")
        original_step=env.step
        def step(action):
            result=original_step(action)
            arr=getattr(env._state,"servo_current",None)
            if arr is None:
                current.append(None)
            else:
                a=np.asarray(arr,dtype=float)
                current.append(a.copy().tolist() if a.shape==(18,) and np.isfinite(a).all() else None)
            return result
        env.step=step
        return env,WrappedPredictor(model,env,job,state,templates),obs,onehot
    base._fresh_env=fresh
    mode,p,cell=job["mode"],job.get("p"),job["cell"]
    # Only recording start changes: post-ramp material observations for straight.
    # Physics, goal clock, WINDOW_TICKS and PULSE_TICKS stay frozen during rollout.
    if mode.startswith("straight_"):
        base.SETTLE_TICK=201
    captures=set(range(600,756)) if mode=="baseline" else {job["ticks"]} if p is None else {p,p+80}
    try:
        identity={}
        tr=base._rollout(job["spec"],vx=.08,wz=cell["wz"],phase_offset=cell["phase_offset"],
            n_ticks=job["ticks"],capture_ticks=captures,identity_out=identity)
    finally:
        base._fresh_env=original_fresh
        base.SETTLE_TICK=original_settle
    row=dict(id=job["id"],state_id=job.get("state_id"),cell=cell,mode=mode,p=p,
        ticks_done=tr["n_ticks_done"],fell=tr["fell"],term_reason=tr["term_reason"],
        truncated=tr["truncated"],identity=identity,controller_state=state,
        current=current_summary(current),trace_hash=trace_hash(tr))
    if mode=="baseline":
        reference=next(x for x in read(HERE/"reference_baselines.json")["baselines"] if x["cell"]==cell)
        row["source_parity"]=[]
        for tick in (600,638):
            row["source_parity"].append(dict(p=tick,
                prefix=base._state_match(tr["states"].get(tick),reference[f"prefix_{tick}"]),
                endpoint=base._state_match(tr["states"].get(tick+80),reference[f"endpoint_{tick}"]),
                window=base._window_hash(tr,tick)==reference[f"hash_{tick}"]))
        row["selections"]=[]
        for selection in job["requested_states"]:
            P,target=selection["original_tick"],selection["heldout_target_phase"]
            selected=select_tick(tr["phase"],P,target)
            item=dict(selection,p=selected)
            if selected is None or selected+80>tr["n_ticks_done"]:
                item.update(p=None,reason="complete_selected_state_or_window_unavailable")
            else:
                item.update(actual_phase=float(tr["phase"][selected-1]),
                    prefix=tr["states"][selected],endpoint=tr["states"][selected+80],
                    window_hash=base._window_hash(tr,selected),
                    metrics=base._window_metrics(tr,selected))
            row["selections"].append(item)
    elif p is not None:
        row.update(prefix=tr["states"].get(p),endpoint=tr["states"].get(p+80),
            window_hash=base._window_hash(tr,p),
            metrics=base._window_metrics(tr,p) if tr["n_ticks_done"]>=p else None)
    else:
        row["endpoint"]=tr["states"].get(tr["n_ticks_done"])
        # Parameterize the same measurement helper after physics has finished.
        old_window=base.WINDOW_TICKS
        try:
            base.WINDOW_TICKS=1300
            row["metrics"]=base._window_metrics(tr,200) if tr["n_ticks_done"]>=200 else None
        finally:
            base.WINDOW_TICKS=old_window
    trace=Path(job["out"])/"traces"/(job["id"]+".npz")
    current_array=np.array([np.full(18,np.nan) if x is None else x for x in current])
    row["current_trace_sha256"]=hashlib.sha256(np.ascontiguousarray(current_array).tobytes()).hexdigest()
    np.savez_compressed(trace,**{k:tr[k] for k in TRACE_KEYS},servo_current_a=current_array)
    row["trace_file"]=trace.name
    dump(Path(job["out"])/"rows"/(job["id"]+".json"),row)
    return row

def batch(jobs,workers,stage):
    results=[]
    if not jobs:
        return results
    with ProcessPoolExecutor(max_workers=min(workers,len(jobs))) as pool:
        futures={pool.submit(run_one,j):j for j in jobs}
        for f in as_completed(futures):
            row=f.result();results.append(row)
            print(json.dumps(dict(stage=stage,done=len(results),total=len(jobs),
                                  id=row["id"],ticks=row["ticks_done"])),flush=True)
    return sorted(results,key=lambda r:r["id"])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--checkpoint",required=True)
    ap.add_argument("--out",required=True,type=Path)
    ap.add_argument("--workers",type=int,default=8)
    args=ap.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    (out/"traces").mkdir();(out/"rows").mkdir()
    started=time.time()
    try:
        reg=read(HERE/"PREREGISTRATION.json")
        hashes={"DESIGN_SOURCE.md":"protocol_sha256","frozen_vectors.json":"frozen_vectors_sha256",
                "reference_baselines.json":"reference_baselines_sha256",
                "pins.json":"pins_sha256","cfg_set.json":"original_cfg_sha256"}
        for path,key in hashes.items():
            if sha(HERE/path)!=reg[key]:
                raise RuntimeError("preregistered file mismatch: "+path)
        pins=read(HERE/"pins.json")
        if sha(args.checkpoint)!=pins["checkpoint_sha256"]:
            raise RuntimeError("checkpoint hash mismatch")
        for path,expected in {**pins["source_hashes"],**pins["asset_hashes"]}.items():
            if sha(PROTO/path)!=expected:
                raise RuntimeError("frozen runtime source/asset mismatch: "+path)
        templates=frozen_templates()
        spec=dict(checkpoint=str(Path(args.checkpoint).resolve()),cfg_set=read(HERE/"cfg_set.json"),
            seed=0,episode_seconds=10,required_identity={k:pins["identity"][k] for k in
            ("model_variant","model_nmesh","model_ngeom","model_mass_kg")})
        dump(out/"execution_manifest.json",dict(started_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
            preregistration=reg,script_sha256=sha(__file__),
            helper_sha256=sha(os.environ["MAGNITUDE_REVIEWED_HELPER"]),
            runtime_proto=str(PROTO),spec=spec,python=sys.version,
            straight_recording_only_settle_tick=201,straight_measurement_window_ticks=1300))
        cells=[dict(vx=.08,wz=w,phase_offset=ph) for w in (.15,-.15) for ph in (0.,math.pi)]
        def job(cell,mode,p=None,selection=None):
            stem=f"w{cell['wz']:+.2f}_ph{0 if cell['phase_offset']==0 else 1}"
            state_id=selection["state_id"] if selection else None
            ident=f"{state_id}_{mode}" if state_id else f"{stem}_{mode}"
            j=dict(id=ident,state_id=state_id,cell=cell,mode=mode,p=p,
                   ticks=755 if mode=="baseline" else 1500 if mode.startswith("straight_") else p+80,
                   spec=dict(spec,episode_seconds=15 if mode.startswith("straight_") else 10),out=str(out))
            if mode=="baseline":
                selections=[]
                for t in templates:
                    if t["wz_sign"]!=(1 if cell["wz"]>0 else -1):continue
                    for m in t["source_members"]:
                        if m["start_phase"]==cell["phase_offset"]:
                            selections.append(dict(m,source_group=t["template_id"],
                                state_id=t["template_id"]+f"_start{0 if m['start_phase']==0 else 1}"))
                j["requested_states"]=selections
            return j
        baselines=batch([job(c,"baseline") for c in cells],args.workers,"baselines")
        dump(out/"baselines_frozen.json",baselines)
        if not all(all(d[k] for k in ("prefix","endpoint","window"))
                   for b in baselines for d in b["source_parity"]):
            raise RuntimeError("original source-baseline parity failure")
        selections=[dict(s,cell=b["cell"]) for b in baselines for s in b["selections"]]
        if len(selections)!=8 or len({s["state_id"] for s in selections})!=8:
            raise RuntimeError("fixed eight-state matrix mismatch")
        dump(out/"selected_states_frozen.json",selections)
        active=[s for s in selections if s["p"] is not None]
        zeros=batch([job(s["cell"],"zero",s["p"],s) for s in active],args.workers,"zeros")
        zmap={r["state_id"]:r for r in zeros}
        base=load_base()
        for s in active:
            z=zmap[s["state_id"]]
            z["zero_parity"]=bool(base._state_match(s["prefix"],z["prefix"])
                and base._state_match(s["endpoint"],z["endpoint"])
                and s["window_hash"]==z["window_hash"])
        dump(out/"zero_controls_frozen.json",zeros)
        if not all(z["zero_parity"] for z in zeros):
            raise RuntimeError("zero-control full-state/window mismatch")
        modes=("candidate_plus","candidate_minus","comparator_plus","comparator_minus")
        pulses=batch([job(s["cell"],mode,s["p"],s) for s in active for mode in modes],
                     args.workers,"signed_branches")
        pmap={(r["state_id"],r["mode"]):r for r in pulses}
        results=[]
        for s in selections:
            r=dict(state_id=s["state_id"],source_group=s["source_group"],cell=s["cell"],p=s["p"],
                   authority=False,allocation=False)
            if s["p"] is None:
                r["unavailable"]=s["reason"];results.append(r);continue
            z=zmap[s["state_id"]]
            branches=[pmap[s["state_id"],mode] for mode in modes]
            for b in branches:
                b["prefix_parity"]=base._state_match(z["prefix"],b["prefix"])
                b["mapping_vector_parity"]=all(b["controller_state"][k]==z["controller_state"][k]
                    for k in ("mapping","candidate_vector","comparator_vector"))
                if not b["prefix_parity"] or not b["mapping_vector_parity"]:
                    raise RuntimeError("pulse prefix/mapping/vector mismatch")
            cp,cn,bp,bn=branches
            clips=sum(d["clip_hits"] for b in branches for d in b["controller_state"]["doses"])
            r.update(allocation_state_pass(cp["metrics"],cn["metrics"],bp["metrics"],
                                          z["metrics"],wz=s["cell"]["wz"],clip_hits=clips))
            r.update(clip_hits=clips,mapping=z["controller_state"]["mapping"],
                     comparator_positive_retention=retention(bp["metrics"],z["metrics"]),
                     comparator_negative_retention=retention(bn["metrics"],z["metrics"]))
            box_read=allocation_state_pass(bp["metrics"],bn["metrics"],cp["metrics"],
                                           z["metrics"],wz=s["cell"]["wz"])
            r["comparator_authority"]=box_read["authority"]
            r["comparator_odd_rad"]=box_read["odd_rad"]
            r["comparator_even_rad"]=box_read["even_rad"]
            results.append(r)
        dump(out/"signed_branches.json",pulses)
        dump(out/"state_results.json",results)
        scells=[dict(vx=.08,wz=0.,phase_offset=ph) for ph in (0.,math.pi)]
        straight=batch([job(c,mode) for c in scells for mode in
                        ("straight_baseline","straight_candidate","straight_comparator")],
                       args.workers,"straight_zero_off")
        checks=[]
        for c in scells:
            bs=next(r for r in straight if r["cell"]==c and r["mode"]=="straight_baseline")
            others=[r for r in straight if r["cell"]==c and r["mode"]!="straight_baseline"]
            valid_baseline=retention(bs["metrics"],bs["metrics"],window_ticks=1300) and not bs["fell"]
            for r in others:
                checks.append(dict(cell=c,mode=r["mode"],
                    parity=bool(bs["trace_hash"]==r["trace_hash"]
                                and bs["current_trace_sha256"]==r["current_trace_sha256"]
                                and base._state_match(bs["endpoint"],r["endpoint"])
                                and bs["ticks_done"]==r["ticks_done"]==1500),
                    zero_off_checked=r["controller_state"]["zero_off_checked_ticks"]==1500,
                    retention=bool(valid_baseline and retention(r["metrics"],bs["metrics"],window_ticks=1300)
                                   and not r["fell"])))
        dump(out/"straight_zero_off.json",dict(rollouts=straight,checks=checks))
        if not all(c["parity"] and c["zero_off_checked"] for c in checks):
            raise RuntimeError("straight exactness failure")
        groups={}
        for t in templates:
            rs=[r for r in results if r["source_group"]==t["template_id"]]
            if len(rs)!=2:raise RuntimeError("fixed quarter-phase pair missing")
            groups[t["template_id"]]=dict(wz_sign=t["wz_sign"],
                authority=all(r["authority"] for r in rs),
                allocation=all(r["allocation"] for r in rs))
        both=lambda k:all(any(g[k] for g in groups.values() if g["wz_sign"]==sign) for sign in (-1,1))
        healthy=all(c["retention"] for c in checks)
        supported=both("allocation") and healthy
        summary=dict(status="COMPLETE",decision="ALLOCATION_SUPPORTED" if supported else "STOP",
            groups=groups,both_sign_authority=both("authority"),both_sign_allocation=both("allocation"),
            states=8,available_states=len(active),branch_slots=40,executed_branches=len(zeros)+len(pulses),
            continuous_baselines=len(baselines),straight_rollouts=len(straight),
            total_rollouts=len(baselines)+len(zeros)+len(pulses)+len(straight),
            zero_parity=True,pulse_prefix_vector_parity=True,straight_parity=True,
            straight_retention=healthy,wall_seconds=time.time()-started,no_PPO=True)
        dump(out/"summary.json",summary);print(json.dumps(summary),flush=True)
    except Exception:
        dump(out/"failure.json",dict(status="INFRASTRUCTURE_FAILURE",traceback=traceback.format_exc(),
                                    wall_seconds=time.time()-started))
        raise

if __name__=="__main__":
    main()
