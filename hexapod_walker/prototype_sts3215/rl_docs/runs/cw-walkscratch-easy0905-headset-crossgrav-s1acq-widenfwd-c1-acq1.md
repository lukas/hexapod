# cw-walkscratch-easy0905-headset-crossgrav-s1acq-widenfwd-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T05:13:33+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s1acq-widenfwd-c1

**hypothesis**: Plain English: s1acq-widenfwd-c1 (forward-composing the full 8-way heading set onto the campaign's cleanest crossgrav champion) just CANARY PASSed at 2M (gait_valid 22/24, no chronic leg sacrifice, but heavy slip/negative progress on the hard quarter-turn/reversal headings -- the same distance-graded course-tracking gap already documented on the medhead/widen2c1 siblings). This is the acquisition-scale (40M) confirmation matching the medhead-widenfwd-c1-acq1 and widen2c1-irrfwd-c1-acq1 precedent (both held clean/improved at 40M): does the campaign's single cleanest source hold this composition at full budget, or does it join the ~half of healthy-source champions that entrench toward chronic leg[1,4] sacrifice under the startjitter panel at ACQ scale (irracq1/irr2acq1/s3acq)?

**gate**: ACQ PASS if aggregate gait_valid stays majority-or-better (>=18/24) with no chronic (same leg flagged in most/all episodes of one mode) single-leg sacrifice, matching or improving the 2M canary's 22/24, and 0 falls. ACQ FAIL if walk_startjitter/det or walk_startjitter/sto collapses to the leg[1,4]-style chronic-park fingerprint or any new chronic single-leg pattern emerges. ACQ CONTINUE if reward is still climbing with borderline (non-chronic) duty softening, per the 08-21 ruling.

