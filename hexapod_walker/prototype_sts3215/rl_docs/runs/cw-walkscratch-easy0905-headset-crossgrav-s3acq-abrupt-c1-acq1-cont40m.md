# cw-walkscratch-easy0905-headset-crossgrav-s3acq-abrupt-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T04:01:27+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s3acq-abrupt-c1-acq1

**wandb_id**: z1e7r91v

**hypothesis**: Plain English: same endurance question as the medhead/widen2c1/widenirrc1/s1acq cont40m siblings, run on the campaign's 2nd-best crossgrav champion (s3acq-abrupt-c1-acq1: 21/24 gait_valid, walk/det+walk/sto clean 6/6, only walk_startjitter/det softened to 3/6 non-chronically, 0 falls). Completes a 5-recipe endurance panel (medhead/widen2c1/widenirrc1/s1acq/s3acq) spanning the full cleanliness range of ACQ-PASSed crossgrav champions, testing whether entrenchment risk given extra 1g budget correlates with source cleanliness or hits every recipe regardless.

**gate**: HARDENING/endurance continuation (+40M, own checkpoint, no cfg change). PASS/HOLDS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with no NEW chronic leg beyond this checkpoint's own established 40M read (21/24). FAIL/ENTRENCHES if a leg[1,4]-pattern chronic sacrifice newly emerges -- completes the 5-recipe endurance panel either way.

