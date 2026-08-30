# cw-standwalk-stage2-dualbc4-walkteach-anchor14coef1-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_PASS

**created**: 2026-08-30T18:17:11+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-canary-s1

**wandb_id**: 3qpeq98p

**hypothesis**: Plain English: seed-1 twin of the dualbc4_walkteach anchor14coef1 canary (see seed0's ledger hypothesis for the full rationale) -- same all-heading/turn-capable BC base, same obs-shape-restoring cfg (walk_heading_max_rad=pi, walk_yaw_cmd=1, walk_phase_run_on_yaw=1, walk_yaw_zero_frac=1.0, walk_cmd_resample_s/jitter, walk_stop_frac, max_delta_q_deg=0.375), same proven anchor/reward wrapper; paired seed for mechanism-health replication before any 8M acquisition spend.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, joint read with seed0: WIRING CHECK train/bc_anchor_loss_walk + train/bc_anchor_fill_walk nonzero every logged update. PASS/promote-to-8M-acquisition if BOTH seeds show det walk gait_valid>=5/6, zero/near-zero sacrificed legs, progress_ratio in the dualbc3 canary/acq8m order of magnitude (0.28-0.43), AND per-heading direction/completion not worse than walkteach-acq12m's own 0.31-0.46 completion band. FAIL if gait_valid collapses (0-1/6), sacrificed legs reappear, or direction/completion regresses hard below the teacher band.

**verdict**: CANARY PASS (seed1, mechanism-health only), JOINT 2/2 with seed0 -- see seed0's verdict for full rationale, replicated numbers here: WIRING CHECK bc_anchor_loss_walk nonzero 24/24 rows (0.0013-0.0043), fill 11844->39276. Own gate/owncfg det walk: gait_valid 6/6, sacrificed_legs 0, progress_ratio med 0.463/0.446 (dualbc3 band 0.28-0.43, same order, slightly above), slip/m 1.77-1.85. Course clause: course_err_1s_med 5.7-6.9deg, wrong_course_frac_1s 0.0-0.02, course_speed_ratio_1s_med 0.44-0.46, inside walkteach-acq12m's 0.31-0.46 band. sto walk collapsed (known pre-existing sigma-band fragility, not new, out of this canary's det-focused gate scope). Own eval_cmd_suite read also showed the same harness-mismatch artifact as seed0 (mode not forced to walk for this joint_walk 4-submode dual-core recipe) -- not treated as evidence, eval_checkpoint's own --modes walk isolation is the valid instrument. Promoting to 8M acquisition continuation.

