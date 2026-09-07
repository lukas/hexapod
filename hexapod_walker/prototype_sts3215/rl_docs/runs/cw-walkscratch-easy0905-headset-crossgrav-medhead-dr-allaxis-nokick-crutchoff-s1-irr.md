# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-irr

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T08:35:06+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-acq1

**wandb_id**: c6pza3js

**hypothesis**: Plain English: the crutch-off full-realism composite has now proven ONE realism rung (8-way heading breadth, CANARY PASS both seeds this cycle). The other single-axis widening already validated at 1g without full DR (medhead-irrfwd-c1-acq1, PASS+cont40m HOLDS) is irregular command TIMING -- jittering the fixed 6s heading-resample interval by +-50% instead of a clean metronome. This tests that axis independently on the full-DR crutch-off composite (NOT stacked with widen8, to keep single-axis attribution clean), init from this seed's own ACQ-passed 40M crutch-off checkpoint. Prediction-if-true (composable): 0 falls, gait_valid majority (>=18/24) on the same 5-heading medium set with jittered timing, matching how irr composed cleanly at 1g. Prediction-if-false: falls or a chronic single-leg sacrifice appear specifically under irregular re-commands (the composite's known push-fragility fingerprint could interact with an unpredictable heading change the same way it interacted with a physical push).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY (2M): held-out gate on own cfg (5-heading medium set with jittered resample timing, det+sto, walk+walk_startjitter, 24 eps). PASS if 0 falls/terminations AND gait_valid >=18/24. FAIL if any fall or chronic (<0.10-duty every episode) single-leg sacrifice.

