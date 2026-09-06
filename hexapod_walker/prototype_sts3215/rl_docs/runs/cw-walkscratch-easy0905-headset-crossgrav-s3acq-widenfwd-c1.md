# cw-walkscratch-easy0905-headset-crossgrav-s3acq-widenfwd-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T04:24:14+00:00

**pod**: hexapod-mjx-train-10

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s3acq-abrupt-c1-acq1

**wandb_id**: zvxecftd

**hypothesis**: Plain English: s3acq-abrupt-c1-acq1 is the 2nd-cleanest crossgrav champion in the sweep (gait_valid 21/24 at 40M, only a mild non-chronic leg-1 jitter-sensitivity). Mirroring the s1acq pair launched this cycle, can the SAME widen2 full-8-way-heading-set composition be added FORWARD, directly at 1g, on this 2nd champion too -- giving n=2 champions x n=2 axes for the forward-compose-on-a-clean-crossgrav-source question?

**gate**: CANARY PASS - INFORMATIVE-POSITIVE if gait_valid stays majority-or-better (>=18/24) with no chronic single-leg sacrifice, matching medhead-widenfwd-c1 (23/24) and the s1acq sibling. FAIL/INFORMATIVE-NEGATIVE if it collapses toward chronic single-leg sacrifice.

