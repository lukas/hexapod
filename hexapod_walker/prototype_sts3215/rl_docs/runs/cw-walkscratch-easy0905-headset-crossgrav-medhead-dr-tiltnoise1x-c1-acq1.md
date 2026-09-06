# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-tiltnoise1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T08:03:51+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-tiltnoise1x-c1

**hypothesis**: Plain English: does the nominal (0.3deg) IMU tilt-sensor noise axis stay a clean walk with a real 40M training budget, not just a 2M canary glance? tiltnoise1x-c1's own 2M canary was a PERFECT 24/24 (0 falls, sac=[] every episode) -- this is its first ACQ-scale confirmation, joining the sibling latency1x/torquefade/mass/friction/gains/geom/fault/extpush/actionnoise/contactstiff/deadband individual-axis durability batch.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show tilt-noise realism needs real training exposure before being called safe.

