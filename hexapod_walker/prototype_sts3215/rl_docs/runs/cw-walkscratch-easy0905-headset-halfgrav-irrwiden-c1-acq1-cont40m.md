# cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T11:06:23+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c1-acq1

**hypothesis**: Plain English: does the halfgrav widen+irr composite champion (jitter-first order, the actual DONE-gate panel shape) keep its clean 40M ACQ-PASS state (22/24 gait_valid, 0 falls, only 2/24 scattered non-chronic flags) after +40M more steps (80M cumulative), matching this campaign's cleanliness-margin-predicts-endurance rule (clean 40M sources hold; already-entrenching ones worsen)?

**gate**: cont40m gate (80M cumulative): PASS/HOLDS if gait_valid stays majority (>=18/24) with no NEW chronic single-leg pattern and 0 falls (matches or improves the parent's 22/24, scattered-non-chronic scatter). FAIL/ENTRENCHES if it drops (<12/24), the scatter consolidates into a chronic single-leg pattern, or a fall appears.

