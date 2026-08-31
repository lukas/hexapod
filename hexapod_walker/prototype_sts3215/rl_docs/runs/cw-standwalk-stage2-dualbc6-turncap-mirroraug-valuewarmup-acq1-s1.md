# cw-standwalk-stage2-dualbc6-turncap-mirroraug-valuewarmup-acq1-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-31T22:49:39+00:00

**pod**: hexapod-mjx-train-3

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-turnpay-canary

**wandb_id**: emjgpx8b

**hypothesis**: Plain English: seed-1 twin of valuewarmup-acq1 -- same value-warmup mechanism (actor frozen 8M steps, critic-only learning, then normal PPO resumes), 2-seed pair per campaign convention since prior twins (yaw5x, stillbal) showed real seed variance in erosion depth. Same base recipe/init as the already-FAILED turnpay-acq1-s1 (PARTIAL-EROSION, wz_med +0.023/+0.029,-0.078/-0.070) with the identical single new variable as seed0. Full reasoning/evidence in valuewarmup-acq1's own hypothesis (probe_yaw_credit CREDIT-BLIND on this exact canary base, lstm_critic marker gap found+fixed this cycle, test_value_learning.py 25/25 green).

**gate**: SAME gate as cw-standwalk-stage2-dualbc6-turncap-mirroraug-valuewarmup-acq1 -- joint read with seed0: mechanism check at the 8M freeze boundary (probe_yaw_credit flip to CREDIT-REWARDS on >=3/4 combos + probe_turn_authority unchanged near canary levels), then final-checkpoint turn-authority durability check if the mechanism passes.

