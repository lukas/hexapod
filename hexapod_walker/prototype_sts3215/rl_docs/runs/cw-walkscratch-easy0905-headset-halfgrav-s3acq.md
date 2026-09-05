# cw-walkscratch-easy0905-headset-halfgrav-s3acq

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-05T13:21:32+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-s3

**hypothesis**: Plain English: the heading canary (headset-halfgrav-s3) already reads clean at 2M (0/24 det falls, slip 1.9-2.6 in-band, forward 1.6-4.0m/20s across the 3-heading set) -- this gives it the full 40M acquisition budget to mature that six-leg 0.5g heading gait toward the same acquisition bar the base family and headset-halfgrav-s1acq are already clearing. Warm-started from headset-halfgrav-s3's own 2M checkpoint (own-track, not a teacher/BC/motion-prior).

**gate**: Acquisition milestone at OWN physics (0.5g) + heading: 20s held-out episodes across the 3-heading set, >=0.03 m/s median net forward along each commanded heading, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: continue/realign if still climbing at cutoff rather than an auto-fail.

