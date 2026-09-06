# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-imumount1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T08:54:19+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: nz5fs9oo

**hypothesis**: Plain English: does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24 clean, 0 falls) survive a nominal residual IMU MOUNT-ROTATION calibration error (dr.imu_mount_deg=10.0, distinct from imu_pos_xy_m/imu_pos_z_m translation already tested clean in imupos1x) with zero retraining? Last untested single-axis realism field in domain_rand.py's RandRanges besides leg_mass_jitter_pct (queued alongside this one).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg sacrifice and 0 falls -- shows IMU mount-rotation realism is free. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows a miscalibrated IMU mount angle is a binding constraint the estimator/DR-rung must budget real training time against.

**verdict**: CANARY PASS (mechanism-health) -- IMU mount-rotation-angle realism DR is free: PERFECT 24/24 gait_valid across all 4 panels (6/6/6/6), 0 falls/terminations, 0 sacrificed legs anywhere, slip/m 3.19-5.23 (in-band), reward still rising every quarter (52.9->237.5). Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_imumount1x_c1_gate/report.json, W&B nz5fs9oo. Why: closes the LAST of the 2 remaining zero-prior-canary DR axes identified by the 09-06 ~10:1x full domain_rand.py RandRanges field sweep (the other, legmass1x-c1, already PASSed) -- every RandRanges field now has at least one clean single-axis canary/PASS on record, the per-axis DR-restore information source is genuinely exhausted with NO remaining untested field. What's next: per QUEUE AIM's own STOP directive this does not license a cont40m (per-axis endurance funding is explicitly closed) -- no further axis-restore spend of any kind is justified; the campaign frontier stays composite/kick-ladder/contextual-rung work only.

