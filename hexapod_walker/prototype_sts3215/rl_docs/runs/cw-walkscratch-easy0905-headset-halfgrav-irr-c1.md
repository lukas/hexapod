# cw-walkscratch-easy0905-headset-halfgrav-irr-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T13:54:11+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-acq1

**wandb_id**: 9h6qj09s

**hypothesis**: Plain English: headset-halfgrav-acq1 already walks cleanly (0.5g) under a heading SET that changes on a fixed 6s clock (24/24 gait_valid, 0/24 falls, slip 2.2-2.6/m) -- this canary tests the track's own next rung, IRREGULAR direction-change timing (goal.walk_cmd_resample_jitter=0.5 added on top of the identical resample_s=6.0/heading-set recipe, no other change), warm-started from acq1's own 40M checkpoint. Moves the campaign from 'fixed heading set' toward the DONE gate's 'irregular direction changes' component.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Canary/mechanism-health at OWN physics (0.5g): env/walk_speed stays alive (not decaying toward 0 vs acq1's live trend), ep_rew_mean/ep_len_mean not collapsing early, no blowup. Per 08-21: healthy canary funds a 40M acquisition follow-up with the real gate (20s held-out panel with jittered heading changes, >=0.03 m/s median net forward per heading, 0 falls/12 det eps, gait_valid majority, six-leg lift/place on video); flat reward + collapsed speed = FAIL, no continuation.

