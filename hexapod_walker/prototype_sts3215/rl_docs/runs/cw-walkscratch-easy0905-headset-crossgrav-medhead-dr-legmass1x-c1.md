# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-legmass1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T08:52:59+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: f9nrfyok

**hypothesis**: Plain English: does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24 clean, 0 falls) survive a nominal per-leg MASS-jitter asymmetry (dr.leg_mass_jitter_pct=0.10, distinct from the whole-body mass_scale already tested clean in mass1x-c1) with zero retraining? Last untested single-axis realism field in domain_rand.py's RandRanges besides imu_mount_deg (queued alongside this one).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg sacrifice and 0 falls -- shows per-leg mass asymmetry realism is free. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows leg-mass asymmetry is a binding constraint the DR-rung must budget real training time against.

**verdict**: CANARY PASS (mechanism-health) -- PERFECT 24/24 gait_valid across all 4 panels (walk/det 6/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6), sac=[] every single episode, 0 falls/terminations. slip/m 3.3-5.2, in-band with the other clean single-axis canaries. Contact sheet confirms upright six-leg tripod-phase cycling, visible forward translation, no drag/tip. Evidence: per-leg mass asymmetry (legmass1x) realism is free for the flagship champion at nominal dose. Why: this closes one of the final 2 untested RandRanges DR fields identified by the 10:17 exhaustive domain_rand.py sweep (the other, imumount1x-c1, has its own gate eval genuinely computing remotely -- left for the next reader). What's next: with this the per-axis DR-restore sweep is now fully exhaustive (every RandRanges field has a canary-clean read); no further per-axis canaries are runnable -- future spend stays on the QUEUE AIM frontier (composite realism, kick-dose ladder, torque-crutch removal, contextual DONE-gate rungs).

