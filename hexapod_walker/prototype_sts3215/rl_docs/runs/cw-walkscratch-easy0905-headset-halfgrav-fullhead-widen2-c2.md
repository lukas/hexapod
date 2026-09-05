# cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T20:30:14+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-medhead2-c1

**wandb_id**: yz196tgc

**hypothesis**: Second-seed twin of fullhead-widen2-c1, same design question (does widening from an already-quarter-turn-capable champion fix the reversal-heading course-tracking gap fullhead-c1 showed), on a DIFFERENT champion lineage: headset-halfgrav-medhead2-c1 (the second-seed 2M medhead canary, CANARY PASS, 24/24 gait_valid, cleaner than the first seed) instead of the 40M first-seed medhead-acq1 champion widen2-c1 uses. Confirms whether any widen-from-medhead improvement is recipe-level (both seeds show it) or one lucky champion.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M), same bar as widen2-c1: gait_valid majority-valid (>=4/6 det) with 0 falls, and direction_err/course_err at the new +-135/180 headings tighter than fullhead-c1's own spread (28-161deg). Read together with widen2-c1: both improve = recipe-level curriculum finding; only one improves = seed-lottery, not yet a design conclusion; neither improves = reversal-heading gap is fundamental, not an init artifact.

