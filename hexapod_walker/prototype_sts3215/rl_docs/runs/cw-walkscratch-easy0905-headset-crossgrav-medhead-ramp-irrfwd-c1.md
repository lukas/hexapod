# cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-irrfwd-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T02:35:46+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-c1-acq1

**wandb_id**: m5sxljmr

**hypothesis**: Plain English: same logic as the widenfwd sibling, but for command-timing jitter instead of heading breadth: medhead-irrfwd-c1 (abrupt transition) is already testing native-1g jitter extension; this gives the ramp-transition champion the same test.

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic single-leg sacrifice under command-timing jitter. FAIL/INFORMATIVE-NEGATIVE if it collapses to chronic leg sacrifice.

