# cw-standwalk-stage2-dualbc6-turncap-mirroraug-cap29-stdwalklohi-triplecore-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAILED

**created**: 2026-09-04T03:31:38+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi

**hypothesis**: Plain English: give pure-turn ticks their own GRU core (gru_policy.TripleGruActorCriticPolicy) instead of sharing core_a (walk) with combined-tick ticks -- the whole open-loop scalar-weight/geometry lever family for turn-while-walking closed 8/8 FAIL this week (bc_anchor_walk_combined_dose + TripodGait.combined_yaw_arm_scale), the shared signature being one representation computing both skills and fighting itself. Dual->Triple transplant (dual_to_triple_transplant): core_b (stance) verbatim, core_a copied into BOTH core_a and the new core_t so turn starts from already-decent walk competence, not scratch. FIRST-CANARY DISCIPLINE (per the design's own mitigation): train.yaw_credit_coef/_vf_coef/_grad_clip and the Dual-only log_std_split/--log-std-anneal-core mechanism are BOTH DROPPED for this read (isolates the core-split's own effect from those orthogonal mechanisms); warm-starting FROM a yaw-credit-trained checkpoint is fine since yaw_credit is a training-time hook, not a permanent weight change. Single lever: architecture only, same reward/goal-mix/bc_anchor cfg as the cap29-stdwalklo-hi control.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait. 2M-step canary vs the matched control (cap29-stdwalklo-hi{,-s1}, identical recipe minus --gru-triple/the dropped yaw_credit+log_std_split mechanisms): PASS if probe_turn_authority.py --vx-cmds combined-tick wz_med (vx=0.08,wz=+-0.25) beats the checkpoint-scope combined comparator on BOTH signs WITHOUT a pure-turn wz regression >10% vs the SAME control, and without new terminations on a walk-only flat DR-0 proxy read -- the exact bar every dose/geometry-lever cell in the 8/8-FAIL family was held to, so the read is apples-to-apples with that closed family. FAIL if combined wz_med is flat/worse on either sign, or the pure-turn cap is blown (same 8/8 signature), or course/direction_err_med/gait_valid regress vs control. Read the full training-reward curve (rider c): the whole cap29 family showed a Q3 training-reward collapse in prior siblings.

**failed_reason**: self-inflicted: identical net_arch-mismatch crash as the seed0 twin (see that entry); fixed in code, relaunching

