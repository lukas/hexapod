# cw-walkscratch-easy0905-headset-crossgrav-irracq1-abrupt-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T01:41:03+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-irracq1-abrupt-c1

**hypothesis**: Plain English: this cycle's crossgrav-irracq1 discovery canary already showed the halfgrav-irr-acq1 champion (irregular command-timing-jitter recipe) survives an abrupt jump to full 1g without the base(1g)-family chronic leg-1/4 sacrifice fingerprint (gait_valid 23/24, 0 falls). Does that hold at full 40M acquisition budget, matching the medhead/widen2 crossgrav acquisitions that already passed? Own-checkpoint continuation, ease.gravity_scale stays at 1.0 (already set by the source run).

**gate**: ACQ PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with no chronic single-leg sacrifice at 40M, matching/improving the 2M canary reads, 0 falls, slip/m at/near the 2.9 teacher band. ACQ FAIL if it collapses to the leg[1,4] chronic-sacrifice fingerprint with more steps.

