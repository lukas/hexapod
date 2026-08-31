# cw-standwalk-stage2-dualbc6-turncap-mirroraug-turndense1-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-31T19:40:04+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-turnpay-canary-s1

**wandb_id**: 2ra2xpoj

**hypothesis**: Seed-1 twin of cw-standwalk-stage2-dualbc6-turncap-mirroraug-turndense1-canary -- same single lever (goal.walk_turn_in_place_frac 0.30->0.60, 2x turn-segment density, unchanged reward weights) off the exact turnpay-canary-s1 recipe/init, testing whether the credit-assignment fix (if any) is seed-consistent like every prior mechanism-class canary pair in this campaign has been (wz within 0.01-0.03 between seeds every time).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. SAME gate as cw-standwalk-stage2-dualbc6-turncap-mirroraug-turndense1-canary (seed0): PASS if probe_yaw_credit forward_verdict is CREDIT-REWARDS (or corr_toward_value_delta>=+0.15) on >=3/4 of the wz_cmd=+-0.25 x seed-internal-probe combos on the 2M checkpoint AND probe_turn_authority wz_med>=0.10 both signs AND det walk gait_valid>=5/6 with clean progress. FAIL if forward_verdict stays BLIND/PUNISHES on >=3/4 of combos regardless of wz_med. PARTIAL otherwise; joint read with the seed0 twin.

