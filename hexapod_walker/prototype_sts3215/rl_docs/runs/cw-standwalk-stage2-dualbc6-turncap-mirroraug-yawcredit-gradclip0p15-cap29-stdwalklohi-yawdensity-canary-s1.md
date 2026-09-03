# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-yawdensity-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-03T12:20:11+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-canary

**wandb_id**: rfas35tp

**hypothesis**: Seed replicate of yawdensity-canary (seed0): same single lever (walk_yaw_zero_frac 0.5->0.2), second seed closes the pass-rate question before any acquisition-scale commitment.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same instruments as the diet-family canaries, but the eval-time cfg-set for the walk-only read must OVERRIDE to the harsh diet regardless of this runs own (gentle) training cfg: goal.walk_cmd_mode=stress_mix, goal.walk_cmd_resample_s=4.0, goal.walk_cmd_resample_jitter=0.5 (matching resamplematch-canary FAIL-numbers protocol exactly) alongside probe_turn_authority (wz-cmds +-0.25, seeds 0/1) and eval_checkpoint.py --modes walk --per-mode 16 x {dr0,ownDR} x {det,sto}. PASS if dir_err_med or course_err_1s_med clears >=20% below the resamplematch-canary FAIL numbers (38-41deg/9.6-12.6deg) toward the acq1 baseline band (25-34deg/7.9-14.6deg) with slip staying <=~3.8 and ZERO new own-DR falls (turn authority already known strong from the ancestor, must stay >=0.07); PARTIAL if steering doesnt clearly move but nothing regresses; FAIL if turn authority regresses below 0.07, new own-DR falls appear, or the run behaves worse than the ancestor on any axis (implicating walk_yaw_zero_frac as not the driver either, closing the whole turn-authority-lever family and forcing an escalation to a full reward-mechanism change).

