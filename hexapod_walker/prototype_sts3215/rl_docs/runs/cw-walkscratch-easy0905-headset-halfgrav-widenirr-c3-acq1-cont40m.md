# cw-walkscratch-easy0905-headset-halfgrav-widenirr-c3-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T07:00:54+00:00

**pod**: hexapod-mjx-train-11

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-widenirr-c3-acq1

**hypothesis**: Plain English: same endurance question as the crossgrav cont40m siblings, run on the halfgrav (0.5g) widenirr champion (headset-halfgrav-widenirr-c3-acq1: 21/24 gait_valid, mild non-chronic degrade from its own 23/24 2M canary, 0 falls, course-tracking metrics actually IMPROVED vs canary) -- first endurance read on a HALFGRAV source (all prior cont40m arms are crossgrav/1g), tests whether the cleanliness-margin-predicts-endurance rule generalizes across gravity regimes too.

**gate**: HARDENING/endurance continuation (+40M, own checkpoint, no cfg change). PASS/HOLDS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with slip_per_m staying tightly banded and no NEW chronic leg beyond this checkpoint's own established 40M read (21/24, scattered non-chronic legs 2/5). FAIL/ENTRENCHES if a chronic single-leg sacrifice newly emerges/spreads across multiple modes.

