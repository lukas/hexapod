# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-transtress-s1-acq8m-mlcontprice2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-04T12:07:19+00:00

**pod**: hexapod-mjx-train-10

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-transtress-s1-acq8m

**wandb_id**: w2m8pcxs

**hypothesis**: Plain English: the policy keeps dying when it switches into a standing hold mid-session because one foot stays unloaded through the switch -- this arm adds a small dense price for that unloaded foot (reward.k_hold_min_load_short=2.0, the priced twin of the hold_min_load termination, sharing its min-over-feet EMA and 0.3N floor, active from the first hold tick including the grace window) plus the EMA-continuity fix (safety.hold_min_load_ema_continuous=1: EMA seeded from measured load at reset and updated every tick in every mode, so hold entries read the load actually carried through the switch), and tests whether 2M steps of it REPAIR the acq8m checkpoint's last 6/72 stress-gate hold_min_load failures that 8M plain steps measurably could not close (acq8m FAIL verdict 09-04). Continues FROM the acq8m checkpoint itself (repair test, not prevention -- acq8m is otherwise the lineage's best walker: progress_ratio 0.242, dir_err 43.1deg), same transition-stress diet. Mechanism landed default-off + semantics-bank proved this cycle (6 new tests green, snapshot 8be71a38). Low-dose arm of a k={2.0, 8.0} pair.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS if eval_cmd_stress (dr0+ownDR, 72 seq episodes, seed base 93000, --strict, identical stress bundle) at 2M: ZERO hold_min_load terminations (acq8m read: 6/72) AND session_complete_frac >= 0.95 AND gait_valid_frac = 1.0 with sacrificed_legs_seen empty (acq8m: 0.986, [1,2,3]) AND walk quality within 10% of the acq8m read (progress_ratio_med 0.242, direction_err_med 43.1deg, slip/m 6.57) AND smoothness not worse (cmd_jerk_p95 7500, slew_sat_frac 1.0 +10% cap). over_current reported separately, never vetoes alone. FAIL if hold_min_load persists at this dose (compare vs the k=8.0 twin before verdicting the mechanism itself) or walk/turn quality regresses past the cap (price interfering with the walk optimum).

**verdict**: CANARY FAIL - MECHANISM (k=2.0 low-dose twin): eval_cmd_stress (seed 93000, --strict) FAILS its own gate: mech_term_reasons hold_min_load 19/216 seq eps (dr0 14/108=13.0%, owndr 5/108=4.6%), session_complete_frac 0.912 (<0.95 bar), gait_valid_frac 0.995 with sacrificed_legs_seen=[0,2,3,5] (gate wants 1.0/empty), direction_err_med 47.9deg vs acq8m's 43.1deg (+11.1%, breaches the 10% cap); progress_ratio/slip/smoothness all within cap. DATA-QUALITY NOTE: this eval used n=54/mode/pass (216 total) vs its k=8.0 twin mlcontprice8's matched n=18/mode/pass (72 total) -- a 3x sample mismatch from the launching cycle's invocation, not a matched canary pair. Read as RATES instead: mlcontprice2(k=2.0) dr0+owndr combined fire rate 8.8% is statistically indistinguishable from the UNFIXED acq8m baseline's own 8.3% (6/72) -- k=2.0 buys ~zero net protection -- while mlcontprice8 (k=8.0, matched n=18) roughly HALVES it to 4.2% and fully cleans DR-0 (0/36) + gait-validity. Per-pass split is non-monotonic in raw dr0 rate (baseline 5.6% -> k2 13.0% -> k8 0%) which is noisy at n=36 per baseline/k8 but the larger-n k2 read is not; treat the k2 dr0 spike as low-dose noise, not evidence the mechanism hurts, since k2 also uniquely fails on direction_err/gait_valid/session_complete that k8 does not. CONCLUSION: dose-response is real and monotonic in net effect (0 -> no help, 8 -> clear partial fix); k=2.0 is below the mechanism's effective threshold. NEXT: bracket further with a higher-dose twin (k=16.0) matched at n=18/mode/pass, continuing from the same acq8m checkpoint on the identical stress diet -- launching this cycle.

