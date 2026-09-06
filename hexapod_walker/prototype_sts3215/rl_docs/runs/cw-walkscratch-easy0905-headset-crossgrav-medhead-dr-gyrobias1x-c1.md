# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-gyrobias1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T06:18:43+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-gyronoise1x-c1

**hypothesis**: Restore nominal (1x) IMU gyro RATE bias (dr.gyro_bias_deg_s=0.5deg/s, a per-episode constant angular-rate offset from imperfect gyro calibration -- distinct from the already-tested gyro NOISE axis (gyronoise1x, just PASSED) and from the attitude/rotation imu_bias_deg axis (imubias1x, already tested) -- the easy0905 recipe has run with gyro_bias_deg_s=0 throughout the whole crossgrav campaign. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal gyro rate-bias without retraining collapse?

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on the zero-gyro-bias idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows gyro rate-bias realism is a binding constraint the DR-rung must budget real training time against.

