# cw-walkscratch-easy0905-headset-crossgrav-medhead-irrwiden-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T03:54:54+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-irrfwd-c1-acq1

**wandb_id**: jbpj69ir

**hypothesis**: Plain English: sibling composite to medhead-widenirr-c1, opposite order -- start from the mature irr-jitter champion (medhead-irrfwd-c1-acq1, ACQ PASS at 40M) and add the full 8-way heading-widen set on top, natively at 1g. Tests whether composition order matters for the same two axes (widen-then-irr vs irr-then-widen), matching the halfgrav family's own irrwiden/widenirr pair-testing discipline.

**gate**: CANARY PASS if aggregate gait_valid stays majority-clean (>=20/24) with 0 falls and no NEW chronic leg sacrifice beyond what either single-axis parent already showed; FAIL if it collapses toward chronic leg-1/4 sacrifice or falls appear.

