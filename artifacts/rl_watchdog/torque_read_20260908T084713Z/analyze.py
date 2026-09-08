from pathlib import Path
import json,statistics as st,hashlib,csv,io,datetime,subprocess
P=Path(__file__).resolve().parent
R={a:{k:json.loads((P/f'{a}_{k}_report.json').read_text()) for k in ['source','zero','child']} for a in ['on','off']}
L={a:json.loads((P/f'{a}_ledger.json').read_text()) for a in R}
W=json.loads((P/'weights.json').read_text())
recipes=json.loads((P/'recovery_recipes.json').read_text())
recovery=json.loads((P/'recovery.json').read_text())
groups=list(R['on']['source']['episodes'])
def cfg(args):return dict(args[i+1].split('=',1) for i,t in enumerate(args) if t=='--cfg-set')
def counts(es):return [sum(leg in e['sacrificed_legs'] for e in es) for leg in range(6)]
def summary(es):
 return {'episodes':len(es),'gait_valid':sum(e['gait_valid'] for e in es),'terminations':sum(e['terminated'] for e in es),'mean_slip_per_m':st.mean(e['slip_per_m'] for e in es),'mean_progress_ratio':st.mean(e['progress_ratio'] for e in es),'median_net_forward_m_s':st.median(e['forward_dist_m']/20 for e in es),'mean_episode_current_max_a':st.mean(e['cur_max_a'] for e in es),'worst_current_max_a':max(e['cur_max_a'] for e in es),'mean_episode_current_p95_a':st.mean(e['cur_p95_a'] for e in es),'sacrificed_leg_counts':counts(es),'sacrificed_leg_episodes':{str(j):[i for i,e in enumerate(es) if j in e['sacrificed_legs']] for j in range(6)}}
