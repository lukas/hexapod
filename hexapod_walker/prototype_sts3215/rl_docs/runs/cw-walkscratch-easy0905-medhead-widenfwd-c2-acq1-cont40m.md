# cw-walkscratch-easy0905-medhead-widenfwd-c2-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T07:35:25+00:00

**pod**: hexapod-mjx-train-0

**steps**: 80000000

**parent**: cw-walkscratch-easy0905-medhead-widenfwd-c2-acq1

**hypothesis**: Plain English: does the 2nd-seed medhead-widenfwd composition (just ACQ PASS at 40M, 21/24 gv, 0 falls) keep holding with double the training budget (80M total), matching the endurance read already funded for seed-1 (medhead-widenfwd-c1-acq1-cont40m) and the other cont40m siblings (irrfwd-c1, widen2c1-irrfwd)?

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 80M with no NEW chronic single-leg pattern and 0 falls beyond the ACQ read's baseline. FAIL/ENTRENCHES if gait_valid drops toward minority or a chronic leg[1,4]-style pattern emerges.

**refused_reason**: steps 80000000 > max_steps_per_run 40000000

