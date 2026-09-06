# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-imumount1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T08:54:19+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: nz5fs9oo

**hypothesis**: Plain English: does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24 clean, 0 falls) survive a nominal residual IMU MOUNT-ROTATION calibration error (dr.imu_mount_deg=10.0, distinct from imu_pos_xy_m/imu_pos_z_m translation already tested clean in imupos1x) with zero retraining? Last untested single-axis realism field in domain_rand.py's RandRanges besides leg_mass_jitter_pct (queued alongside this one).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg sacrifice and 0 falls -- shows IMU mount-rotation realism is free. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows a miscalibrated IMU mount angle is a binding constraint the estimator/DR-rung must budget real training time against.

