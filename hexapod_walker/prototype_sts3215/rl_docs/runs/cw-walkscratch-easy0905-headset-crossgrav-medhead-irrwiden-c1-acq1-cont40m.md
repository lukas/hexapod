# cw-walkscratch-easy0905-headset-crossgrav-medhead-irrwiden-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T11:59:59+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-irrwiden-c1-acq1

**hypothesis**: Plain English: does the irr-then-widen composite (irr-timing jitter composed before the 8-way heading widen, on the medhead crossgrav source) stay clean over a SECOND 40M block (80M cumulative, true continuation via --init-from-source), the same endurance question already answered for every per-axis DR arm and several other composition-line sources? Its own 40M ACQ read is already clean (22/24 gait_valid: 5/6 det, 5/6 sto, 6/6 startjitter/det, 6/6 startjitter/sto, 0 falls) -- per the campaign's cleanliness-margin-predicts-endurance rule this is a strong cont40m candidate, and it forms a matched composition-order pair with the sibling widenirr-c1-acq1-cont40m launched the same cycle.

**gate**: PASS/HOLDS if gait_valid stays majority (>=18/24, ideally close to its own 22/24) with 0 falls and no NEW chronic single-leg pattern emerges (the parent's scattered det/sto flags were non-chronic, no leg repeating across most episodes). FAIL/entrenches if gait_valid drops materially, a fall appears, or a chronic single-leg sacrifice consolidates -- would be the first composition-line source to fail cont40m endurance despite a clean 40M ACQ read.

