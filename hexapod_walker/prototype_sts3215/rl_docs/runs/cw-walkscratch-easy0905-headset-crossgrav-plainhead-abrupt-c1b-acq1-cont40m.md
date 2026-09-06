# cw-walkscratch-easy0905-headset-crossgrav-plainhead-abrupt-c1b-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T06:43:26+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-plainhead-abrupt-c1b-acq1

**hypothesis**: Plain English: same endurance question as the medhead/widen2c1/widenirrc1 cont40m siblings, run on the simplest never-composited crossgrav champion (plainhead-abrupt-c1b-acq1: 23/24 gait_valid, EXACT match to its own 2M canary, 0 falls, cleanest un-composed source). If it holds clean at 80M, adds a 2nd un-composed-source confirmation that endurance tolerance tracks cleanliness margin, not composition; if it entrenches, shows even the simplest recipe isn't immune given enough budget.

**gate**: HARDENING/endurance continuation (+40M, own checkpoint, no cfg change). PASS/HOLDS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with slip_per_m staying tightly banded (no new outlier class) and no NEW chronic leg beyond this checkpoint's own established 40M read (23/24, one non-chronic startjitter/det dip). FAIL/ENTRENCHES if a leg[1,4]-pattern (or any single-leg) chronic sacrifice newly emerges across multiple modes.

