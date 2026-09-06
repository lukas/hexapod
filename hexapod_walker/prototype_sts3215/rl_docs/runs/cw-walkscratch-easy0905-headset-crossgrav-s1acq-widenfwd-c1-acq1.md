# cw-walkscratch-easy0905-headset-crossgrav-s1acq-widenfwd-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T05:13:33+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s1acq-widenfwd-c1

**wandb_id**: wzh30m53

**hypothesis**: Plain English: s1acq-widenfwd-c1 (forward-composing the full 8-way heading set onto the campaign's cleanest crossgrav champion) just CANARY PASSed at 2M (gait_valid 22/24, no chronic leg sacrifice, but heavy slip/negative progress on the hard quarter-turn/reversal headings -- the same distance-graded course-tracking gap already documented on the medhead/widen2c1 siblings). This is the acquisition-scale (40M) confirmation matching the medhead-widenfwd-c1-acq1 and widen2c1-irrfwd-c1-acq1 precedent (both held clean/improved at 40M): does the campaign's single cleanest source hold this composition at full budget, or does it join the ~half of healthy-source champions that entrench toward chronic leg[1,4] sacrifice under the startjitter panel at ACQ scale (irracq1/irr2acq1/s3acq)?

**gate**: ACQ PASS if aggregate gait_valid stays majority-or-better (>=18/24) with no chronic (same leg flagged in most/all episodes of one mode) single-leg sacrifice, matching or improving the 2M canary's 22/24, and 0 falls. ACQ FAIL if walk_startjitter/det or walk_startjitter/sto collapses to the leg[1,4]-style chronic-park fingerprint or any new chronic single-leg pattern emerges. ACQ CONTINUE if reward is still climbing with borderline (non-chronic) duty softening, per the 08-21 ruling.

**verdict**: ACQ PASS/HOLDS — s1acq-widenfwd-c1-acq1 (8-way heading set forward-composed onto the campaign's single cleanest crossgrav champion, s1acq-abrupt-c1-acq1) matches its own 2M canary at full 40M budget. Aggregate gait_valid 21/24 vs the canary's 22/24 (walk/det 5/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 4/6) — within noise, 0 falls/terminations in all 24 episodes. Sacrifice pattern: det/4 keeps the IDENTICAL leg[0,3] flag at the identical episode index as the canary (unchanged); startjitter/sto shows leg[0] in 2 episodes (idx1,5), replacing the canary's own single leg[4] flag at idx4 — a lateral shift, not a new chronic pattern (no leg majority-flagged in any one mode). Reward rising every quarter. Video (walk_det_0/1 frame strips) shows continued six-leg forward gait, no drag/freeze. This is the campaign's cleanest single source holding a heading-breadth composition at full budget, matching the medhead-widenfwd-c1-acq1 and widen2c1-irrfwd-c1-acq1 precedent (both held/improved). Next: licensed a cont40m endurance helping this cycle (clean-at-40M source, per the established cleanliness-margin-at-40M rule).

