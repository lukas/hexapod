# cw-walkscratch-easy0905-headset-base-s0c1-dgate2-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T17:34:05+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-s0c1-acq1

**wandb_id**: j41igzz5

**hypothesis**: The FAILED s0c1-acq1 checkpoint walks fast with zero falls but chronically parks leg 4 at duty 0.03-0.07 (marginal underuse, NOT gSDE-style near-zero LEGPARK-SKATE, now closed for good). The prior repair attempt (headset-base-s0c1-dgate-c1, walk_duty_gate=0.9/floor=0.15) was CANARY FAIL - MECHANISM (INERT-DOSE): PPO's own training-time rollout noise already satisfies the lenient 0.15 floor even for a leg whose deterministic policy sits at 0.04-0.07, so almost no repair gradient reached eval-time behavior. This canary retries the SAME repair at a stronger, bank-proven dose (floor 0.15->0.35, ~2.3x; full gate strength g=1.0) that the new test_duty_gate_strong_floor_* bank (walkcurr-dutygate-strongfloor-bank-0905, 39/39 green) proves still leaves a healthy six-leg tripod's income untouched (leg-4 duty ~0.52 >> 0.35) while measurably increasing the price on a token-touchdown twin at the same ~0.05 duty magnitude as the real fingerprint (return drops from -432 to -536 on the identical trajectory, floor=0.15 vs 0.35).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (2M): env/walk_duty_min and env/walk_duty_gate_factor must show REAL movement off the 0.15-floor plateau this exact checkpoint/dose combo already produced (not stuck at 0.9-1.0 the whole run the way the inert 0.9/0.15 dose did); det-mode leg-4 duty in the harness gate report should climb measurably above the 0.04-0.07 baseline (not necessarily clear the 0.10 sacrifice bar at 2M, but real movement toward it); no new falls vs the s0c1-acq1 baseline; slip/m not dramatically worse. FAIL if duty stays pinned at the exact same 0.04-0.07 baseline (still inert) or if a DIFFERENT leg parks or falls appear (destabilized). PASS licenses a 40M acquisition continuation to see if the base-family champion selection changes.

