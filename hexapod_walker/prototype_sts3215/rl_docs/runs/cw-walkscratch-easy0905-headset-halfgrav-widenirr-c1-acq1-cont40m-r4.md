# cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1-acq1-cont40m-r4

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T12:10:17+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1-acq1

**hypothesis**: The widen-first widen2+irr composite (halfgrav) ACQ PASSed cleanly at 40M (23/24 gait_valid, 0 falls, no chronic leg, beats plain widen2 sibling) but has never been continued past 40M -- cleanest halfgrav composition champion still lacking cont40m, per the campaign's cleanliness-margin-predicts-endurance rule. (r4: r1 launch-syntax bug, r2/r3 hit a transient self-repair tar race under concurrent-cycle repo contention; retrying.)

**gate**: HARDENING PASS/HOLDS if gait_valid stays majority (>=18/24) at 80M cumulative with no NEW chronic single-leg pattern and 0 falls. HARDENING FAIL/ENTRENCHES if it drops below majority, a new chronic leg appears, or any fall appears.

**refused_reason**: hexapod-mjx-train-7 already runs cw-assistfade-rung2-anchorfade-s1-reseed8m — GPU pods host exactly one run; pick a free GPU pod.

