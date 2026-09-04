# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-combdose0p6-s1-r3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-04T01:45:57+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-combdose0p6-s1-r2

**wandb_id**: xjeb4bec

**hypothesis**: Plain English: second clean retry of combdose0p6-s1, whose FIRST TWO attempts both failed to train (global_step stuck at 0) on the SAME pod hexapod-mjx-train-1 -- node g129004 load1 read 66-85 at investigation time (node g142d86 read 140+), so this retry deliberately targets hexapod-mjx-train-2 on the low-load node g131eec (load1 ~8.7) to control for node-contention as the cause, per the second-death infra-escalation rule. Identical spec (train.bc_anchor_walk_combined_dose=0.6, seed1) to complete the pre-registered 4-cell dose grid, now 3/4 FAIL (dose0.3 seed0+seed1 FAIL-MECHANISM; dose0.6 seed0 FAIL-MECHANISM and worse than dose0.3).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same pre-registered gate as combdose0p6 (seed0), read against the seed1 control cap29-stdwalklo-hi-s1: PASS if probe_turn_authority.py --vx-cmds (full 84-key cfg replay) combined-tick wz_med beats the seed1 control's own combined read on BOTH signs, WITHOUT a pure-turn/straight-walk wz regression >10% vs that control; FAIL if combined wz_med is flat/worse on either sign, or the regression cap is blown.

**verdict**: CANARY FAIL - MECHANISM (train.bc_anchor_walk_combined_dose=0.6, seed1, 3rd launch attempt -r3 after 2 node-load infra deaths). Ran on the run's own pod (hexapod-mjx-train-2, via kubectl exec, matching this family's own gotcha of replaying the FULL 84-key non-train cfg-set extracted from the run's own ledger extra_args -- no standard gate/owncfg harness artifact exists for this dual-core custom-obs family, only probe_turn_authority.py --vx-cmds). Seed-avg vs matched control cap29-stdwalklo-hi-s1's own cached combined_09-03 read: combined-tick (vx=0.08) wz_med WINS both signs cleanly (+0.1046 vs ctrl +0.0868 = +20.4%; -0.1653 vs ctrl -0.1369 = +20.7%) -- the strongest combined-tick win of any dose-0.6 cell (its own seed0 twin COLLAPSED to a near-zero +0.1%/+1.6% win at this same dose, so this is a genuine seed-dependent swing, not just a replay of the seed0 shape). But pure-turn (vx=0.0) wz_med REGRESSES past the 10% cap on BOTH signs: +0.1996 vs ctrl +0.2279 = 12.4% regression; -0.2051 vs ctrl -0.2459 = 16.6% regression. Straight-walk wz drift (vx=0.08,wz=0) shrinks toward zero (-0.0080 vs ctrl -0.0189, ideal is 0, not a regression). Zero falls (12/12 rows, fell=False every cell). Training reward healthy and genuinely trained this time (quarters [23.9, 53.1, -91.1, 140.9], final ep_rew_mean 176.1 at the full 2,031,616-step budget) -- matches the family's known Q3-dip/Q4-recovery shape, so this is a real mechanism verdict, not a starved/crashed run like its own -r2/first attempts. This closes the bc_anchor_walk_combined_dose axis 4/4 FAIL (0.3 seed0/seed1 FAIL, 0.6 seed0/seed1 FAIL) -- same root-cause pathology as every cell: any dose/seed strong enough to win the combined-tick wz axis blows the pure-turn regression cap, confirming (a 4th independent time) the shared-dual-core-representation diagnosis. Combined with the already-closed 4/4-FAIL yaw-arm-scale geometry-lever grid, the WHOLE open-loop scalar-weight/geometry lever family for standwalk item 2 (steering) is now exhausted at 8/8 FAIL. Next: the next lever must act on something neither family reaches -- of the two named candidates (phase-schedule the anchor weight WITHIN a stride vs give pure-turn ticks a protected sub-path/core), the protected-sub-path route has real unused scaffolding already in the codebase (walk_task.MODE_ONEHOT_ORDER has a RESERVED, never-lit 'turn' slot; sim_env.py already computes an exact per-tick _bc_pure_turn boolean for the turn-skip lever) -- see STATUS.md for the scoped design.

