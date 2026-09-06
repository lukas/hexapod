# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-deadband1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T08:08:13+00:00

**pod**: hexapod-mjx-train-9

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-deadband1x-c1

**hypothesis**: Plain English: does the nominal (1x) actuator-deadband spread (dr.deadband_scale=0.5,1.8) stay a clean walk with a real 40M training budget, not just a 2M canary glance? deadband1x-c1's own 2M canary was 23/24 (0 falls, one non-chronic leg-5 flag in startjitter/det) -- this is its first ACQ-scale confirmation, joining the sibling latency1x/torquefade/mass/friction/gains/geom/fault/extpush/actionnoise/contactstiff/noise/tiltnoise individual-axis durability batch.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show deadband realism needs real training exposure before being called safe.

**refused_reason**: hexapod-mjx-train-9 already runs cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-deadband1x-c1-acq1 — GPU pods host exactly one run; pick a free GPU pod.

