# cw-walkscratch-easy0905-cartfoot-halfgrav-c1-s7-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-08T09:03:07+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-s7

**hypothesis**: Plain English: does the Cartesian-foot-target action space actually learn to walk at 0.5g over a full budget the way it already does at 1g, and how does its slip compare to the matched joint-space sibling at the SAME fresh-init depth? Own-checkpoint 40M continuation of the CANARY-PASSed cart_foot ON arm at half gravity (seed 7), matched against offctrl-s7-acq1 launched the same cycle. Mirrors the already-answered 1g fork(b) question (cartfoot-freshinit-c1-s7-acq1) on the other validated gravity cell of the base/halfgrav x joint/cartfoot 2x2 matrix.

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with cartfoot-halfgrav-offctrl-s7-acq1 at the SAME budget. PASS/CONTINUE per the 08-21 ruling if reward is still rising; slip/m vs the matched OFF sibling is the headline comparison, not a hardening bar.

**refused_reason**: hexapod-mjx-train-2 already runs cw-walkscratch-easy0905-cartfoot-halfgrav-s7-acq1 — GPU pods host exactly one run; pick a free GPU pod.

