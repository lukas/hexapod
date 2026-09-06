# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T07:56:09+00:00

**pod**: hexapod-mjx-train-11

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade1x-c1

**wandb_id**: 11p0scan

**hypothesis**: Does the campaign's hardest torque-fade dose point (dr.torque_scale 1.0, i.e. the REAL unassisted servo torque spec with zero battery/actuator-assist crutch, PERFECT 24/24 gait_valid at its 2M canary) hold up at a real acquisition-scale (40M) training budget, the same canary-vs-ACQ durability question already answered YES for friction1x and mass1x?

**gate**: ACQ PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg sacrifice vs the 2M canary and 0 falls. ACQ FAIL - MECHANISM if it collapses (gait_valid <12/24, a new chronic leg, or falls appear).

