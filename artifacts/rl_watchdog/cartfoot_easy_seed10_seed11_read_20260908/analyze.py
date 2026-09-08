from pathlib import Path
import json, hashlib, statistics as st, datetime, csv, io, subprocess
P=Path(__file__).resolve().parent
keys=['s10on','s10off','s11on','s11off']
R={k:json.loads((P/f'{k}_report.json').read_text()) for k in keys}
L={k:json.loads((P/f'{k}_ledger.json').read_text()) for k in keys}
C={k:json.loads((P/f'{k}_cfg.json').read_text()) for k in keys}
A={k:json.loads((P/f'{k}_params.json').read_text()) for k in keys}
B={k:json.loads((P/f'{k}_parent.json').read_text()) for k in keys}
groups=list(R[keys[0]]['episodes'])
out={'read_completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Exact own _gate reports only; read-only, no replays/renders/launches/verdict changes.','runs':{},'pairs':{},'prior_seed7':{},'source_audit':{}}
for k in keys:
 r,l=R[k],L[k]
 txt=(P/f'{k}_metrics.txt').read_text()
 w=json.JSONDecoder().raw_decode(txt[txt.index('{'):])[0]
 csvtxt=txt.split('## wandb_history.csv',1)[1].split('\n',1)[1]
 rows=list(csv.DictReader(io.StringIO(csvtxt.strip())))
 rewards={}
 for x in rows:
  if x.get('global_step') and x.get('rollout/ep_rew_mean'):rewards[int(float(x['global_step']))]=float(x['rollout/ep_rew_mean'])
 trend=sorted(rewards.items())
 sm={}
 for g,es in r['episodes'].items():
  assert len(es)==6
  sm[g]={'n':6,'gait_valid':sum(e['gait_valid'] for e in es),'terminations':sum(e['terminated'] for e in es),'term_reasons':[e['term_reason'] for e in es if e['terminated']],'mean_slip_per_m':st.mean(e['slip_per_m'] for e in es),'median_slip_per_m':st.median(e['slip_per_m'] for e in es),'mean_progress_ratio':st.mean(e['progress_ratio'] for e in es),'median_netforward_m_s':st.median(e['forward_dist_m']/20 for e in es),'invalid_gait':[{'episode':i,'sacrificed_legs':e['sacrificed_legs']} for i,e in enumerate(es) if not e['gait_valid']]}
 assert sum(x['n'] for x in sm.values())==24
 meta={a:b for a,b in r.items() if a not in ['checkpoint','episodes']}
 bargs=B[k]['extra_args']
 out['runs'][k]={'run':l['run'],'query':l['run']+'_gate','exact_source':(P/f'{k}_report.txt').read_text().splitlines()[0].lstrip('# '),'checkpoint':r['checkpoint'],'metadata':meta,'groups':sm,'total_gait':sum(x['gait_valid'] for x in sm.values()),'total_terminations':sum(x['terminations'] for x in sm.values()),'registered_criterion':l['gate'],'registered_hypothesis':l['hypothesis'],'ledger_status_at_read':l['status'],'requested_continuation_steps':l['steps'],'wandb_finished_step':w['summary']['global_step'],'own_parent':l['parent'],'parent_requested_steps':B[k]['steps'],'parent_has_init_from':'--init-from' in bargs,'train_seed':A[k]['--seed'],'init_from':A[k].get('--init-from'),'training_commit':l.get('checks',{}).get('code_sha_pod'),'parent_commit':B[k].get('checks',{}).get('code_sha_pod'),'movement_diagnostic_met':any(sm[g]['median_netforward_m_s']>=.03 for g in ['walk/det','walk/sto']) and sm['walk/det']['terminations']==0,'reward_tail':{'distinct_steps':len(trend),'first':trend[0] if trend else None,'last':trend[-1] if trend else None,'first3_mean':st.mean(x[1] for x in trend[:3]) if trend else None,'last3_mean':st.mean(x[1] for x in trend[-3:]) if trend else None,'points':trend},'evidence_sha256':{f'{k}_{t}'+ext:hashlib.sha256((P/(f'{k}_{t}'+ext)).read_bytes()).hexdigest() for t,ext in [('report','.json'),('report','.txt'),('ledger','.json'),('parent','.json'),('metrics','.txt'),('walk_det_0','.png')]}}
