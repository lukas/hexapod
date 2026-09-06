# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T09:55:06+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis1x-c1

**hypothesis**: Plain English: allaxis1x-c1 (all ~30 nominal DR axes at once) FAILED with 5/24 real falls, but that arm bakes in the FULL-dose kick (walk_kick_prob=0.3), the one axis already known to fall in isolation (kick1x-c1). This control arm restores every OTHER axis identically but turns kick fully OFF (0.0, not even the safe half-dose) to test the cleanest possible read: do the other ~28 already-individually-clean axes compose without ANY kick confound at all? A companion allaxiskickhalf1x-c1 (kick=0.15) tests the same composite with kick still present at half dose; together the two arms bracket whether kick alone explains the composite failure or whether some OTHER pairwise interaction also contributes.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if the full 4-panel harness reaches 0 falls with aggregate gait_valid majority (>=18/24) and no new chronic single-leg sacrifice -- confirms kick was the SOLE broken ingredient in allaxis1x-c1's composite FAIL. FAIL/INFORMATIVE-NEGATIVE if a fall or gait_valid collapse still appears with kick fully off -- proves a DIFFERENT axis interaction is also broken, independent of kick.