out={'read_completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Read-only six exact24-episode reports; corrected evalfix1 baselines only. No source/ledger/doc mutations, simulations, renders or PPO.','source_commit':'1e9736a846b3257bd899860fef80c2954990c654','runs':{},'paired_trained_slip':{},'pairing':{},'weights':W,'frozen_parent_provenance':{'checkpoint_sha256':recovery['checkpoint_sha256'],'only_source_cfg_change':recovery['only_source_cfg_change'],'protocol':recovery['protocol'],'source_checks':recovery['source_checks'],'matching_motor_model_and_packages':recovery['matching_motor_model_and_packages']}}
for a in R:
 run={'registered_gate':L[a]['gate'],'ledger_status_at_read':L[a]['status'],'ledger_verdict_at_read':L[a].get('verdict'),'requested_child_steps':L[a]['steps'],'reports':{},'health':{},'child_vs_zero':{}}
 for k,r in R[a].items():
  sm={g:summary(es) for g,es in r['episodes'].items()}
  assert sum(s['episodes'] for s in sm.values())==24
  run['reports'][k]={'source_path':(P/f'{a}_{k}_report.txt').read_text().splitlines()[0].lstrip('# '),'checkpoint':r['checkpoint'],'metadata':{x:y for x,y in r.items() if x not in ['episodes','checkpoint']},'groups':sm,'total_gait_valid':sum(s['gait_valid'] for s in sm.values()),'total_terminations':sum(s['terminations'] for s in sm.values())}
 source=run['reports']['source']
 assert source['total_gait_valid']==({'on':23,'off':19}[a])
 for k in ['zero','child']:
  new=run['reports'][k]
  patterns=[{'group':g,'leg':j,'source_count':source['groups'][g]['sacrificed_leg_counts'][j],'count':new['groups'][g]['sacrificed_leg_counts'][j],'episodes':new['groups'][g]['sacrificed_leg_episodes'][str(j)]} for g in groups for j in range(6) if new['groups'][g]['sacrificed_leg_counts'][j]>=3 and source['groups'][g]['sacrificed_leg_counts'][j]<3]
  movement=any(new['groups'][g]['median_net_forward_m_s']>=.03 for g in ['walk/det','walk/sto'])
  no_terms=new['total_terminations']==0
  gait_retained=new['total_gait_valid']>=source['total_gait_valid']
  verdict='HEALTH RETAINED' if no_terms and movement and gait_retained and not patterns else 'PARTIAL' if no_terms and movement else 'NEGATIVE HEALTH'
  run['health'][k]={'classification_under_original_gate':verdict,'zero_terminations':no_terms,'movement_floor':movement,'gait_count_retained':gait_retained,'new_recurring_patterns':patterns}
 for g in groups:
  z=run['reports']['zero']['groups'][g];c=run['reports']['child']['groups'][g]
  run['child_vs_zero'][g]={'mean_slip_delta':c['mean_slip_per_m']-z['mean_slip_per_m'],'mean_slip_ratio':c['mean_slip_per_m']/z['mean_slip_per_m'],'median_forward_speed_delta_m_s':c['median_net_forward_m_s']-z['median_net_forward_m_s'],'median_forward_speed_ratio':c['median_net_forward_m_s']/z['median_net_forward_m_s'],'mean_progress_delta':c['mean_progress_ratio']-z['mean_progress_ratio'],'gait_count_delta':c['gait_valid']-z['gait_valid']}
 rec=next(x for x in recipes if ('_offctrl_' in x['out'])==(a=='off'))
 zcfg=dict(x.split('=',1) for x in rec['cfg']);pcfg=cfg(rec['parent']['extra_args']);ccfg=cfg(L[a]['extra_args'])
 run['config_checks']={'zero_vs_child_equal':zcfg==ccfg,'source3x_to_zero1x_differences':{k:[pcfg.get(k),zcfg.get(k)] for k in pcfg.keys()|zcfg.keys() if pcfg.get(k)!=zcfg.get(k)},'frozen_parent_sha_matches_weight_read':rec['parent']['sha256']==W[a]['checkpoints'][0]['sha256']}
 txt=(P/f'{a}_metrics.txt').read_text();wb=json.JSONDecoder().raw_decode(txt[txt.index('{'):])[0]
 csvtxt=txt.split('## wandb_history.csv',1)[1].split('\n',1)[1]
 rows=list(csv.DictReader(io.StringIO(csvtxt.strip())))
 run['reward_trajectory']=[{'global_step':int(float(r['global_step'])),'reward_per_tick':float(r['optimization/reward_per_tick']),'ep_rew_mean':float(r['rollout/ep_rew_mean']),'ep_len_mean':float(r['rollout/ep_len_mean'])} for r in rows if r.get('optimization/reward_per_tick')]
 run['actual_child_steps']=wb['summary']['global_step']
 out['runs'][a]=run
 out['pairing'][a]={}
 for first,second in [('source','zero'),('zero','child')]:
  pp={}
  for g in groups:
   es1=R[a][first]['episodes'][g];es2=R[a][second]['episodes'][g]
   ignore={'torque_scale'} if first=='source' else set()
   pp[g]={'randomization_equal_except_intentional_torque':[ {k:v for k,v in e1['randomization'].items() if k not in ignore}=={k:v for k,v in e2['randomization'].items() if k not in ignore} for e1,e2 in zip(es1,es2)],'reset_jitter_summaries_equal':[e1.get('reset_start_jitter')==e2.get('reset_start_jitter') for e1,e2 in zip(es1,es2)],'reset_jitter_summaries':[e1.get('reset_start_jitter') for e1 in es1]}
  out['pairing'][a][first+'_to_'+second]=pp
for g in groups:
 on=out['runs']['on']['reports']['child']['groups'][g]['mean_slip_per_m']
 off=out['runs']['off']['reports']['child']['groups'][g]['mean_slip_per_m']
 out['paired_trained_slip'][g]={'on_mean':on,'off_mean':off,'ratio':on/off,'at_most_1p2':on/off<=1.2}
