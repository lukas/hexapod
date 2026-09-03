# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-resamplematch-mild-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-03T10:33:08+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-resamplematch-canary

**wandb_id**: km91ejhd

**hypothesis**: Plain English: the just-read resamplematch-canary (full eval-diet match, resample_s 4.0/jitter 0.5) CANARY-FAILED its own pre-registered gate at 2M steps -- turn authority held (wz_med 0.17-0.18 >> 0.07) but steering did NOT improve (dir_err 38-41deg / slip 3.6-4.7 / prog 0.22-0.25, all WORSE than the same-harness stdwalklohi-acq1 baseline's 25-34deg/2.3-3.8/0.31-0.40) AND a NEW own-DR fall mode appeared (3/16 owndr-det episodes: immediate t=0.01s tilt_roll, all six legs sacrificed -- not seen in the ancestor's own-DR reads). Per this track's own pre-registered FAIL branch ('diet too hard, retry milder resample_s'): does a MILDER version of the same diet-match lever (resample_s 4.0->5.0, jitter 0.5->0.35 -- halfway between the ancestor's training default 6.0/0.2 and the failed hard-stress eval diet 4.0/0.5, keeping walk_cmd_mode=stress_mix so it is still testing the same train/eval-diet-mismatch idea) avoid the new own-DR falls while still nudging steering, or does even this milder dose already break robustness (pointing at walk_cmd_mode=stress_mix's turn-in-place/near-zero-net-displacement segments, not the resample rate, as the harmful ingredient)?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same instruments as resamplematch-canary's own gate, run on the run's own pod (probe_turn_authority wz-cmds 0.25,-0.25 seeds 0,1; eval_checkpoint.py --modes walk --per-mode 16 det+sto x dr-scale 0.0/0.5, same full obs-contract cfg-set stack). PASS if dir_err_med or course_err_1s_med clears >=20% below the resamplematch-canary FAIL numbers (38-41deg/9.6-12.6deg) toward the acq1 baseline band (25-34deg/7.9-14.6deg) with slip staying <=~3.8 and ZERO new falls under own-DR; PARTIAL if falls are gone and turn-authority holds but steering doesn't clearly move; FAIL if the immediate-tilt own-DR falls persist even at this milder dose (implicates walk_cmd_mode=stress_mix itself, not resample_s/jitter, as the next lever) or turn authority regresses below 0.07.

