# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-transtress-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-04T08:11:51+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi-s1

**wandb_id**: o8ehsz4g

**hypothesis**: Plain English: seed-1 twin of -transtress — the best sit/rise/walk/lower policy continues on a transition-STRESS diet (SEQ_NEXT_STRESS grammar: interrupted rise->lower, walk->hold stop/restart; 2.5-9s segments so switches land mid-transition; walk commands resample ~3s) so arbitrary command changes at any time become survivable, per operator directive fb_20260904T074505_6a3ac9. Predictions identical to the seed0 arm, read against the matched -cont-s1 control.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M): vs cap29-stdwalklohi-cont-s1. PASS if eval_cmd_stress DR-0: mech_term_reasons=={} AND session_complete_frac >= control-0.10 AND walk progress_ratio_med/direction_err_med within 10% of control AND smoothness medians (cmd_jerk_p95_deg_s2, slew_sat_frac) <= control+10%. over_current terminations REPORTED separately, never veto alone (uncalibrated estimator rail — audit_over_current.py). FAIL if mech terms appear, completion drops >0.10 vs control, or walk/turn quality regresses >10%.

