# cw-robotwalk-turns-20260906-arcaware

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T13:30:44+00:00

**pod**: hexapod-mjx-train-0

**steps**: 8000000

**parent**: cw-robotwalk-turns-20260906

**wandb_id**: nr57brps

**hypothesis**: Plain English: the 8M turns arm's own course-income/sway audit (09-06 ~13:0x, OPERATOR_QUESTIONS) found the excess-sway reward term was over-charging genuine turning (a tight-arc semantics-bank cell decomposed to income=+165 vs sway=-1177, a 7x mismatch) because it measured sway as perpendicular distance from ONE straight chord across the whole window, which an arc bows away from even when perfectly tracked -- not a real course problem. Built + bank-proved a fix this cycle: reward.walk_sway_arc_aware (default-off, bit-exact-verified on every drive in the base semantics-bank stack and explicitly on a curving command) projects each sample against a LOCAL per-tick tangent of a shadow reference path anchored at the body's own window-start position instead of one global chord; test_course_income_semantics.py's own previously-RED test_wz_arc_tight_turn_gracefully_discounted_not_exploited now PASSES with this flag on (12/14 green; the 2 remaining reds are the SEPARATE, already-deferred plant-geometry recalibration debt named in OPERATOR_QUESTIONS 2026-09-02, untouched by this fix). This run turns the fix on and resumes the turns-20260906 lineage from its clean 8M checkpoint (NOT the misaligned -cont8m-resume1 continuation) to see whether removing this reward-side artifact lets the ALREADY-healthy turn-tracking mechanism close the joygate's course_err_1s_med gap (8.55deg vs the 5.17deg bar) that the previous continuation made WORSE while reward kept rising (audited misalignment, not a budget ceiling).

**gate**: ACQ 8M (16M cumulative on this lineage). PASS if: (a) DR-0 gate gait_valid stays 6/6 all 4 modes, 0 falls/terminations, no sacrificed legs (walking must not regress); (b) fresh eval_joystick_gate stress_mix course_err_1s_med improves vs this run's own 8M parent's 8.55deg reading (moving toward or under the 5.17deg Candidate-B bar), with gait_valid_frac still 1.0 and 0 falls; (c) fresh eval_cmd_suite/eval_yaw tip wz_err_med does not regress vs the parent's 0.108/0.100 baseline read on identical cells; (d) straight-heading forward prog_m stays >=0.29 m/12s, slip/m <=2.9. FAIL/misaligned if course_err_1s_med is flat-or-worse than the parent's 8.55deg while reward still rises (repeats the -cont8m-resume1 fingerprint even with the reward-side fix on -- would mean the sway-chord artifact was not the (or not the only) cause and the deadband/sigma dose itself needs the deferred plant recalibration first). CONTINUE (08-21) if course_err improves but has not yet cleared 5.17deg and reward is still rising with no exploit signature.

