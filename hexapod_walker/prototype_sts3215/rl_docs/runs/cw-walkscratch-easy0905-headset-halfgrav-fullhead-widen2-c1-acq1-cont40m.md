# cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T12:13:41+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c1-acq1

**wandb_id**: aox3y4ss

**hypothesis**: The full 8-way-heading-incl-reversals widen2 champion (halfgrav, seed c1) ACQ PASSed cleanly at 40M (21/24 gait_valid, 0 falls); sibling c2b FAILED at cont40m, c3 is mid-cont40m elsewhere, c1 is the remaining endurance question. (multiple prior attempts this cycle hit a launch-syntax bug then a transient self-repair tar race then a pod collision; explicit free pod picked here.)

**gate**: HARDENING PASS/HOLDS if gait_valid stays majority (>=18/24) at 80M cumulative with no NEW chronic single-leg pattern and 0 falls. HARDENING FAIL/ENTRENCHES if it drops below majority, a new chronic leg appears, or any fall appears.

