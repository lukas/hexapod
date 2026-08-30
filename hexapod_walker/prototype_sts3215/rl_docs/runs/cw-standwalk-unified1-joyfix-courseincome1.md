# cw-standwalk-unified1-joyfix-courseincome1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-08-30T03:03:03+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-standwalk-unified1-joyfix-coursedisp-w015-c1

**hypothesis**: Plain English: does adding the new windowed net-command-following INCOME term plus an excess-sway charge on top of the already-trained sub-stride course-disp mechanism (warm-start off cw-standwalk-unified1-joyfix-coursedisp-w015-c1, window_s=0.15, k_walk_course_disp=2.0) finally move direction_err off the flat ~55-65deg band that every disp-only window dose (1.5s=coursedisp-c1, 0.35s=w035-c1, 0.15s=w015-c1 -- all three now verdicted PASS-no-delta, dir_err medians 56.5-64.1deg pooled det, activation ~52% of commanded ticks per a fresh course-trace re-measurement this cycle, correcting an earlier n=1 probe that used the wrong denominator) failed to move? Per REWARD.md's own reward-design directive (fb_20260829T142239_63c818): k_walk_course_income prices NET windowed displacement vs the INTEGRATED command (support-gated, teacher-deadbanded angle x speed-completion factor, optimum at the command) and k_walk_excess_sway prices only RMS path deviation beyond the teacher's own 5mm allowance -- together these are the operator-registered primary moving-command objective, distinct from the disp term's raw cosine-to-instant-displacement pricing. Single new lever: both k coefficients added at their bank-proven dose (2.0/2.0, WALK_COURSE_INCOME bank 12/12 green), everything else byte-identical to the w015-c1 recipe (still carries k_walk_course_disp=2.0/window=0.15).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Mechanism-health CANARY ONLY at 2M (same DR-0 panel as the coursedisp trio, n=6 det+sto per walk-family mode incl startjitter): PASS-with-delta = direction_err_mean_deg (walk/det+walk_startjitter/det pooled) drops >=15deg off the established 55-65deg flat band (i.e. med <=40-50deg) AND slip/m stays within 1.5x the long-s0 parent band (det ~3.2, sto ~18.1) AND gait_valid>=5/6 with no new sacrificed leg AND reward doesn't collapse vs w015-c1's own quarters trend -> the income/sway mechanism succeeds where raw disp pricing didn't; escalate to acquisition + seed replicate. PASS-no-delta (income/sway telemetry fires but dir_err stays flat) = the course-tracking problem needs a bigger structural fix (stage-2 composition/distillation with a genuinely better walk source, not more reward shaping on this lineage) -- do not fund a 3rd reward-shaping lever on unified1-mix. FAIL = reward collapse vs w015-c1's own trend or terminations spike -> revert, root-cause before any repeat.

