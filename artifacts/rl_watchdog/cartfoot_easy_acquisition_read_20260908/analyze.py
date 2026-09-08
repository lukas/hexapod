from pathlib import Path
import json, hashlib, statistics, datetime
p=Path('/tmp/cartfoot-easy-acq-read-20260908T073843Z')
def parse_report(arm):
 t=(p/f'{arm}_report.txt').read_text()
 return json.JSONDecoder().raw_decode(t[t.index('{'):])[0]
def parse_ledger(arm):
 t=(p/f'{arm}_run.txt').read_text()
 return json.JSONDecoder().raw_decode(t[t.index('{'):])[0]
reports={a:parse_report(a) for a in ('on','off')}
ledgers={a:parse_ledger(a) for a in ('on','off','s10')}
def cfg(args):
 d={}
 for i,x in enumerate(args):
  if x=='--cfg-set':
   k,v=args[i+1].split('=',1);d[k]=v
 return d
cs={a:cfg(ledgers[a]['extra_args']) for a in ('on','off')}
cfgdiff={k:{a:cs[a].get(k) for a in cs} for k in cs['on'].keys()|cs['off'].keys() if cs['on'].get(k)!=cs['off'].get(k)}
meta_keys=['task','dr_scale','seed','model_source','model_variant','model_nmesh','model_ngeom','model_mass_kg','motor_contract','policy_std','start_jitter_panel']
out={'read_completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Read-only exact own 24-episode gates; no new rendering, simulations, launches, verdict changes or owner edits.','reports':{},'metadata_equal':{k:reports['on'].get(k)==reports['off'].get(k) for k in meta_keys},'on_metadata':{k:reports['on'].get(k) for k in meta_keys},'cfg_differences':cfgdiff,'groups':{},'pairing':{},'ledger':{a:{k:ledgers[a].get(k) for k in ['run','parent','steps','hypothesis','gate','created','status','checks']} for a in ledgers}}
for a,r in reports.items():
 path=p/f'{a}_report.json';path.write_text(json.dumps(r,indent=2)+'\n')
 out['reports'][a]={'native_query':ledgers[a]['run']+'_gate','source_path':(p/f'{a}_report.txt').read_text().splitlines()[0].lstrip('# '),'checkpoint':r['checkpoint'],'local_report_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'native_text_sha256':hashlib.sha256((p/f'{a}_report.txt').read_bytes()).hexdigest(),'episode_count':sum(map(len,r['episodes'].values()))}
for g,es in reports['on']['episodes'].items():
 row={}
 for a,r in reports.items():
  episodes=r['episodes'][g]
  row[a]={'n':len(episodes),'gait_valid':sum(e['gait_valid'] for e in episodes),'terminations':sum(e['terminated'] for e in episodes),'term_reasons':[e['term_reason'] for e in episodes if e['terminated']],'slip_per_m_mean':statistics.mean(e['slip_per_m'] for e in episodes),'slip_per_m_median':statistics.median(e['slip_per_m'] for e in episodes),'progress_ratio_mean':statistics.mean(e['progress_ratio'] for e in episodes),'netforward_speed_m_s_median':statistics.median(e['forward_dist_m']/20 for e in episodes),'invalid_gait_episodes':[{'index':i,'sacrificed_legs':e['sacrificed_legs']} for i,e in enumerate(episodes) if not e['gait_valid']]}
 row['on_over_off_mean_slip']=row['on']['slip_per_m_mean']/row['off']['slip_per_m_mean']
 out['groups'][g]=row
 out['pairing'][g]={'randomization_payload_matches':[e['randomization']==reports['off']['episodes'][g][i]['randomization'] for i,e in enumerate(es)],'reset_start_jitter_summary_matches':[e.get('reset_start_jitter')==reports['off']['episodes'][g][i].get('reset_start_jitter') for i,e in enumerate(es)],'reported_reset_start_jitter':[e.get('reset_start_jitter') for e in es],'on_unique_randomization_payloads':len({json.dumps(e['randomization'],sort_keys=True) for e in es})}
out['acquisition_movement_gate']={a:any(out['groups'][g][a]['netforward_speed_m_s_median']>=.03 for g in ['walk/det','walk/sto']) and out['groups']['walk/det'][a]['terminations']==0 for a in ['on','off']}
out['conclusion']='Both seed7 arms meet their registered movement/no-det-fall acquisition criterion. The predicted 3–10x Cartesian slip inflation is absent in this matched EASY seed7 comparison; ON mean slip is 1.2–5.6% lower across the four groups. This is descriptive acquisition parity, not a demonstrated general Cartesian advantage or current1x readiness.'
out['limitations']=['EASY recipe: fixed forward 0.06 m/s, 3x torque, no latency/deadband/sensor noise, DR scale0, mesh_mjx twin (0 meshes/91 geoms). No current1x/fullmesh/hardware claim.','Each nominal deterministic group repeats one condition six times, not six independent seeds. Only one matched training-seed acquisition pair is assessed here.','All 24 reported randomization payloads and all 12 start-jitter summaries match between arms. Summaries omit full reset offset vectors and hidden RNG/state, so this does not prove byte-exact full-state or every RNG draw parity. Own ON/OFF checkpoints differ by design.','Progress ratios 2.61–3.32 indicate acquisition with substantial overspeed relative to the fixed reference, not speed tracking qualification.','No generic hardening slip threshold or old retrofit 1.5x/3x rule is imported: the seed7 ledger explicitly makes slip the comparison headline, not its acquisition gate. The expected OFF5–6/m band was not a lower bound.','A movement gate pass does not independently authorize a further continuation; reward trajectory and next bounded hypothesis belong to active owner073301.']
out['visual_review']={'existing_images':['on_walk_det_0.png','off_walk_det_0.png'],'observed':'Both existing ten-frame deterministic gate contact strips show upright bodies and changing leg poses with visible net translation. No shown collapse/tip. Similar qualitative appearance; no visual superiority assertion.','limits':'Existing still contact strips are not a load/slip physics measurement and legacy capture is not used to infer speed.'}
out['s10']={'exact_native_report':'absent at 07:42:34 UTC','exact_worker_report':'absent at ~07:43 UTC','worker':'hexapod-mjx-train-7','gate_dir':'/workspace/prototype_sts3215/logs/ckpt_eval/cw_walkscratch_easy0905_base_cartfoot_fresh_s10_c1b_gate','observed_gate_pid':2949171,'gate_elapsed':'05:08 at ~07:44 UTC','state':'CPU eval_checkpoint gate active; recent walk_sto_5 artifacts timestamp07:43. Training/final-artifact finalizer completion is distinct from completion of this separate gate. No incomplete/session report substituted.','decision':'Not assessed until exact24-episode gate report exists.'}
(p/'summary.json').write_text(json.dumps(out,indent=2)+'\n')
lines=['# Independent EASY seed7 acquisition read','',out['conclusion'],'','| Group | ON/OFF gait | ON/OFF mean slip per m | Slip ratio | ON/OFF mean progress | ON/OFF median net forward m/s |','|---|---:|---:|---:|---:|---:|']
for g,d in out['groups'].items():
 a,b=d['on'],d['off']
 lines.append(f"| {g} | {a['gait_valid']}/6 vs {b['gait_valid']}/6 | {a['slip_per_m_mean']:.3f}/{b['slip_per_m_mean']:.3f} | {d['on_over_off_mean_slip']:.3f} | {a['progress_ratio_mean']:.3f}/{b['progress_ratio_mean']:.3f} | {a['netforward_speed_m_s_median']:.4f}/{b['netforward_speed_m_s_median']:.4f} |")
lines += ['','Both arms: zero terminations in all24 episodes. Gait totals ON23/24 vs OFF19/24, driven by deterministic start-jitter5/6 vs1/6. Failed gait reports identify sacrificed leg4 (plus leg1 in one OFF episode).','','Exact registered seed7 gate: '+ledgers['on']['gate'],'','Pairing: identical report metadata; same training seed7 and respective own2M canary checkpoints, then the same40M continuation budget. Only effective cfg-set differences are the three Cartesian box extents; all24 randomization summaries and all12 jitter summaries match. See summary.json for exact fields and per-episode jitter summaries.','','Visual check: '+out['visual_review']['observed'],'']+[f'- {s}' for s in out['limitations']]+['','Seed10 c1b: separate own gate is still computing (PID2949171, recent artifacts); no gate conclusion or substitution from session reports. Its older-family PASS-BAND criterion is preserved verbatim in summary.json.','']
(p/'README.md').write_text('\n'.join(lines))
empty=p/'s10_worker_exact_report.json'
if empty.exists() and empty.stat().st_size==0: empty.unlink()
print(json.dumps({'out':str(p),'cfg_differences':cfgdiff,'gate':out['acquisition_movement_gate'],'ratios':{g:r['on_over_off_mean_slip'] for g,r in out['groups'].items()}},indent=2))

