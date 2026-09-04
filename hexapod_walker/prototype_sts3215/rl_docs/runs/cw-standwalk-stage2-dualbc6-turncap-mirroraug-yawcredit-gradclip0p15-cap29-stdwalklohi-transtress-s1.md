# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-transtress-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-04T08:11:51+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi-s1

**wandb_id**: o8ehsz4g

**hypothesis**: Plain English: seed-1 twin of -transtress — the best sit/rise/walk/lower policy continues on a transition-STRESS diet (SEQ_NEXT_STRESS grammar: interrupted rise->lower, walk->hold stop/restart; 2.5-9s segments so switches land mid-transition; walk commands resample ~3s) so arbitrary command changes at any time become survivable, per operator directive fb_20260904T074505_6a3ac9. Predictions identical to the seed0 arm, read against the matched -cont-s1 control.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M): vs cap29-stdwalklohi-cont-s1. PASS if eval_cmd_stress DR-0: mech_term_reasons=={} AND session_complete_frac >= control-0.10 AND walk progress_ratio_med/direction_err_med within 10% of control AND smoothness medians (cmd_jerk_p95_deg_s2, slew_sat_frac) <= control+10%. over_current terminations REPORTED separately, never veto alone (uncalibrated estimator rail — audit_over_current.py). FAIL if mech terms appear, completion drops >0.10 vs control, or walk/turn quality regresses >10%.

**verdict**: CANARY PASS -- clean promotion-gate win for the operator's smoother-universal-policy directive (fb_20260904T074505), seed1 half of the quartet. eval_cmd_stress DR-0+ownDR (72 seq episodes, identical stress bundle as the -cont-s1 control): ZERO mechanical terminations (0/72, vs control's 38/72 = 52.8% termination rate), session_complete_frac 1.0 (vs control 0.472, hard gate wants >=control-0.10), segments_reached_frac 1.0, zero over_current. Walk quality within/better than control: dir_err_med 49.9deg (control 52.9), progress_ratio 0.214 (control 0.225, -4.9%, within the 10% band), slip/m 7.4 (control 8.4, better). Smoothness TIED at the champion's slew cap, not worse: cmd_jerk_p95 7500 deg/s^2 (=control), slew_sat_frac 1.0 (=control); cur_rail_frac_med 0.008 vs control's 0.095 (>10x less current-railing -- fewer near-stall attempts, consistent with the stability win). Every pre-registered HARD+soft criterion in the run's own gate text is met or beaten. CAVEAT (why this isn't yet a green light for the acquisition-length rung): the SEED0 half of the same quartet (-transtress, verdict owned by another cycle) reads the OPPOSITE way on the identical stress eval -- 33/72 mech terms, session_complete_frac 0.542 (worse than ITS OWN -cont control's 0.819), gait_valid 0.986 with 3 sacrificed legs [3,4,5]. The transition-stress diet HELPS seed1 dramatically and HURTS seed0 on the same objective -- a real seed-dependent divergence, not a shared story. Flagging as a fork decision (see cycle DIG-IN note / STATUS Next): do not launch the acquisition-length continuation on the strength of this seed alone until the seed0/seed1 disagreement is root-caused (video + per-leg gait read on the seed0 sacrificed-leg pathology).

