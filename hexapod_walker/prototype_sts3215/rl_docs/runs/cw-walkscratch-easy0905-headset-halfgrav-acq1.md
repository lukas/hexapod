# cw-walkscratch-easy0905-headset-halfgrav-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T11:57:23+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-c2

**wandb_id**: veqsr4jm

**hypothesis**: Plain English: the 2M heading canary (headset-halfgrav-c2) already proved the heading-tracking gradient is live under the SAME reward the fixed-forward halfgrav family trained under (no new keys) -- this gives it the full 40M acquisition budget to learn walking toward the commanded heading set (straight/+45/-45deg) as cleanly as halfgrav-s1/s2/s3/s0-c1 walked straight at 0.5g. Matching sibling to headset-base-acq1 (1g). Warm-started from headset-halfgrav-c2's own 2M checkpoint (own-track, not a teacher/BC/motion-prior).

**gate**: Acquisition milestone at OWN physics (0.5g) + heading: 20s held-out episodes across the 3-heading set, >=0.03 m/s median net forward along each commanded heading, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: continue/realign if still climbing at cutoff rather than an auto-fail.

