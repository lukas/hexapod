# cw-walkscratch-easy0905-cartfoot-freshinit-c1-s7-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-08T06:51:38+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-c1-s7

**hypothesis**: Own-checkpoint continuation of the fresh-init cart-foot canary (fork b, seed 7): the 2M cold-start read (this arm CANARY PASS HEALTHY-PARITY vs its matched offctrl-s7 control, also CANARY PASS) found no cold-start inductive-bias handicap for the Cartesian foot-target decode, but too early for any slip/quality claim. This run asks whether the same +38M budget that took base-s0..s4 from 2M cold start to their established PASS band also gets this fresh cart-foot ON arm there, and if so whether its MATURE slip/m beats or loses to that band -- paired with the concurrently-running seed10 fork(b) continuation (s10-c1b) for a 2-seed replicate at full budget.

**gate**: PASS-BAND if it reaches gait_valid/no-falls/slip comparable to the base family's own established PASS band (base-s0..s4) on the same fixed-forward walk panel -- report slip/m specifically vs that band. FAIL if it cannot reach walking at all by 40M while sibling base-family seeds all could. Per the 08-21 ruling, judge on reward trend + eval together, not reward alone.

