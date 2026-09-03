# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-yawarm1p5

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-03T22:16:32+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi

**hypothesis**: Plain English: a live-sim joint-tracking probe (probe_joint_tracking.py, this cycle) found the SafetyLayer's per-tick yaw slew clip (physically pinned 0.375deg/tick@100Hz=37.5deg/s, must not be raised) saturates ~48% of combined walk+turn ticks but ~0% of pure-turn ticks at the identical wz_cmd -- the actual root cause of the combined-tick turn-authority gap. Two same-family levers were tried and refuted first: boosting omega (train.bc_anchor_teacher_omega_boost) recovered scripted-teacher wz but its RL canary showed a sign-asymmetric pure-turn regression (4/4 FAIL); discounting omega (probe_turn_authority.py --scripted-omega-boost <1, zero training this cycle) makes combined wz MONOTONICALLY WORSE with no clip-relief benefit. This is a different, new lever: TripodGait.combined_yaw_arm_scale inflates ONLY the atan2 denominator used to back out the yaw SERVO ANGLE from a leg's true tangential foot swing (hip/knee IK keeps the true r_planar/z target, so foot placement/lift are untouched) -- gated to combined ticks only, so pure-turn is bit-exact by construction. Zero-training gate (this cycle, both tools): at dose 2.0, probe_turn_authority.py --policy scripted shows combined wz_med improving 0.0723->0.0807 rad/s (both signs) at flat vx_med while pure-turn wz_med stays EXACTLY 0.2198 every dose (8/8 seeds/signs bit-identical); probe_joint_tracking.py confirms the mechanism -- combined clip_sat_frac_yaw drops 0.477->0.226 (toward the pure-turn 0.0 baseline) at the SAME dose, pure-turn's own clip_sat_frac_yaw untouched. This canary tests whether the scripted-level gain survives RL fine-tune (the omega-boost lesson: it might not).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M-step canary vs the matched control (cap29-stdwalklo-hi{,-s1}, identical recipe minus this flag): PASS if probe_turn_authority.py --vx-cmds combined-tick wz_med (vx=0.08,wz=+-0.25) on this checkpoint beats the checkpoint-scope combined comparator (cap29-stdwalklo-hi{,-s1} own combined read: +0.110/-0.171) on BOTH signs, without a pure-turn or straight-walk wz regression >10% vs control, and without new terminations on a walk-only flat DR-0 proxy read; FAIL if combined wz_med is flat/worse on either sign, or course/direction_err_med/gait_valid regress vs control. Read the FULL training-reward curve, not just the final-step number (rider c: the whole cap29 family showed a Q3 training-reward collapse in prior siblings).

