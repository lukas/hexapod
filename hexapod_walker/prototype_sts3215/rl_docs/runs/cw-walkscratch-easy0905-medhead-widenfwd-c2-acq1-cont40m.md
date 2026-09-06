# cw-walkscratch-easy0905-medhead-widenfwd-c2-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T07:40:40+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-medhead-widenfwd-c2-acq1

**wandb_id**: bfwfmdmo

**hypothesis**: Plain English: does the 2nd-seed medhead-widenfwd composition (just ACQ PASS at 40M, 21/24 gv, 0 falls) keep holding with another 40M of training (warm-started from the ACQ checkpoint, matching the endurance recipe already funded for seed-1's medhead-widenfwd-c1-acq1-cont40m and the other cont40m siblings)?

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) after the extra 40M with no NEW chronic single-leg pattern and 0 falls beyond the ACQ read's baseline. FAIL/ENTRENCHES if gait_valid drops toward minority or a chronic leg[1,4]-style pattern emerges.

