# cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-irrfwd-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T03:32:53+00:00

**pod**: hexapod-mjx-train-9

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-irrfwd-c1-acq1

**hypothesis**: Plain English: the ramp-transition champion's 2M canary just PASSED the same native-1g command-timing-jitter extension test its abrupt sibling passed -- does it hold up at full 40M acquisition scale too, mirroring the abrupt-irrfwd-c1-acq1 companion arm?

**gate**: ACQ PASS if aggregate gait_valid stays >=17/24 with no NEW chronic single-leg sacrifice pattern vs the 2M canary's own 22/24 baseline (max 2/6 per leg); 0 falls required. FAIL/MECHANISM if a chronic leg-sacrifice fingerprint (>=4/6 same leg in any mode) emerges that wasn't present at 2M.

