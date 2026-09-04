# cw-standwalk-stage2-dualbc6-turncap-mirroraug-cap29-stdwalklohi-triplecore

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAILED

**created**: 2026-09-04T03:31:06+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi

**hypothesis**: Plain English: give pure-turn ticks their own GRU core (gru_policy.TripleGruActorCriticPolicy) instead of sharing core_a (walk) with combined-tick ticks -- the whole open-loop scalar-weight/geometry lever family for turn-while-walking closed 8/8 FAIL this week (bc_anchor_walk_combined_dose + TripodGait.combined_yaw_arm_scale), the shared signature being one representation computing both skills and fighting itself. Dual->Triple transplant (dual_to_triple_transplant): core_b (stance) verbatim, core_a copied into BOTH core_a and the new core_t so turn starts from already-decent walk competence, not scratch. FIRST-CANARY DISCIPLINE (per the design's own mitigation): train.yaw_credit_coef/_vf_coef/_grad_clip and the Dual-only log_std_split/--log-std-anneal-core mechanism are BOTH DROPPED for this read (isolates the core-split's own effect from those orthogonal mechanisms); warm-starting FROM a yaw-credit-trained checkpoint is fine since yaw_credit is a training-time hook, not a permanent weight change. Single lever: architecture only, same reward/goal-mix/bc_anchor cfg as the cap29-stdwalklo-hi control.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait. 2M-step canary vs the matched control (cap29-stdwalklo-hi{,-s1}, identical recipe minus --gru-triple/the dropped yaw_credit+log_std_split mechanisms): PASS if probe_turn_authority.py --vx-cmds combined-tick wz_med (vx=0.08,wz=+-0.25) beats the checkpoint-scope combined comparator on BOTH signs WITHOUT a pure-turn wz regression >10% vs the SAME control, and without new terminations on a walk-only flat DR-0 proxy read -- the exact bar every dose/geometry-lever cell in the 8/8-FAIL family was held to, so the read is apples-to-apples with that closed family. FAIL if combined wz_med is flat/worse on either sign, or the pure-turn cap is blown (same 8/8 signature), or course/direction_err_med/gait_valid regress vs control. Read the full training-reward curve (rider c): the whole cap29 family showed a Q3 training-reward collapse in prior siblings.

**verdict**: CANARY FAIL - INFRASTRUCTURE: self-inflicted code bug, not a mechanism-health finding. TripleGruActorCriticPolicy (item-2's new protected-turn-core architecture, built this cycle) crashed at step 0 on dual_to_triple_transplant's own shape-mismatch guard -- the Dual parent lineage (cap29-stdwalklo-hi) was actually built with net_arch=None (SB3 default {pi:[64,64],vf:[64,64]}), but the fresh Triple construction blindly used the CLI --net-arch default [128,128], so policy_net.0 shapes (64,256) vs (128,256) never matched. Zero corruption (the transplant's own guard caught it before any weight copy), zero training steps; both seeds (s0/s1) hit the identical crash within seconds. FIX (train_ppo_mjx.py --gru-triple branch): derive net_arch AND lstm_hidden_size from the loaded Dual checkpoint itself, never the CLI defaults, when building the fresh Triple policy -- every other --init-from path reconstructs via algo_cls.load() which inherits the checkpoint's own policy_kwargs for free; Triple's from-scratch construction did not. Committed ff3cd275. Next: r2 seed-matched retries (s1-r2 already RUNNING past the crash point on train-8; seed0 r2 launching this cycle).

**failed_reason**: self-inflicted: dual_to_triple_transplant net_arch mismatch (old checkpoint's lineage was built with net_arch=None -> SB3 default {pi:[64,64],vf:[64,64]}, fresh Triple construction blindly used the CLI --net-arch default [128,128]); the transplant's own shape check correctly refused before any corruption/training (0 steps), fixed in code (derive net_arch/lstm_hidden_size from the loaded Dual checkpoint, not the CLI defaults), relaunching