for seed in ['s10','s11']:
 on,off=seed+'on',seed+'off'
 pair={'cfg_set_differences':{k:{'on':C[on].get(k),'off':C[off].get(k)} for k in C[on].keys()|C[off].keys() if C[on].get(k)!=C[off].get(k)},'non_identity_argument_differences':{k:{'on':A[on].get(k),'off':A[off].get(k)} for k in A[on].keys()|A[off].keys() if k not in ['--notes','--out-name','--init-from'] and A[on].get(k)!=A[off].get(k)},'metadata_equal':out['runs'][on]['metadata']==out['runs'][off]['metadata'],'groups':{}}
 for g in groups:
  eo,ef=R[on]['episodes'][g],R[off]['episodes'][g]
  pair['groups'][g]={'on_off_mean_slip_ratio':out['runs'][on]['groups'][g]['mean_slip_per_m']/out['runs'][off]['groups'][g]['mean_slip_per_m'],'reported_randomization_equal':[a['randomization']==b['randomization'] for a,b in zip(eo,ef)],'reported_reset_jitter_equal':[a.get('reset_start_jitter')==b.get('reset_start_jitter') for a,b in zip(eo,ef)],'reset_jitter_summaries':[a.get('reset_start_jitter') for a in eo],'unique_nominal_randomization_payloads':len({json.dumps(e['randomization'],sort_keys=True) for e in eo})}
 out['pairs'][seed]=pair
repo=str(P.parents[2])
for title,first,second in [('seed10_training',L['s10on']['checks']['code_sha_pod'],L['s10off']['checks']['code_sha_pod']),('seed11_training',L['s11on']['checks']['code_sha_pod'],L['s11off']['checks']['code_sha_pod']),('seed10_parent',B['s10on']['checks']['code_sha_pod'],B['s10off']['checks']['code_sha_pod'])]:
 result=subprocess.run(['git','diff','--name-only',first,second,'--','hexapod_walker/prototype_sts3215'],cwd=repo,text=True,capture_output=True,check=True)
 names=result.stdout.splitlines()
 out['source_audit'][title]={'from':first,'to':second,'changed_prototype_paths':names,'training_sim_or_config_source_changed':any('/rl_move/sim/' in n or n.endswith('/config.yaml') for n in names)}
