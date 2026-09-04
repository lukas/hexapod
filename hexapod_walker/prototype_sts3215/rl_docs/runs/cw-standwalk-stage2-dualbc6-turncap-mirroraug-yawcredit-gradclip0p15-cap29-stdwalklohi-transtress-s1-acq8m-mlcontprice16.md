# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-transtress-s1-acq8m-mlcontprice16

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-04T14:38:04+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-transtress-s1-acq8m-mlcontprice8

**hypothesis**: Plain English: bracket the hold-load unloaded-foot price one step higher than the k=8.0 twin that halved (not zeroed) residual own-DR hold_min_load fires (3/72) while leaving walk quality intact. Same continuity fix (safety.hold_min_load_ema_continuous=1) and same mechanism, dose doubled to k=16.0 (up to 16/s of hold, >2x the termination's own term_cost_per_remaining_s=3.0 cap 60 integral), continuing from the identical acq8m checkpoint on the identical transition-stress diet, matched at n=18/mode/pass (72 total) -- NOT n=54 like the just-FAILED k=2.0 arm's mismeasured canary, so this reads as a clean 3-point dose bracket (k=0 acq8m baseline 6/72=8.3%, k=2 ~matches baseline at higher n, k=8 3/72=4.2%, k=16 this arm) against the k=8 result. If k=16 pushes fires toward zero without breaching the walk/smoothness caps, dose is still climbing the curve and a further raise or added steps is next; if it plateaus near k=8's rate or starts corrupting walk quality, k=8 is near the mechanism's usable ceiling and the next lever is a genuine own-DR-specific fix (e.g. logging per-episode DR draws to find which randomized param correlates with residual fires).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS if eval_cmd_stress (dr0+ownDR, 72 seq episodes matched n=18/mode/pass, seed base 93000, --strict, identical stress bundle) at 2M: hold_min_load terminations <= k=8.0's 3/72 (ideally 0) AND session_complete_frac >= 0.95 AND gait_valid_frac = 1.0 with sacrificed_legs_seen empty AND walk quality within 10% of acq8m's read (progress_ratio_med 0.242, direction_err_med 43.1deg, slip/m 6.57) AND smoothness not worse (cmd_jerk_p95 7500, slew_sat_frac 1.0 +10% cap). over_current reported separately, never vetoes alone. FAIL if hold_min_load still nonzero AND worse-or-equal to k=8's rate (mechanism plateaued, need a different lever) or walk/turn quality regresses past the cap (price interfering with the walk optimum).

