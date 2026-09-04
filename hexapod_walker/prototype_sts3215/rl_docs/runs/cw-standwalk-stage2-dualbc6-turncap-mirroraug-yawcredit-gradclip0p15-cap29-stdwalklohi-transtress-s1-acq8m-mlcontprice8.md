# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-transtress-s1-acq8m-mlcontprice8

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-04T12:11:29+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-transtress-s1-acq8m

**wandb_id**: 7zcmt9mm

**hypothesis**: Plain English: high-dose twin of -mlcontprice2 -- same continuity fix (safety.hold_min_load_ema_continuous=1) and the same dense unloaded-foot-at-hold-entry price, at 4x the dose (reward.k_hold_min_load_short=8.0), continuing the acq8m checkpoint on the identical transition-stress diet, to bracket whether the shortfall price repairs the last 6/72 stress-gate hold_min_load failures and at what cost to walk quality. At full shortfall this dose charges 8/s of hold -- comparable in integral to the termination's own cost (term_cost_per_remaining_s=3.0 cap 60) -- so if the mechanism works at all, this arm should show it; if it also degrades walk/turn quality past the cap while k=2.0 does not, the dose-response localizes the usable band. Mechanism landed default-off + semantics-bank proved this cycle (snapshot 8be71a38).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS if eval_cmd_stress (dr0+ownDR, 72 seq episodes, seed base 93000, --strict, identical stress bundle) at 2M: ZERO hold_min_load terminations (acq8m read: 6/72) AND session_complete_frac >= 0.95 AND gait_valid_frac = 1.0 with sacrificed_legs_seen empty (acq8m: 0.986, [1,2,3]) AND walk quality within 10% of the acq8m read (progress_ratio_med 0.242, direction_err_med 43.1deg, slip/m 6.57) AND smoothness not worse (cmd_jerk_p95 7500, slew_sat_frac 1.0 +10% cap). over_current reported separately, never vetoes alone. FAIL if hold_min_load persists at BOTH doses (mechanism insufficient -- next lever is entry-window termination carry-over, not more dose) or this dose regresses walk/turn quality past the cap while k=2.0 does not (dose ceiling found).

**verdict**: CANARY FAIL - MECHANISM: eval_cmd_stress (seed 93000, 72 seq eps, dr0+ownDR, --strict) at 2M: hold_min_load 3/72 (down from acq8m's 6/72, but NOT the pre-registered ZERO bar -> FAIL on its own gate). Split tells the real story: DR-0 pass is now fully CLEAN (0/36, was 2/36) and gait_valid_frac=1.0 with sacrificed_legs_seen=[] (was 0.986/[1,2,3], the companion pathology fully closed); the 3 residual fires are ALL under own-DR (3/36, was 4/36) -- domain randomization still occasionally beats the k=8 price. Walk quality held (progress_ratio 0.23 vs 0.242 -4.9%, dir_err 44.5 vs 43.1deg +3.2%, slip/m 6.08 vs 6.57 -7.5%, all within the 10% cap) and smoothness unchanged (cmd_jerk_p95 7500, slew_sat 1.0) -- the price did not corrupt the walk optimum at this dose, so this is not the dose-ceiling FAIL shape. WHY: the continuity+price mechanism (safety.hold_min_load_ema_continuous + reward.k_hold_min_load_short=8.0) is directionally correct and dose-responsive (halved fires, fully fixed gait-validity), just insufficient magnitude under own-DR at k=8. NEXT: read against the k=2.0 twin (mlcontprice2, concurrent cycle) before calling the mechanism itself insufficient -- if k=2 also fails only under own-DR at a similar or worse rate, the dose-response argues for either a higher k or the pre-declared next lever (entry-window termination carry-over); if k=2 fails worse, the mechanism is real and just needs more dose.

