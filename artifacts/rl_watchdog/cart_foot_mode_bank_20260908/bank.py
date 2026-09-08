"""Isolated exact-recipe paired Cartesian MODE comparator preflight.
No PPO, policy, checkpoint, W&B, training or production edits. Run from prototype root.
Historical MED margins are retained; unrealized comparator behavior makes ranking unavailable.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import sys
import time

POLICIES = ("track", "fixedhead", "wronghead", "park", "stall", "topple")
SEEDS = (0, 1)  # Existing comparator evaluation seeds, not new training seeds.
EPISODE_S = 20.0
MAX_TICKS = 2000
FK_TOL_M = 1e-6
Q_TOL_RAD = 1e-5
SOURCE_FILES = (
    "rl_move/sim/cart_foot_decode.py", "rl_move/sim/joint_task.py",
    "rl_move/sim/mjx_host.py", "rl_move/sim/mjx_sharded_vec_env.py",
    "rl_move/sim/mjx_backend.py", "rl_move/sim/sim_env.py",
    "hexapod_core/joint_frame.py", "mesh_mujoco/hexapod_mesh_mjx.xml",
    "rl_move/config.yaml", "rl_move/sim/servo_model.py",
    "rl_move/sim/walk_task.py", "rl_move/sim/goal_task.py", "rl_move/safety.py",
    "hexapod_core/tripod_gait.py", "rl_move/sim/probe_walk_income.py",
    "rl_move/tests/test_walkscratch_easy_pilot.py",
)
PREREGISTRATION = {
    "source": "test_walkscratch_easy_pilot.py EASY_HEADING_MED (means over seeds 0,1)",
    "policies": list(POLICIES), "seeds": list(SEEDS), "arms": ["OFF", "ON"],
    "episode_seconds": EPISODE_S, "max_total_control_ticks": 48000,
    "historical_checks": [
        "mean R(track) > mean R(fixedhead) + 15",
        "mean net planar displacement(track) > 0.5 m",
        "mean R(track) > mean R(park) + 25",
        "mean R(track) > mean R(stall) + 25",
        "min(mean R(park), mean R(stall)) > mean R(wronghead) + 15",
        "mean topple steps < 400 and mean R(topple) < min(mean R(park),mean R(stall))-15",
        "nonzero commands have abs(heading)<100 degrees; some abs(heading)>80 degrees",
    ],
    "death_scope": "Historical death probe used 20 degrees. This panel KEEPS exact recipe 30 degrees. Survival or unrepresentable fold makes death ordering UNAVAILABLE; no 20-degree substitution.",
    "reachability": "Clipping/FK/joint reconstruction are diagnostics, not automatic rejection: legacy joint boxes also clip. Rank only when realized behavior supports its label. Track needs positive body-along progress, wronghead negative; stationary uses the existing reward.walk_idle_speed_m_s threshold (default .02m/s); stall additionally requires varying actions and actual joint motion; fixedhead needs positive initial-heading progress and resampled commands. A surviving topple leaves death-ordering unavailable.",
    "reward_parity": "No ON/OFF reward equality assertion: k_action_delta=.01 acts on normalized actions, whose coordinates change. Full scalar reward is retained.",
    "scope": "Behavior-comparator MODE preflight, not policy qualification, exhaustive exploit coverage, or function-preserving actor initialization. Offline scripted trajectories are never training data.",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def array_sha(a):
    return hashlib.sha256(np.asarray(a).tobytes()).hexdigest()


def clean(x):
    if isinstance(x, dict): return {str(k): clean(v) for k,v in x.items()}
    if isinstance(x, (list, tuple)): return [clean(v) for v in x]
    if isinstance(x, np.ndarray): return clean(x.tolist())
    if isinstance(x, np.generic): return clean(x.item())
    if isinstance(x, float) and not math.isfinite(x): return None
    return x


def save(result, path):
    temp=path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(clean(result), indent=2, allow_nan=False)+"\n")
    temp.replace(path)


def model_identity(env):
    return {"source": env._model_source, "nmesh": int(env.model.nmesh),
            "mass_kg": float(np.sum(env.model.body_mass)),
            "gravity": env.model.opt.gravity.tolist(),
            "physics_dt": float(env.model.opt.timestep), "control_dt": float(env.dt),
            "body_pos_sha256": array_sha(env.model.body_pos),
            "body_mass_sha256": array_sha(env.model.body_mass),
            "geom_friction_sha256": array_sha(env.model.geom_friction)}


def rollout(cfg, arm, policy, seed):
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    from rl_move.sim.servo_model import SimServoParams, motor_contract
    from rl_move.sim.cart_foot_decode import CartFootDecoder
    from hexapod_core.tripod_gait import TripodGait
    from rl_move.sim.probe_walk_income import WALK_PLANT
    env=SimHexapodJointWalkEnv(cfg=copy.deepcopy(cfg), params=SimServoParams.from_cfg(cfg),
        randomize=True, dr_scale=0.0, episode_seconds=EPISODE_S, seed=seed)
    row={"arm":arm,"policy":policy,"seed":seed,"status":"ERROR","trace":[]}
    try:
        assert env._model_source=="mesh_mjx"
        assert bool(env._cart_foot_active)==(arm=="ON")
        assert abs(env.dt-.01)<1e-12 and env.episode_steps==MAX_TICKS
        row["nominal_model"]=model_identity(env)
        assert abs(row["nominal_model"]["mass_kg"]-4.80573)<.001, row["nominal_model"]
        center=np.asarray(env._joint_action_box_center).copy()
        box=np.array([.06,.035,.04])
        decoder=env._cart_foot if arm=="ON" else CartFootDecoder(env.model,center,box)
        # This helper uses only fresh MjData and its own local RNG; never live state.
        row["nominal_analytic_vs_mujoco_fk_max_m"]=decoder.verify_fk(env.model,n=12,seed=137)
        assert row["nominal_analytic_vs_mujoco_fk_max_m"]<FK_TOL_M
        row["motor_contract"]=motor_contract(cfg,params=SimServoParams.from_cfg(cfg))
        obs,_=env.reset()
        assert np.all(np.isfinite(obs))
        row["reset_model"]=model_identity(env)
        row["reset_qpos_sha256"]=array_sha(env.data.qpos)
        row["reset_qvel_sha256"]=array_sha(env.data.qvel)
        row["reset_obs_sha256"]=array_sha(obs)
        traj=env._goal_traj
        command=np.stack([traj.vx,traj.vy],axis=1)
        assert len(command)>=MAX_TICKS and np.all(np.isfinite(command))
        row["generated_command_xy_m_s"]=command.tolist()
        row["command_sha256"]=array_sha(command)
        row["command_changed"]=bool(np.any(np.linalg.norm(command-command[0],axis=1)>1e-6))
        angles=np.degrees(np.arctan2(command[:,1],command[:,0]))
        moving=np.linalg.norm(command,axis=1)>1e-6
        row["command_abs_heading_max_deg"]=float(np.max(np.abs(angles[moving])))
        row["command_heading_valid"]=bool(np.all(np.abs(angles[moving])<100))
        gait=TripodGait(vx=0.,lift=.025)
        gait.sync_plant_stance(*WALK_PLANT)
        plant=np.array([0.,*WALK_PLANT]*6)*math.pi/180
        topple=plant.copy()
        for leg in (0,1):
            topple[3*leg+1:3*leg+3]-=80*math.pi/180
        xy0=np.asarray(env.data.qpos[:2]).copy()
        total=0.; along=0.; initial_along=0.; speed_integral=0.; action_variation=0.; clipped_ticks=0; qbad=0; fkbad=0
        previous_action=None
        qlo=np.asarray(env._state.joint_position).copy(); qhi=qlo.copy()
        maxraw=0.; maxq=0.; maxfk=0.; sums={}; done=trunc=False; reason=None
        xy=xy0.copy()
        for tick in range(MAX_TICKS):
            cvx,cvy=map(float,command[tick])
            if policy=="track": gait.set_velocity(vx=cvx,vy=cvy)
            elif policy=="fixedhead": gait.set_velocity(vx=float(command[0,0]),vy=float(command[0,1]))
            elif policy=="wronghead": gait.set_velocity(vx=-cvx,vy=-cvy)
            elif policy=="stall": gait.set_velocity(vx=0.,vy=0.)
            if policy=="park": wanted=plant.copy()
            elif policy=="topple": wanted=topple.copy()
            else: wanted=np.asarray(gait.desired_deg(tick*env.dt))*math.pi/180
            foot=decoder.fk(wanted)  # nominal leg-root frame matching actual decoder
            raw=((foot-decoder.center_p)/decoder.box).reshape(18) if arm=="ON" else (wanted-center)/env._joint_action_box_rad
            action=np.clip(raw,-1.,1.)
            decoded,ok,msg=env._act_to_q(action)
            assert ok and not msg and np.all(np.isfinite(decoded))
            qerr=float(np.max(np.abs(np.asarray(decoded)-wanted)))
            ferr=float(np.max(np.linalg.norm(decoder.fk(decoded)-foot,axis=1)))
            clipped=bool(np.any(np.abs(raw)>1+1e-9))
            clipped_ticks+=int(clipped); qbad+=int(qerr>Q_TOL_RAD); fkbad+=int(ferr>FK_TOL_M)
            maxraw=max(maxraw,float(np.max(np.abs(raw)))); maxq=max(maxq,qerr); maxfk=max(maxfk,ferr)
            obs,reward,done,trunc,info=env.step(action)
            assert np.all(np.isfinite(obs)) and math.isfinite(float(reward))
            assert np.all(np.isfinite(env.data.qpos)) and np.all(np.isfinite(env.data.qvel))
            total+=float(reward)
            xynew=np.asarray(env.data.qpos[:2]).copy()
            speed=math.hypot(cvx,cvy)
            body_v=np.asarray(env._body_vel_xy(),dtype=float)
            assert np.all(np.isfinite(body_v))
            if speed>1e-9: along+=float(np.dot(body_v,np.array([cvx,cvy])/speed))*env.dt
            first_speed=float(np.linalg.norm(command[0]))
            if first_speed>1e-9: initial_along+=float(np.dot(body_v,command[0]/first_speed))*env.dt
            speed_integral+=float(np.linalg.norm(body_v))*env.dt
            if previous_action is not None: action_variation+=float(np.sum(np.abs(action-previous_action)))
            previous_action=action.copy()
            qactual=np.asarray(env._state.joint_position);qlo=np.minimum(qlo,qactual);qhi=np.maximum(qhi,qactual)
            xy=xynew
            scalar={k:float(v) for k,v in info.items() if isinstance(v,(int,float,np.number)) and not isinstance(v,(bool,np.bool_))}
            assert all(math.isfinite(v) for v in scalar.values())
            for key,val in scalar.items(): sums[key]=sums.get(key,0.)+val
            reason=info.get("termination_reason")
            row["trace"].append({"tick":tick,"cmd_xy":[cvx,cvy],"reward":float(reward),
                "body_v_xy_m_s":body_v.tolist(),"base_xy":xy.tolist(),"raw_action_abs_max":float(np.max(np.abs(raw))),
                "input_clipped":clipped,"target_joint_max_error_rad":qerr,"target_fk_max_error_m":ferr,
                "reward_info":{k:v for k,v in scalar.items() if k.startswith(("reward","r_"))},
                "done":bool(done),"truncated":bool(trunc)})
            if done or trunc: break
        assert done or trunc, "hard 2000-tick bound reached without env termination/truncation"
        reachable=(clipped_ticks==0 and qbad==0 and fkbad==0)
        duration=len(row["trace"])*env.dt
        idle_speed=float(cfg.get("reward",{}).get("walk_idle_speed_m_s",.02))
        stationary=speed_integral/duration<=idle_speed
        joint_span=float(np.max(qhi-qlo))
        semantic={"track":along>1e-6,"fixedhead":initial_along>1e-6 and row["command_changed"],
            "wronghead":along < -1e-6,"park":stationary,
            "stall":stationary and action_variation>1e-6 and joint_span>1e-5,
            "topple":bool(done)}[policy]
        row.update(status="COMPLETE",ticks=len(row["trace"]),return_sum=total,
            realized_comparator_valid=bool(semantic),
            semantic_unavailable_reason=None if semantic else "realized motion did not instantiate the named comparator",
            stationary_speed_threshold_m_s=idle_speed,mean_body_speed_m_s=speed_integral/duration,
            initial_heading_displacement_m=initial_along,actual_joint_span_max_rad=joint_span,
            action_total_variation=action_variation,
            net_planar_displacement_m=float(np.linalg.norm(xy-xy0)),
            along_command_displacement_m=along,terminated=bool(done),truncated=bool(trunc),
            termination_reason=reason,clip_ticks=clipped_ticks,
            q_reconstruction_bad_ticks=qbad,fk_reconstruction_bad_ticks=fkbad,
            raw_action_abs_max=maxraw,joint_reconstruction_max_rad=maxq,fk_reconstruction_max_m=maxfk,
            intended_target_exactly_representable=reachable,
            comparator_scope="exact_targets" if reachable else "projected_targets_label_requires_realized_semantics",
            scalar_info_sums=sums,
            scalar_info_note="Raw per-key sums; reward telemetry can include overlapping components and must not be blindly added.")
    except TimeoutError:
        raise
    except Exception as exc:
        row["error"]=f"{type(exc).__name__}: {exc}"
    finally:
        env.close()
    return row


def summarize(rows):
    index={(r["arm"],r["policy"],r["seed"]):r for r in rows}
    expected={(a,p,s) for a in ("OFF","ON") for p in POLICIES for s in SEEDS}
    matrix_complete=len(index)==len(rows)==24 and set(index)==expected
    pairing=[]
    if matrix_complete:
        for p in POLICIES:
            for s in SEEDS:
                off,on=(index[(a,p,s)] for a in ("OFF","ON"))
                keys=("command_sha256","reset_qpos_sha256","reset_qvel_sha256","reset_obs_sha256","reset_model")
                pairing.append({"policy":p,"seed":s,"equal":all(k in off and off[k]==on.get(k) for k in keys)})
    pair_ok=matrix_complete and all(r["equal"] for r in pairing)
    arms={}
    for arm in ("OFF","ON"):
        checks=[]
        def add(name,pols,fn,extra=None):
            rr=[index.get((arm,p,s)) for p in pols for s in SEEDS]
            ready=pair_ok and all(r and r.get("status")=="COMPLETE" and r.get("realized_comparator_valid") for r in rr)
            if ready and extra is not None: ready=extra(rr)
            checks.append({"name":name,"status":("PASS" if fn() else "FAIL") if ready else "UNAVAILABLE"})
        def mean(p,k): return float(np.mean([index[(arm,p,s)][k] for s in SEEDS]))
        r=lambda p:mean(p,"return_sum")
        add("track_over_fixed_plus15",("track","fixedhead"),lambda:r("track")>r("fixedhead")+15,
            lambda rr:all(x["command_changed"] for x in rr))
        add("track_displacement_over_0.5m",("track",),lambda:mean("track","net_planar_displacement_m")>.5)
        for p in ("park","stall"):
            add(f"track_over_{p}_plus25",("track",p),lambda p=p:r("track")>r(p)+25)
        add("wronghead_below_stationary_minus15",("wronghead","park","stall"),lambda:min(r("park"),r("stall"))>r("wronghead")+15)
        add("death_floor_at_actual30deg",("topple","park","stall"),
            lambda:mean("topple","ticks")<400 and r("topple")<min(r("park"),r("stall"))-15,
            lambda rr:all(x["terminated"] for x in rr if x["policy"]=="topple"))
        ar=[index.get((arm,p,s),{}) for p in POLICIES for s in SEEDS]
        heading_ok=all(x.get("command_heading_valid",False) for x in ar) and any(x.get("command_abs_heading_max_deg",0)>80 for x in ar)
        checks.append({"name":"five_heading_wiring","status":"PASS" if heading_ok else "FAIL"})
        no_unexpected_falls=all(not x.get("terminated",True) for x in ar if x.get("policy")!="topple")
        checks.append({"name":"non_topple_comparators_survive","status":"PASS" if no_unexpected_falls else "FAIL"})
        arms[arm]={"checks":checks,"mode_bank_pass":all(c["status"]=="PASS" for c in checks)}
    return {"matrix_complete":matrix_complete,"on_off_reset_command_pairing":pairing,"pairing_pass":pair_ok,
        "arms":arms,"mode_preflight_pass":pair_ok and all(v["mode_bank_pass"] for v in arms.values()),
        "claim_scope":PREREGISTRATION["scope"],"not_policy_qualification":True}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recipe",type=Path,required=True)
    ap.add_argument("--expected-hashes",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args(); root=Path.cwd()
    assert (root/"rl_move/sim").is_dir(), "run from prototype root"
    sys.path.insert(0,str(root))
    os.environ["HEXAPOD_MODEL_SOURCE"]="mesh_mjx"
    os.environ["HEXAPOD_CONTROL_HZ"]="100"
    for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):os.environ[k]="1"
    global np
    import numpy as np
    from rl_move.config import load_config
    from rl_move.sim.train_ppo_sim import _parse_cfg_set
    recipe=json.loads(args.recipe.read_text())
    assert len(recipe["cfg_overrides"])==78 and recipe["seed"]==2 and recipe["dr_scale"]==0
    expected_cart=["goal.walk_cart_foot_box_x_m=0.06","goal.walk_cart_foot_box_y_m=0.035","goal.walk_cart_foot_box_z_m=0.04"]
    assert recipe["cartesian_overrides"]==expected_cart
    source_hashes={p:sha(root/p) for p in SOURCE_FILES}
    for p,digest in json.loads(args.expected_hashes.read_text()).items():
        assert source_hashes[p]==digest,f"source changed: {p}"
    cfgs={}
    for arm in ("OFF","ON"):
        cfg=load_config()
        parsed=_parse_cfg_set(recipe["cfg_overrides"]+(expected_cart if arm=="ON" else []))
        assert len(parsed)==(81 if arm=="ON" else 78)
        for key,value in parsed.items():
            sec,leaf=key.split(".",1); cfg.setdefault(sec,{})[leaf]=value
        assert cfg["safety"]["max_roll_deg"]==cfg["safety"]["max_pitch_deg"]==30
        assert cfg["reward"]["k_action_delta"]==.01
        cfgs[arm]=cfg
    result={"status":"RUNNING","preregistration":PREREGISTRATION,"recipe":recipe,
        "recipe_sha256":sha(args.recipe),"script_sha256":sha(__file__),
        "source_hashes":source_hashes,"resolved_cfg":cfgs,"rows":[],
        "serialization_note":"Nonfinite values in error-only output are null; runtime assertions reject nonfinite observations, physics, rewards and scalar info."}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    log=args.out.with_suffix(".log")
    def emit(msg):
        line=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())+" "+msg
        print(line,flush=True)
        with log.open("a") as f:f.write(line+"\n")
    def timeout(_s,_f): raise TimeoutError("external bounded timeout")
    signal.signal(signal.SIGTERM,timeout)
    started=time.monotonic();save(result,args.out)
    try:
        for seed in SEEDS:
            for policy in POLICIES:
                for arm in ("OFF","ON"):
                    emit(f"START {arm} {policy} seed={seed}")
                    row=rollout(cfgs[arm],arm,policy,seed);result["rows"].append(row)
                    emit(f"END {arm} {policy} seed={seed} status={row['status']} ticks={row.get('ticks')} return={row.get('return_sum')} realized={row.get('realized_comparator_valid')} exact_targets={row.get('intended_target_exactly_representable')}")
                    save(result,args.out)
        result["summary"]=summarize(result["rows"])
        assert {p:sha(root/p) for p in SOURCE_FILES}==source_hashes,"source changed during panel"
        result["status"]="PASS" if result["summary"]["mode_preflight_pass"] else "NOT_PASS"
    except BaseException as exc:
        result.update(status="ERROR",error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        result["elapsed_seconds"]=time.monotonic()-started;save(result,args.out)
        emit("FINAL "+result["status"])
    return 0 if result["status"]=="PASS" else 2


if __name__=="__main__":
    raise SystemExit(main())
