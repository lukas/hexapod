# cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-widenfwd-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T02:37:04+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-c1-acq1

**hypothesis**: Plain English: the abrupt-transition medhead champion already got a native-1g forward-extension test this cycle (medhead-widenfwd-c1, widen2 full-8-way heading added directly at 1g, running). The gentler ramp-transition sibling (medhead-ramp-c1-acq1, ACQ PASS 21/24) never got the same test. Does the ramp champion ALSO support forward heading-set extension natively at 1g, completing the abrupt-vs-ramp symmetry one rung further?

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic single-leg sacrifice under the widened 8-way heading set. FAIL/INFORMATIVE-NEGATIVE if it collapses to chronic leg sacrifice -- would mean the ramp recipe's gentler transition doesn't generalize to further curriculum extension as well as the abrupt one.

