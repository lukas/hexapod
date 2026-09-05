# cw-walkscratch-easy0905-headset-halfgrav-irr2-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T23:36:48+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irr-c2

**wandb_id**: 1tqy50b7

**hypothesis**: Does the halfgrav irregular-direction-change-timing (goal.walk_cmd_resample_jitter=0.5) acquisition rung generalize across seeds, matching the n=2 seed-confirmation discipline already applied to medhead/widen2? headset-halfgrav-irr-c2 (seed 3, warm-started from the independently-passed headset-halfgrav-s1acq champion, not c1's own halfgrav-acq1) is one of 3 healthy 2M irr-timing canaries (irr-c1/c2/c3 all CANARY PASS) but only c1 was ever continued to a full 40M acquisition (irr_acq1, itself ACQ PASS: 22/24 gait_valid, 0 falls, slip at/under the 2.9 band). This is the SAME already-bank-proved recipe (no new reward keys, no new mechanism) on a DIFFERENT seed/parent-champion lineage (s1acq not acq1), giving the irr-timing rung its own n=2 confirmation before any further composition arm (widenirr/irrwiden, already in flight off irr_acq1 alone) draws a recipe-level conclusion resting on a single seed.

**gate**: ACQ PASS if walk/det gait_valid >=4/6 AND walk_startjitter/det >=4/6 (matching the adopted s0c1-acq1 rule), 0 falls, slip/m at/under the 2.9 teacher band, no chronically sacrificed leg (duty>0.10 on all six) in a majority of episodes. CONTINUE if walk/det clears >=4/6 but walk_startjitter/det is borderline (duty 0.06-0.11, not chronic 0.0-0.02) with reward still climbing, matching medhead2-acq1's own accepted CONTINUE precedent. ACQ FAIL if either primary mode stays <4/6 with a chronic (duty<=0.05) sacrificed leg regardless of reward trend.

