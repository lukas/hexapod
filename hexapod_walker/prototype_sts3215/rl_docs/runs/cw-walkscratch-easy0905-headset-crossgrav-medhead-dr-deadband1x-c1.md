# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-deadband1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T04:47:36+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: 07qw8xz0

**hypothesis**: Restore nominal (1x, non-randomized) actuator deadband -- the easy0905 recipe has run with deadband_scale=0 (ZERO dead-zone, fully idealized instant-exact command execution) throughout the whole crossgrav campaign. Same durability question as the sibling latency arm (medhead-dr-latency1x-c1), isolated to this single axis, off the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls).

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on the zero-deadband idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows deadband realism is a binding constraint the DR-rung must budget real training time against.

**verdict**: Restoring nominal (1x) actuator-deadband DR (dr.deadband_scale=0.5,1.8, vs the recipe's collapsed-to-0 default) on the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m) does NOT meaningfully break the gait. Evidence: harness 23/24 gait_valid (walk/det 6/6, walk/sto 6/6, startjitter/det 5/6 -- one non-chronic leg-5 flag, startjitter/sto 6/6), zero falls, no repeated/chronic leg across episodes, slip/prog bands flat vs the zero-DR champion. Reward rose cleanly through all 4 quarters (74->152->251->360) over the 2M canary budget. Why: deadband realism is not a binding constraint for this champion. Next: no further deadband-axis spend needed; closes the deadband cell of the single-axis DR-hardening battery.

