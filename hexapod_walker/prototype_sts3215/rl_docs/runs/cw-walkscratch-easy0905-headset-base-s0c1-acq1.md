# cw-walkscratch-easy0905-headset-base-s0c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T13:00:21+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-base-s0c1

**wandb_id**: 6n31rtzj

**hypothesis**: Plain English: headset-base-s0c1's 2M canary just proved the heading-tracking gradient is live on a THIRD base-family seed (same recipe as headset-base-c1/acq1) -- this gives it the full 40M acquisition budget to see if it learns to walk toward the commanded heading set (straight/+45/-45deg) as cleanly as base-s2/s4/s0-c1/s1-c1 walked straight. Warm-started from its own 2M checkpoint (own-track, not teacher/BC/motion-prior). If true: gait_valid=True six-leg walk on all 3 headings, 0 falls, slip near the base family's own 2.6-3.4 band. If false: sacrificed-leg/flag-leg pattern or falls under heading commands, same as the gSDE family's LEGPARK-SKATE (ruled out here since this is plain Gaussian, no --use-sde).

**gate**: Acquisition milestone (own physics, unchanged): 20s held-out heading-set (0/+45/-45deg), >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto.

