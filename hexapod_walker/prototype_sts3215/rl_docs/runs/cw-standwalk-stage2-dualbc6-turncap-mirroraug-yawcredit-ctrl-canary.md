# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-ctrl-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-01T09:48:56+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-turnpay-acq1

**wandb_id**: qkdv2457

**hypothesis**: Plain English: matched CONTROL for the reward-decomposed (yaw-component) critic canary -- a plain continuation of the SAME turnpay-canary init, same full recipe (bc_anchor_coef=3.0, mirror-augmented base, k_walk_yaw=1.0) as the turnpay-acq1 lineage that itself eroded to ACQ FAIL - TURN EROSION by 38M, but capped at 2M steps with NO new mechanism -- this establishes the 2M erosion baseline the yaw-credit treatment arm (launched alongside, same init/recipe/seed, only difference: train.yaw_credit_coef=1.0/train.yaw_credit_vf_coef=0.5) must beat to be worth funding further. This closes the whole update-size-constraint (freeze/value-warmup/kl-rollback) mechanism family's replacement lever: does decomposing the critic by reward component fix the credit-assignment problem probe_yaw_credit.py (08-31) diagnosed, where a real yaw-reward income exists but the shared advantage never anticipates it because the walk-forward reward dominates?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Read jointly with the yawcredit-canary treatment arm. Record this arm's own final (2M) probe_turn_authority wz_med (own TURNCAP_CFG_SET) and det walk gait_valid/progress_ratio as the CONTROL baseline -- no PASS/FAIL verdict on this arm alone.

