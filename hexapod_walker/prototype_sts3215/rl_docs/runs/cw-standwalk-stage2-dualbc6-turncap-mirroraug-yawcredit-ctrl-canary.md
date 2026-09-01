# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-ctrl-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-01T09:48:56+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-turnpay-acq1

**wandb_id**: qkdv2457

**hypothesis**: Plain English: matched CONTROL for the reward-decomposed (yaw-component) critic canary -- a plain continuation of the SAME turnpay-canary init, same full recipe (bc_anchor_coef=3.0, mirror-augmented base, k_walk_yaw=1.0) as the turnpay-acq1 lineage that itself eroded to ACQ FAIL - TURN EROSION by 38M, but capped at 2M steps with NO new mechanism -- this establishes the 2M erosion baseline the yaw-credit treatment arm (launched alongside, same init/recipe/seed, only difference: train.yaw_credit_coef=1.0/train.yaw_credit_vf_coef=0.5) must beat to be worth funding further. This closes the whole update-size-constraint (freeze/value-warmup/kl-rollback) mechanism family's replacement lever: does decomposing the critic by reward component fix the credit-assignment problem probe_yaw_credit.py (08-31) diagnosed, where a real yaw-reward income exists but the shared advantage never anticipates it because the walk-forward reward dominates?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Read jointly with the yawcredit-canary treatment arm. Record this arm's own final (2M) probe_turn_authority wz_med (own TURNCAP_CFG_SET) and det walk gait_valid/progress_ratio as the CONTROL baseline -- no PASS/FAIL verdict on this arm alone.

**verdict**: CANARY PASS (baseline-only, no independent skill verdict per this arm's own gate text -- 'no PASS/FAIL verdict on this arm alone'; mechanism-health clean: finished cleanly, sensible values, used solely as the comparison baseline for the sibling treatment's verdict). Matched plain-continuation control for the yaw-credit canary pair, 2M steps off the same turnpay-canary init/recipe/seed, coef=0 (no new mechanism). Own probe_turn_authority (TURNCAP_CFG_SET, run myself on-pod train-0 after pushckpt) reads wz_med pos +0.0774/+0.0886 (avg 0.083, seeds 0/1), neg -0.1354/-0.1400 (avg -0.138) -- roughly at/above the whole closed update-size-constraint mechanism family's own ceiling (~0.075-0.09 pos / -0.10 to -0.12 neg), i.e. a plain continuation with no held guard erodes turn authority only mildly at 2M. This baseline is what cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-canary-rr1 (treatment) read materially WORSE than on both signs -> that sibling's own CANARY FAIL - MECHANISM verdict. Evidence: logs/ckpt_eval/turn_probe_yawcredit_ctrl_canary.json.

