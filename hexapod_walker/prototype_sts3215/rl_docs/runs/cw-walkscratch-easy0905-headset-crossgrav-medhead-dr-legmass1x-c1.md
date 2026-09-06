# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-legmass1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T08:52:59+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: f9nrfyok

**hypothesis**: Plain English: does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24 clean, 0 falls) survive a nominal per-leg MASS-jitter asymmetry (dr.leg_mass_jitter_pct=0.10, distinct from the whole-body mass_scale already tested clean in mass1x-c1) with zero retraining? Last untested single-axis realism field in domain_rand.py's RandRanges besides imu_mount_deg (queued alongside this one).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg sacrifice and 0 falls -- shows per-leg mass asymmetry realism is free. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows leg-mass asymmetry is a binding constraint the DR-rung must budget real training time against.

