# cw-walkscratch-easy0905-cartfoot-freshinit-c1-s11-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS - PARITY

**created**: 2026-09-08T07:07:33+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-c1-s11

**wandb_id**: udt4qxx3

**hypothesis**: Plain English: completes the fork (b) n>=3 fresh-init seed cohort (s7 acq1 pair already running, s10 own-continuation already running) by giving seed 11 its matched 40M acquisition pair too -- does the Cartesian-foot-space fresh-init lineage actually learn to walk over a full budget at THIS seed, and how much slippier is it than its own joint-space sibling (offctrl-s11-acq1) at the same fresh-init depth? Own-checkpoint 40M continuation of the HEALTHY-PARITY CANARY-PASSed cart_foot ON arm (seed 11), matched against offctrl-s11-acq1 launched the same cycle. Prediction from the s7 pair and the c1-s3/offctrl-s3 precedent: ON reaches gait_valid parity with OFF but at several-x the slip/m.

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with offctrl-s11-acq1 at the SAME budget. PASS/CONTINUE per the 08-21 ruling if reward is still rising; slip/m vs the matched OFF sibling is the headline comparison, not a hardening bar.

**verdict**: Fresh-init cart_foot ON, seed11, 40M: 0/24 falls, gait_valid 6/6 det, 6/6 sto, 5/6 startjitter/det, 6/6 startjitter/sto (only leg4 sac in 1 ep). Mean slip/m by group ON-vs-matched-OFF: 2.89/3.02 (0.96x), 3.32/3.53 (0.94x), 2.81/2.91 (0.97x), 3.34/3.34 (1.00x) -- ON at-or-under OFF in ALL 4 groups, matching seed7's PARITY shape almost exactly (0.94-0.99x there). speed_mean above the 0.03 m/s floor in all groups. Reward rises every quarter (-462.7->1680.2), no plateau. Frame strip walk_det_0.png shows level body, real alternating leg swing, no drag/flag-leg. This is the 2nd independent full ratio-matched replicate (after seed7) of fork(b)'s fresh-init PARITY finding -- promotes it from n=1 to a track-level result: FROM-SCRATCH Cartesian foot-target training does not show fork(a)'s warm-started-retrofit slip inflation.

