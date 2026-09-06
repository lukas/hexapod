# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-imupos1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T06:11:09+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**hypothesis**: Restore nominal (1x) IMU-MOUNT-POSITION spread (imu_pos_xy_m/imu_pos_z_m: the physical IMU could be bolted anywhere from the chassis deck to a raised platform; an off-center IMU feels lever-arm accelerations whenever the body rotates, corrupting the accel-derived tilt specifically while leaning -- distinct from the already-tested imu_bias_deg/imu_mount_deg ROTATION-error axis in imubias1x-c1) -- the easy0905 recipe has trained with the IMU pinned at the exact modeled origin every episode (dr-scale=0.0 collapses this to 0 when not explicitly overridden). Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal own-DR IMU-position spread (+-70mm xy, -20/+100mm z) without retraining collapse? Isolated single-axis diagnostic, same template as the sibling latency/deadband/torque/noise/mass/friction/gain/geometry/zerobias/fault/imubias DR-restoration arms.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on the fixed-IMU-position idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows IMU-mount-position realism is a binding constraint the DR-rung must budget real training time against, likely via corrupted lean-detection during actual rotation.

**refused_reason**: hexapod-mjx-train-1 code marker e55ab8a51e89b0725b33a997b00d2ed059834c85-dirty != local HEAD e55ab8a51e89b0725b33a997b00d2ed059834c85 and the delta is not benign-orchestrator-only. Sync first: snapshot.sh --sync hexapod-mjx-train-1 (and snapshot/commit before that if the tree is dirty).

