# cw-walkscratch-easy0905-headset-halfgrav-irr-c2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T14:41:59+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irr-c1

**wandb_id**: 73esx971

**hypothesis**: headset-halfgrav-irr-c1 tests whether irregular direction-change timing (goal.walk_cmd_resample_jitter=0.5) preserves the six-leg heading gait at 0.5g, warm-started from the flagship headset-halfgrav-acq1 checkpoint; this is the SAME jitter mechanism on the OTHER just-PASSed halfgrav seed (headset-halfgrav-s1acq, this cycle's cleanest-yet ACQ PASS: 24/24 gait_valid, zero sacrificed legs) to check the irr result isn't specific to one checkpoint.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as headset-halfgrav-irr-c1: 2M canary, 0 falls, six-leg gait_valid on video across the 3-heading set under jittered resample timing; continue/realign per 08-21 if still climbing.

