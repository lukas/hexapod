import io,json,zipfile,hashlib
from pathlib import Path
import torch
base=Path('/workspace/hexapod/hexapod_walker/prototype_sts3215/rl_move/sim/policies')
out={}
for arm,stem in [('on','c1'),('off','offctrl')]:
 root='ppo_goal_cw_walkscratch_easy0905_cartfoot_freshinit_'+stem+'_s7_acq1'
 paths=[base/(root+'.zip'),base/(root+'_torque1x_c1.zip')]
 ds=[];meta=[]
 for p in paths:
  if not p.is_file():raise SystemExit('missing '+p.name)
  with zipfile.ZipFile(p) as z:
   ds.append(torch.load(io.BytesIO(z.read('policy.pth')),map_location='cpu',weights_only=True))
   d=json.loads(z.read('data'));meta.append({'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'num_timesteps':d.get('num_timesteps')})
 a,b=ds; changed=[];equal=[];diff2=base2=0;num=0;mx=0
 for k in a:
  if k not in b or tuple(a[k].shape)!=tuple(b[k].shape):raise SystemExit('key/shape mismatch '+k)
  if k=='log_std':continue
  x=a[k].double();y=b[k].double();delta=y-x
  n=int(torch.count_nonzero(delta));num+=x.numel();diff2+=float(torch.sum(delta*delta));base2+=float(torch.sum(x*x));mx=max(mx,float(delta.abs().max()))
  if n:changed.append({'key':k,'changed_elements':n,'numel':x.numel(),'max_abs_delta':float(delta.abs().max())})
  else:equal.append(k)
 out[arm]={'checkpoints':meta,'non_log_std_numel':num,'non_log_std_changed_tensor_count':len(changed),'non_log_std_l2_delta':diff2**.5,'non_log_std_relative_l2':(diff2/base2)**.5,'non_log_std_max_abs_delta':mx,'changed_tensors':changed,'unchanged_tensors':equal,'log_std_parent':a.get('log_std').tolist(),'log_std_child':b.get('log_std').tolist()}
print(json.dumps(out))

