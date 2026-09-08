# cw-walkscratch-easy0905-cartfoot-halfgrav-s10-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T11:45:14+00:00

**pod**: hexapod-mjx-train-2

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-s10-acq1

**wandb_id**: s5f2imns

**hypothesis**: Does the halfgrav cart_foot (ON) seed10 arm's 40M ACQ PASS (0 falls/24, speed 0.20-0.23 m/s, gait_valid 17/24) hold or degrade with 10M more training, mirroring seed7's own cont10m retention read (HELD its 22/24 band) and extending that depth check to a 2nd seed of this same recipe/budget/gravity/torque pair.

**gate**: RETENTION at 50M cumulative: PASS/HOLDS = 0 new falls/terminations vs this run's own 40M read, gait_valid staying in-or-above its established 17/24 band, slip/m staying within +/-20% of the 40M read. Read together with the matched offctrl-s10-acq1-cont10m sibling: does the seed7 pattern (ON holds, OFF gait_valid degrades further, gap widens) generalize to a 2nd seed, or does seed10 behave differently at depth.

