# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-transtress-s1-acq8m-mlcontprice2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-04T12:07:19+00:00

**pod**: hexapod-mjx-train-10

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-transtress-s1-acq8m

**wandb_id**: w2m8pcxs

**hypothesis**: Plain English: the policy keeps dying when it switches into a standing hold mid-session because one foot stays unloaded through the switch -- this arm adds a small dense price for that unloaded foot (reward.k_hold_min_load_short=2.0, the priced twin of the hold_min_load termination, sharing its min-over-feet EMA and 0.3N floor, active from the first hold tick including the grace window) plus the EMA-continuity fix (safety.hold_min_load_ema_continuous=1: EMA seeded from measured load at reset and updated every tick in every mode, so hold entries read the load actually carried through the switch), and tests whether 2M steps of it REPAIR the acq8m checkpoint's last 6/72 stress-gate hold_min_load failures that 8M plain steps measurably could not close (acq8m FAIL verdict 09-04). Continues FROM the acq8m checkpoint itself (repair test, not prevention -- acq8m is otherwise the lineage's best walker: progress_ratio 0.242, dir_err 43.1deg), same transition-stress diet. Mechanism landed default-off + semantics-bank proved this cycle (6 new tests green, snapshot 8be71a38). Low-dose arm of a k={2.0, 8.0} pair.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS if eval_cmd_stress (dr0+ownDR, 72 seq episodes, seed base 93000, --strict, identical stress bundle) at 2M: ZERO hold_min_load terminations (acq8m read: 6/72) AND session_complete_frac >= 0.95 AND gait_valid_frac = 1.0 with sacrificed_legs_seen empty (acq8m: 0.986, [1,2,3]) AND walk quality within 10% of the acq8m read (progress_ratio_med 0.242, direction_err_med 43.1deg, slip/m 6.57) AND smoothness not worse (cmd_jerk_p95 7500, slew_sat_frac 1.0 +10% cap). over_current reported separately, never vetoes alone. FAIL if hold_min_load persists at this dose (compare vs the k=8.0 twin before verdicting the mechanism itself) or walk/turn quality regresses past the cap (price interfering with the walk optimum).

