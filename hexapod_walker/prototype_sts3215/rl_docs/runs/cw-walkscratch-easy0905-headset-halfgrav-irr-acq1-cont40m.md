# cw-walkscratch-easy0905-headset-halfgrav-irr-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T12:12:23+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irr-acq1

**wandb_id**: nildfnf2

**hypothesis**: Plain English: does the halfgrav (0.5g) irregular-direction-change-timing composite (headset-halfgrav-irr, seed/canary c1) stay clean over a SECOND 40M block (80M cumulative, true continuation via --init-from-source)? Its own 40M ACQ read is ACQ PASS with 20/24 gait_valid (4/6 det, 6/6 sto, 4/6 startjitter/det, 6/6 startjitter/sto, 0 falls, scattered non-chronic leg4 flags) -- moderately clean, worth the endurance check per the campaign's standard cont40m refill pattern (queued, not launched immediately -- this cycle's 80M-step cap was already spent on the cleaner crossgrav-medhead irrwiden/widenirr pair).

**gate**: PASS/HOLDS if gait_valid stays majority (>=18/24) with 0 falls and no NEW chronic single-leg pattern (the parent's leg4 flags were scattered/non-chronic across det modes only, not sto). FAIL/entrenches if gait_valid drops materially, a fall appears, or leg4 (or another leg) consolidates into a chronic sacrifice across most episodes.

