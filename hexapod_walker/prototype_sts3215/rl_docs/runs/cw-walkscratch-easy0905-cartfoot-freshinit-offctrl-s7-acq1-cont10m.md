# cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s7-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL - GAIT RETENTION

**created**: 2026-09-08T07:46:06+00:00

**pod**: hexapod-mjx-train-3

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s7-acq1

**wandb_id**: irimsdt7

**hypothesis**: This cycle's ON cont10m (cartfoot-freshinit-c1-s7-acq1-cont10m, already running) tests whether the fresh-init cart_foot ON arm's 40M slip PARITY (0.94-0.99x vs OFF) holds or degrades at 50M cumulative, mirroring fork(a)'s late-onset-degradation shape. That comparison is only valid against a matched OFF continuation at the SAME depth -- this run is that missing matched control, warm-started from the OFF arm's own PASSed 40M acquisition checkpoint, same +10M budget as its ON sibling.

**gate**: 24-ep walk/walk_startjitter det+sto retention gate at 50M cumulative: PASS/HOLDS = 0 new falls/terminations vs this run's own 40M read, gait_valid staying in-or-above its established 6/6 (det)/1-6 (startjitter/det) band, mean slip/m staying in the 2.6-3.4/m band already measured at 40M (no unexplained drift). This band is what the ON cont10m's slip ratio is read against -- if this control itself drifts, read the ON/OFF cont10m pair as inconclusive rather than crediting/blaming the Cartesian mechanism.

**verdict**: CORRECTED RETENTION READ (root watchdog, 2026-09-08): the exact frozen OFF control gate requires gait_valid in-or-above 6/6 ordinary det and 1-6/6 start-jitter det. The 40M->cont10m report changes are 6->0/6 and1->0/6, aggregate19->12/24, so this control fails its registered gait-retention condition. Zero terminations and mean-slip retention remain supported: means2.8130/3.3687/2.8615/3.3070 per four panels. Shared deterministic leg-use decline in both arms is informative about recipe/depth, but does not waive the preregistered control-health condition. Its explicit control-drift proviso makes the overall paired depth conclusion inconclusive; narrow slip/fall parity is still descriptive. No new physics/reward/evaluator threshold, no universalCartesian closure, and no automatic extension. Original PASS text and exact gate retained in artifacts/rl_watchdog/cartfoot_depth_read_20260908/verdicts_before_correction.json and Git history; exact eight reports and mean-based audit in that directory. This does not alter the separate torque1x canaries, which start from frozen40M parents.

