# cw-walkscratch-easy0905-base-cartfoot-freshoffctrl-s10-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-08T07:15:03+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-cartfoot-freshoffctrl-s10

**hypothesis**: Plain English: matched joint-space (no Cartesian-foot-target) control for base-cartfoot-fresh-s10-c1b -- same own-checkpoint +38M continuation of the fresh-init OFF canary, seed 10, so the fork(b) n=3 fresh-init seed cohort (s7 pair running, s11 pair running) gets its third seed's matched control at the same 40M budget instead of only an ON arm running alone.

**gate**: PASS-BAND if it reaches gait_valid/no-falls/slip comparable to the established base-family PASS band (base-s0..s4) on the fixed-forward walk panel. Read paired against base-cartfoot-fresh-s10-c1b at the same cumulative depth: this completes the seed-10 half of the n>=3 fresh-init ON/OFF cohort. FAIL if it cannot reach walking at all by 40M despite sibling base-family seeds all reaching it. Per the 08-21 ruling, judge on reward trend + eval together.

**refused_reason**: acquisition runs require --evidence: name the healthy canary and a comparable full-budget learning precedent.

