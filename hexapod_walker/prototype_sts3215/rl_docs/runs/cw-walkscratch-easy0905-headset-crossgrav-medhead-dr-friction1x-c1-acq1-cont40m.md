# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-friction1x-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T09:00:28+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-friction1x-c1-acq1

**hypothesis**: Plain English: does the friction-restore axis (dr.friction_scale 0.6-1.4) hold up over a SECOND 40M block (80M cumulative), the same endurance question already asked of the crossgrav/halfgrav cont40m siblings? Source is clean at 40M (24/24 gait_valid, 0 falls, sac=[] every episode, monotonic reward).

**gate**: PASS/HOLDS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with slip_per_m staying near the source's own 3.4-4.3 band and no NEW chronic single-leg sacrifice. FAIL/ENTRENCHES if a chronic single-leg sacrifice newly emerges/spreads across multiple modes.

