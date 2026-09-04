# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-combdose0p6-s1-r2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAILED

**created**: 2026-09-04T00:53:10+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-combdose0p6-s1

**wandb_id**: ecde4pum

**hypothesis**: Plain English: clean retry of combdose0p6-s1, which never trained (W&B global_step stuck at 0 for 1200s, an infra launch failure, not a result) -- identical spec (train.bc_anchor_walk_combined_dose=0.6, seed1) to complete the pre-registered 4-cell dose grid (combdose0p3{,-s1}/combdose0p6{,-s1}) whose seed0 half is now 2/2 FAIL (dose0.3 FAIL-MECHANISM, dose0.6 FAIL-MECHANISM and WORSE than dose0.3 on both combined-tick win size and pure-turn regression size).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same pre-registered gate as combdose0p6 (seed0), read against the seed1 control cap29-stdwalklo-hi-s1: PASS if probe_turn_authority.py --vx-cmds (full 84-key cfg replay) combined-tick wz_med beats the seed1 control's own combined read on BOTH signs, WITHOUT a pure-turn/straight-walk wz regression >10% vs that control; FAIL if combined wz_med is flat/worse on either sign, or the regression cap is blown.

**failed_reason**: W&B global_step not advancing (0 -> 0) after 1200s (n_steps=64, cpu-time flat for 0 polls)

