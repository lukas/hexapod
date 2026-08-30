# cw-standwalk-stage2-dualbc4-walkteach-turndiet-anchor14coef1-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T21:28:37+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc4-walkteach-anchor14coef1-canary

**wandb_id**: 67p8bc3m

**hypothesis**: Plain English: wave-2 of the walkteach/dualbc lineage -- does the SAME proven anchor14coef1 unified-policy fine-tune recipe (just CANARY PASSED on the all-heading dualbc4_walkteach base, det walk gait_valid 6/6, prog_med 0.43-0.46, course_err_1s_med 5.5-7.0deg) also learn genuine turn-in-place command tracking once the diet actually exposes commanded turns? Wave-1's diet had ZERO turn ticks (goal.walk_yaw_zero_frac=1.0, goal.walk_turn_in_place_frac=0 implicit default) -- any turn authority measured there was emergent/teacher-retained, never trained. This arm adds goal.walk_turn_in_place_frac=0.15 (existing mechanism, operator 08-10 command-exposure fix: 15% of episodes become a dedicated whole-episode turn-in-place command, 50/50 CW/CCW, matching the walk_stop_frac=0.15 precedent already in this cfg) PLUS reward.walk_kernel_yaw_gate=1.0 (the pre-registered, bank-proven fix for the freeze-the-turn exploit this exact reward stack reopens on turn ticks per the 19:3x root-cause finding -- WALKTEACH_YAWGATE bank in test_task_semantics.py pins park/turn ratio drops 0.98->0.42 with this one flag). Same init-from (dualbc4_walkteach.zip pre-RL BC base) and every other cfg key as the just-passed canary -- single/dual-lever change (turn exposure + its required reward-side gate), not a redesign.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (same convention as wave-1): WIRING CHECK bc_anchor_loss_walk/fill_walk nonzero every logged update. PASS/promote-to-8M if BOTH seeds show det walk gait_valid>=5/6, sacrificed legs ~0, progress_ratio not worse than wave-1's own 0.43-0.46 (turn exposure must not break straight-line walking), AND a turn-in-place probe (tip_ccw/tip_cw rollout or held wz command) shows real wz tracking -- median |wz_err| clearly below the un-gated freeze-floor prediction (wz_err should approach 0 during a sustained turn command, not sit near |wz_ref| the way a frozen body would). FAIL if gait_valid collapses, sacrificed legs reappear, straight-walk progress_ratio regresses hard, or turn probes still show frozen-body (wz_err ~ wz_ref) despite the yaw-gate fix -- the latter would mean the freeze-floor bank's fix doesn't transfer from the toy rollout to full PPO and needs a dig-in.

