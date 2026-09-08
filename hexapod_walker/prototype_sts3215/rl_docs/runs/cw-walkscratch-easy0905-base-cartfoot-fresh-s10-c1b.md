# cw-walkscratch-easy0905-base-cartfoot-fresh-s10-c1b

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-08T06:47:32+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-cartfoot-fresh-s10

**hypothesis**: Corrected relaunch of s10-c1 (crashed <1s on the documented --activation-fn+--init-from SystemExit gotcha, zero steps logged). Own-checkpoint continuation of the fresh-init cart-foot canary (fork b, seed 10): does the same +38M budget that took base-s0..s4 from 2M cold start to their established PASS band (six-leg walking, zero falls) also get the fresh cart-foot ON arm there, and if so does its MATURE slip/m beat or lose to that established band -- the fork(b) question fork(a)'s warm-start retrofit could not answer cleanly.

**gate**: PASS-BAND if it reaches gait_valid/no-falls/slip comparable to the base family's own established PASS band (base-s0..s4) on the same fixed-forward walk panel -- report slip/m specifically vs that band. FAIL if it cannot reach walking at all by 40M while sibling base-family seeds all could. Per the 08-21 ruling, judge on reward trend + eval together, not reward alone.

