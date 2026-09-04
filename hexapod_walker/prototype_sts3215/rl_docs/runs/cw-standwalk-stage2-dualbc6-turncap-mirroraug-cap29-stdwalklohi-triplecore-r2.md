# cw-standwalk-stage2-dualbc6-turncap-mirroraug-cap29-stdwalklohi-triplecore-r2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-04T03:48:41+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-cap29-stdwalklohi-triplecore

**hypothesis**: Plain English: give pure-turn ticks their own GRU core (gru_policy.TripleGruActorCriticPolicy) instead of sharing core_a (walk) with combined-tick ticks -- the whole open-loop scalar-weight/geometry lever family for turn-while-walking closed 8/8 FAIL this week (bc_anchor_walk_combined_dose + TripodGait.combined_yaw_arm_scale), the shared signature being one representation computing both skills and fighting itself. Dual->Triple transplant (dual_to_triple_transplant): core_b (stance) verbatim, core_a copied into BOTH core_a and the new core_t so turn starts from already-decent walk competence, not scratch. FIRST-CANARY DISCIPLINE: train.yaw_credit_coef/_vf_coef/_grad_clip and the Dual-only log_std_split mechanism are BOTH DROPPED for this read. Single lever: architecture only, same reward/goal-mix/bc_anchor cfg as the cap29-stdwalklo-hi control. (r2: fixed a net_arch-derivation self-inflicted bug from the r1 attempt -- r1 crashed at 0 training steps before any corruption on dual_to_triple_transplant's own shape-mismatch guard because the fresh Triple build used the CLI net_arch default [128,128] instead of the Dual parent's actual [64,64]; code-only fix in train_ppo_mjx.py's --gru-triple branch, commit ff3cd275, verified past the crash point by the seed1 twin s1-r2 already RUNNING.)

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. 2M-step canary vs the matched control (cap29-stdwalklo-hi{,-s1}, identical recipe minus --gru-triple/the dropped yaw_credit+log_std_split mechanisms): PASS if probe_turn_authority.py --vx-cmds combined-tick wz_med (vx=0.08,wz=+-0.25) beats the checkpoint-scope combined comparator on BOTH signs WITHOUT a pure-turn wz regression >10% vs the SAME control, and without new terminations on a walk-only flat DR-0 proxy read. FAIL if combined wz_med is flat/worse on either sign, or the pure-turn cap is blown (same 8/8 signature), or course/direction_err_med/gait_valid regress vs control.

**refused_reason**: a process for cw-standwalk-stage2-dualbc6-turncap-mirroraug-cap29-stdwalklohi-triplecore-r2 already exists on hexapod-mjx-train-3

