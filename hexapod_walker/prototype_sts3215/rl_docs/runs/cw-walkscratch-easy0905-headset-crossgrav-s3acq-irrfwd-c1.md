# cw-walkscratch-easy0905-headset-crossgrav-s3acq-irrfwd-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T04:26:54+00:00

**pod**: hexapod-mjx-train-11

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s3acq-abrupt-c1-acq1

**hypothesis**: Plain English: s3acq-abrupt-c1-acq1 is the 2nd-cleanest crossgrav champion in the sweep (gait_valid 21/24 at 40M). Mirroring the s1acq pair launched this cycle, can the SAME irr command-timing-jitter composite be added FORWARD, directly at 1g, on this 2nd champion too -- completing n=2 champions x n=2 axes for the forward-compose-on-a-clean-crossgrav-source question?

**gate**: CANARY PASS - INFORMATIVE-POSITIVE if gait_valid stays majority-or-better (>=18/24) with no chronic single-leg sacrifice, matching medhead-irrfwd-c1 (22/24) and the s1acq sibling. FAIL/INFORMATIVE-NEGATIVE if it collapses toward chronic single-leg sacrifice.

