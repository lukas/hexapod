# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-latency1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T04:44:50+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: 5xqrfrqd

**hypothesis**: Restore nominal (1x, non-randomized) actuator latency -- the easy0905 recipe has run with latency_scale=0 (ZERO actuator delay, fully idealized) throughout the whole crossgrav campaign. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal nonzero actuator latency without retraining collapse?

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on the zero-latency idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows actuator latency realism is a binding constraint the DR-rung must budget real training time against, not a free realism add.

