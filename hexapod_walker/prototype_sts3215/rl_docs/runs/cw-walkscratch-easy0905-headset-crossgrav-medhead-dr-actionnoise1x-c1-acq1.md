# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-actionnoise1x-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T08:01:06+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-actionnoise1x-c1

**wandb_id**: lut6o6wk

**hypothesis**: Does the campaign's clean actuator-side action-noise DR-restore canary (nominal dose, 22/24 gait_valid at 2M, 0 falls, only a single non-chronic leg-5 flag) hold up at a real acquisition-scale (40M) training budget, the same canary-vs-ACQ durability question already answered YES for friction1x/mass1x/gains1x-family single axes?

**gate**: ACQ PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) at 40M with no NEW chronic single-leg sacrifice vs the 2M canary and 0 falls. ACQ FAIL - MECHANISM if it collapses (gait_valid <12/24, a new chronic leg, or falls appear).

**verdict**: ACQ PASS/HOLDS (exact hold): 40M gait_valid 22/24 (walk/det 4/6, sto 6/6, startjitter/det 6/6, startjitter/sto 6/6), 0 falls/terms -- reproduces its own 2M canary EXACTLY, same leg-5 flag in the identical 2 walk/det episodes (ep1,ep3), same non-chronic pattern, nothing new or worse. slip/m flat (det med 3.53 vs canary 3.59, sto/startjitter bands unchanged), reward rose every quarter (783.7->1375.9->1457.2->1542.7). 6th individual-axis DR-restore ACQ confirmation to hold clean (after friction/mass/latency/gyrobias/gains-class). Per STATUS QUEUE AIM this closes out per-axis ACQ confirmations for action-noise; no further spend on this axis.

