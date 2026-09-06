# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade2x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T04:50:51+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**hypothesis**: Fade the fixed 3x torque/battery assist crutch down to 2x (still a fixed, non-randomized single value, not yet the project's real 0.80-1.05 nominal range) -- the single lever CURRENT_TRUTHS/STATUS explicitly flagged as the key open DR-rung decision. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) tolerate losing a third of its assist without retraining collapse?

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg sacrifice and 0 falls. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows the 3x assist is load-bearing and any fade needs its own training rung (not a zero-retrain free lunch), and roughly by how much.

