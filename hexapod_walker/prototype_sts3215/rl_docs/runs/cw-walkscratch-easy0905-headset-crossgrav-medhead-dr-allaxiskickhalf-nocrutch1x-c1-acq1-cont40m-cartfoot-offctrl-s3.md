# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-cartfoot-offctrl-s3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FINISHED

**created**: 2026-09-08T06:02:34+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

**wandb_id**: a2o71f5o

**hypothesis**: Plain English: matched zero/off control for cartfoot-c1-s3 -- the byte-identical seed3 +2M continuation of the cont40m champion with NO cart_foot keys, so the ON seed replicate's read is causal (mechanism vs seed noise) rather than 'seed3 training happened to differ.'

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Retention gate: 0 falls/terminations, gait_valid in-or-above the source's 21-24/24 band, slip/m in the established 5-6/m det band. Serves as the comparison baseline for cartfoot-c1-s3; if this control itself regresses, read the seed3 pair as inconclusive.

