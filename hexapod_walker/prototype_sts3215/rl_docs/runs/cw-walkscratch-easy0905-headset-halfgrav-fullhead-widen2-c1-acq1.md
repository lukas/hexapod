# cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T22:23:34+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c1

**wandb_id**: v33rv9wx

**hypothesis**: Plain English: widen2-c1's 2M canary showed that widening the halfgrav heading champion's command set from the passing 5-way (0,+-45,+-90) to the full 8-way compass (adding reversals +-135/180) FROM the medhead champion (not a cold jump) keeps the gait valid (21/24, 0 falls) and tightens reversal-heading tracking vs the cold-jump fullhead-c1 baseline (direrr 88.5->75.5deg, slip 6.8x lower). This is the acquisition-scale (40M) confirmation: does the progressive-widen recipe hold up at full budget, closing the reversal-heading course-tracking gap enough to call the widen curriculum shape validated for this ladder?

**gate**: ACQ PASS if gait_valid stays majority (>=18/24, matching medhead-acq1's own bar) with 0 falls AND direction_err_mean_deg/course_err at the reversal headings continues to tighten vs both fullhead-c1's cold-jump baseline (28-161deg) and this run's own 2M canary read (walk/det med slip 5.02, prog med 1.14) rather than re-widening back toward fullhead-c1's failure range. ACQ FAIL if gait_valid drops into minority or a leg is chronically sacrificed (matching the base-family entrenchment pattern). ACQ CONTINUE if reward is still climbing and gait stays valid but course-tracking is still improving/ambiguous at 40M.

