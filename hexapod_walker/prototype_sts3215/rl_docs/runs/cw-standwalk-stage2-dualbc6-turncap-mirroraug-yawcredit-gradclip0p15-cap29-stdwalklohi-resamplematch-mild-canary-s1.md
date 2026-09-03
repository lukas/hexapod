# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-resamplematch-mild-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-03T10:45:56+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-resamplematch-canary

**wandb_id**: 7c7vxb9i

**hypothesis**: Seed replicate of resamplematch-mild-canary (seed0, train-1, RUNNING): same milder single-lever retry (resample_s 4.0->5.0, jitter 0.5->0.35, walk_cmd_mode=stress_mix kept) off the resamplematch-canary CANARY-FAIL-MECHANISM finding (steering unchanged/worse + new immediate own-DR tilt-roll falls at the full-stress dose). Second seed closes the pass-rate question before any acquisition-scale commitment.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same as resamplematch-mild-canary seed0's gate (probe_turn_authority + det/sto walk-mode eval_checkpoint.py read under stress_mix, dr0+owndr): PASS if BOTH seeds clear >=20% steering improvement with zero new own-DR falls; FAIL if either seed reproduces the immediate-tilt own-DR falls or turn authority regression.

