# cw-walkscratch-easy0905-cartfoot-halfgrav-s10-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T10:19:03+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-s10

**wandb_id**: chxamgkj

**hypothesis**: Own-checkpoint 40M continuation of the CANARY-PASSed cart_foot (ON) halfgrav+seed10 arm: does the Cartesian foot-target action decode learn real six-leg walking at 0.5g over a full budget at a 2nd seed, and how does its slip/m compare to the matched joint-space sibling offctrl-s10-acq1 at the same depth? Extends the seed7 halfgrav 2x2 acquisition result (already ACQ PASS - PARITY) to build the n=3 seed cohort the 1g cell already has.

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with offctrl-s10-acq1 at the SAME budget. PASS/CONTINUE per the 08-21 ruling if reward is still rising; slip/m vs the matched OFF sibling is the headline comparison, not a hardening bar.

