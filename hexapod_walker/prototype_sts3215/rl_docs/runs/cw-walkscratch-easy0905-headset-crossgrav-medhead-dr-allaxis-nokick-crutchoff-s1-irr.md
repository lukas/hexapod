# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-irr

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-07T08:35:06+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-acq1

**wandb_id**: c6pza3js

**hypothesis**: Plain English: the crutch-off full-realism composite has now proven ONE realism rung (8-way heading breadth, CANARY PASS both seeds this cycle). The other single-axis widening already validated at 1g without full DR (medhead-irrfwd-c1-acq1, PASS+cont40m HOLDS) is irregular command TIMING -- jittering the fixed 6s heading-resample interval by +-50% instead of a clean metronome. This tests that axis independently on the full-DR crutch-off composite (NOT stacked with widen8, to keep single-axis attribution clean), init from this seed's own ACQ-passed 40M crutch-off checkpoint. Prediction-if-true (composable): 0 falls, gait_valid majority (>=18/24) on the same 5-heading medium set with jittered timing, matching how irr composed cleanly at 1g. Prediction-if-false: falls or a chronic single-leg sacrifice appear specifically under irregular re-commands (the composite's known push-fragility fingerprint could interact with an unpredictable heading change the same way it interacted with a physical push).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY (2M): held-out gate on own cfg (5-heading medium set with jittered resample timing, det+sto, walk+walk_startjitter, 24 eps). PASS if 0 falls/terminations AND gait_valid >=18/24. FAIL if any fall or chronic (<0.10-duty every episode) single-leg sacrifice.

**verdict**: CANARY FAIL - MECHANISM: irregular command-timing (goal.walk_cmd_resample_jitter=0.5, +-50% jitter on the 6s heading-resample interval) induces a reproducible new fall on the crutch-off full-DR composite that the clean parent baseline (s1-acq1, 21/24 gv, 0 terms) does not show. Evidence: walk/sto ep4 TERMINATES (tilt_roll) -- the parent's own s1-acq1 gate does NOT terminate at that same episode index (prog 1.243, no term); gait_valid also drops to 19/24 with sac spreading into walk/det and walk_startjitter/det, modes the parent's clean signature never touches (parent's only flag is walk_startjitter/sto). Why: matches the arm's own pre-registered 'Prediction-if-false' branch exactly ('falls...appear specifically under irregular re-commands'); this is a genuine regression, not noise -- see s2-irr sibling for an identical fall at the identical episode index (decisive 2/2 reproduction). Next: irregular-timing does NOT compose on the crutch-off full-DR composite as-is; do not relaunch this exact axis without a mitigation (e.g. dampen jitter under active pushes/DR, or investigate whether the tilt_roll fall coincides with a push+resample collision). Note: the trio's 3rd seed (s0-irr) was mis-launched at ACQ (40M) steps instead of a 2M canary and was mechanically SEED-PRUNED for reward stagnation before a clean canary read was possible -- not informative for this verdict.

