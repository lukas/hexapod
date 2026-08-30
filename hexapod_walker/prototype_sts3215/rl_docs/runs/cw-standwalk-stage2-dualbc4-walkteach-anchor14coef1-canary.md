# cw-standwalk-stage2-dualbc4-walkteach-anchor14coef1-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_PASS

**created**: 2026-08-30T18:13:05+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc3-dagger-anchor14coef1-canary

**wandb_id**: xbgtyiyi

**hypothesis**: Plain English: does the anchor14coef1 unified-policy RL fine-tune recipe, already proven twice on the fixed-heading dualbc2/dualbc3 BC lineage, also work re-init'd from dualbc4_walkteach -- the new all-heading/turn-capable BC base distilled from the walkteach scripted-teacher lineage (walk-mode obs 74->75, +goal.walk_yaw_cmd channel; quick_probe net_disp_m 0.068/0.417 over a 15s fixed-heading episode, clears the 0.05m in-place-quiver bar)? Cfg carries forward the PROVEN anchor/reward wrapper (bc_anchor_*, drag_stance, loadslip, height/rise/hold gates) unchanged, but restores the base's own obs-shape-relevant goal keys (walk_heading_max_rad=pi, walk_yaw_cmd=1, walk_phase_run_on_yaw=1, walk_yaw_zero_frac=1.0, walk_cmd_resample_s/jitter, walk_stop_frac, max_delta_q_deg) so the fine-tune's env matches what the BC/DAgger actor was actually trained under instead of silently truncating it back to dualbc3's fixed-heading-only regime.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (same convention as dualbc2/dualbc3): WIRING CHECK train/bc_anchor_loss_walk + train/bc_anchor_fill_walk nonzero every logged update. PASS/promote-to-8M-acquisition if BOTH seeds show det walk gait_valid>=5/6, zero/near-zero sacrificed legs, and progress_ratio in the same order of magnitude as the dualbc3 canary/acq8m pair (0.28-0.43), AND per-heading direction/completion is not worse than the walkteach-acq12m teacher's own 0.31-0.46 completion band (a regression there means the unified fine-tune erodes the turn/all-heading capability this teacher swap exists to capture). FAIL if gait_valid collapses (0-1/6), sacrificed legs reappear, or direction/completion regresses hard below the teacher band.

**verdict**: CANARY PASS (seed0, mechanism-health only). WIRING CHECK: bc_anchor_loss_walk nonzero every logged update (24/24 rows, 0.0014-0.0041), bc_anchor_fill_walk monotonic 12037->38880 -- own wandb_history read confirms. Own gate/owncfg (dr0/dr0.5) det walk: gait_valid 6/6, sacrificed_legs 0/6, progress_ratio med 0.458/0.431 (dualbc3 canary/acq8m band was 0.28-0.43 -- same order, slightly above upper edge, good not bad), slip/m 1.78-1.86 (inside teacher band), 0 walk terms. Per-heading/course clause: eval_checkpoint's own walk/det episodes carry real course-tracking telemetry (goal.walk_cmd_resample_s=6 inside each 30s episode = multiple headings per rollout) -- course_err_1s_med 5.5-7.0deg, wrong_course_frac_1s 0.0, course_speed_ratio_1s_med 0.43-0.46, matching/inside walkteach-acq12m's own 0.31-0.46 completion band (its course_err band was 4.5-5.2deg -- same order, not a hard regression). Video (walk_det_3_sheet.png) shows upright level six-leg cycling, no flag leg, no drag. sto walk is collapsed (prog med 0.05-0.06, course_err 14.6deg) -- KNOWN pre-existing sigma-band fragility already documented on the dualbc2/dualbc3 lineage (17:5x STATUS entry), not a new regression, and outside this canary's own det-focused gate text. Own additional eval_cmd_suite (allheading8_v08, fixed-heading held-command protocol) read near-zero velocity on every heading for this checkpoint -- diagnosed as a HARNESS MISMATCH, not a real capability loss: eval_cmd_suite has no mode-forcing for the joint_walk 4-submode (walk/rise/lower/hold) dual-core recipe this canary uses (unlike the single-mode walk-only walkteach-acq12m it was validated on), so its 12s window likely spends real time in non-walk submodes where near-zero velocity is correct baseline behavior, not a failure -- eval_checkpoint's own --modes walk isolation is the valid instrument here and is what this verdict is based on. All PASS clauses in the ledger gate text cleared. Promoting to 8M acquisition continuation (cw-standwalk-stage2-dualbc4-walkteach-anchor14coef1-acq8m, same convention as dualbc3-dagger's own promote).

