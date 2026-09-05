# cw-walkscratch-easy0905-headset-base-irr-c2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T14:38:21+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-irr-c1

**wandb_id**: lp4katkf

**hypothesis**: headset-base-irr-c1 tests whether irregular direction-change timing (goal.walk_cmd_resample_jitter=0.5) preserves the six-leg heading gait, warm-started from the flagship headset-base-acq1 checkpoint; this is the SAME jitter mechanism on the OTHER already-PASSed base seed (headset-base-s1c1-acq1) to check the irr result isn't specific to one checkpoint.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as headset-base-irr-c1: 2M canary, 0 falls, six-leg gait_valid on video across the 3-heading set under jittered resample timing; continue/realign per 08-21 if still climbing.

