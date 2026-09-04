# cap29-stdwalklohi-selomegaboost4p0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-04T06:43:34+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cap29-stdwalklohi-yawarm1p5

**hypothesis**: Plain English: a new teacher-side lever boosts the REAL foot displacement (not just the commanded yaw angle) for only the 3 legs the vx cross term weakens during a combined walk+turn tick, restoring their pure-turn-level torque, while leaving the 3 already-strong legs byte-identical. Every prior candidate on this axis (uniform combined_yaw_arm_scale, selective combined_yaw_amplify_scale, the unwired detangle-the-vx-cross-term idea) only reshaped the commanded YAW ANGLE via an atan2-denominator trick and all failed because shrinking the commanded angle shrinks the physical rotation right along with it. This lever is mechanically different: on a combined tick it recomputes ONLY the attenuated legs true foot target (dx/dy/dz, hip+knee included, via TripodGait.combined_selective_omega_boost) using a boosted omega -- mirroring the already-tried UNIFORM train.bc_anchor_teacher_omega_boost (proven to recover real scripted-teacher wz at a vx cost) but restricted to only the legs that lose authority to vx cancellation. Zero-training scripted-teacher validation this cycle (probe_turn_authority.py --policy scripted --scripted-selective-omega-boost): dose 3.0-4.0 raises combined wz_med from ~0.081/-0.077 toward 0.20-0.24/-0.20-0.24 rad/s (BOTH signs, sign-symmetric -- unlike every prior lever's sign-asymmetric response) with pure-turn/pure-walk BIT-EXACT untouched (the combined-tick gate lives inside TripodGait itself); at dose 3.0 it beats the already-RL-tested uniform omega_boost's own best dose on real wz (0.231 vs 0.168 rad/s, same command). This canary tests whether that clean, sign-symmetric scripted-level gain survives RL fine-tuning, where every prior teacher-side lever (uniform omega_boost, yaw_arm_scale, combined-tick BC-anchor-skip) failed on a SIGN-ASYMMETRIC pure-turn regression >10% despite the pure-turn training target itself being untouched by construction -- if this ALSO fails the same way, that closes the geometry/teacher-lever axis for good and the honest next move is a gait-structure change or a DONE-gate turn-authority renegotiation.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M-step canary vs the matched control (cap29-stdwalklo-hi{,-s1}, identical recipe minus this flag): PASS if probe_turn_authority.py --vx-cmds combined-tick wz_med (vx=0.08,wz=+-0.25) on this checkpoint beats the checkpoint-scope combined comparator (seed0 control: +0.110/-0.170; seed1 control: +0.086/-0.142) on BOTH signs, without a pure-turn wz_med regression >10% vs control (seed0 pure-turn +0.223/-0.250; seed1 +0.226/-0.247) or straight-walk vx regression >10%, and without new terminations on a walk-only flat DR-0 proxy read; FAIL if combined wz_med is flat/worse on either sign, or pure-turn/course/direction_err_med/gait_valid regress past the cap vs control. Read the FULL training-reward curve, not just the final-step number (rider c: the whole cap29 family showed a Q3 training-reward collapse in prior siblings).

**refused_reason**: experiments must use the cw- prefix

