# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-multiteach-b05-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T04:59:02+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-selomegaboost3p0-s1

**wandb_id**: j2cuhm67

**hypothesis**: Plain English: instead of pulling harder on the SAME already-degraded combined-turn demo -- every static reweight of that one target (combined_skip, combined_dose, yaw_arm_scale, omega_boost, selective_omega_boost) already failed 4/4-per-cell across ~20 arms -- this teaches toward a SECOND, more ambitious demo (the undegraded pure-turn foot geometry) that only takes over gradually as training progresses, so early updates still lock onto the safe/proven degraded gait before the policy is nudged toward the more aggressive one. Mechanism (built + tested this cycle, 137/137 rl_move/tests/test_bc_anchor.py green, 10 new): sim_env now runs a SEPARATE persistent scripted-gait clock alongside the existing walk BC-anchor teacher, driven by the identical wall-clock ticks but with forward speed always zeroed (the pure-turn-in-place geometry TripodGait would command if this tick had no forward component); bc_anchor.py blends the two targets at LOSS TIME on a schedule ramping 0 -> train.bc_anchor_multiteacher_blend over the first train.bc_anchor_multiteacher_schedule_frac=0.5 of training progress (mirrors this recipe's own --log-std-anneal-frac 0.5 cadence). Untried axis: every prior lever held ONE static dose/target for the WHOLE run; none varied the target over TRAINING PROGRESS. This canary asks whether phasing the aggressive target in late (once the shared dual-core representation has already consolidated on the safe/degraded gait) avoids the shared-representation drift that broke every static-dose sibling. If this ALSO fails the identical sign-asymmetric pure-turn regression, the reward/supervision-side lever space for standwalk item-1/item-2 closes for good and the only remaining move is a gait-structure change (turn-dedicated tripod phase offset) or a DONE-gate turn-authority renegotiation.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M-step canary vs the matched control (cap29-stdwalklo-hi{,-s1}, identical recipe minus this flag, same comparator this whole lever family uses): PASS if probe_turn_authority.py --vx-cmds combined-tick wz_med (vx=0.08,wz=+-0.25) on this checkpoint beats the checkpoint-scope combined comparator (seed0 control: +0.110/-0.170; seed1 control: +0.086/-0.142) on BOTH signs, without a pure-turn wz_med regression >10% vs control (seed0 pure-turn +0.223/-0.250; seed1 +0.226/-0.247) or straight-walk vx regression >10%, and without new terminations on a walk-only flat DR-0 proxy read; FAIL if combined wz_med is flat/worse on either sign, or pure-turn/course/direction_err_med/gait_valid regress past the cap vs control -- same closing criterion as every other cell in this lever family so a 4/4 FAIL here joins them as one axis-level finding.

