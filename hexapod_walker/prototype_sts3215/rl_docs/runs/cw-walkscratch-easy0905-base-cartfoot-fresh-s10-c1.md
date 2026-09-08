# cw-walkscratch-easy0905-base-cartfoot-fresh-s10-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-08T06:47:18+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-cartfoot-fresh-s10

**hypothesis**: Own-checkpoint continuation of the fresh-init cart-foot canary (fork b): the 2M cold-start read found HEALTHY-PARITY between ON and OFF (no cold-start inductive-bias handicap for the Cartesian foot-target decode), but too early for any slip/quality claim. This run asks whether the same +38M budget that took the base family from 2M cold start to their established PASS band also gets the fresh cart-foot arm there, and if so whether its mature slip/m beats or loses to that band -- the actual fork(b) question fork(a)'s warm-start retrofit could not answer cleanly.

**gate**: PASS-BAND if it reaches gait_valid/no-falls/slip comparable to the base family's own established PASS band (base-s0/s1/s2/s3/s4) on the same fixed-forward walk panel -- report slip/m specifically vs that band. FAIL if it cannot reach walking at all by 40M while sibling base-family seeds all could. Per the 08-21 ruling, judge on reward trend + eval together, not reward alone.

**refused_reason**: W&B already has a run named cw-walkscratch-easy0905-base-cartfoot-fresh-s10-c1 (names are append-only; pick a new one)

