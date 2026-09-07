# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-irr

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-07T08:33:50+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s2-acq1

**wandb_id**: ao9cqm48

**hypothesis**: Plain English: same question as the s1 twin -- tests the command-timing-irregularity axis (jittered heading-resample interval, already validated composable at 1g via medhead-irrfwd-c1-acq1 PASS+cont40m HOLDS) independently on the full-DR crutch-off composite, init from this seed's own ACQ-passed 40M crutch-off checkpoint. Prediction-if-true: 0 falls, gait_valid majority (>=18/24). Prediction-if-false: falls or chronic single-leg sacrifice under irregular re-commands.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY (2M): held-out gate on own cfg (5-heading medium set with jittered resample timing, det+sto, walk+walk_startjitter, 24 eps). PASS if 0 falls/terminations AND gait_valid >=18/24. FAIL if any fall or chronic (<0.10-duty every episode) single-leg sacrifice.

**verdict**: CANARY FAIL - MECHANISM: 2nd seed independently confirms s1-irr's finding -- irregular command-timing (goal.walk_cmd_resample_jitter=0.5) induces a fall at the EXACT SAME episode index (walk/sto ep4, tilt_roll) not present in this seed's own clean s2-acq1 baseline (21/24 gv, 0 terms, no term at ep4). gait_valid drops to 20/24, sac spreads into walk/det, walk_startjitter/det, walk_startjitter/sto -- again broader than the parent's baseline signature (walk_startjitter/sto only). Why: identical failure mode + identical episode index across 2 independent seeds is decisive, not variance -- closes the crutch-off-composite irr-timing axis 2/2 FAIL. This is the same jitter axis that already composed cleanly at 1g without full DR (medhead-irrfwd-c1-acq1 ACQ PASS); the regression is specific to the full-DR composite, likely a jitter+push/DR interaction. Next: do not relaunch bare irr-timing on this composite; if this axis matters for the DONE gate, the fix needs to target the jitter/push interaction (e.g. suppress mid-turn resample jitter during an active push window) as a new mechanism, not a bare relaunch.

