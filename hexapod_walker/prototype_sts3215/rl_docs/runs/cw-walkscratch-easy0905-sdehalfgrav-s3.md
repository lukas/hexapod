# cw-walkscratch-easy0905-sdehalfgrav-s3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T09:56:49+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s0

**wandb_id**: 1h3dcec8

**hypothesis**: Plain English: seed 3 of the sde+halfgrav factorial cell, seed-MATCHED to sde-s3/halfgrav-s3 so every family has n>=4 seeds for the 2x2 comparison. From-scratch 40M, identical to sdehalfgrav-s1 except --seed 3.

**gate**: Acquisition milestone at OWN physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Mechanism evidence inherited from the family 2M CANARY PASS; spot-check ~2M in W&B. Not met with signals rising = continue/realign per 08-21; FAIL only on flat v_along+reward at budget or park recapture.

