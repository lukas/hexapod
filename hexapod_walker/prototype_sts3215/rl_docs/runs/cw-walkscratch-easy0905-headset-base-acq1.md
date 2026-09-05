# cw-walkscratch-easy0905-headset-base-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T11:54:05+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-base-c1

**wandb_id**: ri9rlmho

**hypothesis**: Plain English: the 2M heading canary (headset-base-c1) already proved the heading-tracking gradient is live under the SAME reward the fixed-forward base family trained under (no new keys) -- this gives it the full 40M acquisition budget to see if it actually learns to walk toward the commanded heading set (straight/+45/-45deg) as cleanly as base-s2/s4/s0-c1/s1-c1 walked straight. Warm-started from headset-base-c1's own 2M checkpoint (own-track, not a teacher/BC/motion-prior).

**gate**: Acquisition milestone at own physics + heading: 20s held-out episodes across the 3-heading set, >=0.03 m/s median net forward along each commanded heading, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: continue/realign if still climbing at cutoff rather than an auto-fail.

