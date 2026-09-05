# cw-walkscratch-easy0905-sde-s3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T09:50:46+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s0

**wandb_id**: 2cz2qe5m

**hypothesis**: Plain English: independent seed 3 of the gSDE exploration family, completing n=4 fresh seeds to match base/halfgrav for the sde-vs-Gaussian family comparison (matched-seed directive 09-05). From-scratch 40M, identical to sde-s2 except --seed 3.

**gate**: Acquisition milestone at OWN physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Mechanism evidence inherited from the family 2M CANARY PASS; spot-check ~2M in W&B. Not met with signals rising = continue/realign per 08-21; FAIL only on flat v_along+reward at budget or park recapture.

