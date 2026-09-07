# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-turndiet-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-03T09:24:53+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-acq1

**hypothesis**: Plain English: now that the walk-core std-anneal fix (stdwalklohi-acq1, PASS 09-03) has closed the sto/det walk-progress collapse, the single remaining open gap on THIS lineage's DONE-gate session read is steering: direction_err_med 43.6-44.6deg (tick) / course_err_1s_med 22.6-28.2deg (windowed) both stayed elevated at full 38M scale, and the 09-02 dig-in traced the worst course_speed_ratio dips to exactly the ~4s walk_cmd_resample_s command-change boundaries in the EVAL diet (eval_mixed_session's stress_mix, resample_s=4.0/jitter=0.5) -- while TRAINING itself only ever exercises a slower/gentler diet (goal.walk_cmd_resample_s=6.0/jitter=0.2, no explicit walk_cmd_mode=stress_mix). Does training on the SAME faster/harder stress_mix command diet the policy is actually judged on (one lever: match train-time resample to eval-time) close some of that steering gap, i.e. is this a train/eval DISTRIBUTION MISMATCH rather than a hard turn-rate ceiling (turn authority wz_med 0.19-0.21 rad/s was already shown std-insensitive and unaffected by seed/dose in the 09-02 grid)?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Cheap 2M canary, warm-started from the SAME 2M gradclip0p15-canary ancestor stdwalklohi-acq1 itself used (one lever changed: cfg only, no init/std change; ancestor checkpoint retroactively stamped robot_abs/robot_abs_tibia_v2 this cycle via the new stamp_legacy_checkpoint tool -- see OPERATOR_QUESTIONS.md 09-03, weights bit-identical, verified). (1) probe_turn_authority (wz_cmd=+-0.25, seeds 0/1) wz_med must stay >=0.07 rad/s. (2) det+sto eval_checkpoint.py walk-mode read UNDER THE SAME eval stress_mix diet (goal.walk_cmd_mode=stress_mix, resample_s=4.0, jitter=0.5) against the stdwalklohi-acq1 session baseline (direction_err_med 44.56deg/course_err_1s_med 22.55-22.84deg seed0, 43.6/27.26-28.2 seed1; slip_per_m_med 2.82-2.94): PASS if direction_err_med or course_err_1s_med drops materially (>=20%) without slip rising past ~3.0 or falls appearing; PARTIAL if turn-authority+zero-fall hold but steering doesn't move; FAIL if turn authority regresses below 0.07 or terminations appear.

**refused_reason**: W&B already has a run named cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-turndiet-canary (names are append-only; pick a new one)

