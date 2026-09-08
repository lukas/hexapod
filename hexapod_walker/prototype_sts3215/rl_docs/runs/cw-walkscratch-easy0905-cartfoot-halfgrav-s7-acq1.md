# cw-walkscratch-easy0905-cartfoot-halfgrav-s7-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T09:02:37+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-s7

**wandb_id**: traypy7y

**hypothesis**: Own-checkpoint 40M continuation of the CANARY-PASSed cart_foot (ON) halfgrav+seed7 arm: does the Cartesian foot-target action decode learn real six-leg walking at 0.5g over a full budget, and how does its slip/m compare to the matched joint-space sibling offctrl-s7-acq1 at the SAME fresh-init-then-continued depth? Mirrors the already-proven 1g fork(b) recipe (cartfoot-freshinit-c1-s7-acq1) one gravity cell over.

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with offctrl-s7-acq1 at the SAME budget. PASS/CONTINUE per the 08-21 ruling if reward is still rising; slip/m vs the matched OFF sibling is the headline comparison, not a hardening bar.

