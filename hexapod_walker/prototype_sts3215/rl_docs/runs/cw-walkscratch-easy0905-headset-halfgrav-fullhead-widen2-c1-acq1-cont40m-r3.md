# cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c1-acq1-cont40m-r3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T12:10:16+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c1-acq1

**hypothesis**: The full 8-way-heading-incl-reversals widen2 champion (halfgrav, seed c1) ACQ PASSed cleanly at 40M (21/24 gait_valid, 0 falls); sibling c2b FAILED at cont40m, c3 is mid-cont40m elsewhere, c1 is the remaining endurance question. (r3: r1 launch-syntax bug, r2 hit a transient self-repair tar race; retrying.)

**gate**: HARDENING PASS/HOLDS if gait_valid stays majority (>=18/24) at 80M cumulative with no NEW chronic single-leg pattern and 0 falls. HARDENING FAIL/ENTRENCHES if it drops below majority, a new chronic leg appears, or any fall appears.

**refused_reason**: hexapod-mjx-train-7 already runs cw-assistfade-rung2-anchorfade-s1-reseed8m — GPU pods host exactly one run; pick a free GPU pod.

