# cw-walkscratch-easy0905-headset-crossgrav-irrwidenc2-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T03:03:10+00:00

**pod**: hexapod-mjx-train-10

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c2-acq1

**hypothesis**: Plain English: the irr-first (jitter-then-widen) composite order previously FAILED cross-gravity transfer on its seed c1 (irrwidenc1-abrupt-c1, CANARY FAIL, walk/det collapsed 5/6->3/6) while the opposite widen-first order (widenirrc1) passed cleanly -- attributed to composition order. This run tests whether that's really an order effect or seed noise: irrwiden-c2 (2nd independent seed of the SAME irr-first order, just ACQ PASSed this cycle at its own 0.5g with gait_valid 22/24 matching its own canary) gets the identical abrupt 1g jump. If c2 ALSO fails, order is confirmed as the causal variable; if c2 passes, c1's failure was seed-specific and the order hypothesis is refuted.

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10-duty every episode) single-leg sacrifice -- refutes the composition-order hypothesis (c1's failure was seed noise). FAIL/INFORMATIVE-NEGATIVE if walk/det regresses to majority failure or the leg[1,4] chronic-sacrifice fingerprint emerges, matching c1 -- confirms irr-first composition order transfers worse than widen-first, independent of seed. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

