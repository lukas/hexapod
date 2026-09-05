# cw-walkscratch-easy0905-headset-halfgrav-s1acq

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T13:19:52+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-s1

**wandb_id**: yqm9c7e8

**hypothesis**: Plain English: the heading canary (headset-halfgrav-s1) already reads exceptionally clean at 2M (24/24 gait_valid, 0 falls, slip in-band) -- this gives it the full 40M acquisition budget to mature that six-leg heading gait (longer strides, less quiver) at 0.5g toward the 3-heading set, matching sibling to headset-halfgrav-acq1 (from c2/seed2) and headset-base-acq1 (1g). Warm-started from headset-halfgrav-s1's own 2M checkpoint (own-track, not a teacher/BC/motion-prior).

**gate**: Acquisition milestone at OWN physics (0.5g) + heading: 20s held-out episodes across the 3-heading set, >=0.03 m/s median net forward along each commanded heading, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: continue/realign if still climbing at cutoff rather than an auto-fail.

