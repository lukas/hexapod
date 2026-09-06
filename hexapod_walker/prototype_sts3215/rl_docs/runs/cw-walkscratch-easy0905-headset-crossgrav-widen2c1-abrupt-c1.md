# cw-walkscratch-easy0905-headset-crossgrav-widen2c1-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS - INFORMATIVE-POSITIVE

**created**: 2026-09-06T00:48:22+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c1-acq1

**wandb_id**: uj013rxq

**hypothesis**: Plain English: this cycle's crossgrav-medhead discovery already showed the 5-way-heading halfgrav champion transfers to full 1g without collapsing into the base(1g) leg-1/4 chronic-sacrifice pattern. Does that generalize to a DIFFERENT, harder halfgrav champion -- the full 8-way-compass widen2-c1-acq1 (ACQ PASS, gait_valid 21/24, includes the two reversal headings) -- or was the medhead result specific to that one recipe/checkpoint? Warm-starts from widen2-c1-acq1 (never seen 1g) and abruptly sets ease.gravity_scale=1.0 from tick 0, same template as medhead-abrupt-c1.

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10 duty every episode) single-leg sacrifice -- extends the cross-gravity-transfer finding to a 2nd, materially different halfgrav recipe (fuller heading set incl. reversals), strengthening it as a general repair path rather than a medhead-specific fluke. FAIL/INFORMATIVE-NEGATIVE if it collapses to the leg[1,4] chronic-sacrifice fingerprint -- would mean the medhead result doesn't generalize across heading-set recipes, narrowing the finding. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

**verdict**: Result: cross-gravity transfer generalizes to a 2nd, materially different leg-healthy halfgrav champion (full 8-way heading incl. reversals, widen2-c1 lineage), not just medhead. Evidence: harness gait_valid 19/24 -- walk/det 5/6 (sac=[] every episode but one, that one flags [0,3] transiently not chronically), walk/sto 6/6 clean, walk_startjitter/det 3/6 and walk_startjitter/sto 5/6 with a mild leg-4 softening under start-pose jitter (duty stays borderline, never zero-touch) -- 0 falls in all 24 episodes, closely matching crossgrav-medhead-abrupt-c1's own 20/24 read at the identical 2M budget and template. Video (contact_sheet.png, walk_startjitter_sto_4.mp4) shows genuine six-leg cycling with the body translating across tiles, not frozen/dragging. A few reversal-heavy episodes show slip/m spikes (up to 207/m) from the known low-net-progress denominator blowup already documented on this widen2/reversal-heading family, not a new pathology. Why: this is the 2nd of 3 generality-check champions to independently PASS the abrupt 1g transfer (medhead abrupt+ramp already PASSED; irracq1-abrupt-c1/widenirrc1-abrupt-c1 pending under concurrent cycles; widen2c2b-abrupt-c1 negative control pending) -- strengthens cross-gravity-transfer as a general base(1g) repair path rather than a medhead-specific fluke. Next: per the gate's own PASS branch and the medhead template, launching a matched 40M ACQ continuation (headset-crossgrav-widen2c1-abrupt-c1-acq1) to test whether the six-leg gait holds/improves at full acquisition budget on this 2nd recipe.

