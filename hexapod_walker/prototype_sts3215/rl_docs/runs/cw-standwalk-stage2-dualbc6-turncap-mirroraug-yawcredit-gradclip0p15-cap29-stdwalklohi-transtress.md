# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-transtress

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-04T08:08:14+00:00

**pod**: hexapod-mjx-train-6

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi

**wandb_id**: 1nt9c9ph

**hypothesis**: Plain English: the best sit/rise/walk/lower policy has only ever trained on polite 6-8s mode segments that settle before switching; this arm continues it on a transition-STRESS diet (new SEQ_NEXT_STRESS grammar: rise can be interrupted into lower, walk can stop into hold; segments 2.5-9s so switches land mid-transition; walk commands resample every ~3s vs 6s) so arbitrary command changes at any time become survivable, per operator directive fb_20260904T074505_6a3ac9. Prediction-if-true: on the new eval_cmd_stress suite (seed base 93000, 60s, det+sto, DR-0+own-DR) this arm gets zero mechanical terminations and session_complete_frac >= the matched -cont control, without degrading walk progress/direction >10% vs control. Prediction-if-false: mechanical terms appear or walk quality collapses (diet too hard at 2M from this init). Strongest alternative: extra steps alone explain any gain — that is exactly what the -cont control isolates.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M, do not judge mature skill): vs the matched cap29-stdwalklohi-cont control. PASS if eval_cmd_stress DR-0: mech_term_reasons=={} AND session_complete_frac >= control-0.10 AND walk progress_ratio_med/direction_err_med within 10% of control AND smoothness medians (cmd_jerk_p95_deg_s2, slew_sat_frac) <= control+10%. over_current terminations are REPORTED separately and never veto alone (uncalibrated estimator rail: 2.64A == 2.2N*m forcerange x 1.2 A/N*m — audit_over_current.py); a safety claim additionally needs corroborated-stall classification. FAIL if mech terms appear, completion drops >0.10 vs control, or walk/turn quality regresses >10%.

