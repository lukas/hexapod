# cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-acq8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-08-30T12:18:55+00:00

**pod**: hexapod-mjx-train-0

**steps**: 8000000

**parent**: cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-canary

**wandb_id**: rqd38e6n

**hypothesis**: Plain English: the dualbc3_dagger-based anchor14coef1 2M canary just PASSED cleanly on a genuinely-walking base (both seeds: det walk gait_valid 8/8, zero sacrificed legs, zero falls, progress_ratio 0.28/0.39 -- well above the 0.10-0.18 band the same recipe showed on the OLD stotight45 teacher). Per this track's own repeated 2M-canary-PASS -> 8M-acquisition convention (bcanchor1/3, anchor14-walkretaincoef1-rescue-acq8m, meshref-8m), does the walk quality keep compounding with 4x the budget the way it did for every prior instance of this exact convention, now for the first time on a genuinely-repaired (DAgger, not raw BC) Stage-2 walk base?

**gate**: ACQUISITION READ (paired 2-seed call, same convention as anchor14-walkretaincoef1-rescue-acq8m): compare 8M det walk DR-0 gate + own-DR against this run's own 2M canary snapshot (prog_ratio med 0.28 DR-0, slip/m med 3.39, gait_valid 8/8 sac=[]). PASS if BOTH seeds show gait_valid stays >=5/6 with zero/near-zero sacrificed legs AND progress_ratio improves (not just noise) over the 2M snapshot with slip/m flat-or-improving. PARTIAL if gait_valid holds but progress_ratio is flat. FAIL only if gait_valid regresses below 5/6 or sacrificed legs reappear on either seed (the anchor4-class catastrophe returns under more training).

**verdict**: ACQUISITION PASS (own-scope, per the gate's own pre-registered criteria): det walk clean, gait_valid 8/8, sacrificed_legs=[] every episode, 0/8 terminations. progress_ratio med 0.429 (min0.427/max0.43) -- UP from this lineage's own 2M canary snapshot (0.28), slip/m med 2.55 -- DOWN/better than canary's 3.39. forward_dist_m ~0.98m/30s at 0.042 m/s, course_err_1s med 6.0deg (clean short-window heading tracking despite a 43.6deg full-episode direction_err_mean -- the same low-speed-early-episode artifact this campaign already names, not a wrong-way walk). Sto mode weaker but still net-forward and zero-fall/zero-sac: progress_ratio med 0.078, slip/m med 10.9, forward_dist_m ~0.18m/30s (softer than det, expected given the std-anneal bundle, and actually better than the 2M canary's own sto numbers 0.04-0.06/13-17). Reward quarters [-62.5,-57.0,239.2,590.2] over the 8M budget (ep_rew_mean 684) -- strong monotonic rise, no plateau/collapse. Cross-checked the seed1 twin (acq8m-s1, also finished, own verdict pending its own concurrently-claimed cycle) on the same fast protocol as an informal joint read: det gait_valid 8/8 sac=[] 0 terms, progress_ratio med 0.423 (up from 0.39), slip/m med 2.45 (down from 2.71) -- same improving pattern, meets the gate's paired-seed PASS bar on both axes for both seeds. Evidence: /tmp/fastcheck_acq8m_s{0,1}_{det,sto}/report.json -- controller-local diagnostic on spare pods (train-4/train-5, checkpoint pushed+md5-verified, weights unchanged), run because the ledger's own video-bearing gate/owncfg/mixedsession harness (watcher-auto-launched on train-0/train-1 at 13:02/13:07) is still genuinely mid-flight (~30min in of a historically 1.5-2h ETA for this exact recipe) -- not waited on, matches this track's repeated fast-read-while-harness-runs precedent. Why this matters: confirms the anchor14coef1-on-DAgger-repaired-base recipe keeps compounding skill with 4x budget (0.28/0.39->0.42/0.43 progress, slip flat-or-better), same shape as the anchor14-walkretaincoef1-rescue-acq8m precedent on the OLD teacher. Next: per that exact precedent, the real decision point is the eval_mixed_session sit->rise->walk->lower DONE-gate read, already running per-seed on train-0/train-1 (watcher auto-launch, ETA ~1.5-3h) -- no further RL budget committed to this lineage until that read lands.

