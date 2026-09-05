# cw-walkscratch-easy0905-headset-halfgrav-medhead2-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T19:18:24+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-medhead2-c1

**wandb_id**: xa9a26bm

**hypothesis**: Second-seed medium-heading (5-way, 0/+-45/+-90deg) acquisition on the halfgrav(0.5g) family: headset-halfgrav-medhead2-c1's own 2M canary already CANARY PASSED cleanly (24/24 harness gait_valid, zero sacrificed legs, slip near the teacher band), warm-started from a DIFFERENT halfgrav champion (headset-halfgrav-s3acq) than the first-seed acq1 continuation (which used medhead-c1, warm-started from halfgrav-acq1). This gives it the full 40M budget to confirm the medium-heading rung acquires cleanly from a second independent seed, mirroring headset-halfgrav-medhead-acq1's template exactly.

**gate**: ACQUISITION (40M): PASS if held-out walk/det + walk_startjitter/det harness gait_valid majority (>=4/6 each) with no chronically-parked leg (duty>=0.10 on all six) across the 5-way heading set, slip_per_m staying near the 2.9 teacher band, zero falls. CONTINUE if gait_valid is marginal but reward/v_along keep climbing without collapse (08-21). FAIL if a leg re-sacrifices majority-of-episodes or course-tracking degrades toward the far/reversal headings the same way the bare 8-way fullhead jump did. PASS (2nd seed) closes the medium-heading rung's acquisition-scale seed-robustness confirmation at n=2 on the halfgrav family.

