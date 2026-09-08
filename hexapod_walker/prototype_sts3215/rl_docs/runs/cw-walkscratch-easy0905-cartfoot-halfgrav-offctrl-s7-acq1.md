# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s7-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T09:04:06+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s7

**wandb_id**: 1myxq3am

**hypothesis**: Plain English: matched joint-space control for the halfgrav cart_foot 40M acquisition (cw-walkscratch-easy0905-cartfoot-halfgrav-s7-acq1, ON, already running): does the joint-space action space learn to walk at 0.5g over a full budget, and how does its slip compare to the cart_foot sibling at the SAME fresh-init depth? Own-checkpoint 40M continuation of the CANARY-PASSed offctrl-s7 OFF arm. Mirrors the already-answered 1g fork(b) pair (cartfoot-freshinit-offctrl-s7-acq1) on the other validated gravity cell of the base/halfgrav x joint/cartfoot 2x2 matrix.

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with cartfoot-halfgrav-s7-acq1 (ON) at the SAME budget. PASS/CONTINUE per the 08-21 ruling if reward is still rising; slip/m vs the matched ON sibling is the headline comparison, not a hardening bar.

