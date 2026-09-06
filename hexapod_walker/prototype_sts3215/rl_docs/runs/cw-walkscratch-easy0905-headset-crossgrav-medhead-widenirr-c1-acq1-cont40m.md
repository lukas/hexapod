# cw-walkscratch-easy0905-headset-crossgrav-medhead-widenirr-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T12:04:07+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-widenirr-c1-acq1

**wandb_id**: ooz1h2dq

**hypothesis**: Plain English: does the widen-then-irr composite (8-way heading widen composed before irr-timing jitter, on the medhead crossgrav source -- the mirror composition order of the irrwiden-c1-acq1-cont40m sibling launched the same cycle) stay clean over a SECOND 40M block (80M cumulative, true continuation via --init-from-source)? Its own 40M ACQ read is already clean (22/24 gait_valid: 5/6 det, 5/6 sto, 6/6 startjitter/det, 6/6 startjitter/sto, 0 falls) -- per the campaign's cleanliness-margin-predicts-endurance rule this is a strong cont40m candidate, and the matched pair tests whether composition ORDER (widen-then-irr vs irr-then-widen) affects endurance.

**gate**: PASS/HOLDS if gait_valid stays majority (>=18/24, ideally close to its own 22/24) with 0 falls and no NEW chronic single-leg pattern emerges. FAIL/entrenches if gait_valid drops materially, a fall appears, or a chronic single-leg sacrifice consolidates. Read alongside the irrwiden-c1-acq1-cont40m sibling to see whether either composition order is more cont40m-durable than the other.

