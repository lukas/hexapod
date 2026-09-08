# cw-walkscratch-easy0905-cartfoot-freshinit-c1-s11-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T07:07:33+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-c1-s11

**wandb_id**: udt4qxx3

**hypothesis**: Plain English: completes the fork (b) n>=3 fresh-init seed cohort (s7 acq1 pair already running, s10 own-continuation already running) by giving seed 11 its matched 40M acquisition pair too -- does the Cartesian-foot-space fresh-init lineage actually learn to walk over a full budget at THIS seed, and how much slippier is it than its own joint-space sibling (offctrl-s11-acq1) at the same fresh-init depth? Own-checkpoint 40M continuation of the HEALTHY-PARITY CANARY-PASSed cart_foot ON arm (seed 11), matched against offctrl-s11-acq1 launched the same cycle. Prediction from the s7 pair and the c1-s3/offctrl-s3 precedent: ON reaches gait_valid parity with OFF but at several-x the slip/m.

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with offctrl-s11-acq1 at the SAME budget. PASS/CONTINUE per the 08-21 ruling if reward is still rising; slip/m vs the matched OFF sibling is the headline comparison, not a hardening bar.

