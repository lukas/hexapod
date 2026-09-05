# cw-walkscratch-easy0905-headset-halfgrav-irr-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T14:39:36+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irr-c1

**wandb_id**: u3gu8x75

**hypothesis**: Plain English: the irregular-direction-change-timing canary on the 0.5g heading family (headset-halfgrav-irr-c1) reads healthy at 2M (reward monotonic 36->129 over 4 quarters, env/walk_speed alive 0.17-0.19 m/s all 4 quarters, ep_len_mean tripling 108->488 i.e. fewer early falls, wrong_way only 2-3%) -- this gives it the full 40M acquisition budget to mature six-leg walking under jittered (goal.walk_cmd_resample_jitter=0.5) direction-change timing, mirroring the base family's already-running headset-base-irr-c1/-c2 pair but on the independently-passed halfgrav heading champion (headset-halfgrav-s1acq). Own-checkpoint warm start only, no teacher/BC/motion-prior.

**gate**: Acquisition milestone at OWN physics (0.5g) with IRREGULAR direction-change timing: 20s held-out episodes across the 3-heading set with jittered resample timing, >=0.03 m/s median net forward along each commanded heading, 0 falls in 12 det episodes, gait_valid true (no sacrificed legs) in the majority of det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: continue/realign if still climbing at cutoff rather than an auto-fail.

