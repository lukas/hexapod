# cw-walkscratch-easy0905-headset-crossgrav-irrwidenc2-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T03:03:10+00:00

**pod**: hexapod-mjx-train-10

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c2-acq1

**wandb_id**: mijsf6td

**hypothesis**: Plain English: the irr-first (jitter-then-widen) composite order previously FAILED cross-gravity transfer on its seed c1 (irrwidenc1-abrupt-c1, CANARY FAIL, walk/det collapsed 5/6->3/6) while the opposite widen-first order (widenirrc1) passed cleanly -- attributed to composition order. This run tests whether that's really an order effect or seed noise: irrwiden-c2 (2nd independent seed of the SAME irr-first order, just ACQ PASSed this cycle at its own 0.5g with gait_valid 22/24 matching its own canary) gets the identical abrupt 1g jump. If c2 ALSO fails, order is confirmed as the causal variable; if c2 passes, c1's failure was seed-specific and the order hypothesis is refuted.

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10-duty every episode) single-leg sacrifice -- refutes the composition-order hypothesis (c1's failure was seed noise). FAIL/INFORMATIVE-NEGATIVE if walk/det regresses to majority failure or the leg[1,4] chronic-sacrifice fingerprint emerges, matching c1 -- confirms irr-first composition order transfers worse than widen-first, independent of seed. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

**verdict**: CANARY PASS - INFORMATIVE-POSITIVE, refutes composition-order-as-causal. This run abruptly transfers this cycle's just-PASSED irrwiden-c2-acq1 champion (2nd independent seed of the irr-first composite order) to full 1g, disambiguating whether irrwidenc1-abrupt-c1's earlier crossgrav FAIL (walk/det collapsed 5/6->3/6) was a real composition-order effect or seed noise. Result: aggregate gait_valid 22/24 (walk/det 5/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 5/6), 0 falls/terminations in all 24 episodes. The two flagged episodes each show a DIFFERENT single leg (leg 3 in walk/det ep4, leg 4 in walk_startjitter/sto ep4) -- no chronic same-leg pattern, unlike irrwidenc1's own leg[1,4] chronic fingerprint. slip/m 4.4-208 (the two high outliers, 36 and 195, match the campaign's already-documented reversal-heading spin-in-place low-progress-denominator artifact, not a new defect); video (walk_det_0) confirms genuine six-leg cycling with clear body translation. Reward declined every quarter (-122.6->-452.1) but this composite's own walk_freeprog shortfall pricing is already established as inherently negative for every seed regardless of outcome (checked against both the PASSing widenirr-c1-acq1 and other siblings) -- non-diagnostic. Per the run's own pre-registered gate ('PASS if gait_valid stays majority (>=4/6) in walk/det with no chronic single-leg sacrifice'), this is a clean PASS. CLOSES the composition-order question: irr-first crossgrav transfer succeeds on this 2nd seed (22/24) just as cleanly as widen-first (6/6 champion set) -- irrwidenc1's original FAIL was seed-specific, not an order effect.

