# cw-walkscratch-easy0905-headset-halfgrav-irr2-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T12:08:56+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irr2-acq1

**wandb_id**: pf38aqrx

**hypothesis**: Plain English: does the halfgrav (0.5g) irr-timing composite's SECOND seed (headset-halfgrav-irr, canary c2, testing seed generalization of the same irr-timing mechanism as the irr-acq1-cont40m sibling) stay clean over a SECOND 40M block (80M cumulative, true continuation via --init-from-source)? Its own 40M ACQ read is ACQ PASS with 19/24 gait_valid (4/6 det, 6/6 sto, 4/6 startjitter/det, 5/6 startjitter/sto, 0 falls, scattered leg1/4 flags) -- queued (not launched immediately -- this cycle's 80M-step cap was already spent on the cleaner crossgrav-medhead irrwiden/widenirr pair).

**gate**: PASS/HOLDS if gait_valid stays majority (>=18/24) with 0 falls and no NEW chronic single-leg pattern. FAIL/entrenches if gait_valid drops materially, a fall appears, or a leg consolidates into a chronic sacrifice across most episodes. Read alongside the irr-acq1-cont40m (c1 seed) sibling for a 2-seed endurance generalization read.

