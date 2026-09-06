# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-deadband1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T04:47:36+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**hypothesis**: Restore nominal (1x, non-randomized) actuator deadband -- the easy0905 recipe has run with deadband_scale=0 (ZERO dead-zone, fully idealized instant-exact command execution) throughout the whole crossgrav campaign. Same durability question as the sibling latency arm (medhead-dr-latency1x-c1), isolated to this single axis, off the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls).

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on the zero-deadband idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows deadband realism is a binding constraint the DR-rung must budget real training time against.

