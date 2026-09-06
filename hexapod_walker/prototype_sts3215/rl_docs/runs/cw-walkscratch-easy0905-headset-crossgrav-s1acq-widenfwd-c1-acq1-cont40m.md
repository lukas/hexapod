# cw-walkscratch-easy0905-headset-crossgrav-s1acq-widenfwd-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T08:11:41+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s1acq-widenfwd-c1-acq1

**hypothesis**: Plain English: does the campaign's cleanest source (s1acq, native 0.5g gait_valid 24/24) still hold its widenfwd (8-way heading) composition after a SECOND 40M helping (80M cumulative), matching the endurance-margin rule already confirmed on medhead/s1acq-abrupt/s3acq-abrupt (cleanliness AT the first 40M read, not total budget, predicts whether more training helps or hurts)? s1acq-widenfwd-c1-acq1's own first 40M ACQ read was a clean 21/24 (0 falls, only a lateral non-worsening leg-shift vs its 22/24 2M canary) -- exactly the 'already clean at 40M' profile the rule predicts should HOLD, not entrench, at 80M.

**gate**: PASS/HOLDS if aggregate gait_valid stays majority (>=18/24, ideally close to its own 21/24 40M read) at 80M cumulative, no NEW chronic single-leg sacrifice, 0 falls. FAIL/WORSENS if it drops further (a new or spreading chronic leg pattern, gait_valid materially below 21/24) -- would be the first clean-at-40M source to worsen with more budget, overturning the endurance-margin rule.

