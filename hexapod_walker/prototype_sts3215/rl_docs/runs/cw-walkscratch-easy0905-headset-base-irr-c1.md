# cw-walkscratch-easy0905-headset-base-irr-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T13:59:12+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-acq1

**wandb_id**: 0zs57vwc

**hypothesis**: Plain English: headset-base-acq1 already walks cleanly (1g) under a heading SET that changes on a fixed 6s clock -- this canary is the 1g sibling of headset-halfgrav-irr-c1, testing the same next rung (IRREGULAR direction-change timing via goal.walk_cmd_resample_jitter=0.5 added on top of the identical resample_s=6.0/heading-set recipe, no other change), warm-started from acq1's own 40M checkpoint. Pairs with the halfgrav arm for an n=2 gravity-cell read of the irregular-timing rung.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Canary/mechanism-health at OWN physics (1g): env/walk_speed stays alive (not decaying toward 0 vs acq1's live trend), ep_rew_mean/ep_len_mean not collapsing early, no blowup. Per 08-21: healthy canary funds a 40M acquisition follow-up with the real gate (20s held-out panel with jittered heading changes, >=0.03 m/s median net forward per heading, 0 falls/12 det eps, gait_valid majority, six-leg lift/place on video); flat reward + collapsed speed = FAIL, no continuation.

