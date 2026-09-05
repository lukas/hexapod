# cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c2b-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T22:28:03+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c2b

**wandb_id**: 5vqxgqjm

**hypothesis**: Plain English: widen2-c1 and widen2-c2b (2 independent seeds, matched 40M-champion provenance) both showed that widening the halfgrav heading champion's command set from the passing 5-way to the full 8-way compass (adding reversals) keeps the gait valid and tightens reversal-heading tracking, closing the champion-specific-luck alternative. This is the 2nd-seed acquisition-scale (40M) confirmation, run in parallel with widen2-c1-acq1, to build the n=2 acquisition-scale evidence this campaign's own pattern (base/halfgrav heading rungs) requires before calling the widen-from-medhead curriculum shape validated.

**gate**: ACQ PASS if gait_valid stays majority (>=18/24) with 0 falls AND direction_err/course_err at the reversal headings continues to tighten vs this run's own 2M canary read (direrr 62.0, courserr 63.6, slip 4.94) rather than re-widening back toward the confounded widen2-c2's failure range (89/130/124). ACQ FAIL if gait_valid drops into minority or a leg is chronically sacrificed. ACQ CONTINUE if reward is still climbing and gait stays valid but course-tracking is still improving/ambiguous at 40M. Read together with widen2-c1-acq1: if both PASS, the widen-from-medhead recipe is validated at acquisition scale for this ladder.

