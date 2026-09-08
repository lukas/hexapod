"""Six untouched, preregistered baseline replays. Import performs no simulation."""
from __future__ import annotations
import os
for _name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ.setdefault(_name,'1')
import argparse, hashlib, importlib.util, json, math, sys, time, traceback
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'turn_magnitude_execution_20260908'
TRACE_KEYS=('yaw','xy','vx','phase','contact','pad_xy','roll','pitch','endpoint_yaw','material_slip','loaded_time','body_forward')
PROFILE_KEYS=('goal','target','_v','_vel_now','_acc_now')
BASE=None

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def serial(x):
    if isinstance(x,np.ndarray): return x.tolist()
    if isinstance(x,np.generic): return x.item()
    if isinstance(x,dict): return {str(k):serial(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [serial(v) for v in x]
    return x
def dump(p,x): Path(p).write_text(json.dumps(serial(x),indent=2,allow_nan=False)+'\n')
def arr(x,shape=None):
    a=np.asarray(x).copy()
    if a.dtype.hasobject or not (np.issubdtype(a.dtype,np.number) or a.dtype==np.dtype(bool)) or not np.isfinite(a).all():
        raise ValueError('required numeric observation unavailable/nonfinite')
    if shape is not None and a.shape!=shape: raise ValueError(f'observation shape {a.shape} != {shape}')
    return a
def vec(x): return arr(x,(18,))
def logical_to_mj(x):
    y=np.asarray(x,dtype=float).copy();y[...,2::3]-=y[...,1::3];return y
def mj_to_logical(x):
    y=np.asarray(x,dtype=float).copy();y[...,2::3]+=y[...,1::3];return y
def array_digest(x): return hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()
def trace_digest(tr):
    h=hashlib.sha256()
    for k in TRACE_KEYS: h.update(np.ascontiguousarray(tr[k]).tobytes())
    h.update(json.dumps(tr['modes']).encode());return h.hexdigest()
def fixed_cells():
    return [dict(id=f'w{w:+.2f}_ph{j}_'+('straight_baseline' if w==0 else 'baseline'),
                 cell=dict(vx=.08,wz=w,phase_offset=ph),ticks=1500 if w==0 else 755)
            for w in (.15,-.15,0.) for j,ph in enumerate((0.,math.pi))]

class Recorder:
    """Sidecar only. Hooks preserve original calls, returns and instance state."""
    def __init__(self,env,digest):
        self.env=env;self.digest=digest;self.control=[];self.profile=[];self.physics=[];self.commands=[]
        self.row=None;self.index=0;self.restorers=[];self.active=False
        p=env._profile
        self.metadata=dict(control_dt=float(env.dt),physics_dt=float(env.model.opt.timestep),
            substeps=int(env._substeps),joint_qpos_indices=arr(env._qadr),joint_qvel_indices=arr(env._vadr),
            position_actuator_indices=arr(env._pos_act),profile_latency_s=vec(p._latency_s),
            profile_deadband_rad=vec(p._deadband),profile_default_velocity_rad_s=vec(p._vel_default),
            profile_default_acceleration_rad_s2=vec(p._acc_default),
            initial_profile_time=float(p._t),initial_profile_state={k:vec(getattr(p,k)) for k in PROFILE_KEYS},
            initial_profile_queue=[dict(time=float(v[0]),q_mj_rad=vec(v[1]),velocity_rad_s=vec(v[2]),
                                       acceleration_rad_s2=vec(v[3])) for v in p._queue],
            write_speed_deg_s=float(env.write_speed_deg_s),write_acc_units=float(env.write_acc_units),
            actuator_gainprm=arr(env.model.actuator_gainprm),actuator_biasprm=arr(env.model.actuator_biasprm),
            actuator_forcerange=arr(env.model.actuator_forcerange),actuator_ctrlrange=arr(env.model.actuator_ctrlrange),
            actuator_forcelimited=arr(env.model.actuator_forcelimited),actuator_ctrllimited=arr(env.model.actuator_ctrllimited))
        if abs(self.metadata['control_dt']-.01)>1e-12 or abs(self.metadata['substeps']*self.metadata['physics_dt']-.01)>1e-12:
            raise ValueError('invalid fixed control/substep timing')

    def _put(self,key,value):
        if self.row is None or key in self.row: raise ValueError('missing/duplicate stage '+key)
        self.row[key]=value

    def predict(self,model,obs,deterministic=True):
        if self.row is not None: raise ValueError('predict without completed control step')
        recurrent=lambda:{n:getattr(model,n) for n in ('_state','_episode_start') if hasattr(model,n)}
        e=self.env
        self.row=dict(tick=self.index,episode_step_pre=int(e._step_i),sim_time_pre=float(e.data.time),
            profile_time_pre=float(e._profile._t),phase_pre=float(e._phase),policy_observation=arr(obs),
            recurrent_before=self.digest(recurrent()),actual_mj_pre_rad=vec(e.data.qpos[e._qadr]),
            actual_mj_pre_rad_s=vec(e.data.qvel[e._vadr]))
        result=model.predict(obs,deterministic=deterministic)
        self._put('policy_action',vec(result[0]));self._put('recurrent_after',self.digest(recurrent()))
        return result

    def _class_hook(self,obj,name,callback):
        cls=type(obj);owned=name in vars(cls);original=getattr(cls,name)
        def wrapper(current,*args,**kwargs):
            if current is obj: return callback(original,current,*args,**kwargs)
            return original(current,*args,**kwargs)
        setattr(cls,name,wrapper)
        def restore():
            if owned:setattr(cls,name,original)
            else:delattr(cls,name)
        self.restorers.append(restore)

    def _env_hook(self,name,callback):
        e=self.env;owned=name in vars(e);original=getattr(e,name)
        setattr(e,name,lambda *a,**kw:callback(original,*a,**kw))
        def restore():
            if owned:setattr(e,name,original)
            else:delattr(e,name)
        self.restorers.append(restore)

    def install(self):
        e=self.env
        def decode(original,clipped):
            self._put('decoder_action',vec(clipped));result=original(clipped)
            self._put('decoded_logical_rad',vec(result[0]));self._put('decoder_ok',bool(result[1]))
            self._put('decoder_reason',str(result[2]));return result
        def safety(original,obj,q,state,**kw):
            self._put('safety_input_logical_rad',vec(q));self._put('safety_previous_logical_rad',vec(obj._last_safe))
            self._put('safety_max_delta_rad',float(obj.max_dq));self._put('safety_entry_ticks',int(obj._entry_ticks))
            self._put('safety_entry_ramp_s',float(obj.entry_ramp_s));self._put('safety_entry_start_rad',float(obj.entry_start_dq))
            self._put('safety_hz',float(obj._hz));result=original(obj,q,state,**kw)
            self._put('safety_output_logical_rad',vec(result[0]))
            for k in ('ok','terminate','held'):self._put('safety_'+k,bool(getattr(result[1],k)))
            self._put('safety_reason',str(result[1].reason));return result
        def command(original,obj,q,**kw):
            if not self.active:raise ValueError('profile write outside observed control step')
            r=dict(tick=self.index,sim_time=float(e.data.time),profile_time=float(obj._t),
                   q_mj_rad=vec(q),speed_deg_s=arr(kw.get('speed_deg_s')),
                   acc_units=arr(kw.get('acc_units')),queue_before=len(obj._queue))
            result=original(obj,q,**kw)
            r.update(queue_after=len(obj._queue),enqueued_time=float(obj._queue[-1][0]),
                     enqueued_q_mj_rad=vec(obj._queue[-1][1]),enqueued_velocity_rad_s=vec(obj._queue[-1][2]),
                     enqueued_acceleration_rad_s2=vec(obj._queue[-1][3]))
            self.commands.append(r);return result
        def profile_tick(original,obj,dt):
            if not self.active:raise ValueError('profile tick outside observed control step')
            j=len(self.profile)-self.row['profile_start']
            r=dict(tick=self.index,substep=j,dt=float(dt),sim_time=float(e.data.time),
                   profile_time_before=float(obj._t),queue_before=len(obj._queue))
            r.update({k+'_before':vec(getattr(obj,k)) for k in PROFILE_KEYS})
            result=original(obj,dt)
            r.update({k+'_after':vec(getattr(obj,k)) for k in PROFILE_KEYS})
            r.update(profile_time_after=float(obj._t),queue_after=len(obj._queue))
            self.profile.append(r);return result
        def step(original,action):
            if self.row is None or self.active:raise ValueError('control-step/predict ordering failure')
            self._put('env_input_action',vec(action));self.row.update(profile_start=len(self.profile),
                physics_start=len(self.physics),command_start=len(self.commands));self.active=True
            try:result=original(action)
            finally:self.active=False
            self.row.update(profile_count=len(self.profile)-self.row['profile_start'],
                physics_count=len(self.physics)-self.row['physics_start'],command_count=len(self.commands)-self.row['command_start'],
                latched_logical_rad=vec(e._cmd),actual_mj_post_rad=vec(e.data.qpos[e._qadr]),
                actual_mj_post_rad_s=vec(e.data.qvel[e._vadr]),sensed_logical_rad=vec(e._state.joint_position),
                sensed_logical_rad_s=vec(e._state.joint_velocity),servo_current_a=vec(e._state.servo_current),
                sim_time_post=float(e.data.time),profile_time_post=float(e._profile._t),episode_step_post=int(e._step_i),
                terminated=bool(result[2]),truncated=bool(result[3]))
            self.control.append(self.row);self.row=None;self.index+=1;return result
        self._env_hook('_act_to_q',decode);self._class_hook(e.safety,'filter',safety)
        self._class_hook(e._profile,'command',command);self._class_hook(e._profile,'tick',profile_tick)
        self._env_hook('step',step)

    def physics_step(self,original,model,data):
        if not self.active:raise ValueError('physics step outside observed control step')
        e=self.env;j=len(self.physics)-self.row['physics_start']
        if len(self.profile)-self.row['profile_start']!=j+1:raise ValueError('profile/physics ordering mismatch')
        r=dict(tick=self.index,substep=j,sim_time_pre=float(data.time),
            q_mj_pre_rad=vec(data.qpos[e._qadr]),q_mj_pre_rad_s=vec(data.qvel[e._vadr]),
            effective_ctrl_mj_rad=vec(data.ctrl[e._pos_act]),qfrc_actuator_pre_nm=vec(data.qfrc_actuator[e._vadr]))
        result=original(model,data)
        r.update(sim_time_post=float(data.time),q_mj_post_rad=vec(data.qpos[e._qadr]),
            q_mj_post_rad_s=vec(data.qvel[e._vadr]),qfrc_actuator_post_nm=vec(data.qfrc_actuator[e._vadr]))
        self.physics.append(r);return result

    def restore(self):
        while self.restorers:self.restorers.pop()()

class Predictor:
    def __init__(self,model,recorder):self.model=model;self.recorder=recorder
    def __getattr__(self,n):return getattr(self.model,n)
    def predict(self,obs,deterministic=True):return self.recorder.predict(self.model,obs,deterministic)

def pack(rows):
    if not rows:return {}
    keys=set(rows[0])
    if any(set(r)!=keys for r in rows):raise ValueError('incomplete record fields')
    result={k:np.asarray([r[k] for r in rows]) for k in sorted(keys)}
    for k,v in result.items():
        if v.dtype.hasobject:raise ValueError('ragged/object capture '+k)
        if np.issubdtype(v.dtype,np.number) and not np.isfinite(v).all():raise ValueError('nonfinite capture '+k)
    return result

def validate_capture(control,profile,physics,commands,n,substeps):
    if len(control.get('tick',[]))!=n or not np.array_equal(control['tick'],np.arange(n)):
        raise ValueError('incomplete control tick coverage')
    for stage in (profile,physics):
        if not np.array_equal(stage['tick'],np.repeat(np.arange(n),substeps)) or not np.array_equal(stage['substep'],np.tile(np.arange(substeps),n)):
            raise ValueError('incomplete physics/profile coverage')
    for k in ('profile_count','physics_count'):
        if not np.all(control[k]==substeps):raise ValueError('wrong per-tick substep count')
    ct=commands.get('tick',np.array([],dtype=int))
    if len(ct)!=int(control['command_count'].sum()):raise ValueError('write count mismatch')
    if np.any(ct<0) or np.any(ct>=n) or np.any(np.diff(ct)<0):raise ValueError('nonchronological write events')
    if not np.array_equal(np.bincount(ct,minlength=n),control['command_count']):raise ValueError('write index mismatch')
    if np.any(control['terminated']) or not np.all(control['decoder_ok']):raise ValueError('unhealthy/incomplete baseline')
    for d in (control,profile,physics,commands):
        for k,a in d.items():
            if a.dtype.hasobject or (np.issubdtype(a.dtype,np.number) and not np.isfinite(a).all()):raise ValueError('nonfinite/incomplete '+k)
    if not np.array_equal(control['policy_action'],control['env_input_action']):raise ValueError('policy action changed')
    if not np.array_equal(control['decoded_logical_rad'],control['safety_input_logical_rad']):raise ValueError('decoder/safety boundary differs')
    return True

def compare_arrays(actual,reference):
    if set(actual)!=set(reference):raise ValueError('reference array fields differ')
    checks={k:bool(actual[k].shape==reference[k].shape and actual[k].dtype==reference[k].dtype
                   and np.ascontiguousarray(actual[k]).tobytes()==np.ascontiguousarray(reference[k]).tobytes()) for k in actual}
    if not all(checks.values()):raise ValueError('reference array mismatch: '+str([k for k,v in checks.items() if not v]))
    return checks

def validate_timing(c,p,f,metadata):
    n=len(c['tick']);s=metadata['substeps'];h=metadata['physics_dt']
    # Clock arithmetic alone tolerates accumulated float64 addition; reference
    # traces and matching observed stage boundaries remain byte-exact.
    if not np.allclose(p['dt'],h,rtol=0,atol=1e-12):raise ValueError('physics timestep changed')
    for delta in (p['profile_time_after']-p['profile_time_before'],f['sim_time_post']-f['sim_time_pre']):
        if not np.allclose(delta,h,rtol=0,atol=1e-10):raise ValueError('incomplete physical time coverage')
    if not np.array_equal(p['sim_time'],f['sim_time_pre']):raise ValueError('profile/physics sample alignment')
    for before,after in [('sim_time_pre','sim_time_post'),('q_mj_pre_rad','q_mj_post_rad'),('q_mj_pre_rad_s','q_mj_post_rad_s')]:
        if not np.array_equal(f[after][:-1],f[before][1:]):raise ValueError('discontinuous physics history '+before)
    for before,after in [('profile_time_before','profile_time_after')]+[(k+'_before',k+'_after') for k in PROFILE_KEYS]:
        if not np.array_equal(p[after][:-1],p[before][1:]):raise ValueError('discontinuous profile history '+before)
    for key,control_key,which in [('sim_time_pre','sim_time_pre',0),('sim_time_post','sim_time_post',-1)]:
        if not np.array_equal(f[key].reshape(n,s)[:,which],c[control_key]):raise ValueError('control/physics clock alignment')
    for a,b,which in [('q_mj_pre_rad','actual_mj_pre_rad',0),('q_mj_post_rad','actual_mj_post_rad',-1)]:
        if not np.array_equal(f[a].reshape(n,s,18)[:,which,:],c[b]):raise ValueError('control/physics joint alignment')
    if not np.array_equal(p['profile_time_before'].reshape(n,s)[:,0],c['profile_time_pre']) or not np.array_equal(p['profile_time_after'].reshape(n,s)[:,-1],c['profile_time_post']):
        raise ValueError('control/profile clock alignment')
    if not np.allclose(c['decoded_logical_rad'],metadata['affine_center_rad']+c['decoder_action']*metadata['affine_half_range_rad'],rtol=0,atol=2e-15):
        raise ValueError('affine decoder numeric contract mismatch')
    return True

def reversals(x):
    return [int(np.count_nonzero(np.diff(np.sign(a[a!=0])))) for a in np.asarray(x).T]
def aggregate(c,p,f,start):
    m=c['tick']>=start;pm=p['tick']>=start;fm=f['tick']>=start
    meanabs=lambda a:np.mean(np.abs(a),axis=0).tolist()
    req=c['decoded_logical_rad']-c['safety_previous_logical_rad']
    got=c['safety_output_logical_rad']-c['safety_previous_logical_rad']
    cap=c['safety_max_delta_rad'].copy();active=c['safety_entry_ramp_s']>0
    t=c['safety_entry_ticks']/c['safety_hz'];ramp=active & (t<c['safety_entry_ramp_s'])
    cap[ramp]=np.minimum(cap[ramp],c['safety_entry_start_rad'][ramp]+t[ramp]/c['safety_entry_ramp_s'][ramp]*(cap[ramp]-c['safety_entry_start_rad'][ramp]))
    return dict(start_tick=start,control_ticks=int(m.sum()),
        decoded_safe_mean_abs_rad=meanabs(c['decoded_logical_rad'][m]-c['safety_output_logical_rad'][m]),
        requested_increment_mean_abs_rad=meanabs(req[m]),safe_increment_mean_abs_rad=meanabs(got[m]),
        requested_slew_exceed_fraction=np.mean(np.abs(req[m])>cap[m,None],axis=0).tolist(),
        profile_goal_target_mean_abs_rad=meanabs(p['goal_after'][pm]-p['target_after'][pm]),
        profile_velocity_cap_max_ratio=np.max(np.abs(p['_v_after'][pm])/p['_vel_now_after'][pm],axis=0).tolist(),
        effective_profile_mean_abs_rad=meanabs(f['effective_ctrl_mj_rad'][fm]-p['target_after'][pm]),
        profile_actual_post_mean_abs_rad=meanabs(p['target_after'][pm]-f['q_mj_post_rad'][fm]),
        effective_actual_pre_mean_abs_rad=meanabs(f['effective_ctrl_mj_rad'][fm]-f['q_mj_pre_rad'][fm]),
        sensed_actual_mean_abs_rad=meanabs(c['sensed_logical_rad'][m]-mj_to_logical(c['actual_mj_post_rad'][m])),
        safe_increment_reversals=reversals(got[m]),profile_velocity_reversals=reversals(p['_v_after'][pm]),
        actual_velocity_reversals=reversals(f['q_mj_post_rad_s'][fm]))

def load_base():
    global BASE
    if BASE is None:
        path=HERE.parent/'turn_actionbank_review_20260908/reviewed_probe_action_response_bank.py'
        spec=importlib.util.spec_from_file_location('chain_frozen_helper',path);BASE=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=BASE;spec.loader.exec_module(BASE)
    return BASE

def run_cell(job,checkpoint,out):
    base=load_base();cell=job['cell'];n=job['ticks'];ident={};holder={}
    old_fresh,old_audit,old_settle=base._fresh_env,base._DynamicsAudit,base.SETTLE_TICK
    refrows=read(OLD/'full_recovered/baselines_frozen.json')+read(OLD/'full_recovered/straight_zero_off.json')['rollouts']
    ref=next(r for r in refrows if r['id']==job['id'])
    def fresh(*a,**kw):
        env,model,obs,onehot=old_fresh(*a,**kw)
        if any(getattr(env,k,False) for k in ('_cart_foot_active','_joint_action_box_active','_joint_action_bias_active')):
            raise ValueError('pinned affine action path not active')
        r=Recorder(env,base._digest);holder['recorder']=r
        from rl_move.sim.joint_task import _CENTER_RAD,_HALF_RAD
        r.metadata.update(affine_center_rad=vec(_CENTER_RAD),affine_half_range_rad=vec(_HALF_RAD))
        r.install();return env,Predictor(model,r),obs,onehot
    class ChainAudit(old_audit):
        def mj_step(self,m,d):return holder['recorder'].physics_step(super().mj_step,m,d)
    base._fresh_env=fresh;base._DynamicsAudit=ChainAudit
    if cell['wz']==0:base.SETTLE_TICK=201
    captures={600,638,680,718,619,657,699,737,n} if cell['wz'] else {n}
    spec=dict(checkpoint=checkpoint,cfg_set=read(OLD/'cfg_set.json'),seed=0,
        episode_seconds=15 if cell['wz']==0 else 10,
        required_identity={k:read(OLD/'pins.json')['identity'][k] for k in ('model_variant','model_nmesh','model_ngeom','model_mass_kg')})
    try:
        tr=base._rollout(spec,**cell,n_ticks=n,identity_out=ident,capture_ticks=captures)
        r=holder['recorder'];c,p,f,w=map(pack,(r.control,r.profile,r.physics,r.commands))
        validate_capture(c,p,f,w,n,r.metadata['substeps'])
        validate_timing(c,p,f,r.metadata)
        if tr['n_ticks_done']!=n or tr['fell']:raise ValueError('incomplete/terminated reference replay')
        arrays={k:tr[k] for k in TRACE_KEYS};arrays['servo_current_a']=c['servo_current_a']
        np.savez_compressed(out/(job['id']+'_chain.npz'),**{prefix+'__'+k:v for prefix,d in [('control',c),('profile',p),('physics',f),('commands',w)] for k,v in d.items()})
        np.savez_compressed(out/(job['id']+'_body.npz'),**arrays)
        reference=dict(np.load(OLD/'full_recovered/traces'/ref['trace_file']))
        parity=compare_arrays(arrays,reference)
        if trace_digest(tr)!=ref['trace_hash'] or array_digest(c['servo_current_a'])!=ref['current_trace_sha256']:
            raise ValueError('recorded body/current hash mismatch')
        statechecks={}
        if cell['wz']:
            bank=next(b for b in read(OLD/'reference_baselines.json')['baselines'] if b['cell']==cell)
            for tick in (600,638):
                statechecks[str(tick)]=base._state_match(tr['states'][tick],bank[f'prefix_{tick}'])
                statechecks[str(tick+80)]=base._state_match(tr['states'][tick+80],bank[f'endpoint_{tick}'])
            for selection in ref['selections']:
                statechecks[str(selection['p'])]=base._state_match(tr['states'][selection['p']],selection['prefix'])
                statechecks[str(selection['p']+80)]=base._state_match(tr['states'][selection['p']+80],selection['endpoint'])
        else:statechecks[str(n)]=base._state_match(tr['states'][n],ref['endpoint'])
        if not all(statechecks.values()):raise ValueError('existing full-state mismatch')
        row=dict(id=job['id'],cell=cell,status='VALID_OBSERVATION',ticks=n,identity=ident,metadata=r.metadata,
            body_array_parity=parity,full_state_parity=statechecks,full_states=tr['states'],
            endpoint_is_new_capture=bool(cell['wz']),reference_trace_hash=ref['trace_hash'],
            actual_trace_hash=trace_digest(tr),current_trace_sha256=array_digest(c['servo_current_a']),
            operation_counts=dict(policy=len(c['tick']),profile=len(p['tick']),physics=len(f['tick']),commands=len(w['tick'])),
            aggregates=[aggregate(c,p,f,0),aggregate(c,p,f,200)])
        dump(out/(job['id']+'.json'),row);return row
    except Exception:
        if 'recorder' in holder:
            r=holder['recorder'];dump(out/(job['id']+'_partial.json'),dict(control=r.control,current=r.row,profile=r.profile,physics=r.physics,commands=r.commands,metadata=r.metadata))
        raise
    finally:
        if 'recorder' in holder:holder['recorder'].restore()
        base._fresh_env,base._DynamicsAudit,base.SETTLE_TICK=old_fresh,old_audit,old_settle

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--checkpoint',required=True);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);started=time.time();rows=[]
    try:
        reg=read(HERE/'PREREGISTRATION.json');proto=Path(os.environ['HEXAPOD_PROTOTYPE_ROOT']).resolve()
        for path,expected in reg['artifact_hashes'].items():
            if sha(HERE.parent/path)!=expected:raise ValueError('artifact hash mismatch '+path)
        pins=read(OLD/'pins.json')
        for path,expected in {**pins['source_hashes'],**pins['asset_hashes'],**reg['additional_source_hashes']}.items():
            if sha(proto/path)!=expected:raise ValueError('runtime hash mismatch '+path)
        if sha(args.checkpoint)!=pins['checkpoint_sha256']:raise ValueError('checkpoint hash mismatch')
        dump(out/'execution_manifest.json',dict(started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
            runner_sha256=sha(__file__),preregistration=reg,runtime=str(proto),checkpoint=args.checkpoint,python=sys.version))
        for job in fixed_cells():
            row=run_cell(job,args.checkpoint,out);rows.append(row)
            print(json.dumps(dict(id=row['id'],status=row['status'],ticks=row['ticks'])),flush=True)
        if len(rows)!=6 or sum(r['ticks'] for r in rows)!=6020:raise ValueError('fixed matrix mismatch')
        summary=dict(status='VALID_OBSERVATION',rollouts=6,ticks=6020,wall_seconds=time.time()-started,
            ids=[r['id'] for r in rows],no_intervention=True,no_PPO=True,
            endpoint_limit='Arc755 full states are new captures; existing755 body/current and all earlier saved full states match exactly. Straight1500 endpoints match existing states.')
        dump(out/'summary.json',summary);print(json.dumps(summary),flush=True)
    except Exception:
        dump(out/'failure.json',dict(status='INVALID_OBSERVATION',traceback=traceback.format_exc(),completed_cells=[r['id'] for r in rows],wall_seconds=time.time()-started));raise

if __name__=='__main__':main()
