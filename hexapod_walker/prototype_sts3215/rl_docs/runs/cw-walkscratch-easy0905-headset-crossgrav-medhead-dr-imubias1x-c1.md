# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-imubias1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T05:20:47+00:00

**pod**: hexapod-mjx-train-11

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: broa7joa

**hypothesis**: Restore nominal (1x) IMU calibration-error spread (imu_bias_deg roll/pitch bias + imu_mount_deg residual mounting rotation) -- the easy0905 recipe has trained with a PERFECTLY calibrated, perfectly-mounted IMU every episode (dr-scale=0.0 collapses both magnitudes to 0 when not explicitly overridden), unlike a real IMU which always has some residual mount rotation and calibration bias after assembly. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal own-DR IMU miscalibration (+-1deg roll/pitch bias, +-10deg mount rotation) without retraining collapse? Isolated single-axis diagnostic, same template as the sibling latency/deadband/torque/noise/mass/friction DR-restoration arms -- this is a BIAS/offset axis, distinct from the already-tested NOISE (variance) axes.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait tolerates IMU miscalibration. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows the perfect-IMU idealization is load-bearing, likely via roll/pitch-gated reward terms reading a biased signal.

