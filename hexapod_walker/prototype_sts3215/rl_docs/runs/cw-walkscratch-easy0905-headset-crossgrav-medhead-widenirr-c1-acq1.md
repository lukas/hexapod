# cw-walkscratch-easy0905-headset-crossgrav-medhead-widenirr-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T05:52:04+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-widenirr-c1

**hypothesis**: The widen-then-irr composite (8-way heading + irr-timing jitter, composed on medhead) holds at full 40M ACQ scale, matching its own 2M canary (22/24) and its irr-then-widen sibling's precedent.

**gate**: ACQ PASS/HOLDS if aggregate gait_valid stays majority (>=18/24) with no NEW chronic single-leg pattern; ACQ FAIL - MECHANISM/ENTRENCHES if a leg[1,4]-style or leg-2/5-worsening chronic sacrifice emerges.

