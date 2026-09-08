# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s10-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-08T10:23:06+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s10

**hypothesis**: Matched joint-space (OFF) control for the halfgrav cart_foot seed10 40M acquisition above: does the joint-space action space learn to walk at 0.5g over a full budget at seed10, and how does its slip compare to the cart_foot sibling at the same depth? Own-checkpoint 40M continuation of the CANARY-PASSed offctrl-s10 OFF arm, extending the seed7 halfgrav pair to build the n=3 seed cohort.

**gate**: MATCHED CONTROL: read together with cartfoot-halfgrav-s10-acq1 at the same budget. >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det); slip/m vs the ON sibling is the headline comparison.

**refused_reason**: hexapod-mjx-train-1 already runs cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s10-acq1 — GPU pods host exactly one run; pick a free GPU pod.

