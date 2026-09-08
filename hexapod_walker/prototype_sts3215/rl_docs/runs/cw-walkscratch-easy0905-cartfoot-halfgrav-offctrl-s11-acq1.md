# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s11-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T10:24:01+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s11

**wandb_id**: i593jcsf

**hypothesis**: Matched joint-space (OFF) control for the halfgrav cart_foot seed11 40M acquisition (cw-walkscratch-easy0905-cartfoot-halfgrav-s11-acq1, ON, already launched by a concurrent cycle on train-0): does the joint-space action space learn to walk at 0.5g over a full budget at seed11, and how does its slip compare to the cart_foot sibling at the same depth? Own-checkpoint 40M continuation of the CANARY-PASSed offctrl-s11 OFF arm, completing the seed11 half of the n=3 halfgrav seed cohort (seed7 already ACQ PASS - PARITY, seed10 pair launched this cycle).

**gate**: MATCHED CONTROL: read together with cartfoot-halfgrav-s11-acq1 at the same budget. >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det); slip/m vs the ON sibling is the headline comparison.

