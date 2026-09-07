# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis135

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-07T10:33:41+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8

**wandb_id**: wpr5ew7a

**hypothesis**: Plain English: the full 8-way heading widen (rear-diagonal +-135deg + straight-back 180deg added to the working 5-way set) makes this crutch-off realism composite ACQ-FAIL 3/3 by 40M with an identical new front-leg-pair[0,5] chronic sacrifice at held-out episodes 0/5 on every seed (CURRENT_TRUTHS/walkcurr STATUS 09-07 ~09:5x-10:0x) -- but that finding never isolated WHICH of the 3 new rear headings triggers the shortcut vs. the other two just riding along in the same 8-way draw. This is arm 1/3 of the pending bisection named in that finding's own remediation list: add ONLY +135deg to the already-ACQ-passed 5-way base (0/45/-45/90/-90), same s0 checkpoint widen8 itself warm-started from, same seed/budget/recipe otherwise. Skipping a redundant 2M canary: the already-PASSED widen8 canary (8-way superset) proved mechanism health for every one of these headings in combination, so a strict subset is an uninformative canary -- going straight to the 40M depth where the entrenchment actually appeared is the budget this question needs. Prediction-if-true (this heading is A driver): a chronic front-pair[0,5] (or similar) sacrifice reappears by 40M matching widen8-acq1's fingerprint. Prediction-if-false: panel stays clean (gait_valid near s0-acq1's own 21/24 baseline, no new chronic sacrifice) -- +135deg alone is not sufficient, narrowing the trigger to -135/180 or an interaction of >=2 new headings.

**gate**: PASS (heading exonerated) if 0 falls/24 AND gait_valid>=19/24 AND no chronic (<0.10 duty every flagged episode) single-leg or leg-pair sacrifice absent from s0-acq1's own clean panel. FAIL (heading implicated) if a chronic front-pair[0,5]-style (or any new persistent single-leg) sacrifice reappears, matching widen8-acq1's own fingerprint, regardless of reward trend (misalignment precedent already established for this exact composite).

**verdict**: Adding ONLY +135deg (one new rear-diagonal heading) to the ACQ-passed 5-way base holds clean at full 40M ACQ depth -- this specific heading is EXONERATED. Evidence: 0 falls/24 (no TERM in any of the 24 held-out episodes), gait_valid 21/24 -- identical total to this seed's own clean acq1 baseline (21/24) -- with the only sacrifice a single isolated walk/det/1 leg[0] episode (new location, but a single occurrence against 24 episodes is inside this campaign's own established noise band, not a repeating pattern) plus the SAME walk_startjitter/sto leg0/leg5 flag every clean baseline in this family already carries (2 episodes here vs 3 in the baseline -- slightly better, not worse). Video (walk_det_1 contact sheet) shows genuine forward translation across the frame with all legs cycling, not the near-stationary spin the two FAIL siblings below show. Why: this is the safe half of the pending widen8 heading-bisection -- widen8 (base5 + 135/-135/180 all three) FAILED 3/3 ACQ with a chronic front-pair[0,5] sacrifice; this arm isolates that +135 ALONE is not the trigger. What's next: recorded as the validated 6-way widened heading set for this composite (base5+135); do NOT stack it back with -135/180 (both independently implicated, see sibling verdicts) without the still-unbuilt role-aware reward mechanism.

