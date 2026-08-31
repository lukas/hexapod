# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yaw5x-acq1-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-31T17:42:09+00:00

**pod**: hexapod-mjx-train-7

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-turnpay-acq1-s1

**wandb_id**: qf8t6yqg

**hypothesis**: Plain English: seed-1 twin of the 5x-yaw-pricing retention test -- can higher pay for turning stop the slow erosion of turn authority that 1x pricing allowed, starting from a base that actually turns? Same design as the seed0 arm (see cw-standwalk-stage2-dualbc6-turncap-mirroraug-yaw5x-acq1): identical recipe to the failed turnpay-acq1-s1 (init from ppo_goal_..._mirroraug_turnpay_canary_s1.zip with live wz_med +-0.12-0.16) except k_walk_yaw/k_yaw_prog 1.0->5.0 and --snapshot-every=5000000 for a measurable erosion curve. Two seeds because the failed pair tracked each other tightly (wz within 0.01-0.03) -- a seed-consistent hold or seed-consistent erosion is a class answer, a split is seed-luck signal. Prediction-if-true: wz_med >= 0.10 both signs at ~40M, flat snapshot curve. Prediction-if-false: acq1-shaped erosion despite 5x income -> reward-magnitude retention refuted, escalate to credit-assignment tracing. Strongest alternative: 5x term distorts the walk (caught by gait/progress clauses).

**gate**: ACQUISITION retention test, seed-1 twin -- SAME gate as cw-standwalk-stage2-dualbc6-turncap-mirroraug-yaw5x-acq1: PASS if final probe_turn_authority wz_med >= 0.10 both signs AND pure-walk det progress_ratio in/above 0.40-0.48 AND gait_valid >= 5/6, zero falls. FAIL if erosion curve matches the 1x acq pair and final wz_med < 0.05 either sign with clean gait. GAIT-BREAK FAIL if gait_valid < 5/6 or progress collapses. PARTIAL otherwise -- quantify the _s<steps> snapshot curve, joint read with the seed0 twin.

