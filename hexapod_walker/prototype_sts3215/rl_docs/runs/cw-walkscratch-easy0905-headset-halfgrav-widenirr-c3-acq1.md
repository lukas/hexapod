# cw-walkscratch-easy0905-headset-halfgrav-widenirr-c3-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T03:30:15+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-widenirr-c3

**hypothesis**: Does widenirr's 3rd tie-breaking seed (23/24 gv 2M canary, own 0.5g, only a course-tracking caveat not a gait-validity one) hold up at full 40M acquisition budget the same way sibling widenirr-c1-acq1 did (ACQ PASS, 22/24)?

**gate**: PASS if gait_valid stays >= its own 2M canary (23/24) or degrades only mildly, 0 falls, no NEW chronically-sacrificed leg. Track course-tracking metrics (wrong_direction_frac, course_err) explicitly -- if they worsen at 40M vs 2M that's a real regression to flag even under an otherwise-passing gait_valid count. FAIL/MECHANISM if gait_valid collapses toward the widenirr-c2b FAIL fingerprint despite rising reward.

