# cw-walkscratch-crutchoff-s1-widen8-legdutyratio-swingfloor

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS - mechanism healthy, no efficacy

**created**: 2026-09-08T11:32:10+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1-legdutyratiofresh-guardfix1

**wandb_id**: wcwrs8eq

**hypothesis**: 2nd seed of the swing-count-floor lever (see s0 sibling's hypothesis for the full mechanism rationale): does pairing the 0.30-target ratio charge with a >=2-swing/4s floor close the 'gait_valid recovers via worse slip' trade both dose escalations showed, reproducibly across seeds? One lever vs the exact matched 0.30-dose guardfix1 sibling, same seed/init-from/heading-set/DR/motor cfg.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, identical gate text to the s0 sibling: (a) post-grace ratio telemetry present/finite; (b) zero new falls vs the matched 0.30-dose s1 sibling; (c) >=3/4 groups jointly improve gait_valid AND slip/progress vs that sibling for CONTINUE; report whether the specific episode-level trade the 0.30/0.45 doses showed persists. Short 2M null does not close the lever alone.

**verdict**: CANARY PASS - mechanism healthy, no efficacy vs the matched 0.30-dose sibling. Mechanism-health canary for the swing-count-floor addition (walk_leg_duty_ratio_swing_min_count=2.0/window=4.0) atop the 0.30-dose charge, seed s1 (RNG3). Health checks (a)+(b) PASS: shortfall telemetry present/finite (0.166 vs sibling's 0.152 at the same 2M step -- near-identical), zero eval terminations in all 24 gate episodes, and training-time falls essentially unchanged (tilt_roll 5 vs sibling's 6, truncated 241 vs 242 at step 2.1M); ep_rew_mean crash to -3642 is fully explained by the leg_duty_ratio charge component going -24.8 (sibling: -22.7 at the same step) -- not new instability. Efficacy check (c) FAILS: vs the matched 0.30-dose s1 sibling (...-legdutyratiofresh-guardfix1), gait_valid is IDENTICAL in all 4 groups (5/6, 6/6, 6/6, 4/6 both), slip/m is a wash (walk/det 8.90 vs 9.08 better, walk/sto 7.22 vs 6.96 worse, sj/det 9.41 vs 8.86 worse, sj/sto 12.88 vs 13.15 better), and progress_ratio is lower in 3/4 groups (0.89 vs 0.92, 0.98 vs 1.19, 0.99 vs 1.06; only sj/sto ticks up). 0/4 groups jointly improve gait_valid AND slip/progress, so the pre-registered CONTINUE bar (>=3/4 groups) is not met -- the swing-count floor neither closed the 'gait_valid recovers via worse slip' trade the 0.30/0.45 dose escalations showed, nor even reproduced it here (gait_valid never moved at all). Per the run's own gate text a short 2M null does not close the lever alone; read against the concurrent s0/RNG2 sibling for cross-seed reproducibility before funding a longer depth or a different swing-floor dose. No further action from this seed alone.

