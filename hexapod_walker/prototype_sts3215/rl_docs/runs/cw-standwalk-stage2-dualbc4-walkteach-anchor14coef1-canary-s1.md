# cw-standwalk-stage2-dualbc4-walkteach-anchor14coef1-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T18:17:11+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-canary-s1

**wandb_id**: 3qpeq98p

**hypothesis**: Plain English: seed-1 twin of the dualbc4_walkteach anchor14coef1 canary (see seed0's ledger hypothesis for the full rationale) -- same all-heading/turn-capable BC base, same obs-shape-restoring cfg (walk_heading_max_rad=pi, walk_yaw_cmd=1, walk_phase_run_on_yaw=1, walk_yaw_zero_frac=1.0, walk_cmd_resample_s/jitter, walk_stop_frac, max_delta_q_deg=0.375), same proven anchor/reward wrapper; paired seed for mechanism-health replication before any 8M acquisition spend.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, joint read with seed0: WIRING CHECK train/bc_anchor_loss_walk + train/bc_anchor_fill_walk nonzero every logged update. PASS/promote-to-8M-acquisition if BOTH seeds show det walk gait_valid>=5/6, zero/near-zero sacrificed legs, progress_ratio in the dualbc3 canary/acq8m order of magnitude (0.28-0.43), AND per-heading direction/completion not worse than walkteach-acq12m's own 0.31-0.46 completion band. FAIL if gait_valid collapses (0-1/6), sacrificed legs reappear, or direction/completion regresses hard below the teacher band.

