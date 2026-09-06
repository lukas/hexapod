# cw-walkscratch-easy0905-headset-crossgrav-widen2c1-abrupt-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T03:51:35+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widen2c1-abrupt-c1-acq1

**wandb_id**: pvdwyhuv

**hypothesis**: Plain English: a sibling crossgrav champion (irr-timing recipe) ACQ-FAILed via base(1g) leg-1/4 structural entrenchment after 40M steps despite a clean 2M canary and rising reward (CURRENT_TRUTHS 09-06 ~03:1x); does the SAME slow-clock entrenchment risk hit the widen2 (full 8-way heading) crossgrav champion given another 40M 1g steps, or is it recipe/seed-specific? widen2c1-abrupt-c1-acq1 is a healthy ACQ PASS (20/24 gait_valid, 0 falls, slip improved vs its own canary) off a materially different recipe (heading-widening, not timing-jitter) than the irracq1 regression.

**gate**: HARDENING/endurance continuation (+40M, own checkpoint, no cfg change). PASS/HOLDS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with no NEW chronic leg beyond this checkpoint's own established 40M read (20/24). FAIL/ENTRENCHES if walk/det or walk/sto regresses to majority failure or a leg[1,4]-pattern chronic sacrifice newly emerges -- adds a 2nd recipe to the 'any crossgrav champion entrenches given enough budget' finding.

**verdict**: PASS/HOLDS: 2nd +40M helping (80M cumulative 1g steps) on widen2c1-abrupt-c1-acq1 reproduces the checkpoint's own established 40M read within noise. Aggregate gait_valid 19/24 (walk/det 6/6, walk/sto 6/6, walk_startjitter/det 3/6 sac=[1] all 3, walk_startjitter/sto 4/6 sac=[1]x1+[5]x1) vs the parent 40M read's own 20/24 (walk/det 6/6, walk/sto 6/6, walk_startjitter/det 3/6 sac mixing [1,4]/[4]/[4], walk_startjitter/sto 5/6 sac=[1]x1). Both primary gated modes (walk/det, walk/sto) stay full majority (6/6) with 0 falls in all 24 episodes either read. The startjitter-panel chronic leg was already leg-1-implicated at 40M (co-sacrificed with leg-4 twice, solo once in sto); at 80M it consolidates to leg-1 alone in det (same 3 episode indices) plus one new isolated (non-chronic, single-occurrence) leg-5 sto miss -- a shift in which member of the pre-existing [1,4] pair dominates, not an unrelated NEW leg entering the picture, and reward is still monotonically rising (quarters 62/355/664/909, no plateau). Contact sheet confirms genuine six-leg cycling with body translation throughout. This is the 2nd 'cleanliness margin predicts endurance outcome' data point in the PASS direction (parent was clean-ish, not chronic, at 40M) -- consistent with the s1acq/medhead precedent that a source without a fully-entrenched chronic pattern at 40M holds flat through a 2nd +40M helping, contrasted with s3acq's genuine worsening from an already-chronic 40M base. No further budget needed on this specific line; folds into the growing endurance-panel dataset for the cleanliness-margin rule.

