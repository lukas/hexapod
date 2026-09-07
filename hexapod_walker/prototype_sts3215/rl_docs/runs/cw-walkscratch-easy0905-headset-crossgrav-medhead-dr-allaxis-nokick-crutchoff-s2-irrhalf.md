# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-irrhalf

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: canary_fail

**created**: 2026-09-07T11:50:09+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-irr

**wandb_id**: qhmtszqz

**hypothesis**: Plain English: 2nd-seed twin of s1-irrhalf -- same jitter-amplitude-halving test (0.5->0.25) on the OTHER failed seed (s2-irr, also CANARY FAIL - MECHANISM at full amplitude), to get an n=2 read on whether reduced dose is composable rather than trusting one seed. Same seed/checkpoint/recipe as the failed s2-irr canary, only goal.walk_cmd_resample_jitter changed. Prediction-if-true: 0 falls/24, gait_valid>=18/24, matches s1-irrhalf if that one also passes -- confirms amplitude-doseresponse. Prediction-if-false: falls/chronic sacrifice reappear -- confirms amplitude is not the driver, jointly with s1-irrhalf's own read.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS (reduced dose composable) if 0 falls/24 and gait_valid>=18/24 with no new chronic single-leg/pair sacrifice absent from this seed's own acq1 clean panel. FAIL (amplitude not the driver) if the same tilt_roll-style fall or a new chronic sacrifice reappears at half amplitude, matching the 0.5-jitter canary's own fingerprint.

**verdict**: CANARY FAIL - MECHANISM: 2nd seed confirms s1-irrhalf's finding -- halving the irr-timing jitter amplitude does NOT clear the crutch-off full-DR composite's jitter+push interaction. Result: 2 real falls (walk/sto ep4 term_reason=tilt_roll -- the IDENTICAL episode index s1-irrhalf also fell at, and NEW walk_startjitter/sto ep0 term_reason=tilt_roll, a mode the parent baseline never fails in), plus new chronic sacrifices in walk/det (sac[5], 1/6) and walk_startjitter/sto (sac[0] on a non-terminated episode too). gait_valid 21/24 total but via a qualitatively different, worse composition than the parent crutchoff-s2-acq1 baseline (21/24, sacrifice confined to walk_startjitter/sto leg0/leg5, 0 falls). This CLOSES the amplitude-halving mitigation 2/2 CANARY FAIL: both seeds reproduce the same tilt_roll fall at the same episode index seen at full amplitude, decisive not noise -- the jitter+push interaction persists even at half dose; a structurally different mitigation (e.g. suppress resample jitter during an active push window) is needed before any further irr-timing spend on this composite. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_allaxis_nokick_crutchoff_s2_irrhalf_gate/report.json vs ..._crutchoff_s2_acq1_gate/report.json. W&B qhmtszqz.

