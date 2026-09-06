# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-zerobiasframe1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T08:15:38+00:00

**pod**: hexapod-mjx-train-10

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-zerobiasframe1x-c1

**hypothesis**: Plain English: does the harder frame-COUPLED zero-bias axis (command-frame bias, not just sensor-side) stay a clean walk at a real 40M training budget, not just its 2M canary glance? zerobiasframe1x-c1's own 2M canary was CANARY PASS (23/24 gait_valid, 0 falls, a single non-chronic leg-0 flag), matching its sensor-only zerobias1x sibling's own clean canary -- this is its first ACQ-scale confirmation, joining the individual-axis durability batch (friction1x/mass1x/gains1x/geom1x/fault1x/extpush1x/actionnoise1x/torquefade1x/1.5x/2x all held at 40M).

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show command-frame-coupled zero-bias realism needs real training exposure before being called safe.

**refused_reason**: hexapod-mjx-train-10 already runs cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-zerobiasframe1x-c1-acq1 — GPU pods host exactly one run; pick a free GPU pod.

