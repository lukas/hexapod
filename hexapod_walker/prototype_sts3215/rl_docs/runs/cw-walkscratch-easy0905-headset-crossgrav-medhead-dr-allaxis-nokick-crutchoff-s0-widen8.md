# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T07:39:03+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-acq1

**wandb_id**: kmyjc7su

**hypothesis**: Plain English: s0's crutch-off full-realism composite now walks and survives pushes at 40M ACQ (just PASSed this cycle, completing the 3-seed crutch-isolation set), but like its s1/s2 siblings it has only ever been commanded the 5-heading medium set at fixed 0.06 m/s. Single-axis test, identical recipe to the already-PASSed s1-widen8/s2-widen8 canaries: widen ONLY goal.walk_heading_set to the full 8-way set (adds rear-diagonal +-135deg and straight-back 180deg), init from s0's own ACQ-passed 40M checkpoint. Prediction-if-true (composable, matching s1/s2): 0 falls, gait_valid stays majority on the 8-way panel at 2M. Prediction-if-false: tilt falls reappear (the composite's known push-fragility fingerprint) or a chronic single-leg sacrifice on rear headings -- would be the ODD one out vs s1/s2, worth a dig-in given s0 is the seed whose crutch-ON fragility only appeared at 40M not 2M.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY (mechanism health, 2M): held-out gate on own cfg (8-way heading set, det+sto, walk+walk_startjitter, 24 eps). PASS if 0 falls/terminations AND gait_valid >=18/24 (matching s1/s2-widen8's own bar). FAIL if any fall or chronic (<0.10-duty every episode) single-leg sacrifice. Low dir-valid confined to the 4 new headings without falls = inconclusive-continue (budget, not mechanism).

