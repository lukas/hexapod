# cw-walkscratch-easy0905-sde-s0-c4

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T11:11:32+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-s1

**wandb_id**: 6e15jpmw

**hypothesis**: Own-checkpoint 40M continuation of sde-s0-c1 (ACQ CONTINUE: ep_len_mean recovered from a mid-training trough to 239 by 40M, ep_rew_mean ended positive +17.1, v_along_cmd ~0.15-0.17 m/s -- same still-learning fingerprint sde-s1/s2/s3 already earned continuations for). CORRECTED relaunch of sde-s0-c3, which silently trained only 2M steps because it was respec'd --from base-s0 (that run's own config is the 2M-canary scale, steps defaulted from it) instead of a 40M-scale sibling -- this respec is --from base-s1 (a 40M full-acquisition config) WITH an explicit --steps 40000000 override so the budget cannot silently inherit wrong.

**gate**: Acquisition milestone at own easy physics: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: FAIL only if v_along_cmd/reward_walk go flat or ep_len re-collapses without recovery; continue further if still climbing at cutoff.

