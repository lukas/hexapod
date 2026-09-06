# cw-walkscratch-easy0905-headset-crossgrav-s1acq-irrfwd-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T04:21:43+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s1acq-abrupt-c1-acq1

**wandb_id**: o3bapgqi

**hypothesis**: Plain English: every widen2/irr heading+jitter composite tested so far was built in 0.5g FIRST then abruptly transferred to 1g (or, for medhead, composed forward on a merely-ACQ-PASS plain champion). s1acq-abrupt-c1-acq1 is the CLEANEST crossgrav champion in the entire sweep (gait_valid PERFECT 24/24 at 40M, sac=[] in every episode) but has never been composed with irregular command-timing jitter. Can the SAME irr composite be added FORWARD, directly at 1g, on top of the cleanest available foundation?

**gate**: CANARY PASS - INFORMATIVE-POSITIVE if gait_valid stays majority-or-better (>=18/24) with no chronic single-leg sacrifice; matches the medhead-irrfwd-c1 precedent (22/24) if the cross-gravity repair is a durable foundation independent of source champion. FAIL/INFORMATIVE-NEGATIVE if it collapses toward chronic single-leg sacrifice.

