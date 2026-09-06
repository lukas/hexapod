# cw-walkscratch-easy0905-headset-crossgrav-irracq1-abrupt-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ_FAIL

**created**: 2026-09-06T01:41:03+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-irracq1-abrupt-c1

**wandb_id**: 4n0z9k3b

**hypothesis**: Plain English: this cycle's crossgrav-irracq1 discovery canary already showed the halfgrav-irr-acq1 champion (irregular command-timing-jitter recipe) survives an abrupt jump to full 1g without the base(1g)-family chronic leg-1/4 sacrifice fingerprint (gait_valid 23/24, 0 falls). Does that hold at full 40M acquisition budget, matching the medhead/widen2 crossgrav acquisitions that already passed? Own-checkpoint continuation, ease.gravity_scale stays at 1.0 (already set by the source run).

**gate**: ACQ PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with no chronic single-leg sacrifice at 40M, matching/improving the 2M canary reads, 0 falls, slip/m at/near the 2.9 teacher band. ACQ FAIL if it collapses to the leg[1,4] chronic-sacrifice fingerprint with more steps.

**verdict**: ACQ FAIL - MECHANISM (informative), the leg[1,4] chronic-entrenchment fingerprint the gate itself pre-registered emerges by 40M despite a clean 23/24 2M canary and training reward RISING throughout (quarters 717->1359->1507->1635). Result: aggregate gait_valid drops from the 2M canary's 23/24 to 14/24 at 40M -- walk/det regresses from clean 6/6 to 4/6 (2 NEW formal sac=[4] flags where the canary had zero), walk/sto holds 6/6, walk_startjitter/det COLLAPSES from 5/6 to 0/6 (5 episodes flag leg 4, one leg 1; one episode's leg-4 swing_count=2 over the full 20s vs 91-239 for every other leg -- a near-frozen leg, not noise), walk_startjitter/sto softens 6/6->4/6. 0 falls/terminations in all 24 episodes -- a gait-quality/favoritism failure, not a safety collapse; video (walk_det_0, walk_startjitter_det_0/3) confirms genuine body translation even in flagged episodes, matching the CURRENT_TRUTHS STRUCTURAL DIAGNOSTIC (09-05 ~22:3x): legs 1/4 are the hexagon's one diametrically-opposite middle pair with no fore/aft neighbor, so a 4-legs-effective gait that idles them is a genuinely cheaper stable 1g gait, not a random exploit. Why this is a FAIL and not a 08-21 'undertrained, keep going' case: this exact reward-misalignment class (base(1g)-family leg favoritism) is ALREADY CLOSED in CURRENT_TRUTHS after 9 independently-designed repair mechanisms (walk_gait_gate, walk_duty_gate x4 provenances, walk_swing_gate x5) all failed to fix it, with the explicit finding that the fix must be STRUCTURAL (curriculum-widen from a healthy checkpoint, role-aware per-leg pricing) not 'more of the same reward' or 'just continue' -- continuing IS what produced this entrenchment. Notable and new: this is the FIRST regression in the ACQ-scale confirmation set for this crossgrav-transfer campaign -- the 3 prior ACQ-scale siblings (medhead-abrupt-c1-acq1 23/24, medhead-ramp-c1-acq1 21/24, widen2c1-abrupt-c1-acq1 20/24) all held clean walk/det (6/6) with only PARTIAL walk_startjitter/det softening (3/6, never 0/6) -- meaning a clean 2M canary does not guarantee ACQ-scale durability, at least for this recipe/seed. What's next: (1) the natural n=2-seed check for this exact irr-timing recipe, irr2acq1-abrupt-c1-acq1, is already training (another cycle's territory) and will show whether this is recipe-general or seed-specific; (2) launched this cycle: medhead-abrupt-c1-acq1-cont40m, a +40M endurance continuation of the campaign's cleanest ACQ-PASS champion, to test whether the SAME late-entrenchment risk applies there too or whether irracq1's regression is recipe/seed-specific.

