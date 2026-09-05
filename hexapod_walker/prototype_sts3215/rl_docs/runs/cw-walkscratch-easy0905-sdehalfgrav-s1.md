# cw-walkscratch-easy0905-sdehalfgrav-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T09:27:35+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s0

**wandb_id**: i6po3x2j

**hypothesis**: Plain English: second seed of the sde+halfgrav factorial cell so the 2x2 grid (base/sde/halfgrav/sde+halfgrav) has n=2 per cell. From-scratch 40M, identical to sdehalfgrav-s0 except --seed 1. (First attempt FAILED pre-boot on train-1: CPU-only torch in that pod venv, repaired to 2.11.0+cu128 this cycle — infrastructure, not recipe.)

**gate**: Acquisition milestone at OWN physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Mechanism evidence inherited from the family 2M CANARY PASS; spot-check ~2M in W&B. Not met with signals rising = continue/realign per 08-21; FAIL only on flat v_along+reward at budget or park recapture.

