"""Preregistered finite analytic support-conditioned yaw assay. No training."""
from __future__ import annotations
import os
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_key, "1")
import argparse, hashlib, importlib.util, json, math, sys, time, traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
PROTO = Path(os.environ.get("HEXAPOD_PROTOTYPE_ROOT", Path.cwd())).resolve()
BASE = None
RCOND, ABS_CUTOFF, DOSE = 1e-6, 1e-10, .05
RESET_CFG = ["reset.start_jitter_deg=3", "reset.start_bad_prob=0.25",
             "reset.start_bad_max_joints=1", "reset.start_bad_deg_min=8",
             "reset.start_bad_deg_max=16"]
TARGETS = [5*math.pi/6, 11*math.pi/6]
PHASES = [math.pi/2, 3*math.pi/2]
TRACE_KEYS = ("yaw", "xy", "vx", "phase", "contact", "pad_xy", "roll", "pitch",
              "endpoint_yaw", "material_slip", "loaded_time", "body_forward")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dump(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")

def load_base():
    global BASE
    if BASE is None:
        path = Path(os.environ["SUPPORT_YAW_REVIEWED_HELPER"]).resolve()
        reg = json.loads((HERE/"PREREGISTRATION.json").read_text())
        if sha(path) != reg["frozen_helper_sha256"]:
            raise RuntimeError("reviewed helper hash mismatch")
        spec = importlib.util.spec_from_file_location("support_yaw_frozen_helper", path)
        BASE = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = BASE
        spec.loader.exec_module(BASE)
    return BASE

def fixed_svd(matrix):
    u, s, vh = np.linalg.svd(matrix, full_matrices=False)
    cutoff = max(ABS_CUTOFF, RCOND*float(s[0])) if len(s) else ABS_CUTOFF
    keep = s > cutoff
    return u, s, vh, keep, cutoff

def geometric_direction(points, loads, action_jacobians, origin, wz):
    """Pure geometry; no phase/response/template lookup or tuning."""
    meta = {"available": False, "reason": "", "support": [],
            "support_rank": None, "leg_ranks": {}, "leg_singular_values": {}}
    zero = np.zeros(18)
    if wz == 0:
        return zero, dict(meta, reason="zero_command")
    if (np.shape(points) != (6, 3) or np.shape(loads) != (6,)
            or np.shape(action_jacobians) != (6, 3, 3)
            or np.shape(origin) != (3,)):
        return zero, dict(meta, reason="missing_geometry")
    support = np.flatnonzero(np.asarray(loads) > .5)
    meta["support"] = support.tolist()
    if len(support) < 3:
        return zero, dict(meta, reason="fewer_than_three_support_feet")
    if not (np.isfinite(points[support]).all()
            and np.isfinite(loads).all()
            and np.isfinite(action_jacobians[support]).all()
            and np.isfinite(origin).all()):
        return zero, dict(meta, reason="nonfinite_geometry")
    xy = points[support, :2]
    _, ss, _, keep, cutoff = fixed_svd(xy - xy.mean(axis=0))
    meta.update(support_rank=int(keep.sum()),
                support_singular_values=ss.tolist(), support_cutoff=cutoff)
    if int(keep.sum()) < 2:
        return zero, dict(meta, reason="support_rank_below_two")
    solution = np.zeros(18)
    for leg in support:
        u, s, vh, keep, cutoff = fixed_svd(action_jacobians[leg])
        meta["leg_ranks"][str(leg)] = int(keep.sum())
        meta["leg_singular_values"][str(leg)] = s.tolist()
        if int(keep.sum()) < 3:
            return zero, dict(meta, reason=f"leg_{leg}_rank_below_three")
        desired = -np.cross(np.array([0., 0., 1.]), points[leg] - origin)
        solution[3*leg:3*leg+3] = vh.T @ ((u.T @ desired) / s)
    solution *= math.copysign(1., wz)
    maximum = float(np.max(np.abs(solution)))
    if not math.isfinite(maximum) or maximum == 0:
        return zero, dict(meta, reason="zero_or_nonfinite_solution")
    vector = solution * (DOSE/maximum)
    meta.update(available=True, reason="", vector=vector.tolist(),
                l1=float(np.linalg.norm(vector, 1)),
                l2=float(np.linalg.norm(vector)), linf=float(np.max(np.abs(vector))))
    return vector, meta

def live_digest(env):
    mj, m, d = env._mujoco, env.model, env.data
    mask = mj.mjtState.mjSTATE_INTEGRATION
    state = np.empty(mj.mj_stateSize(m, mask))
    mj.mj_getState(m, d, state, mask)
    h = hashlib.sha256(state.tobytes())
    for key in ("xpos", "xmat", "sensordata", "efc_force", "qacc_warmstart"):
        h.update(np.ascontiguousarray(getattr(d, key)).tobytes())
    return h.hexdigest()

def observe_vector(env, wz):
    """Read stored solved forces, endpoint kinematics on separate private copies."""
    if wz == 0:
        return np.zeros(18), {"available": False, "reason": "zero_command"}
    base = load_base()
    from rl_move.sim.servo_model import joint_qvel_addrs
    from rl_move.sim.joint_task import _HALF_RAD
    mj, m, d = env._mujoco, env.model, env.data
    if (getattr(env, "_cart_foot_active", False)
            or getattr(env, "_joint_action_box_active", False)
            or getattr(env, "_joint_action_bias_active", False)):
        raise RuntimeError("frozen affine action decoder is not active")
    before = live_digest(env)
    force_copy, endpoint = mj.MjData(m), mj.MjData(m)
    mj.mj_copyData(force_copy, m, d)
    mj.mj_copyData(endpoint, m, d)
    mj.mj_kinematics(m, endpoint)
    mj.mj_comPos(m, endpoint)
    root = int(m.body_rootid[env._chassis_bid])
    robot_geoms = set(np.flatnonzero(m.body_rootid[m.geom_bodyid] == root))
    pads = [m.body(f"L{i}_pad").id for i in range(6)]
    geom_foot = {g: i for i, pad in enumerate(pads)
                 for g in range(m.ngeom) if m.geom_bodyid[g] == pad}
    loads, weighted = np.zeros(6), np.zeros((6, 3))
    f6 = np.empty(6)
    for ci in range(force_copy.ncon):
        c = force_copy.contact[ci]
        if c.efc_address < 0:
            continue
        inside1, inside2 = c.geom1 in robot_geoms, c.geom2 in robot_geoms
        if inside1 == inside2:
            continue
        foot = geom_foot.get(c.geom1 if inside1 else c.geom2)
        if foot is None:
            continue
        mj.mj_contactForce(m, force_copy, ci, f6)
        if not np.isfinite(f6).all():
            raise RuntimeError("nonfinite stored contact wrench")
        if f6[0] > 0:
            pad = pads[foot]
            R = force_copy.xmat[pad].reshape(3, 3)
            local = R.T @ (c.pos - force_copy.xpos[pad])
            loads[foot] += float(f6[0])
            weighted[foot] += float(f6[0])*local
    points, jac = np.zeros((6, 3)), np.zeros((6, 3, 3))
    dofs = joint_qvel_addrs(m)
    logical = env._mujoco_to_logical_q(d.qpos[env._qadr])
    converted = env._logical_to_mujoco_q(logical)
    conversion = np.column_stack([
        env._logical_to_mujoco_q(logical + np.eye(18)[j])-converted
        for j in range(18)])
    if not np.allclose(conversion, np.diag(np.diag(conversion)), atol=1e-12, rtol=0):
        raise RuntimeError("unexpected coupled logical-to-MuJoCo conversion")
    for foot in range(6):
        pad = pads[foot]
        local = weighted[foot]/loads[foot] if loads[foot] > 0 else np.zeros(3)
        points[foot] = (endpoint.xpos[pad]
                       + endpoint.xmat[pad].reshape(3, 3) @ local)
        jp, jr = np.zeros((3, m.nv)), np.zeros((3, m.nv))
        mj.mj_jac(m, endpoint, jp, jr, points[foot], pad)
        sl = slice(3*foot, 3*foot+3)
        jac[foot] = jp[:, dofs[sl]] @ conversion[sl, sl] @ np.diag(_HALF_RAD[sl])
    vector, meta = geometric_direction(points, loads, jac,
                                      endpoint.xpos[env._chassis_bid], wz)
    meta.update(normal_load_n=loads.tolist(), endpoint_contact_points_world=points.tolist(),
                endpoint_chassis_world=endpoint.xpos[env._chassis_bid].tolist(),
                action_jacobians=jac.tolist(),
                endpoint_time_s=float(d.time),
                solved_force_time_s=float(d.time-m.opt.timestep),
                solved_force_age_s=float(m.opt.timestep),
                world_yaw_axis=[0., 0., 1.],
                private_observation_live_parity=(before == live_digest(env)))
    if not meta["private_observation_live_parity"]:
        raise RuntimeError("private diagnostic mutated live state")
    return vector, meta

class WrappedPredictor:
    def __init__(self, model, env, state, pulse_tick, mode, wz):
        self.model, self.env, self.state = model, env, state
        self.pulse_tick, self.mode, self.wz = pulse_tick, mode, wz
        self.index, self.vector = 0, np.zeros(18)
    def __getattr__(self, name):
        return getattr(self.model, name)
    def predict(self, obs, deterministic=True):
        if self.mode == "straight_zero_off":
            off, meta = observe_vector(self.env, 0.)
            if np.any(off):
                raise RuntimeError("zero-yaw controller produced nonzero action")
            if self.index == 0:
                self.state["controller"] = meta
        if self.index == self.pulse_tick:
            self.vector, meta = observe_vector(self.env, self.wz)
            self.state["controller"] = meta
            self.state["frozen_vector"] = self.vector.tolist()
        act, st = self.model.predict(obs, deterministic=deterministic)
        if (self.pulse_tick is not None and self.pulse_tick <= self.index < self.pulse_tick+5
                and self.mode in ("positive", "negative") and np.any(self.vector)):
            delta = self.vector * (1 if self.mode == "positive" else -1)
            raw = np.asarray(act, dtype=np.float32).copy() + delta
            changed = np.clip(raw, self.env.action_space.low,
                              self.env.action_space.high).astype(np.float32)
            self.state["doses"].append({"tick": self.index,
                "requested": delta.tolist(),
                "applied": (changed-np.asarray(act)).tolist(),
                "clip_hits": int(np.count_nonzero(raw != np.clip(raw,
                    self.env.action_space.low, self.env.action_space.high)))})
            act = changed
        self.index += 1
        return act, st

def trace_hash(tr):
    h = hashlib.sha256()
    for key in TRACE_KEYS:
        h.update(np.ascontiguousarray(tr[key]).tobytes())
    h.update(json.dumps(tr["modes"]).encode())
    return h.hexdigest()

def run_one(job):
    base = load_base()
    cell, mode, p = job["cell"], job["mode"], job.get("p")
    spec = dict(job["spec"], seed=cell["reset_seed"])
    state = {"doses": []}
    fresh = base._fresh_env
    def wrapped_fresh(*args, **kwargs):
        env, model, obs, onehot = fresh(*args, **kwargs)
        state["reset"] = {
            "offset_rad": None if env._reset_start_offset_rad is None
                          else env._reset_start_offset_rad.tolist(),
            "bad_joints": list(env._reset_start_bad_joints),
            "initial_qpos": env.data.qpos.tolist()}
        return env, WrappedPredictor(model, env, state, p, mode, cell["wz"]), obs, onehot
    base._fresh_env = wrapped_fresh
    try:
        ident = {}
        tr = base._rollout(spec, vx=.08, wz=cell["wz"],
            phase_offset=cell["phase"], n_ticks=job["ticks"],
            capture_ticks=(set(range(600, 755)) if mode == "baseline"
                           else {job["ticks"]} if p is None else {p,p+80}),
            identity_out=ident)
    finally:
        base._fresh_env = fresh
    out = {"id":job["id"],"cell":cell,"mode":mode,"p":p,
           "controller_state":state,"identity":ident,
           "ticks_done":tr["n_ticks_done"],"fell":tr["fell"],
           "term_reason":tr["term_reason"],"trace_hash":trace_hash(tr),
           "final_qpos":tr["final_qpos"].tolist()}
    if mode == "baseline":
        available_ticks = list(range(600,675)) if tr["n_ticks_done"] >= 675 else []
        out["selections"]=[]
        for target_index, target in enumerate(TARGETS):
            if not available_ticks:
                out["selections"].append({"target_index":target_index,"p":None,
                                         "unavailable":"baseline_ended_before_window"})
                continue
            pp=min(available_ticks,key=lambda n:(abs((float(tr["phase"][n-1])-target+math.pi)
                                                     %(2*math.pi)-math.pi), n))
            if pp+80 > tr["n_ticks_done"]:
                out["selections"].append({"target_index":target_index,"p":None,
                    "selected_tick":pp,"unavailable":"baseline_ended_before_selected_window"})
                continue
            out["selections"].append({"target_index":target_index,"p":pp,
                "target_phase":target,"actual_phase":float(tr["phase"][pp-1]),
                "metrics":base._window_metrics(tr,pp),
                "window_hash":base._window_hash(tr,pp),
                "prefix":tr["states"][pp],"endpoint":tr["states"][pp+80]})
    elif p is not None:
        out.update(metrics=base._window_metrics(tr,p) if tr["n_ticks_done"] >= p else None,
                   window_hash=base._window_hash(tr,p),
                   prefix=tr["states"].get(p),endpoint=tr["states"].get(p+80))
    else:
        out["endpoint"]=tr["states"].get(tr["n_ticks_done"])
    path=Path(job["out"])/"traces"/(job["id"]+".npz")
    np.savez_compressed(path, **{k:tr[k] for k in TRACE_KEYS})
    out["trace_file"]=str(path.name)
    return out

def retention(m, b):
    if not m or not b:
        return False
    return (m["valid"] and b["valid"] and b["fwd_disp_m"]>0
            and m["fwd_disp_m"] >= .9*b["fwd_disp_m"]
            and m["loaded_slip_m"] <= 1.25*b["loaded_slip_m"]
            and m["max_abs_roll_deg"] <= b["max_abs_roll_deg"]+3
            and m["max_abs_pitch_deg"] <= b["max_abs_pitch_deg"]+3
            and m["window_ticks"]==80 and not m["terminated_in_window"]
            and m["nonwalk_ticks"]==0)

def batch(jobs, workers, label):
    results=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(run_one,j):j for j in jobs}
        for f in as_completed(futures):
            row=f.result()
            results.append(row)
            print(json.dumps({"stage":label,"done":len(results),"total":len(jobs),
                              "id":row["id"],"ticks":row["ticks_done"]}),flush=True)
    return sorted(results,key=lambda r:r["id"])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--checkpoint",required=True)
    ap.add_argument("--out",required=True,type=Path)
    ap.add_argument("--workers",type=int,default=8)
    args=ap.parse_args()
    out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    (out/"traces").mkdir()
    started=time.time()
    try:
        pins=json.loads((HERE/"pins.json").read_text())
        reg=json.loads((HERE/"PREREGISTRATION.json").read_text())
        if sha(HERE/"PROPOSAL_SOURCE.md") != reg["protocol_sha256"]:
            raise RuntimeError("protocol hash mismatch")
        if sha(args.checkpoint) != pins["checkpoint_sha256"]:
            raise RuntimeError("checkpoint hash mismatch")
        if sha(HERE/"cfg_set.json") != pins["cfg_json_sha256"]:
            raise RuntimeError("original cfg hash mismatch")
        for path, expected in {**pins["source_hashes"],**pins["asset_hashes"]}.items():
            if sha(PROTO/path) != expected:
                raise RuntimeError("frozen source/asset mismatch: "+path)
        spec={"checkpoint":str(Path(args.checkpoint).resolve()),
              "cfg_set":json.loads((HERE/"cfg_set.json").read_text())+RESET_CFG,
              "episode_seconds":10,
              "required_identity":{k:pins["identity"][k] for k in
                                  ("model_variant","model_nmesh","model_ngeom","model_mass_kg")}}
        dump(out/"execution_manifest.json",{"started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
            "preregistration":reg,"script_sha256":sha(__file__),
            "helper_sha256":sha(os.environ["SUPPORT_YAW_REVIEWED_HELPER"]),
            "runtime_proto":str(PROTO),"spec":spec,"python":sys.version})
        cells=[{"reset_seed":r,"phase_index":pi,"phase":phase,"wz":wz}
               for r in (1,2) for pi,phase in enumerate(PHASES) for wz in (.15,-.15)]
        def job(cell,mode,p=None,target=None):
            ident=f"r{cell['reset_seed']}_ph{cell['phase_index']}_w{cell['wz']:+.2f}"
            if target is not None: ident+=f"_t{target}"
            ident+="_"+mode
            ticks=755 if mode=="baseline" else 1500 if p is None else p+80
            return {"id":ident,"cell":cell,"mode":mode,"p":p,"ticks":ticks,
                    "spec":dict(spec,episode_seconds=15 if mode.startswith("straight_") else 10),
                    "out":str(out)}
        baselines=batch([job(c,"baseline") for c in cells],args.workers,"baselines")
        dump(out/"baselines_frozen.json",baselines)
        # Confirm exact same reset offsets across phases and command signs.
        for seed in (1,2):
            offsets=[r["controller_state"]["reset"]["offset_rad"] for r in baselines
                     if r["cell"]["reset_seed"]==seed]
            if not all(offset==offsets[0] for offset in offsets):
                raise RuntimeError("reset draw changed across paired conditions")
        slots=[]
        for b in baselines:
            for sel in b["selections"]:
                slots.append({"cell":b["cell"],"selection":sel,"baseline":b["id"]})
        dump(out/"selected_states_frozen.json",slots)
        active=[s for s in slots if s["selection"]["p"] is not None]
        zeros=batch([job(s["cell"],"zero",s["selection"]["p"],s["selection"]["target_index"])
                     for s in active],args.workers,"zero_controls")
        zmap={(r["cell"]["reset_seed"],r["cell"]["phase_index"],r["cell"]["wz"],r["p"]):r
              for r in zeros}
        base=load_base()
        for s in active:
            c,sel=s["cell"],s["selection"]
            z=zmap[(c["reset_seed"],c["phase_index"],c["wz"],sel["p"])]
            z["zero_parity"]=(base._state_match(sel["prefix"],z["prefix"])
                             and base._state_match(sel["endpoint"],z["endpoint"])
                             and sel["window_hash"]==z["window_hash"])
        dump(out/"zero_controls_frozen.json",zeros)
        if not all(z["zero_parity"] for z in zeros):
            raise RuntimeError("zero-control full-state/trace parity failure")
        pulses=batch([job(s["cell"],mode,s["selection"]["p"],s["selection"]["target_index"])
                      for s in active for mode in ("positive","negative")],
                     args.workers,"pulse_branches")
        pmap={(r["cell"]["reset_seed"],r["cell"]["phase_index"],r["cell"]["wz"],r["p"],r["mode"]):r
              for r in pulses}
        rows=[]
        for s in slots:
            c,sel=s["cell"],s["selection"]
            row={"cell":c,"target_index":sel["target_index"],"p":sel["p"],"qualifies":False}
            if sel["p"] is None:
                row["unavailable"]=sel["unavailable"]
                rows.append(row);continue
            key=(c["reset_seed"],c["phase_index"],c["wz"],sel["p"])
            z=zmap[key]; positive=pmap[(*key,"positive")]; negative=pmap[(*key,"negative")]
            for branch in (positive,negative):
                branch["prefix_parity"]=base._state_match(z["prefix"],branch["prefix"])
                branch["vector_parity"]=(branch["controller_state"]["frozen_vector"]
                                        ==z["controller_state"]["frozen_vector"])
                if not branch["prefix_parity"] or not branch["vector_parity"]:
                    raise RuntimeError("pulse prefix/vector mismatch")
            b=sel["metrics"];mp=positive.get("metrics");mn=negative.get("metrics")
            gp=math.copysign(1,c["wz"])*(mp["d_yaw_rad"]-b["d_yaw_rad"]) if mp else None
            gm=math.copysign(1,c["wz"])*(mn["d_yaw_rad"]-b["d_yaw_rad"]) if mn else None
            rp,rn=retention(mp,b),retention(mn,b)
            available=z["controller_state"]["controller"]["available"]
            row.update(available=available,controller=z["controller_state"]["controller"],
                Gplus_rad=gp,Gminus_rad=gm,odd_rad=None if gp is None or gm is None else (gp-gm)/2,
                even_rad=None if gp is None or gm is None else (gp+gm)/2,
                positive_retention=rp,negative_retention=rn,
                qualifies=bool(available and gp is not None and gm is not None
                               and gp>=.005 and (gp-gm)/2>0 and rp and rn))
            rows.append(row)
        dump(out/"pulse_branches.json",pulses)
        dump(out/"state_results.json",rows)
        straight_cells=[dict(c,wz=0.) for c in cells if c["wz"]>0]
        straight=batch([job(c,mode) for c in straight_cells
                        for mode in ("straight_baseline","straight_zero_off")],
                       args.workers,"straight_zero_off")
        pairs=[]
        for c in straight_cells:
            pair=[r for r in straight if r["cell"]==c]
            a,b=pair
            pairs.append({"cell":c,"parity":a["trace_hash"]==b["trace_hash"]
                and base._state_match(a["endpoint"],b["endpoint"])
                and a["ticks_done"]==b["ticks_done"]==1500,
                "fell":[a["fell"],b["fell"]]})
        dump(out/"straight_zero_off.json",{"rollouts":straight,"pairs":pairs})
        if not all(p["parity"] for p in pairs):
            raise RuntimeError("straight zero-off parity failure")
        sign_targets={}
        for wz in (.15,-.15):
            sign_targets[str(wz)]={str(t):all(r["qualifies"] for r in rows
                if r["cell"]["wz"]==wz and r["target_index"]==t) for t in (0,1)}
        supported=all(any(v.values()) for v in sign_targets.values())
        summary={"status":"COMPLETE","decision":"BURST_AUTHORITY_SUPPORTED" if supported else "STOP",
            "sign_target_qualification":sign_targets,"branch_slots":48,
            "executed_branches":len(zeros)+len(pulses),"states":len(rows),
            "available_states":sum(r.get("available",False) for r in rows),
            "qualifying_states":sum(r["qualifies"] for r in rows),
            "zero_parity":all(z["zero_parity"] for z in zeros),
            "all_pulse_prefix_vector_parity":True,"straight_parity":True,
            "wall_seconds":time.time()-started,"no_PPO":True}
        dump(out/"summary.json",summary)
        print(json.dumps(summary),flush=True)
    except Exception:
        dump(out/"failure.json",{"status":"INFRASTRUCTURE_FAILURE",
             "traceback":traceback.format_exc(),"wall_seconds":time.time()-started})
        raise
if __name__=="__main__":
    main()
