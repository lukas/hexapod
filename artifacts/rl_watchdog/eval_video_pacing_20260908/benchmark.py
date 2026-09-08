"""Finite CPU-only rendering parity benchmark; not a qualification gate."""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.setdefault("MUJOCO_GL", "osmesa")
for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "2"
import sys, random, json, time, resource, hashlib, importlib.util
from pathlib import Path
PROTO = Path("/workspace/hexapod/hexapod_walker/prototype_sts3215")
MODULE = Path("/tmp/hexapod_eval_checkpoint_pacing_f37ab4beb.py")
OUT = Path("/tmp/hexapod_video_pacing_benchmark_f37ab4beb_frozen")
RUN = "cw-walkscratch-crutchoff-s1-widen8-legdutyratio-guardfix-acq10m"
CKPT = PROTO/"rl_move/sim/policies"/("ppo_goal_"+RUN.replace("-","_")+".zip")
sys.path[:0] = [str(PROTO), str(PROTO/"linux_control")]
import numpy as np
import torch
torch.set_num_threads(2)
from rl_move.config import load_config
from rl_move.sim.walk_task import SimHexapodJointWalkEnv
from rl_move.sim.servo_model import SimServoParams
from rl_move.sim import servo_model as sm
sm.MESH_DIR = Path("/workspace/hexapod-turnphase-wt/hexapod_walker/prototype_sts3215/mesh_mujoco")
sm.MESH_XML = sm.MESH_DIR / "hexapod_mesh.xml"
sm.MESH_MJX_XML = sm.MESH_DIR / "hexapod_mesh_mjx.xml"
assert hashlib.sha256(sm.MESH_XML.read_bytes()).hexdigest() == "7efb8e8a0cb014c0b4bac27c41e7a85e683553168b87d85aac0d52d6a8e5a837"
from rl_move.sim.gru_policy import load_checkpoint_auto
from rl_move.sim.train_ppo_sim import _annotate_frame, _parse_cfg_set
import imageio.v2 as imageio
spec = importlib.util.spec_from_file_location("rl_move.sim.eval_checkpoint_pacing_bench", MODULE)
ev = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ev
spec.loader.exec_module(ev)
entry = [e for e in json.loads((PROTO/"rl_move/orchestrator/experiments.json").read_text())
         if e.get("run")==RUN and e.get("extra_args")][-1]
argv = entry["extra_args"]
overrides = [argv[i+1] for i,k in enumerate(argv) if k=="--cfg-set"]
def config():
    cfg = load_config()
    for key,value in _parse_cfg_set(overrides).items():
        section,name=key.split(".",1); cfg.setdefault(section,{})[name]=value
    cfg["env"]["model_source"]="mesh"
    return cfg
def equal(x,y):
    if isinstance(x,np.ndarray):
        assert x.dtype==y.dtype and x.shape==y.shape and x.tobytes()==y.tobytes()
    elif isinstance(x,dict):
        assert x.keys()==y.keys()
        for k in x: equal(x[k],y[k])
    elif isinstance(x,(list,tuple)):
        assert len(x)==len(y)
        for a,b in zip(x,y): equal(a,b)
    elif isinstance(x,float) and np.isnan(x):
        assert np.isnan(y)
    else:
        assert x==y,(x,y)
def trial(fps,det):
    cfg=config()
    model=load_checkpoint_auto(CKPT,device="cpu")
    model.policy.set_training_mode(False)
    random.seed(19); np.random.seed(19); torch.manual_seed(19)
    env=SimHexapodJointWalkEnv(cfg,params=SimServoParams.from_cfg(cfg),seed=0,
        episode_seconds=1.2,randomize=False,dr_scale=0,render_mode="rgb_array")
    assert env.model.nmesh==34,env.model.nmesh
    identity={"nmesh":int(env.model.nmesh),"mass_kg":float(env.model.body_mass.sum())}
    assert abs(identity["mass_kg"]-4.80573)<1e-4,identity
    # Exactly the same two resets in both arms; renderer warmup excluded.
    env.reset(seed=0); env.render(); env.reset(seed=0)
    trace=[]; timing={}
    ru=resource.getrusage(resource.RUSAGE_SELF)
    cpu0=ru.ru_utime+ru.ru_stime
    start=time.perf_counter()
    try:
        ep,frames=ev.run_episode(env,model,deterministic=det,video=True,
            annotate=_annotate_frame,trace_sink=trace,video_fps=fps,video_timing=timing)
    finally:
        env.close()
    wall=time.perf_counter()-start
    ru=resource.getrusage(resource.RUSAGE_SELF)
    cpu=ru.ru_utime+ru.ru_stime-cpu0
    path=OUT/f'{"det" if det else "sto"}_{fps or "legacy"}'
    encode_start=time.perf_counter()
    ev._save_video(frames,path,timing=timing if fps is not None else None)
    encode_wall=time.perf_counter()-encode_start
    with imageio.get_reader(path.with_suffix(".mp4")) as reader:
        meta=reader.get_meta_data()
        encoded_frames=reader.count_frames()
    result=dict(requested_fps=fps,deterministic=det,render_rollout_wall_s=wall,
        process_cpu_s=cpu,encode_wall_s=encode_wall,frame_count=len(frames),
        encoded_frame_count=encoded_frames,encoded_fps=meta["fps"],
        encoded_duration_s=meta["duration"],timing=timing,model=identity,
        episode=ep)
    return ep,trace,result
OUT.mkdir(exist_ok=True)
results=[]
for det in (True,False):
    old,t0,b=trial(None,det)
    new,t1,a=trial(25.0,det)
    equal(old,new); equal(t0,t1)
    assert a["frame_count"]==a["encoded_frame_count"]
    assert abs(a["encoded_duration_s"]-a["timing"]["simulated_seconds"])<=1/25+1e-8
    b["exact_metrics_and_trace_parity"]=a["exact_metrics_and_trace_parity"]=True
    results.extend([b,a])
    print(json.dumps({k:a[k] for k in ("deterministic","render_rollout_wall_s",
        "process_cpu_s","frame_count","encoded_fps","encoded_duration_s",
        "exact_metrics_and_trace_parity","model")}),flush=True)
    print(json.dumps({"legacy_wall_s":b["render_rollout_wall_s"],
        "legacy_cpu_s":b["process_cpu_s"],"legacy_frames":b["frame_count"],
        "legacy_duration_s":b["encoded_duration_s"]}),flush=True)
mesh=sm.MESH_DIR
files=[mesh/"hexapod_mesh.xml",mesh/"hexapod_mesh_mjx.xml"]+sorted((mesh/"assets").glob("*"))
provenance={"checkpoint":str(CKPT),"checkpoint_md5":hashlib.md5(CKPT.read_bytes()).hexdigest(),
    "evaluator_sha256":hashlib.sha256(MODULE.read_bytes()).hexdigest(),
    "asset_sha256":{str(p.relative_to(mesh)):hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in files if p.is_file()},
    "training_run":RUN,"cfg_overrides":overrides,
    "benchmark_overrides":{"env.model_source":"mesh","randomize":False,"dr_scale":0,
        "episode_seconds":1.2,"env_seed":0,"policy_rng_seed":19,"torch_threads":2},
    "limitations":"Short rendering benchmark with an actual checkpoint; not a held-out qualification."
}
(OUT/"results.json").write_text(json.dumps({"results":results,"provenance":provenance},indent=2))
print("BENCHMARK_COMPLETE "+str(OUT/"results.json"),flush=True)
