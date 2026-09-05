# cw-walkscratch-easy0905-base-s0-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T09:20:18+00:00

**pod**: hexapod-mjx-train-9

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-s0

**wandb_id**: xjm7cd59

**hypothesis**: Plain English: the healthy 2M canary showed learning pointed the right way (v_along rising through zero, per-tick reward improving) but only 4 PPO updates deep; this continuation gives the SAME recipe its pre-registered acquisition budget from its OWN checkpoint. Own-checkpoint 40M continuation of base-s0 (operator 09-05 order raised +18M to +40M), zero recipe changes; --activation-fn stripped per plain --init-from restriction (PPO.load preserves ELU + checkpoint log_std; log_std_final anneal continues per fb_20260905T080341_ef45b6).

**gate**: Acquisition milestone at own easy physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, all six legs repeatedly lift/place on video, no belly drag; report sto. Not met with v_along/reward still rising = continue/realign per 08-21 ruling, not auto-FAIL; genuine FAIL only if v_along_cmd and reward_walk are flat at this budget or park recapture.

