# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p5-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-01T11:00:29+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-canary-rr1

**hypothesis**: Plain English: does putting the yaw-credit mechanism's extra actor policy-gradient step through a trust region (a plain gradient-norm clip, torch.nn.utils.clip_grad_norm_ over policy.parameters() right before that step's own optimizer.step() -- new cfg train.yaw_credit_grad_clip, default 0.0/off, bit-exact when unset, 18/18 test_yaw_critic.py green incl. 3 new tests) recover the SAME coef=1.0/vf_coef=0.5 dose to at least parity with the matched coef=0 control it lost to? Direct follow-up to this cycle's own cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-canary-rr1 CANARY FAIL - MECHANISM verdict: at grad_clip=0 (the only dose tried), the yaw-advantage step regressed wz_med WORSE than a plain matched continuation on BOTH signs (pos 0.028 vs control 0.083, neg -0.097 vs control -0.138) while its own reward crashed deeper than the control's (Q3/Q4 -337/-62 vs -208/-22) -- a signature consistent with an oversized, unconstrained extra actor update, exactly the failure mode the whole closed freeze/value-warmup/kl-rollback update-size-constraint family exists to guard against, just stacked on a NEW, previously-uncapped step. Prediction-if-true: a clip in some tested range recovers wz_med to >=parity with the coef=0 control (pos delta >=-0.01, neg delta >=-0.01) with gait/progress held -- promote that dose to an acquisition-scale continuation next. Prediction-if-false: even the tightest clip tested still regresses vs control -- the pg step's DIRECTION (not just its size) is bad, ruling out grad-clip as the fix and pointing at either a smaller coef, a shared (non-detached) trunk variant, or retiring the whole reward-decomposed-critic lever in favor of the mirror-augment ceiling this control already re-confirmed (~0.075-0.09 pos / -0.10 to -0.12 neg).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Read jointly against the ALREADY-FINISHED matched control cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-ctrl-canary (own probe_turn_authority TURNCAP_CFG_SET wz_med pos avg 0.083 seeds0/1, neg avg -0.138) and against the FAILED grad_clip=0 sibling cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-canary-rr1 (pos avg 0.028, neg avg -0.097). PASS/PROMOTE (this dose) if final (2M) probe_turn_authority wz_med clears the control's own final within 0.01 on BOTH signs (i.e. recovers parity, erosion no worse than the plain-continuation baseline) AND det walk gait_valid>=5/6 zero falls AND purewalk det progress_ratio within 0.03 of the control's own. INFORMATIVE if it beats the grad_clip=0 sibling by >=0.02 both signs but still falls short of full parity with the control -- report the partial recovery, the size of the clip matters, consider an intermediate dose. FAIL if it reads within noise of (or worse than) the grad_clip=0 sibling -- the pg step's problem is direction, not size; grad-clip is refuted as the fix.

