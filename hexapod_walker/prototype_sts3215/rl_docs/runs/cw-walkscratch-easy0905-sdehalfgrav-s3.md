# cw-walkscratch-easy0905-sdehalfgrav-s3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-05T09:56:49+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s0

**wandb_id**: 1h3dcec8

**hypothesis**: Plain English: seed 3 of the sde+halfgrav factorial cell, seed-MATCHED to sde-s3/halfgrav-s3 so every family has n>=4 seeds for the 2x2 comparison. From-scratch 40M, identical to sdehalfgrav-s1 except --seed 3.

**gate**: Acquisition milestone at OWN physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Mechanism evidence inherited from the family 2M CANARY PASS; spot-check ~2M in W&B. Not met with signals rising = continue/realign per 08-21; FAIL only on flat v_along+reward at budget or park recapture.

**verdict**: ACQ FAIL — 3rd sde+halfgrav seed confirms the same reward-misalignment fingerprint as sdehalfgrav-s0/s1. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_sdehalfgrav_s3_gate/report.json — gait_valid 0/24 across every scenario (walk/sto x startjitter), 2+ legs sacrificed every episode (e.g. [3,5], [0,2,3,5]), every det/sto episode TERM tilt_pitch, fwd 0.10-0.26m/20s (bar 0.6m). wandb_history.csv: rollout/ep_len_mean rose to a peak ~204 by ~5M then COLLAPSED to a 62-74-tick plateau for the entire back half (23M-40M: 89.1->62.6->70.4->68.6->74.3) while ep_rew_mean crept -375->-2.2 — the same reward-per-burst 'sprint then fall' hack as s0/s1, not survival learning. Why: 3/4 sde+halfgrav seeds now share the flat-ep_len fingerprint (only sdehalfgrav-s2, still training/off-limits this cycle, remains unconfirmed) — this is a robust, seed-independent finding, not a fluke. Per 08-21 ruling this is a genuine FAIL (ep_len truly flat/plateaued at budget, not still rising) despite reward creep. Next: do not fund further from-scratch sde+halfgrav arms; the DIG-IN design item already flagged by the s0/s1 verdicts (survival-duration pricing fix — raise term_penalty and/or dose reward.alive, proven via a test_task_semantics.py bank first) is now backed by 3 independent seeds and should be prioritized before any more of this cell is launched.

