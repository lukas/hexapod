# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis180

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T10:40:47+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8

**wandb_id**: rx6wrkz3

**hypothesis**: Plain English: same bisection as arm 1 (widenbis135)/arm 2 (widenbism135), arm 3/3: add ONLY 180deg (straight-back) to the ACQ-passed 5-way base, same s0 checkpoint/seed/budget/recipe. Isolates whether the direct-reverse command alone drives the front-pair[0,5] chronic-sacrifice shortcut widen8-acq1 showed 3/3 (plausible: 180 is the heading where the front pair is most symmetric/least load-bearing for a straight-back gait). Prediction-if-true: chronic front-pair (or similar) sacrifice reappears by 40M. Prediction-if-false: panel stays clean near s0-acq1's 21/24 baseline -- 180deg alone is not sufficient, implicating the two diagonals or an interaction of >=2 headings.

**gate**: PASS (heading exonerated) if 0 falls/24 AND gait_valid>=19/24 AND no chronic single-leg/pair sacrifice absent from s0-acq1's own clean panel. FAIL (heading implicated) if a chronic front-pair[0,5]-style (or any new persistent single-leg) sacrifice reappears, matching widen8-acq1's fingerprint.

