# cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s7-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T06:52:55+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s7

**wandb_id**: 0mribzhl

**hypothesis**: Plain English: matched joint-space control for cartfoot-freshinit-c1-s7-acq1 -- same fresh-init recipe, seed, and 40M budget, no cart_foot keys. Own-checkpoint 40M continuation of the HEALTHY-PARITY CANARY-PASSed OFF arm, giving a same-depth same-seed slip/m and gait_valid comparator for the ON arm launched this cycle (avoids reusing the mature cont40m offctrl-s3 comparator, which reached maturity via a long continuation chain, not fresh-init).

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det). Read together with cartfoot-freshinit-c1-s7-acq1: this is the joint-space baseline, expected to reach the campaign's established 5-6/m slip band.

