# cw-walkscratch-easy0905-cartfoot-halfgrav-s11-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T10:21:05+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-s11

**wandb_id**: 6ldf24zk

**hypothesis**: Own-checkpoint 40M continuation of the CANARY-PASSed cart_foot (ON) halfgrav+seed11 arm: does the Cartesian foot-target action decode learn real six-leg walking at 0.5g over a full budget at a 3rd seed, completing the n=3 (seed7/10/11) halfgrav acquisition cohort the 1g cell already has; slip/m vs the matched joint-space sibling offctrl-s11-acq1 at the same depth is the headline comparison.

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with offctrl-s11-acq1 at the SAME budget. PASS/CONTINUE per the 08-21 ruling if reward is still rising; slip/m vs the matched OFF sibling is the headline comparison, not a hardening bar.

