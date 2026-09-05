# cw-walkscratch-easy0905-headset-base-irr-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T14:48:50+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-base-irr-c1

**wandb_id**: hqxngd1e

**hypothesis**: Plain English: the irregular-direction-change-timing canary on the 1g base heading family (headset-base-irr-c1) reads healthy at 2M and, unusually, the harness's own 24-episode gate panel (run early by the prestage/podeval tooling) already shows the family's established clean fingerprint -- 6/6 gait_valid on plain walk/det, 6/6 on walk/sto, 6/6 on walk_startjitter/sto, 0/24 falls, fwd 0.11-0.17 m/s, only the known walk_startjitter/det leg-1/4 favoritism (3/6) that every other base-family PASS also shows -- this gives it the full 40M acquisition budget to mature under jittered (goal.walk_cmd_resample_jitter=0.5) direction-change timing, mirroring the halfgrav sibling's headset-halfgrav-irr-acq1 (same rung, same cycle). Own-checkpoint warm start only, no teacher/BC/motion-prior.

**gate**: Acquisition milestone at OWN physics (1g) with IRREGULAR direction-change timing: 20s held-out episodes across the 3-heading set with jittered resample timing, >=0.03 m/s median net forward along each commanded heading, 0 falls in 12 det episodes, gait_valid true (no sacrificed legs) in the majority of det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: continue/realign if still climbing at cutoff rather than an auto-fail.

