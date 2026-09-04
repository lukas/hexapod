# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-04T08:15:06+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi

**wandb_id**: e96q4a2c

**hypothesis**: Plain English: MATCHED CONTROL for -transtress (operator directive fb_20260904T074505_6a3ac9): the identical 2M continuation of the best sit/rise/walk/lower policy with the training diet UNCHANGED, isolating 'more training steps' from 'the new transition-stress diet' and producing the smoothness-telemetry + stress-suite baseline the arm's gate reads against. Prediction: its own stress-suite read reflects the lineage's current transition fragility; any -transtress gain beyond this baseline is diet-caused.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. COMPARATOR run (2M canary): health-only — reward not collapsing, no new termination class on standard prestage evals; its eval_cmd_stress + purewalk reads become the named baseline for the -transtress PASS/FAIL. No behavior-class closure from this run alone.

**verdict**: CANARY PASS (health-only, as designed — not a skill/behavior gate). 2M-step plain continuation of cap29-stdwalklo-hi (seed0), the matched control for -transtress. eval_cmd_stress (dr0+owndr, 72 seq episodes): 13/72 mech terms (hold_low_height 5, hold_min_load 8 -- known hold-posture classes, no new class), session_complete_frac 0.819, dir_err_med 53deg, slip/m 6.7, progress_ratio 0.249, gait_valid 1.0, zero sacrificed legs, zero over_current. Reward mean 145.8, quarters [20.2,49.8,-102.9,-29.3] -- Q3 dip / Q4 partial recovery matches the known cap29-family shape, not a new collapse. Machinery healthy; serves its purpose as -transtress's baseline (see that verdict). NEW FINDING (not this run's own gate, logged for the steering axis): its own probe_turn_authority pure-turn wz_med (+0.171/-0.194, +0.172/-0.206 across 2 episode seeds) already sits ~22-23% below the FROZEN cap29-stdwalklo-hi baseline (+0.223/-0.250) used to gate the whole steering-lever axis -- plain continuation alone breaches that axis's 10% pure-turn cap with zero lever involved. See STATUS Next: re-score the lever-axis FAIL wall against matched-continuation controls (this run + -cont-s1), not the stale frozen baseline.

