# cw-standwalk-stage2-dualbc4-walkteach-anchor14coef1-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T18:13:05+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-canary

**wandb_id**: xbgtyiyi

**hypothesis**: Plain English: does the anchor14coef1 unified-policy RL fine-tune recipe, already proven twice on the fixed-heading dualbc2/dualbc3 BC lineage, also work re-init'd from dualbc4_walkteach -- the new all-heading/turn-capable BC base distilled from the walkteach scripted-teacher lineage (walk-mode obs 74->75, +goal.walk_yaw_cmd channel; quick_probe net_disp_m 0.068/0.417 over a 15s fixed-heading episode, clears the 0.05m in-place-quiver bar)? Cfg carries forward the PROVEN anchor/reward wrapper (bc_anchor_*, drag_stance, loadslip, height/rise/hold gates) unchanged, but restores the base's own obs-shape-relevant goal keys (walk_heading_max_rad=pi, walk_yaw_cmd=1, walk_phase_run_on_yaw=1, walk_yaw_zero_frac=1.0, walk_cmd_resample_s/jitter, walk_stop_frac, max_delta_q_deg) so the fine-tune's env matches what the BC/DAgger actor was actually trained under instead of silently truncating it back to dualbc3's fixed-heading-only regime.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (same convention as dualbc2/dualbc3): WIRING CHECK train/bc_anchor_loss_walk + train/bc_anchor_fill_walk nonzero every logged update. PASS/promote-to-8M-acquisition if BOTH seeds show det walk gait_valid>=5/6, zero/near-zero sacrificed legs, and progress_ratio in the same order of magnitude as the dualbc3 canary/acq8m pair (0.28-0.43), AND per-heading direction/completion is not worse than the walkteach-acq12m teacher's own 0.31-0.46 completion band (a regression there means the unified fine-tune erodes the turn/all-heading capability this teacher swap exists to capture). FAIL if gait_valid collapses (0-1/6), sacrificed legs reappear, or direction/completion regresses hard below the teacher band.

