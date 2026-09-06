# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-gyronoise1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T04:57:26+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-deadband1x-c1

**wandb_id**: oey1wf38

**hypothesis**: Restore nominal (1x) IMU gyro noise -- the easy0905 recipe has run with gyro_noise_deg_s=0 (zero sensor noise on the angular-rate reading) throughout the whole crossgrav campaign. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal (domain_rand.py default 0.5deg/s) gyro-sensing noise without retraining collapse? Isolated single-axis diagnostic, same template as the sibling deadband/latency/encoder-noise/tilt-noise DR-restoration arms.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on the zero-gyro-noise idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows gyro-noise realism is a binding constraint the DR-rung must budget real training time against.

