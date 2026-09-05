# cw-walkscratch-easy0905-headset-halfgrav-medhead-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T18:17:58+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-medhead-c1

**wandb_id**: dejrlkhv

**hypothesis**: the 2M medium-heading canary (headset-halfgrav-medhead-c1) already proved the heading-tracking gradient is live and mechanism-healthy on the 5-way quarter-turn set at 0.5g (v_along cleared the noise floor, full survival, harness-confirmed 24/24 gait_valid six-leg walking, no collapse) -- this gives it the full 40M acquisition budget to see if it learns to walk toward all 5 commanded headings as cleanly as halfgrav-acq1 learned the 3-way set. Warm-started from headset-halfgrav-medhead-c1's own 2M checkpoint (own-track continuation, not a teacher/BC/motion-prior), mirroring headset-base-medhead-acq1's template on the sibling 1g family.

**gate**: ACQUISITION (40M): PASS if held-out walk/det + walk_startjitter/det harness gait_valid majority (>=4/6 each) with no chronically-parked leg (duty>=0.10 on all six) across the 5-way heading set, slip_per_m staying near the 2.9 teacher band, zero falls. CONTINUE if gait_valid is marginal but reward/v_along keep climbing without collapse (08-21). FAIL if a leg re-sacrifices majority-of-episodes or course-tracking degrades toward the far/reversal headings the same way the bare 8-way fullhead jump did.

