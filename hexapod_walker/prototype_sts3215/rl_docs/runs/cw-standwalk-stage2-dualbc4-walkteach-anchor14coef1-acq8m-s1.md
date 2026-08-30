# cw-standwalk-stage2-dualbc4-walkteach-anchor14coef1-acq8m-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T21:21:16+00:00

**pod**: hexapod-mjx-train-3

**steps**: 8000000

**parent**: cw-standwalk-stage2-dualbc4-walkteach-anchor14coef1-canary-s1

**wandb_id**: t8tnn8ag

**hypothesis**: Seed-1 twin of the dualbc4-walkteach anchor14coef1 acq8m continuation (see seed0's ledger hypothesis for full rationale) -- same canary-checkpoint warm-start, same cfg, paired seed for replication.

**gate**: ACQUISITION (own-scope): det walk gait_valid stays >=5/6, sacrificed legs stay 0, progress_ratio improves or holds vs the canary's 0.44-0.46 (not regresses), slip/m stays inside teacher band (<=2.9), course_err_1s_med does not regress below walkteach-acq12m's own band, zero new walk terminations. Full DONE-gate mixedsession read follows per dualbc3 convention before any further unified-policy budget.

