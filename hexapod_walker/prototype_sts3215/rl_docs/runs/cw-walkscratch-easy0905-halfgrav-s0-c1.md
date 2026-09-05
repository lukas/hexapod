# cw-walkscratch-easy0905-halfgrav-s0-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T09:19:01+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-halfgrav-s0

**wandb_id**: wkxt570w

**hypothesis**: Plain English: the half-gravity canary was healthy; acquisition budget from its own checkpoint tests whether stepping emerges earlier at half weight. Own-checkpoint 40M continuation of halfgrav-s0 (ease.gravity_scale=0.5 retained), --activation-fn stripped per plain --init-from restriction. Evaluated at ITS OWN 0.5g; full-gravity is a later diagnostic only.

**gate**: Acquisition milestone at own easy physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, all six legs repeatedly lift/place on video, no belly drag; report sto. Not met with v_along/reward still rising = continue/realign per 08-21 ruling, not auto-FAIL; genuine FAIL only if v_along_cmd and reward_walk are flat at this budget or park recapture.

