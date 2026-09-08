# cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s11-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-08T07:12:00+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s11

**hypothesis**: Plain English: matched control for cartfoot-freshinit-c1-s11-acq1 -- the same exact 40M own-checkpoint continuation of the joint-decode (no Cartesian keys) seed-11 arm, so the fresh-init seed cohort's ON-vs-OFF slip/gait_valid read at full budget is causal to the 3 cart keys, not a seed or training-depth artifact. Completes the n>=3 fresh-init pair set (s7 done, s10 in flight, s11 now paired).

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with cartfoot-freshinit-c1-s11-acq1 at the SAME budget. This is the matched control -- if it itself drifts/fails the acquisition bar, read the ON/OFF pair as inconclusive rather than crediting/blaming the Cartesian mechanism.

