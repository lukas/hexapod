# cw-walkscratch-easy0905-headset-halfgrav-widenirr-c3-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T03:30:15+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-widenirr-c3

**wandb_id**: 9o5dtbpz

**hypothesis**: Does widenirr's 3rd tie-breaking seed (23/24 gv 2M canary, own 0.5g, only a course-tracking caveat not a gait-validity one) hold up at full 40M acquisition budget the same way sibling widenirr-c1-acq1 did (ACQ PASS, 22/24)?

**gate**: PASS if gait_valid stays >= its own 2M canary (23/24) or degrades only mildly, 0 falls, no NEW chronically-sacrificed leg. Track course-tracking metrics (wrong_direction_frac, course_err) explicitly -- if they worsen at 40M vs 2M that's a real regression to flag even under an otherwise-passing gait_valid count. FAIL/MECHANISM if gait_valid collapses toward the widenirr-c2b FAIL fingerprint despite rising reward.

**verdict**: ACQ PASS -- gait_valid holds at 40M: aggregate 21/24 (walk/det 5/6, walk/sto 5/6, walk_startjitter/det 6/6, walk_startjitter/sto 5/6) vs the own 2M canary's 23/24, a mild degrade within the gate's own tolerance. 0 falls/24 in both. No NEW chronic single-leg sacrifice: every flagged sac list is a single non-chronic episode (walk/det ep3 [2,5], walk/sto ep5 [2], walk_startjitter/sto ep0 [4]), never the same leg repeating >=4/6 like the widenirr-c2b FAIL fingerprint this gate explicitly named. Course-tracking metrics the gate flagged for special attention IMPROVED, not worsened: wrong_direction_frac median 0.331->0.273, course_err_1s_med 56.4->38.5deg (canary vs acq1, all-episode aggregate). The occasional huge slip_per_m outlier (100+) in isolated /sto episodes is a pre-existing pattern already present at the 2M canary (canary had 4 such outliers vs acq1's 2), not a new regression. Video (walk_det_2, 6-frame strip) confirms genuine six-leg cycling with clear rightward body translation across the checkerboard. This is the 3rd/3 widenirr halfgrav seed to reach acquisition scale cleanly (c1 CANARY PASS, c2b CANARY FAIL, c3 now ACQ PASS at 40M) -- closes the tie-breaking seed question 2/3 healthy. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_halfgrav_widenirr_c3_acq1_gate/report.json vs .../cw_walkscratch_easy0905_headset_halfgrav_widenirr_c3_gate/report.json, walk_det_2_sheet.png, W&B 9o5dtbpz.