out['slip_parity_criterion']={'required_panels':3,'met_panels':sum(x['at_most_1p2'] for x in out['paired_trained_slip'].values()),'supported':sum(x['at_most_1p2'] for x in out['paired_trained_slip'].values())>=3}
out['conclusion']='The retention asymmetry exists zero-shot: corrected frozen ON parent at1x already retains23/24 gait with zero terminations; corrected OFF parent already has12/24 with the same new chronic walk/det leg4 pattern seen in its child. Both2M children preserve those exact gait classifications. There is no acquired gait recovery. Real policy/value weights moved, and slip changes are small and mixed: ON improves3/4 panel means but ordinary-det slip worsens2.1% with11.1% less net-forward speed; OFF improves2/4 slip means. This does not support the old catastrophic-zero-shot recovery narrative.'
out['pending']='None of the six required reports is pending after canonical staging; no additional evaluation is warranted for this finite read.'
out['limitations']=['Source hashes/config/package and motor parity come from published recovery receipts plus exact report metadata; no stale original ON baseline enters calculations.','All report summaries use seed0,DR0,20s,100Hz,policy_std rounded0.135 and MJX twin0meshes91geoms4.80573kg. Policy log_std tensors do differ slightly with training; full values are preserved in weights.json.','All reported reset/randomization comparisons are explicit. No early termination occurs, but summary equality still does not prove full reset vectors, hidden states or every RNG draw identical.','Six nominal deterministic repeats are one condition. This is one training-seed2M comparison, not a new mature-skill or hardware qualification.','Normal torque removes one idealization only:4096counts/s write-speed setting,1000acceleration,3.6deg/tick,no sensor noise,DR0 and100A configured safety limit remain.','Parent1x vs child1x reveals observed checkpoint changes after training, not a fully controlled decomposition of actor-weight versus exploration-std effects. Non-log-std movement rules out a std-only unchanged-policy explanation.','Close the finite2M read under the original plan. No automatic40M extension, new seed or dose grid follows.']
ref='e56e535f48ea53a096b7ddfed525839880d948ec'
repo=str(P.parents[2])
passages={}
for doc,spans in [('rl_docs/tracks/walkcurr/STATUS.md',[(44,65),(237,258)]),('rl_docs/SKILLS.md',[(1409,1413)])]:
 path='hexapod_walker/prototype_sts3215/'+doc
 content=subprocess.run(['git','show',ref+':'+path],cwd=repo,text=True,capture_output=True,check=True).stdout
 lines=content.splitlines()
 passages[doc]={'commit':ref,'sha256':hashlib.sha256(content.encode()).hexdigest(),'excerpts':[{'first_line':lo,'last_line':hi,'text':'\n'.join(lines[lo-1:hi])} for lo,hi in spans]}
