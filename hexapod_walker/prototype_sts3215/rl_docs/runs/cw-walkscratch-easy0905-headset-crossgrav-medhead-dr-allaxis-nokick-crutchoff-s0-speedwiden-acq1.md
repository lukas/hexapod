# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-speedwiden-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T11:07:22+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-speedwiden

**wandb_id**: wz9biedf

**hypothesis**: Plain English: does the speed-band widening (0.03-0.12 m/s dynamic cap) that just CANARY PASSed (3/3 seeds, clean vs each seed's own baseline) hold at real 40M acquisition budget, or does it re-open the composite's known late-entrenchment fragility the way the widen8 heading axis did (canary PASS 3/3, then ACQ FAIL 3/3 via a heading-dependent front-leg-pair sacrifice)? Same single-axis test, warm-started from this seed's own speedwiden-CANARY-PASS checkpoint.

**gate**: PASS (widening holds) if 0 falls/24 (or near-0, matching each seed's own acq1 baseline of 0 terms) and gait_valid >=18/24 with no new chronic sacrifice beyond the parent acq1's own walk_startjitter/sto leg0/leg5 flag. FAIL if a new chronic sacrifice or falls appear, matching widen8's own ACQ-depth regression shape.

