# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-noise1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T04:54:48+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: zky69ilf

**hypothesis**: Turn on the project's standard nominal sensor-noise levels (encoder/tilt/gyro), all currently pinned at 0 (noiseless sensors) throughout the whole easy0905 campaign -- the exact same encoder_noise_deg/tilt_noise_deg/gyro_noise_deg_s defaults already used as the 'own-DR' nominal elsewhere in the project (domain_rand.py), isolated as its own axis, off the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls).

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg sacrifice and 0 falls. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows sensor-noise realism is a binding constraint.

**verdict**: PASS/INFORMATIVE-POSITIVE: restoring nominal (1x) sensor-noise realism (encoder_noise_deg/tilt_noise_deg/gyro_noise_deg_s from the project's own domain_rand.py own-DR defaults, 0->0.09/0.3/0.5) on the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24 clean) costs almost nothing. Aggregate gait_valid 23/24 (walk/det 6/6, walk/sto 6/6, walk_startjitter/det 5/6 sac=[5] once non-chronic, walk_startjitter/sto 6/6), 0 falls/24, slip/m tightly banded 3.4-4.9 across every panel. Reward rising every quarter (67.8/138.9/245.4/346.7, still climbing at 2M canary budget). Contact sheet confirms clean six-leg cycling with body translation. Sensor-noise realism is NOT a binding constraint for this champion at nominal magnitude -- no hardening-rung budget needed for this axis.

