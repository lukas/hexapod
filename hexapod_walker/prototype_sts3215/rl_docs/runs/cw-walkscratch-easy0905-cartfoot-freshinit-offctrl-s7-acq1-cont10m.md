# cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s7-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T07:46:06+00:00

**pod**: hexapod-mjx-train-3

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s7-acq1

**wandb_id**: irimsdt7

**hypothesis**: This cycle's ON cont10m (cartfoot-freshinit-c1-s7-acq1-cont10m, already running) tests whether the fresh-init cart_foot ON arm's 40M slip PARITY (0.94-0.99x vs OFF) holds or degrades at 50M cumulative, mirroring fork(a)'s late-onset-degradation shape. That comparison is only valid against a matched OFF continuation at the SAME depth -- this run is that missing matched control, warm-started from the OFF arm's own PASSed 40M acquisition checkpoint, same +10M budget as its ON sibling.

**gate**: 24-ep walk/walk_startjitter det+sto retention gate at 50M cumulative: PASS/HOLDS = 0 new falls/terminations vs this run's own 40M read, gait_valid staying in-or-above its established 6/6 (det)/1-6 (startjitter/det) band, mean slip/m staying in the 2.6-3.4/m band already measured at 40M (no unexplained drift). This band is what the ON cont10m's slip ratio is read against -- if this control itself drifts, read the ON/OFF cont10m pair as inconclusive rather than crediting/blaming the Cartesian mechanism.

