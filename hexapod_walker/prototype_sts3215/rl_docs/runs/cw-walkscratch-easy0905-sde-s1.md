# cw-walkscratch-easy0905-sde-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T09:08:03+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s0

**wandb_id**: ne2pwden

**hypothesis**: Plain English: independent seed 1 of the gSDE exploration family — the healthiest early-signal variant of the cohort (sde-s0 had best v_along at 2M) — at acquisition budget (mechanism evidence inherited from sde-s0's 2M CANARY PASS; operator 09-05: replicate healthy exploration variants). From-scratch 40M, identical to sde-s0 (--use-sde, resample 20 ticks; legal here because fresh build) except --seed 1. Question: is temporally-correlated gSDE exploration a robust advantage over per-tick Gaussian across seeds?

**gate**: Acquisition milestone at OWN physics (halfgrav arms at their own 0.5g): 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, all six legs repeatedly lift/place on video, no belly drag; report sto. Mechanism-health evidence inherited from the family's 2M CANARY PASS 09-05 — spot-check at ~2M in W&B, do not re-canary. Not met with v_along/reward still rising = continue/realign per 08-21 ruling; FAIL only on flat v_along+reward at this budget or park recapture.