prior=P.parent/'cartfoot_easy_acquisition_read_20260908/summary.json'
old=json.loads(prior.read_text())
out['prior_seed7']={'source':str(prior),'sha256':hashlib.sha256(prior.read_bytes()).hexdigest(),'gait_on_off':[23,19],'terms_on_off':[0,0],'group_slip_ratios':{g:d['on_over_off_mean_slip'] for g,d in old['groups'].items()}}
out['conclusion']='The absence of several-fold Cartesian slip inflation repeats across all three fresh-init EASY seeds7/10/11. This supports acquisition viability at the tested Cartesian dose; it does not establish a general slip benefit, consistent deterministic six-leg gait, or current1x capability.'
out['criterion_interpretation']={'seed11':'Both arms meet their own numeric acquisition criterion (>=0.03 m/s median net forward in walk/det or sto and zero det falls). ON23/24 versus OFF12/24 gait is a real descriptive difference, but gait was not a separate hardening bar in this registered criterion.','seed10':'Both arms walk with zero falls and stochastic gait12/12; both deterministic panels have gait0/12. Their registered PASS-BAND invokes gait_valid/no-falls/slip comparable to established base-family walking, without a numeric pass fraction. Thus movement/slip-band parity is supported, while clean deterministic six-leg qualification is not. Preserve this qualification alongside the owner recorded ON ACQ PASS - PARITY (BAND-MATCH, non-blocking det quirk); this audit does not mutate that verdict.'}
out['pairing_caveats']=['Each pair has the same seed, 2M fresh-init parents without --init-from, own-checkpoint40M continuation, and only three Cartesian cfg-set differences. Seed10 parent ledger names base-s0 as recipe parent but command has no --init-from: it is not mature-checkpoint transfer.','All four final W&B steps are read explicitly; do not silently rewrite 40M requested continuation to the hypothesis narrative +38M.','Reported randomization matches24/24 within each pair and jitter summaries match12/12. Full offset vectors and hidden RNG/state are absent, so this is reported-draw pairing, not byte-exact full-state proof.','Six nominal deterministic repetitions are one condition, not six independent samples. Only three training seeds total; no inferential significance or pooled144-episode claim.','Training commits differ but compared prototype deltas contain no training simulator or config source changes. This does not independently hash uncommitted live pod source or every loaded asset.','All gates use the EASY3x-torque, no-latency/deadband/sensor-noise, DR0, fixed-forward0.06m/s, 100Hz, mesh_mjx0-mesh91-geom4.80573kg recipe. Progress ratios2.48–3.07 reflect overspeed, not tracking qualification.','No session/hardening reports or old retrofit1.5x/3x slip criteria enter the acquisition interpretation.']
out['visual_review']={'existing_gate_images':[k+'_walk_det_0.png' for k in keys],'observed':'All four existing deterministic contact strips were viewed. Bodies stay upright across shown frames with translation and changing leg poses; the reports quantify sacrificed-leg failures. No clean deterministic six-leg or measured slip claim is inferred from still images.','no_new_render_or_simulation':True}
out['next_implication']='The repeated EASY result leaves a meaningful orthogonal question of torque dependence, so a predeclared matched fixed1x test remains scientifically justified. Do not claim readiness at1x, or expand EASY training simply because numerical acquisition passed. Retain the active owners and existing bounded continuation decisions.'
(P/'summary.json').write_text(json.dumps(out,indent=2)+'\n')
lines=['# Exact EASY acquisition repeat-seed audit','',out['conclusion'],'','| Seed | Group | ON/OFF gait | ON/OFF mean slip/m | Ratio | ON/OFF mean progress | ON/OFF median forward m/s |','|---|---|---:|---:|---:|---:|---:|']
for seed in ['s10','s11']:
 for g in groups:
  a=out['runs'][seed+'on']['groups'][g];b=out['runs'][seed+'off']['groups'][g];q=out['pairs'][seed]['groups'][g]
  lines.append(f"| {seed[1:]} | {g} | {a['gait_valid']}/6 vs {b['gait_valid']}/6 | {a['mean_slip_per_m']:.3f}/{b['mean_slip_per_m']:.3f} | {q['on_off_mean_slip_ratio']:.3f} | {a['mean_progress_ratio']:.3f}/{b['mean_progress_ratio']:.3f} | {a['median_netforward_m_s']:.4f}/{b['median_netforward_m_s']:.4f} |")
lines+=['','Zero terminations across each of the four24-episode reports. Seed10 gait totals12/24 ON and12/24 OFF; seed11 totals23/24 ON and12/24 OFF. These totals include repeated nominal deterministic episodes, not independent trials.','',out['criterion_interpretation']['seed11'],'',out['criterion_interpretation']['seed10'],'','Registered criteria (verbatim from native ledger reads):','']
for k in keys: lines+=['- '+k+': '+out['runs'][k]['registered_criterion']]
lines+=['','Pairing and limits:','']+['- '+x for x in out['pairing_caveats']]+['','Existing gate strips were viewed. '+out['visual_review']['observed'],'',out['next_implication'],'','Exact reports, ledger/parent snapshots, cached metrics, native video path metadata, image hashes and repeatable analysis are stored alongside this note. No owner verdict, code, launch or active process was changed.','']
text='\n'.join(lines)
for a,b in [('seeds7/10/11','seeds 7/10/11'),('Seed10','Seed 10'),('seed11','seed 11'),('four24','four 24'),('totals12','totals 12'),('totals23','totals 23'),('and12','and 12'),('own-checkpoint40M','own-checkpoint 40M'),('matches24','matches 24'),('match12','match 12'),('EASY3x','EASY 3x'),('mesh_mjx0','mesh_mjx 0'),('91-geom4','91-geom 4'),('DR0','DR 0'),('fixed-forward0','fixed-forward 0'),('ratios2','ratios 2'),('at1x','at 1x'),('fixed1x','fixed 1x')]:text=text.replace(a,b)
(P/'README.md').write_text(text)
print(json.dumps({'path':str(P),'ratios':{s:{g:d['on_off_mean_slip_ratio'] for g,d in p['groups'].items()} for s,p in out['pairs'].items()},'reward_tail':{k:{a:r['reward_tail'][a] for a in ['first','last','first3_mean','last3_mean']} for k,r in out['runs'].items()},'steps':{k:r['wandb_finished_step'] for k,r in out['runs'].items()},'argdiff':{s:p['non_identity_argument_differences'] for s,p in out['pairs'].items()}},indent=2))
