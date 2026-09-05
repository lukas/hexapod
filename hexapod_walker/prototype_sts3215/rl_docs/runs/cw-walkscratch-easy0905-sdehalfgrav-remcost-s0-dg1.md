# cw-walkscratch-easy0905-sdehalfgrav-remcost-s0-dg1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T15:07:50+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-sdehalfgrav-remcost-s0

**wandb_id**: 698t5lme

**hypothesis**: Plain English: sdehalfgrav-remcost-s0 also learned LEGPARK-SKATE (1/4 legs chronically parked) and the recency-based walk_gait_gate repair FAILED here too (4/4 closed, gate factor saturated at ceiling). This is the new duty-FRACTION gate (reward.walk_duty_gate=1.0, bank-verified 5/5 green this cycle) ported onto the remcost recipe's different term-cost pricing -- tests whether the mechanism generalizes off bare-sde. Single lever, cheap 2M canary before any 40M spend.

**gate**: MECHANISM-HEALTH CANARY: env/walk_duty_gate_factor should climb toward 1.0 (not saturate at ceiling the way walk_gait_gate_factor did), reward/speed not collapsing, 0 blowups. PASS funds a 40M acquisition continuation with the real gate (gait_valid majority, duty>=0.10 all legs); FAIL closes the lever on remcost too.

