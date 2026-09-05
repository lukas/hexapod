# cw-walkscratch-easy0905-base-s1-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T09:17:44+00:00

**pod**: hexapod-mjx-train-10

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-s1

**wandb_id**: if3jt8v8

**hypothesis**: Plain English: second-seed twin of the base continuation — healthy 2M canary gets its acquisition budget from its own checkpoint. Own-checkpoint 40M continuation of base-s1, zero recipe changes; --activation-fn stripped per plain --init-from restriction.

**gate**: Acquisition milestone at own easy physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, all six legs repeatedly lift/place on video, no belly drag; report sto. Not met with v_along/reward still rising = continue/realign per 08-21 ruling, not auto-FAIL; genuine FAIL only if v_along_cmd and reward_walk are flat at this budget or park recapture.

