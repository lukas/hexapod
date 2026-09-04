# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-04T08:18:16+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi-s1

**wandb_id**: 14qwcfjl

**hypothesis**: Plain English: seed-1 MATCHED CONTROL for -transtress-s1 (operator directive fb_20260904T074505_6a3ac9): identical 2M continuation with the training diet unchanged, isolating extra steps from the transition-stress diet and providing the seed-1 stress-suite/smoothness baseline.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. COMPARATOR run (2M canary): health-only — reward not collapsing, no new termination class on standard prestage evals; its eval_cmd_stress + purewalk reads are the named baseline for the -transtress-s1 PASS/FAIL. No behavior-class closure from this run alone.

**verdict**: CANARY PASS (health-only, as designed). 2M-step plain continuation of cap29-stdwalklo-hi-s1 (seed1), the matched control for -transtress-s1. eval_cmd_stress: 38/72 mech terms (hold_low_height 18, hold_min_load 20 -- known hold classes), session_complete_frac 0.472 (notably worse hold-stability than seed0's -cont at 0.819/13terms -- a genuine seed effect, not new pathology), dir_err_med 53deg, slip/m 8.4, progress_ratio 0.225, gait_valid 1.0, zero sacrificed legs, zero over_current. Reward mean -38.4, quarters [17.6,44.1,-41.2,-95.9] -- same family Q3-dip shape as -cont but WITHOUT -cont's Q4 partial recovery (worse end-of-window trajectory for this seed). Machinery healthy (no blowup, no new termination class); becomes -transtress-s1's confirmed baseline (PASS, see that verdict). Also the seed-1 half of the continuation-drift finding: probe_turn_authority pure-turn wz_med (+0.147/+0.158, -0.190/-0.191) sits 30-35% below the frozen cap29-stdwalklo-hi-s1 baseline (+0.226/-0.247) from plain continuation alone -- corroborates -cont's finding that the steering-lever axis's FAIL wall (scored vs frozen baselines) is contaminated by continuation drift and needs re-scoring against these matched controls.

