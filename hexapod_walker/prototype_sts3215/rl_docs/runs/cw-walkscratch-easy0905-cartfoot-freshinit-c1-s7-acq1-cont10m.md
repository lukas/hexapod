# cw-walkscratch-easy0905-cartfoot-freshinit-c1-s7-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T07:42:38+00:00

**pod**: hexapod-mjx-train-1

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-c1-s7-acq1

**wandb_id**: suh2oldf

**hypothesis**: Does the fresh-init cart_foot ON arm's slip PARITY with its matched joint-space control (measured this cycle at 40M: ON/OFF slip ratio 0.94-0.99x across all 4 groups, 0 falls) HOLD or DEGRADE at 10M more steps (50M cumulative)? This mirrors fork(a)'s own design: that mature/warm-started cart_foot lineage looked fine at 12M cumulative then developed 3 NEW tilt_roll falls and 2-6x slip inflation only after +10-20M more steps. If TRUE (parity holds): slip ratio stays <=1.2x in >=3/4 groups and 0 NEW falls -- the fresh-init mechanism is durable, not just early-luck. If FALSE (parity degrades): slip ratio climbs toward or past fork(a)'s 1.5-2x range and/or new falls appear -- fresh-init only delays, does not avoid, the same late-onset degradation fork(a) found. Strongest alternative: reward keeps rising with no degradation at all (the cleanest possible outcome, matching this run's own un-plateaued reward curve at 40M).

**gate**: ACQUISITION CONTINUATION: read together with the matched offctrl-s7-acq1-cont10m at the same budget. PROMISING/HOLDS = mean slip/m ratio (ON/OFF) <=1.2x in >=3/4 groups AND 0 new falls/terminations vs this run's own 40M read. DEGRADES = ratio >1.5x in >=2/4 groups OR any new fall/termination not present at 40M -- names this a late-onset-degradation replicate of fork(a), not a parity closure. Per 08-21 ruling, continue further only if reward is still rising and evals are ambiguous; a clean DEGRADES or a clean HOLDS both close this specific depth question without further automatic extension.

