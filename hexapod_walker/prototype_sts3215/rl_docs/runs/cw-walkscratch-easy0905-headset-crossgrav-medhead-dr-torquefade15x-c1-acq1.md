# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade15x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T07:34:07+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade15x-c1

**hypothesis**: Plain English: does the halfway torque-assist dose (dr.torque_scale 3x->1.5x, midway between the already-ACQ-confirmed-in-progress 1x/2x points) stay a clean walk with real training budget, not just a 2M canary glance? torquefade15x-c1's own 2M canary was a PERFECT 24/24 (0 falls, sac=[] every episode) -- this is its first ACQ-scale (40M) confirmation, joining the sibling torquefade2x-c1-acq1/friction1x-c1-acq1/mass1x-c1-acq1/encnoise1x-c1-acq1 individual-axis durability batch.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24, ideally close to its own 24/24 canary) at 40M, no NEW chronic single-leg sacrifice, 0 falls. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- would show even the mid-point torque-fade dose needs real training exposure before being called safe.

