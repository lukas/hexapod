# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade2x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T06:46:05+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade2x-c1

**wandb_id**: n838t060

**hypothesis**: Plain English: does removing HALF the torque/battery-assist crutch (3x->2x) stay a clean walk once trained for real, not just at a 2M canary glance? torquefade2x-c1's own 2M canary was a PERFECT 24/24 (0 falls, no sacrificed leg) on the campaign's cleanest champion -- this is its first ACQ-scale (40M) confirmation, the same durability question already asked of every irr/widen composition axis but never yet asked of a bare single-axis DR-realism restore.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24, ideally close to its own 24/24 canary) across the full 4-panel harness at 40M, no NEW chronic single-leg sacrifice, 0 falls -- confirms simple single-axis DR canaries durability-check the same way composition axes do. FAIL/ENTRENCHES if it drops (<12/24, a new chronic leg, or a fall) -- shows even a currently-idealized torque-crutch axis needs real training exposure, not a bare canary read, before it can be called safe; would flag the whole single-axis-restore sweep's canary-only PASSes as provisional pending their own ACQ checks.

