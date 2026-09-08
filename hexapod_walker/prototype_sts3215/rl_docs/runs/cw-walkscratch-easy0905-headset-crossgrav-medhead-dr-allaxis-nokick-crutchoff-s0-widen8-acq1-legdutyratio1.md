# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1-legdutyratio1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-08T00:19:21+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widen8-acq1

**hypothesis**: PLAIN ENGLISH: same new additive per-leg duty-balance reward charge as s0-widen8-acq1-legdutyratiofresh, but RETROFIT onto the ALREADY-ENTRENCHED 40M widen8-acq1 checkpoint (--init-from-source) instead of applied from scratch -- tests whether the charge can repair a habit that already baked in over 40M steps, the same fresh-vs-retrofit split every prior mechanism in this campaign (legdutyterm1 vs legdutyfresh) tested. PREDICTION IF TRUE: the entrenched leg's duty recovers within the 2M canary budget (peer-relative ratio climbing toward 0.22+), gait_valid improves vs the undosed baseline. PREDICTION IF FALSE: the entrenched sacrifice persists (matching every prior retrofit-class mechanism's own 0/N record), or reward destabilizes as the newly-charged habit gets unlearned -- the charge may need a longer budget than 2M to unlearn 40M steps of habit even if it eventually works (08-21 continuation candidate, not a same-cycle redesign).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS: entrenched leg's duty recovers (peer-relative ratio >=0.22 majority of episodes), gait_valid improves materially vs the undosed s0-widen8-acq1 baseline, 0 new falls. CONTINUE (08-21): reward rising, charge measurably firing+declining in wandb_history.csv, gait_valid trending up but short at 2M -- fund a longer continuation before judging repair-of-entrenched-habit FAIL. FAIL: sacrifice persists AND the charge has gone quiet/saturated (not still applying real pressure) by canary end.

