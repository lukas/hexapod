# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-gyrobias1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T06:18:43+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-gyronoise1x-c1

**wandb_id**: kbypfyyp

**hypothesis**: Restore nominal (1x) IMU gyro RATE bias (dr.gyro_bias_deg_s=0.5deg/s, a per-episode constant angular-rate offset from imperfect gyro calibration -- distinct from the already-tested gyro NOISE axis (gyronoise1x, just PASSED) and from the attitude/rotation imu_bias_deg axis (imubias1x, already tested) -- the easy0905 recipe has run with gyro_bias_deg_s=0 throughout the whole crossgrav campaign. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal gyro rate-bias without retraining collapse?

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on the zero-gyro-bias idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows gyro rate-bias realism is a binding constraint the DR-rung must budget real training time against.

**verdict**: Nominal IMU gyro RATE-bias axis (dr.gyro_bias_deg_s=0.5, previously OFF/untested) restores clean on the flagship champion: PERFECT 24/24 gait_valid across all 4 modes (walk/det,sto, walk_startjitter/det,sto), sac=[] every episode, 0 terminations/falls. slip_per_m 3.3-4.9 (consistent with sibling DR-restore canaries' band). Infra note: this run actually completed healthy at 2M steps (W&B kbypfyyp, finished) but its ledger entry was stuck at INTENT with no wandb_id/pod (the documented non-atomic experiments.json write-race, same incident class as the 06:59-08:2x truncations) so it silently sat unverdicted and un-drainable ('already exists in W&B — dropping backlog item (duplicate)' repeatedly refusing the requeue). Fixed via launch_run.py update --set (status/wandb_id/pod) before verdicting, same recovery pattern as encnoise1x-c1-acq1. Closes the gyro-rate-bias axis; joins the ~30-axis single-DR-restore sweep as clean.

