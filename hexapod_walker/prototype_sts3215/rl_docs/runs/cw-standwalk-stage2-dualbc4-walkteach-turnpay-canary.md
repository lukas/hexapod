# cw-standwalk-stage2-dualbc4-walkteach-turnpay-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T23:38:42+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc4-walkteach-turndiet-anchor14coef1-canary-s1

**wandb_id**: brkhi8oe

**hypothesis**: Plain English: if the robot is actually PAID for rotating on command (direct yaw-tracking income, not just un-paying the freeze) and sees yaw commands often, it should finally start turning - where exposure-only (turndiet, CANARY FAIL - MECHANISM: probe wz~0.001 vs cmd 0.25, yaw factor declining 0.22->0.07) produced literally zero rotation in 2M. Delta vs turndiet (same init ppo_goal_cw_standwalk_stage2_dualbc4_walkteach.zip, same mix/DR): (1) direct yaw income - the bank-proven OMNI turn stack k_walk_yaw=1 + walk_yaw_kernel_gate + k_yaw_prog with yaw_prog_overshoot_decay/yaw_prog_avg_s + k_yaw_still=50 with yaw_still_avg_s + walk_yaw_hold_prog_gate (core turn bank 5/5 green this cycle on current mesh/100Hz code; walk_kernel_yaw_ema deliberately EXCLUDED - its defect-proof clause fails on mesh/100Hz, raw kernel already orders tracked>under-rotator 658 vs 584); (2) denser exposure - tip_frac 0.15->0.30 and walk_yaw_zero_frac 1.0->0.5 so nonzero wz also appears during ordinary walking episodes (the lineage's wz obs channel was constant zero its whole life; 4.5% exposure gave no gradient). Prediction-if-true: probe_turn_authority wz_med >= 0.08 both signs by 2M. Prediction-if-false: wz_med still ~0 -> incentive+exposure jointly refuted at canary scale; next suspect is architecture/obs-channel resurrection (targeted BC on turn episodes from the omega-conditioned scripted gait). Strongest alternative: yaw income destabilizes the straight gait (k_yaw_still charge) - caught by the gait/progress clauses.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, joint with -s1 twin: PASS/promote if BOTH seeds show probe_turn_authority (checkpoint own cfg, wz_cmd=+-0.25, walk-mode-filtered) wz_med >= 0.08 both signs (frozen-body prediction is wz_med~0), det walk gait_valid >= 5/6, sacrificed legs ~0, and pure-walk (mode_seq OFF) det progress_ratio not hard-regressed vs the wave-1 band 0.43-0.48. FAIL if wz_med < 0.03 (still frozen), gait collapses, or straight-walk progress craters. Do not judge mature turn quality or close the reward class at 2M.

