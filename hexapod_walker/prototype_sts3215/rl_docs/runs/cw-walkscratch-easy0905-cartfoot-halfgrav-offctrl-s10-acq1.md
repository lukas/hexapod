# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s10-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-08T10:21:34+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s10

**hypothesis**: Own-checkpoint 40M continuation of the CANARY-PASSed joint-space (OFF) halfgrav+seed10 control: matched budget/seed sibling to cartfoot-halfgrav-s10-acq1 (already launched this window by a concurrent cycle), completing the seed10 ON/OFF pair and extending the seed7 halfgrav 2x2 acquisition result toward the 1g cell's n=3 seed cohort.

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with cartfoot-halfgrav-s10-acq1 at the SAME budget. PASS/CONTINUE per the 08-21 ruling if reward is still rising; slip/m vs the matched ON sibling is the headline comparison, not a hardening bar.

