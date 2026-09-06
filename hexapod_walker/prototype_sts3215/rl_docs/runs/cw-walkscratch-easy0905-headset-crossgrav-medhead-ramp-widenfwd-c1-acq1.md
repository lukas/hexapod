# cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-widenfwd-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T03:31:35+00:00

**pod**: hexapod-mjx-train-11

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-widenfwd-c1-acq1

**wandb_id**: x1nue97w

**hypothesis**: Plain English: the ramp-transition champion's 2M canary just PASSED the same native-1g heading-widen extension test its abrupt sibling passed -- does it hold up at full 40M acquisition scale too, mirroring the abrupt-widenfwd-c1-acq1 companion arm?

**gate**: ACQ PASS if aggregate gait_valid stays >=18/24 with no NEW chronic single-leg sacrifice pattern vs the 2M canary's own 21/24 baseline (max 2/6 per leg); 0 falls required. FAIL/MECHANISM if a chronic leg-sacrifice fingerprint (>=4/6 same leg in any mode) emerges that wasn't present at 2M.

