# cw-walkscratch-easy0905-headset-crossgrav-plainhead-abrupt-c1b-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T03:23:33+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-plainhead-abrupt-c1b

**wandb_id**: 2ngv7lap

**hypothesis**: Does the plain (never-composited) 3-way heading champion's clean 0.5g->1.0g abrupt transfer (23/24 gv, 0 falls, 2M canary) hold up at full 40M acquisition budget, matching the 6/6 healthy-source crossgrav siblings already confirmed (medhead/widen2c1/irracq1/irr2acq1/s1acq/s3acq)?

**gate**: PASS if gait_valid stays >= its own 2M canary (23/24) or degrades only mildly with no NEW chronically-sacrificed leg across the 40M run, 0 falls, slip/m flat-or-better. FAIL/MECHANISM if gait_valid collapses well below the canary (matching the already-seen ACQ-scale entrenchment regression pattern, e.g. irracq1-abrupt-c1-acq1's 23/24->14/24 drop) despite rising reward.

