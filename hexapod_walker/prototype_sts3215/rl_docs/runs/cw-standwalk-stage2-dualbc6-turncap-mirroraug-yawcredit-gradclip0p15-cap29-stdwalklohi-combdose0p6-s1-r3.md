# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-combdose0p6-s1-r3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-04T01:45:57+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-combdose0p6-s1-r2

**wandb_id**: xjeb4bec

**hypothesis**: Plain English: second clean retry of combdose0p6-s1, whose FIRST TWO attempts both failed to train (global_step stuck at 0) on the SAME pod hexapod-mjx-train-1 -- node g129004 load1 read 66-85 at investigation time (node g142d86 read 140+), so this retry deliberately targets hexapod-mjx-train-2 on the low-load node g131eec (load1 ~8.7) to control for node-contention as the cause, per the second-death infra-escalation rule. Identical spec (train.bc_anchor_walk_combined_dose=0.6, seed1) to complete the pre-registered 4-cell dose grid, now 3/4 FAIL (dose0.3 seed0+seed1 FAIL-MECHANISM; dose0.6 seed0 FAIL-MECHANISM and worse than dose0.3).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same pre-registered gate as combdose0p6 (seed0), read against the seed1 control cap29-stdwalklo-hi-s1: PASS if probe_turn_authority.py --vx-cmds (full 84-key cfg replay) combined-tick wz_med beats the seed1 control's own combined read on BOTH signs, WITHOUT a pure-turn/straight-walk wz regression >10% vs that control; FAIL if combined wz_med is flat/worse on either sign, or the regression cap is blown.

