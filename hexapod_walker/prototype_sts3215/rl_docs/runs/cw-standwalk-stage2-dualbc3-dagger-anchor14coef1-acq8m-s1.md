# cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-acq8m-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQUISITION PASS

**created**: 2026-08-30T12:21:43+00:00

**pod**: hexapod-mjx-train-1

**steps**: 8000000

**parent**: cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-canary-s1

**wandb_id**: ac6gojxk

**hypothesis**: Seed1 companion of cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-acq8m (same recipe/question). Per this track's own repeated 2M-canary-PASS -> 8M-acquisition convention, does the walk quality keep compounding with 4x the budget on this seed too, now for the first time on a genuinely-repaired (DAgger) Stage-2 walk base?

**gate**: Same as the seed0 twin, read jointly: PASS if BOTH seeds show gait_valid stays >=5/6 zero-sac AND progress_ratio improves over the 2M snapshot (0.39 DR-0) with slip/m flat-or-improving. PARTIAL if gait_valid holds but progress flat. FAIL if gait_valid regresses below 5/6 or sacrificed legs reappear on either seed.

**verdict**: ACQUISITION PASS (own-scope, joint call with seed0 twin, both now PASS): det walk clean, gait_valid 8/8, sacrificed_legs=[] every episode, 0/8 terminations. progress_ratio med 0.4225 (range 0.418-0.425) -- UP from this lineage's own 2M canary snapshot (0.39), slip/m med ~2.37 (range 2.36-2.66) -- flat/slightly better than canary's 2.71. forward_dist_m ~0.97m/30s at 0.043 m/s, dir_err_mean 47-51deg (full-episode artifact, same low-speed-early-episode shape this campaign already names -- not scored). Sto mode: progress_ratio med 0.077 (up from the 2M canary's 0.04-0.06), slip/m med ~1.99 (down from 12-17) -- markedly cleaner than the canary snapshot, consistent with the std-anneal bundle (log-std-final -4.0) tightening exploration; gait_valid 8/8, sac=[], 0/8 terms in sto too. No anchor4-class catastrophe at any point (zero sacrificed legs across 16 det+sto episodes). Reward quarters [-83.7,-9.5,253.5,587.1] (ep_rew_mean 931) -- strong monotonic rise, no plateau/collapse, matches the seed0 twin's own trajectory shape. Meets the gate's own pre-registered PASS bar (gait_valid>=5/6 zero-sac AND progress_ratio improved with slip/m flat-or-better) on both det and sto. Evidence: /tmp/fastcheck_dualbc3_acq8m_s1_{det,sto}/report.json (controller-local diagnostic, checkpoint pushed+md5-verified to spare pod train-2, weights unchanged) -- independently corroborates the concurrent cycle's own cross-check numbers on this same checkpoint (their /tmp/fastcheck_acq8m_s1_{det,sto}/report.json on train-5: progress_ratio 0.423/slip 2.45 det -- matches to within noise). Ran because the ledger's own video-bearing gate/owncfg/mixedsession harness (watcher-auto-launched on train-1 at 13:08) is still genuinely mid-flight (~30min in of a historically 1.5-2h+ ETA), confirmed alive via ps (eval_checkpoint + eval_mixed_session processes actively progressing, video frames being written) -- not waited on, matches this track's repeated fast-read precedent. JOINT CALL: both seed0 (acq8m) and seed1 (acq8m-s1) now independently PASS on the gate's own paired-seed criteria -- the anchor14coef1-on-DAgger-repaired-base recipe keeps compounding skill cross-seed with 4x budget. Next (per the seed0 verdict's own registered next step, same for this seed): the real decision point is the eval_mixed_session sit->rise->walk->lower DONE-gate read, already running per-seed on train-0/train-1 (watcher auto-launch, ETA ~1.5-3h) -- no further RL budget committed to this lineage until that read lands.

