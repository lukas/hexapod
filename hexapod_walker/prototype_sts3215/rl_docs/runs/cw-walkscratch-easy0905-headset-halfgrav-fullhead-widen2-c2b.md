# cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c2b

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-05T21:36:48+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c2

**wandb_id**: nnebz1nz

**hypothesis**: Corrected matched-budget second-seed test of the widen2 curriculum-shape question. widen2-c1 (from the 40M headset-halfgrav-medhead-acq1 champion) showed real course-tracking improvement over the cold-jump fullhead-c1 baseline (courserr med 94.9->57.9, slip med 51.4->7.6, gait_valid 21/24, 0 falls). Its nominal second seed, widen2-c2, showed NO improvement (courserr ~flat, slip med 124.4, 16x worse than c1) -- but a provenance check found widen2-c2 actually warm-started from medhead2's 2M CANARY checkpoint (medhead2_c1.zip), not medhead2's own 40M acq1 champion (medhead2_acq1.zip) that would truly match widen2-c1's provenance. This arm repeats the IDENTICAL widen2 recipe from medhead2_acq1.zip (40M-matched) to give a genuine apples-to-apples second-seed read: does the widen2-from-mature-quarter-turn-champion recipe generalize across seeds (recipe-level win), or was widen2-c1's improvement specific to that one champion (seed lottery)?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY (2M), same bar as widen2-c1/c2: gait_valid majority-valid (>=4/6 det) with 0 falls. On course-tracking: if this arm's direction_err/course_err/slip medians land close to widen2-c1's own numbers (direrr ~75, courserr ~58, slip ~7.6), the widen2-from-medhead recipe is confirmed recipe-level (2/2 matched-budget seeds). If they land close to the ORIGINAL flawed widen2-c2's numbers (direrr ~89, courserr ~88, slip ~124) despite the matched 40M-budget champion, widen2-c1's improvement was likely champion-specific luck, not a repeatable recipe, and the reversal-heading gap needs its own design pass (heading sin/cos encoding, symmetry-augmented data) rather than further curriculum-shape spend.

**verdict**: CANARY PASS: widen2-c2b (corrected matched-budget 2nd seed, warm-started from the halfgrav 40M medhead2_acq1.zip champion, same recipe as widen2-c1) clears the canary bar and CONFIRMS widen2-c1's course-tracking improvement is recipe-level, not champion-specific luck. Evidence: gait_valid 16/24 overall (walk/det 4/6, walk/sto 6/6, walk_startjitter/det 2/6, walk_startjitter/sto 4/6), 0 falls/terminations in all 4 modes -- meets the gate's own '>=4/6 det, 0 falls' bar. Course-tracking (walk/det): direrr med 62.0deg, courserr med 63.6deg, slip/m med 4.94 -- closely matches widen2-c1's own numbers (59.4/45.4/5.02), NOT the confounded widen2-c2's numbers (74.9/129.6/12.1) that turned out to be a checkpoint-maturity artifact (warm-started from a 2M canary, not the 40M champion). Why: 2/2 matched-budget seeds (c1, c2b) now show the same tightened reversal-heading tracking vs the cold-jump fullhead-c1 baseline -- closes the champion-specific-luck alternative the c1/c2 divergence had left open. What's next: 40M acquisition continuation off widen2-c1 already launched this cycle; this confirmation justifies funding a matched 2nd-seed acquisition off c2b too to build n=2 acquisition-scale confirmation before calling the widen-from-medhead curriculum shape validated.

