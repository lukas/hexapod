# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-mass1x-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T09:03:11+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-mass1x-c1-acq1

**wandb_id**: 61qwjqbf

**hypothesis**: Plain English: does the mass-restore axis (dr.mass_scale 0.85-1.20, leg_mass_jitter_pct 0.10) hold up over a SECOND 40M block (80M cumulative), the same endurance question already asked of the crossgrav/halfgrav cont40m siblings? Source is clean at 40M (24/24 gait_valid, 0 falls, sac=[] every episode, monotonic reward).

**gate**: PASS/HOLDS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with slip_per_m staying near the source's own 3.6-4.7 band and no NEW chronic single-leg sacrifice. FAIL/ENTRENCHES if a chronic single-leg sacrifice newly emerges/spreads across multiple modes.