out['doc_passages']=passages
out['correction_recommendation']={'history_preserving_action':'Append/prepend a dated corrected-zero-shot read in STATUS and a dated correction under the torque row in SKILLS; retain older entries as historical observations and link them to this correction. Do not edit completed cycle logs.','actual_false_claim':'Cycle20260908T082731 final summary at08:39:42 explicitly claims catastrophic zero-shot57–185/m and genuine2M recovery. Its old train5 evaluator lacked Cartesian decode. Withdraw that interpretation; the corrected ON zero-shot already passes retention.','current_docs_nuance':'Published e56e535f STATUS44–65 and237–258 and SKILLS1413 do NOT assert catastrophic recovery; they explicitly defer acquired-asymmetry claims because zero-shot was not run in that cycle. Update that pending caveat with the completed corrected result rather than falsely accusing those passages of the cycle-log claim.','replace_malformed_gait_tuples':'Use ON6/6,6/6,5/6,6/6; OFF source6/6,6/6,1/6,6/6 and zero/child0/6,6/6,0/6,6/6. Prior prose has spurious fifth numbers. Replace bit-identical fingerprint with same sacrificed-leg episode indices; other reported trajectory metrics differ.','proposed_text':'Corrected frozen-parent1x baselines (evalfix1, source matched to child evaluator) show ON health retention23/24 and OFF partial retention12/24 before retraining. Their2M children keep these gait counts and recurring-leg patterns, so the asymmetry is zero-shot, not an acquired gait recovery. Trained mean-slip ON/OFF ratios are0.840/0.910/0.871/0.891 (all4<=1.2). Small mixed slip/speed changes after real weight updates are reported separately. The earlier catastrophic ON baseline used the wrong action decoder and cannot support adaptation. This finite2M read is closed; no automatic extension.'}
out['evidence_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in P.iterdir() if p.is_file() and p.name not in ['summary.json','README.md']}
(P/'summary.json').write_text(json.dumps(out,indent=2)+'\n')
lines=['# Corrected seed7 torque read','',out['conclusion'],'','| Arm | Group | Gait source3x / zero1x / child1x | Mean slip/m source3x / zero1x / child1x | Net forward m/s zero1x / child1x |','|---|---|---|---|---|']
for a in ['on','off']:
 for g in groups:
  ss=[out['runs'][a]['reports'][k]['groups'][g] for k in ['source','zero','child']]
  lines.append(f"| {a.upper()} | {g} | "+' / '.join(str(s['gait_valid'])+'/6' for s in ss)+' | '+' / '.join(f"{s['mean_slip_per_m']:.3f}" for s in ss)+f" | {ss[1]['median_net_forward_m_s']:.4f} / {ss[2]['median_net_forward_m_s']:.4f} |")
lines+=['','All six reports contain exactly24 episodes and zero terminations. OFF adds recurring leg4 sacrifice in walk/det from0/6 source to6/6 in BOTH corrected zero-shot and trained child; its existing jitter-det leg4 count5/6 becomes6/6 in both. ON has no new recurring pattern and preserves the single jitter-det leg4 episode(index1).','',out['pending'],'','Original registered health and mean-slip gates are preserved verbatim in summary.json and PLAN.md. Both ON zero/child are HEALTH RETAINED; both OFF zero/child are PARTIAL. Trained mean-slip ratio<=1.2 is met in4/4 panels; this is separate from health and does not repair OFF retention.','','Normalized reward per tick at524,288→2,097,152steps: ON0.986866→1.125428; OFF1.033928→1.185338. Actual non-log-std tensor L2 changes ON0.476046/OFF0.525812; all16 tensors changed, including policy network and action head. Parent checkpoint SHA256 matches the preregistered files; children each contain2,097,152steps.','','Recommended history-preserving correction: '+out['correction_recommendation']['proposed_text'],'','Current STATUS/SKILLS already retain a no-adaptation caveat; the explicit catastrophic-recovery claim is in cycle082731. Exact published passage/line references and correction nuance are in summary.json.','']+['- '+s for s in out['limitations']]+['']
t='\n'.join(lines)
for a,b in [('at1x','at 1x'),('retains23','retains 23'),('has12','has 12'),('Both2M','Both 2M'),('improves3','improves 3'),('improves2','improves 2'),('worsens2','worsens 2'),('with11','with 11'),('source3x','source 3x'),('zero1x','zero 1x'),('child1x','child 1x'),('exactly24','exactly 24'),('leg4','leg 4'),('from0','from 0'),('to6','to 6'),('count5','count 5'),('becomes6','becomes 6'),('episode(index1)','episode (index 1)'),('in4/4','in 4/4'),('at524','at 524'),('ON0.','ON 0.'),('OFF0.','OFF 0.'),('OFF1.','OFF 1.'),('all16','all 16'),('contain2','contain 2')]:t=t.replace(a,b)
(P/'README.md').write_text(t)
print(json.dumps({'artifact':str(P),'health':{a:r['health'] for a,r in out['runs'].items()},'slip':out['paired_trained_slip'],'cfg':{a:r['config_checks'] for a,r in out['runs'].items()},'all_reported_draws_match':all(all(d['randomization_equal_except_intentional_torque']) and all(d['reset_jitter_summaries_equal']) for aa in out['pairing'].values() for bb in aa.values() for d in bb.values())},indent=2))
