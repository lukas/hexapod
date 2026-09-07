# cw-robotwalk-turns-20260907-yawref-acq8m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T06:10:21+00:00

**pod**: hexapod-mjx-train-1

**steps**: 8000000

**parent**: cw-robotwalk-turns-20260906-cont8m-resume1

**wandb_id**: 3j03b9ro

**hypothesis**: Plain English: the turning walker kept failing its steering gate not because it turns badly but because the reward and the gate metric both PAID it to refuse turning while walking -- fixing that frame bug (and slightly raising the pay for turning) should finally let one policy walk AND steer on command. Mechanism (bounded CPU replay, probe_combined_frame.py on the EXACT cw-robotwalk-turns-20260906 reward stack, combined cell vx=0.08 wz=+0.25): course-income/excess-sway/course-disp integrate (vx_ref,vy_ref) as a FIXED WORLD CHORD never rotated by wz_ref, while the velocity kernel is BODY-frame and obs (walk_obs_body_vel=2) has no world compass -- a wz-IGNORING straight walker out-earned the faithful arc-follower 2094.5 vs 1959.8 total (course income +597 vs +438) AND scored 0.90 deg vs 12.33 deg on the joygate chord course_err_1s metric: the 8.55->10.2->11.93 deg 'worsening' across cont8m/arcaware was the policy genuinely turning MORE, textbook 08-21 misalignment (both prior FAILs + the 09-06 17:3x 'look elsewhere' note are this bug). Fix: reward.walk_course_ref_yaw=1 rotates the course reference by the integrated commanded yaw anchored at each window-start body heading (body-frame joystick semantics: vx+wz = arc; bit-exact off, bank-proven) + walk_sway_arc_aware=1 (shadow path curves too) + minimal dose k_yaw_prog 1->2 covering the measured honest physics cost of arcing (post-fix gap -42.3, dose swing +157): replayed optimum is now the faithful arc (2204.3 > refusal 2089.2 > crab 2077.5), and the new eval course_yawref_* keys order behaviors correctly (arc 4.59 deg < refusal 7.06). Warm from the recovered 16M checkpoint (operator-named lineage; walk retention 24/24, 0 falls, best tip tracking 0.078/0.085). Prediction-if-true: combined-cell wz_err (stuck 0.21/0.23 across 16M+arcaware) finally moves toward the tip band, joygate course_yawref_err_1s_med <=5.17 deg, straight walking retained. Prediction-if-false: combined wz_err or course_yawref flat-or-worse with reward rising -- then the residual defect is NOT the reward frame (next suspects per 09-06 17:3x: PPO convergence at the operating point or the command generator), and no same-recipe continuation is funded. Strongest alternative: policy games doubled k_yaw_prog by over-rotating -- priced by its own overshoot decay + walk_yaw_hold_prog_gate, and gate (e) still fails standing-still smoothness.

**gate**: ACQ 8M, original absolute gates preserved, no relaxation: (a) tip both signs correct yaw sign and wz_err_med<0.076; (b) combined cells vx=0.08 wz=+-0.2..0.3 both signs: correct-sign achieved wz, wz_err AND course improved vs BOTH matched comparators (parent cw-robotwalk-turns-20260906-cont8m-resume1 checkpoint AND fresh Candidate B) on IDENTICAL cells/full gravity; (c) walk retained: det 8-heading zero falls, positive progress all, forward>=0.29m/12s, slip/m<=2.9, no sacrificed legs on video; (d) joygate stress_mix pass=true AND per_pass.dr0.course_yawref_err_1s_med<=5.17deg (the frame-corrected metric, SAME absolute bar; comparators re-read on the same corrected key -- legacy chord course_err_1s_med reported for continuity but is proven to pay turn-refusal 0.90 vs 12.33 deg, probe_combined_frame, so it is diagnostic-only for yaw-capable candidates); (e) translation cells require real progress, standing-still smoothness = FAIL; clean translation/reverse/release/both-arcs video. Falsification: combined wz_err or course_yawref flat-or-worse at 8M with reward rising = the frame fix is not the (only) bug -- next suspects PPO convergence at operating point / command generator; no same-recipe continuation.

