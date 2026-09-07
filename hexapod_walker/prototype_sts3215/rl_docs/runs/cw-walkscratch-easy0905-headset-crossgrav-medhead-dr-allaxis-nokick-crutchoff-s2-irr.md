# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-irr

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T08:33:50+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-acq1

**wandb_id**: ao9cqm48

**hypothesis**: Plain English: same question as the s1 twin -- tests the command-timing-irregularity axis (jittered heading-resample interval, already validated composable at 1g via medhead-irrfwd-c1-acq1 PASS+cont40m HOLDS) independently on the full-DR crutch-off composite, init from this seed's own ACQ-passed 40M crutch-off checkpoint. Prediction-if-true: 0 falls, gait_valid majority (>=18/24). Prediction-if-false: falls or chronic single-leg sacrifice under irregular re-commands.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY (2M): held-out gate on own cfg (5-heading medium set with jittered resample timing, det+sto, walk+walk_startjitter, 24 eps). PASS if 0 falls/terminations AND gait_valid >=18/24. FAIL if any fall or chronic (<0.10-duty every episode) single-leg sacrifice.

