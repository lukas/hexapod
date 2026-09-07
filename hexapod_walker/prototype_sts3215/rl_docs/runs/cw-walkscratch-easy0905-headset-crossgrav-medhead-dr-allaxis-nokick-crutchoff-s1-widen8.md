# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-07T07:15:51+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-acq1

**wandb_id**: 3cfy682l

**hypothesis**: Plain English: the crutch-off full-realism composite now walks and survives pushes at 40M on this seed, but it has only ever been commanded the 5-heading medium set at fixed 0.06 m/s -- the next realism rung is command breadth. Single-axis test: widen ONLY goal.walk_heading_set to the full 8-way set (adds rear-diagonal +-135deg and straight-back 180deg), init from this seed's own ACQ-passed 40M checkpoint. Prediction-if-true (composable): 0 falls, gait_valid stays majority on the 8-way panel at 2M, matching how the same widening composed cleanly at 1g WITHOUT DR (widenfwd-c1/c2 PASS+cont40m). Prediction-if-false: tilt falls reappear (the composite's known push-fragility fingerprint) or a chronic single-leg sacrifice on rear headings. Strongest alternative: low dir-valid on the 4 NEW headings without falls = 2M budget too short to adapt, which reads as continue-not-FAIL per the 08-21 ruling.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY (mechanism health, 2M): held-out gate on own cfg (8-way heading set, det+sto, walk+walk_startjitter, 24 eps). PASS if 0 falls/terminations AND gait_valid >=18/24. FAIL if any fall or chronic (<0.10-duty every episode) single-leg sacrifice. Low dir-valid confined to the 4 new headings without falls = inconclusive-continue (budget, not mechanism).

**verdict**: CANARY PASS. The crutch-off full-realism composite now takes the full 8-way heading set (adds rear-diagonal +-135deg and straight-back 180deg) on top of its already-ACQ-passed 40M push-hardened checkpoint. 0 falls/terminations across all 24 held-out episodes; gait_valid 21/24 (walk/det 5/6, walk/sto 6/6, startjitter/det 6/6, startjitter/sto 4/6), matching the pre-registered PASS bar (0 falls AND gait_valid>=18/24). Non-chronic single-leg flags only on the hardest startjitter/sto cell, same soft-flag pattern already seen on this recipe's other canaries. Confirms the 8-way widening composes cleanly on the crutch-off composite at mechanism-health scale, matching the precedent that this same widening already composed cleanly at 1g without DR (widenfwd-c1/c2 PASS+cont40m). Next: does it hold at 40M ACQ scale under the full composite (the real question, since this composite's known failure mode only appeared at ACQ depth for one of the three crutch-isolation seeds) -- launching the ACQ continuation now.

