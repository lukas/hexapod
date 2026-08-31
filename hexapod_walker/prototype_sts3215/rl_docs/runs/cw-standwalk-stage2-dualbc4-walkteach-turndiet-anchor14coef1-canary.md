# cw-standwalk-stage2-dualbc4-walkteach-turndiet-anchor14coef1-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-08-30T21:28:37+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc4-walkteach-anchor14coef1-canary

**wandb_id**: 67p8bc3m

**hypothesis**: Plain English: wave-2 of the walkteach/dualbc lineage -- does the SAME proven anchor14coef1 unified-policy fine-tune recipe (just CANARY PASSED on the all-heading dualbc4_walkteach base, det walk gait_valid 6/6, prog_med 0.43-0.46, course_err_1s_med 5.5-7.0deg) also learn genuine turn-in-place command tracking once the diet actually exposes commanded turns? Wave-1's diet had ZERO turn ticks (goal.walk_yaw_zero_frac=1.0, goal.walk_turn_in_place_frac=0 implicit default) -- any turn authority measured there was emergent/teacher-retained, never trained. This arm adds goal.walk_turn_in_place_frac=0.15 (existing mechanism, operator 08-10 command-exposure fix: 15% of episodes become a dedicated whole-episode turn-in-place command, 50/50 CW/CCW, matching the walk_stop_frac=0.15 precedent already in this cfg) PLUS reward.walk_kernel_yaw_gate=1.0 (the pre-registered, bank-proven fix for the freeze-the-turn exploit this exact reward stack reopens on turn ticks per the 19:3x root-cause finding -- WALKTEACH_YAWGATE bank in test_task_semantics.py pins park/turn ratio drops 0.98->0.42 with this one flag). Same init-from (dualbc4_walkteach.zip pre-RL BC base) and every other cfg key as the just-passed canary -- single/dual-lever change (turn exposure + its required reward-side gate), not a redesign.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (same convention as wave-1): WIRING CHECK bc_anchor_loss_walk/fill_walk nonzero every logged update. PASS/promote-to-8M if BOTH seeds show det walk gait_valid>=5/6, sacrificed legs ~0, progress_ratio not worse than wave-1's own 0.43-0.46 (turn exposure must not break straight-line walking), AND a turn-in-place probe (tip_ccw/tip_cw rollout or held wz command) shows real wz tracking -- median |wz_err| clearly below the un-gated freeze-floor prediction (wz_err should approach 0 during a sustained turn command, not sit near |wz_ref| the way a frozen body would). FAIL if gait_valid collapses, sacrificed legs reappear, straight-walk progress_ratio regresses hard, or turn probes still show frozen-body (wz_err ~ wz_ref) despite the yaw-gate fix -- the latter would mean the freeze-floor bank's fix doesn't transfer from the toy rollout to full PPO and needs a dig-in.

**verdict**: CANARY FAIL - MECHANISM (seed0, joint with the already-recorded -s1 FAIL -- this seed was never independently probed before, closing an untriaged ledger gap). Same turn-in-place exposure (goal.walk_turn_in_place_frac=0.15, walk_yaw_zero_frac=1.0) plus the yaw-gate fix (reward.walk_kernel_yaw_gate=1.0) still produces zero turn authority: probe_turn_authority (full 88-key launch cfg-set replayed exactly, walk-mode-filtered, seeds 0/1) gives wz_med in [0.0002,0.0023] both wz_cmd signs -- wz_err_med 0.2477-0.2502, indistinguishable from the frozen-body prediction |wz_cmd|=0.25, same as -s1's own reading. Straight-walk health is clean and matches -s1: own gate walk/det gait_valid 6/6, sacrificed_legs 0/6, 0 terminations, progress_ratio med 0.39-0.42, course_err_1s_med 4.2-4.4deg, slip_per_m ~2.0-2.5 -- so this is a clean mechanism-exonerated FAIL (turn clause fails, straight-walk clause is fine), not a gait-collapse confound. Confirms the joint call: turn-diet exposure alone (without direct yaw income) does not transfer past the toy-rollout bank into full PPO on either seed. No promote to 8M. This closes the same lineage's already-executed next step (turnpay canary, direct income) -- already independently verdicted CANARY FAIL - MECHANISM too.

