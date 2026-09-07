# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbism135

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T10:37:00+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8

**wandb_id**: c3hqpdus

**hypothesis**: Plain English: same bisection as arm 1 (see widenbis135), arm 2/3: add ONLY -135deg (the mirror rear-diagonal heading) to the ACQ-passed 5-way base, same s0 checkpoint/seed/budget/recipe. Isolates whether the LEFT rear-diagonal alone (vs. the right one or straight-back) drives the front-pair[0,5] chronic-sacrifice shortcut widen8-acq1 showed 3/3. Prediction-if-true: chronic front-pair (or similar) sacrifice reappears by 40M. Prediction-if-false: panel stays clean near s0-acq1's 21/24 baseline -- -135deg alone is not sufficient.

**gate**: PASS (heading exonerated) if 0 falls/24 AND gait_valid>=19/24 AND no chronic single-leg/pair sacrifice absent from s0-acq1's own clean panel. FAIL (heading implicated) if a chronic front-pair[0,5]-style (or any new persistent single-leg) sacrifice reappears, matching widen8-acq1's fingerprint.

