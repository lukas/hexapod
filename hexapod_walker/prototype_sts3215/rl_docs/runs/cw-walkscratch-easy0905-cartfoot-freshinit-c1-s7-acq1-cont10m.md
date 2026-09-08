# cw-walkscratch-easy0905-cartfoot-freshinit-c1-s7-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-08T07:42:38+00:00

**pod**: hexapod-mjx-train-1

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-c1-s7-acq1

**wandb_id**: suh2oldf

**hypothesis**: Does the fresh-init cart_foot ON arm's slip PARITY with its matched joint-space control (measured this cycle at 40M: ON/OFF slip ratio 0.94-0.99x across all 4 groups, 0 falls) HOLD or DEGRADE at 10M more steps (50M cumulative)? This mirrors fork(a)'s own design: that mature/warm-started cart_foot lineage looked fine at 12M cumulative then developed 3 NEW tilt_roll falls and 2-6x slip inflation only after +10-20M more steps. If TRUE (parity holds): slip ratio stays <=1.2x in >=3/4 groups and 0 NEW falls -- the fresh-init mechanism is durable, not just early-luck. If FALSE (parity degrades): slip ratio climbs toward or past fork(a)'s 1.5-2x range and/or new falls appear -- fresh-init only delays, does not avoid, the same late-onset degradation fork(a) found. Strongest alternative: reward keeps rising with no degradation at all (the cleanest possible outcome, matching this run's own un-plateaued reward curve at 40M).

**gate**: ACQUISITION CONTINUATION: read together with the matched offctrl-s7-acq1-cont10m at the same budget. PROMISING/HOLDS = mean slip/m ratio (ON/OFF) <=1.2x in >=3/4 groups AND 0 new falls/terminations vs this run's own 40M read. DEGRADES = ratio >1.5x in >=2/4 groups OR any new fall/termination not present at 40M -- names this a late-onset-degradation replicate of fork(a), not a parity closure. Per 08-21 ruling, continue further only if reward is still rising and evals are ambiguous; a clean DEGRADES or a clean HOLDS both close this specific depth question without further automatic extension.

**verdict**: PARITY HOLDS at +10M (50M cumulative) -- fresh-init cart_foot durability confirmed, no fork(a)-style late-onset degradation. Matched-control ratios (ON/OFF slip per m, computed from both this run's report.json and the matched offctrl-s7-acq1-cont10m report.json I ran myself via podeval since it wasn't prestaged): walk/det 2.795/2.81=0.99x, walk/sto 3.30/3.41=0.97x, startjitter/det 2.74/2.83=0.97x, startjitter/sto 3.11/3.30=0.94x -- all 4/4 groups <=1.2x (comfortably under the HOLDS bar), 0 new falls/terminations in 24/24 episodes on either arm (same as their 40M reads). Reward still rising every quarter on both (ON 313.9->1865.7, OFF 349.0->2057.7), no plateau. One flagged-but-not-new finding: walk/det gait_valid dropped to 0/6 on BOTH arms (leg 4 duty 0.06-0.08 vs siblings' 0.52-0.59, swing_count 65-88 vs 200+ -- still cycling, not frozen) -- this is the SAME family-wide det-only leg-underuse quirk already precedented non-blocking for halfgrav-s0-c1 and seen in startjitter/det at 40M for both these arms; it widened to plain walk/det at +10M on BOTH arms equally, so it is a shared recipe-depth characteristic, not a cart_foot-specific or ON-specific regression, and does not gate this run (gate is slip-ratio + falls only). Sto modes stay clean (6/6, 5/6 gait_valid). This closes the seed7 durability question: fresh-init cart_foot parity is durable to +10M past acquisition, matching seed10's durability precedent shape. Video frame strips (walk_det_0_sheet.png) confirm level body, real leg cycling, one rigid trailing leg on the sacrificed index -- consistent with the harness's sacrificed_legs metric.

