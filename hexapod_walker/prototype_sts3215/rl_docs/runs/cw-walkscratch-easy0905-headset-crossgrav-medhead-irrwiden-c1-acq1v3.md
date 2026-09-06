# cw-walkscratch-easy0905-headset-crossgrav-medhead-irrwiden-c1-acq1v3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T05:58:31+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-irrwiden-c1

**hypothesis**: The irr-then-widen composite (irr-timing jitter + 8-way heading, composed on medhead) holds at full 40M ACQ scale, matching its own 2M canary (23/24) and its widen-then-irr sibling's precedent.

**gate**: ACQ PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg pattern; ACQ FAIL - MECHANISM/ENTRENCHES if a leg[1,4]-style or leg-2/5-worsening chronic sacrifice emerges.

