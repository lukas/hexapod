# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-canary-rr1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-01T10:04:08+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-turnpay-acq1

**wandb_id**: k2t1kdr9

**hypothesis**: Retry of cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-canary (attempt 1 crashed on-pod: cuDNN RNN backward requires training mode, and the separate yaw-value-head's optimizer param group broke checkpoint reload shape -- both root-caused and fixed this cycle, rl_move/sim/yaw_critic.py, snapshot exp/yaw-decomposed-critic-fix-cudnn-and-checkpoint-shape, 13/13 tests green including new regression tests for both bugs). Same hypothesis as attempt 1: does a SECOND value head trained only off the yaw-reward component, plus a separate yaw-advantage actor policy-gradient step, slow/reverse turn-authority erosion vs the matched control (cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-ctrl-canary, already finished at 2M) without hurting walk quality? Doses unchanged: train.yaw_credit_coef=1.0, train.yaw_credit_vf_coef=0.5.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/PROMOTE if final (2M) probe_turn_authority (own TURNCAP_CFG_SET) wz_med improves over the matched control's own final by >=0.02 on BOTH signs AND det walk gait_valid>=5/6 zero falls AND purewalk det progress_ratio within 0.03 of the control's own. INFORMATIVE/NO-EFFECT if within ~0.01-0.02 of the control -- try coef 3.0-5.0 or a shared-trunk variant before abandoning. FAIL if gait_valid/progress_ratio regress hard vs the control -- cut coef 5-10x and retry, or tighten the pg step's trust region.

