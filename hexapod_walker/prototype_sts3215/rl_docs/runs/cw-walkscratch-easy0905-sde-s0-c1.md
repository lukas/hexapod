# cw-walkscratch-easy0905-sde-s0-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-05T09:49:24+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s0

**hypothesis**: Plain English: the gSDE canary had the strongest early forward signal of the cohort; this continues it from its own checkpoint at acquisition budget. Own-checkpoint 40M continuation of sde-s0. Built by respec from the base-s0 vector because plain --init-from REJECTS retained --use-sde/--activation-fn (fb_20260905T080341_ef45b6): PPO.load preserves the checkpoint's own gSDE mode (sde_sample_freq=20) and ELU; the vector is otherwise identical to sde-s0's.

**gate**: Acquisition milestone at own easy physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, all six legs repeatedly lift/place on video, no belly drag; report sto. Not met with v_along/reward still rising = continue/realign per 08-21 ruling, not auto-FAIL; genuine FAIL only if v_along_cmd and reward_walk are flat at this budget or park recapture. Also verify at first eval that the loaded policy is gSDE (use_sde=True, sde_sample_freq=20 in checkpoint data).

