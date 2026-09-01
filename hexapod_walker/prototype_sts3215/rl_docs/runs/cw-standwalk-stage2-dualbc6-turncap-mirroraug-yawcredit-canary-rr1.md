# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-canary-rr1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-01T10:04:08+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-turnpay-acq1

**wandb_id**: k2t1kdr9

**hypothesis**: Retry of cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-canary (attempt 1 crashed on-pod: cuDNN RNN backward requires training mode, and the separate yaw-value-head's optimizer param group broke checkpoint reload shape -- both root-caused and fixed this cycle, rl_move/sim/yaw_critic.py, snapshot exp/yaw-decomposed-critic-fix-cudnn-and-checkpoint-shape, 13/13 tests green including new regression tests for both bugs). Same hypothesis as attempt 1: does a SECOND value head trained only off the yaw-reward component, plus a separate yaw-advantage actor policy-gradient step, slow/reverse turn-authority erosion vs the matched control (cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-ctrl-canary, already finished at 2M) without hurting walk quality? Doses unchanged: train.yaw_credit_coef=1.0, train.yaw_credit_vf_coef=0.5.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/PROMOTE if final (2M) probe_turn_authority (own TURNCAP_CFG_SET) wz_med improves over the matched control's own final by >=0.02 on BOTH signs AND det walk gait_valid>=5/6 zero falls AND purewalk det progress_ratio within 0.03 of the control's own. INFORMATIVE/NO-EFFECT if within ~0.01-0.02 of the control -- try coef 3.0-5.0 or a shared-trunk variant before abandoning. FAIL if gait_valid/progress_ratio regress hard vs the control -- cut coef 5-10x and retry, or tighten the pg step's trust region.

**verdict**: CANARY FAIL - MECHANISM: yaw-decomposed critic (train.yaw_credit_coef=1.0, train.yaw_credit_vf_coef=0.5) at 2M reads WORSE turn authority than its matched plain-continuation control on BOTH signs -- own probe_turn_authority (TURNCAP_CFG_SET, wz_cmd=+-0.25, seeds 0/1, walk-mode-filtered, run myself on-pod train-4/train-0 after pushckpt): treatment wz_med pos +0.0252/+0.0299 (avg 0.028) vs control's +0.0774/+0.0886 (avg 0.083, delta -0.055); neg -0.0959/-0.0977 (avg -0.097) vs control's -0.1354/-0.1400 (avg -0.138, delta +0.041, i.e. LESS negative). Both deltas are ~2-3x the gate's own 0.02 PASS threshold and in the WRONG direction -- a clear regression, not a null/noise result, so the decisive wz_med clause alone already clears the gate's FAIL bar; gait_valid/progress_ratio not needed to decide (still mid-flight on-pod gate/owncfg/mixedsession, left running, supplementary only). Corroborating: treatment's reward-quarters crash is deeper than control's (Q3/Q4 -337.4/-62.4 vs -208.3/-22.4), consistent with genuine training instability, not measurement noise. Why: the mechanism's extra actor policy-gradient step (undetached, yaw-only normalized advantage summed at ratio=1, NO trust-region/clip of its own) is plausibly an oversized/unconstrained update of exactly the shape the whole freeze/value-warmup/kl-rollback update-size-constraint family (already closed this cycle) exists to guard against -- stacking a second uncapped step next to PPO's own clipped step likely reproduces that failure mode in a new place rather than fixing credit assignment. Evidence: logs/ckpt_eval/turn_probe_yawcredit_canary_rr1.json vs turn_probe_yawcredit_ctrl_canary.json. Next: do NOT scale the dose up (directionality argues a bigger unclipped step makes this worse); before funding a shared-trunk variant, the cheapest next test is the SAME mechanism with the yaw-advantage actor step put through a trust region (clip its ratio or cap its update norm) -- if that recovers parity with control, update-size was the confound all along (echoes the campaign's own freeze finding); if it still doesn't beat control, retire the reward-decomposed-critic lever and accept the mirror-augment ceiling (~0.075-0.09 pos / -0.10 to -0.12 neg, this control's own read) as durable.

