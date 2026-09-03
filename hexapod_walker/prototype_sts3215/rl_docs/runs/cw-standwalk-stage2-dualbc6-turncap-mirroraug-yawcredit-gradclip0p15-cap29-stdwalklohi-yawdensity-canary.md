# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-yawdensity-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-03T12:21:26+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-canary

**hypothesis**: Plain English: the diet-rate lever (resample_s/jitter matching train-time command-change rate to the harsh eval diet) is now CLOSED both doses/both seeds (resamplematch-canary CANARY FAIL, resamplematch-mild-canary{,-s1} CANARY FAIL-shaped-PARTIAL) -- steering never moved even though the own-DR fall scare at the hard dose resolved cleanly at the milder dose, meaning the falls were dose-linked knife-edge instability, not evidence the diet lever helps steering. Per the tracks own pre-registered fork, this canary tests the STRUCTURAL alternative instead: goal.walk_yaw_zero_frac controls, independently of the linear (forward) command, whether a resampled walk segment gets a nonzero yaw-rate draw (currently 0.5 = 50% zero); turn-IN-PLACE itself is a SEPARATE, already-strong skill (goal.walk_turn_in_place_frac=0.30 forces whole dedicated-turn episodes, and probe_turn_authority confirms wz tracking is excellent, wz_med 0.15-0.22 rad/s across every diet arm tried) so that lever is left untouched. Does lowering walk_yaw_zero_frac 0.5->0.2 (nonzero-yaw segments 50%->80% of non-turn-in-place resampled segments, i.e. far more frequent STEERING-WHILE-WALKING-FORWARD exposure during training, the one thing every diet arm held constant) reduce the direction_err_med/course_err_1s_med gap measured under the SAME harsh stress_mix/resample_s=4.0/jitter=0.5 eval-time diet used throughout this investigation (the resamplematch-canary FAIL numbers: dir_err 38-41deg/course_err_1s 9.6-12.6deg/slip~3.8), independent of any training-time diet change (this run trains on the ancestors OWN gentle diet, resample_s=6.0/jitter=0.2, no stress_mix -- ONE lever changed from the ancestor: walk_yaw_zero_frac only)?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same instruments as the diet-family canaries, but the eval-time cfg-set for the walk-only read must OVERRIDE to the harsh diet regardless of this runs own (gentle) training cfg: goal.walk_cmd_mode=stress_mix, goal.walk_cmd_resample_s=4.0, goal.walk_cmd_resample_jitter=0.5 (matching resamplematch-canary FAIL-numbers protocol exactly) alongside probe_turn_authority (wz-cmds +-0.25, seeds 0/1) and eval_checkpoint.py --modes walk --per-mode 16 x {dr0,ownDR} x {det,sto}. PASS if dir_err_med or course_err_1s_med clears >=20% below the resamplematch-canary FAIL numbers (38-41deg/9.6-12.6deg) toward the acq1 baseline band (25-34deg/7.9-14.6deg) with slip staying <=~3.8 and ZERO new own-DR falls (turn authority already known strong from the ancestor, must stay >=0.07); PARTIAL if steering doesnt clearly move but nothing regresses; FAIL if turn authority regresses below 0.07, new own-DR falls appear, or the run behaves worse than the ancestor on any axis (implicating walk_yaw_zero_frac as not the driver either, closing the whole turn-authority-lever family and forcing an escalation to a full reward-mechanism change).

