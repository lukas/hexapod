# cw-walkscratch-easy0905-cartfoot-freshinit-c1-s7-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-08T06:49:23+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-c1-s7

**wandb_id**: qnrtrce1

**hypothesis**: Plain English: does the Cartesian-foot-space fresh-init lineage actually learn to walk over a full budget, and if so how much slippier is it than its own joint-space sibling at the SAME fresh-init depth (not warm-started onto a mature multi-axis lineage the way the c1-s3/offctrl-s3 comparison was)? Own-checkpoint 40M continuation of the HEALTHY-PARITY CANARY-PASSed cart_foot ON arm (seed 7), matched against the sibling offctrl-s7-acq1 launched the same cycle. Prediction from the c1-s3 precedent: ON reaches gait_valid parity with OFF but at 3-10x the slip/m; alternative: fresh-init (vs warm-started) closes some or all of that gap.

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with offctrl-s7-acq1 at the SAME budget. PASS/CONTINUE per the 08-21 ruling if reward is still rising; slip/m vs the matched OFF sibling is the headline comparison, not a hardening bar.

