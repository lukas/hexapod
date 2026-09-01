# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip2p0-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-01T11:07:33+00:00

**pod**: hexapod-mjx-train-6

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-canary-rr1

**hypothesis**: Plain English: dose-bracket sibling of this cycle's gradclip0p5-canary and gradclip0p15-canary (batched per operator 08-22 batch-the-grid rule) -- does a LOOSER trust-region clip (2.0, ~4x looser than 0.5) on the same coef=1.0/vf_coef=0.5 yaw-advantage actor step still recover parity with the matched coef=0 control (pos avg 0.083/neg avg -0.138), or does it read closer to the unclipped grad_clip=0 FAIL (rr1: pos avg 0.028/neg avg -0.097)? Together with 0.15/0.5 this brackets the dose-response curve in one wave instead of one clip value per cycle. Same parent/init/seed/recipe, single lever changed (clip value only).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Read jointly against the control (yawcredit-ctrl-canary, wz_med pos avg 0.083/neg avg -0.138), the grad_clip=0 FAIL sibling (rr1, pos avg 0.028/neg avg -0.097), and the grad_clip=0.15/0.5 siblings (read jointly when all finish, places the dose-response curve). PASS/PROMOTE if final (2M) probe_turn_authority wz_med clears the control's own final within 0.01 on BOTH signs AND det walk gait_valid>=5/6 zero falls AND purewalk det progress_ratio within 0.03 of the control's own. INFORMATIVE if it beats the grad_clip=0 sibling by >=0.02 both signs but still short of full parity. FAIL if within noise of (or worse than) the grad_clip=0 sibling at this looser dose -- strengthens the direction-not-size read and that only a tight clip (if any) helps.

**verdict**: CANARY FAIL - MECHANISM: the LOOSE end of the dose bracket (train.yaw_credit_grad_clip=2.0, ~13x looser than the 0.15 sibling that fully recovers+overshoots) reads within noise of the unclipped grad_clip=0 FAIL (rr1) on the decisive gait/progress clause, even though wz_med shows a small partial uptick. Own probe_turn_authority (TURNCAP_CFG_SET, wz_cmd=+-0.25, seeds 0/1, run myself on-pod train-5): wz_med pos +0.040/+0.047 (avg 0.043) vs rr1's 0.028 (delta +0.015, UNDER the gate's own 0.02 both-signs INFORMATIVE bar) and vs control's 0.083 (delta -0.040, misses PASS by 4x the 0.01 band); neg -0.131/-0.133 (avg -0.132) vs rr1's -0.097 (delta -0.035, clears the 0.02 bar on this sign alone) and vs control's -0.138 (delta +0.006, near-parity) -- an asymmetric partial that fails the gate's own 'both signs' INFORMATIVE requirement. Decisive: built the harness's own purewalk det read myself (own pod train-2, same method as the gate text names, no-video for speed since the standard video gate was 1.5-2h out) -- progress_ratio 0.176/0.162 and slip/m 5.63/5.67, ESSENTIALLY IDENTICAL to rr1's own 0.177/0.159 and 5.34/5.76 (both ~2x the control's 0.376-0.380/2.72-2.96, both breach the joystick <=2.9 slip band) -- the walk-quality collapse is NOT rescued at this dose, matching the gate's own FAIL clause ('within noise of the grad_clip=0 sibling'). gait_valid 8/8 both modes (the weak clause, cheap to clear) but that alone cannot pass the conjunctive gate when progress_ratio misses by 0.2 (7x the 0.03 band). Contrast: this cycle's own gradclip0p15 sibling (same recipe, single lever = clip value, 0.15 vs 2.0) fully recovers BOTH wz_med (0.198/-0.200) AND progress/slip (0.38-0.40/2.2-2.6) -- confirms a SHARP dose cliff, not a smooth monotonic curve: the mechanism only works inside a narrow trust-region window, and 2.0 sits outside it just like unclipped. Evidence: logs/ckpt_eval/turn_probe_yawcredit_gradclip2p0_canary.json, purewalk_gradclip2p0_canary.json/purewalk_rr1.json/purewalk_ctrl.json (built this cycle). Do not fund a looser-clip lever further -- the cliff is on the tight side; if more doses are wanted, bracket BELOW 0.5 (between 0.15 and 0.5), not above. No promote.

**refused_reason**: a process for cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip2p0-canary already exists on hexapod-mjx-train-5

