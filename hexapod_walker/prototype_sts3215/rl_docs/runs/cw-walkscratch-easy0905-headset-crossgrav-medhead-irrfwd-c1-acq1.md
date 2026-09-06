# cw-walkscratch-easy0905-headset-crossgrav-medhead-irrfwd-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T03:11:04+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-irrfwd-c1

**hypothesis**: Plain English: the medhead-irrfwd-c1 2M canary just PASSed (gait_valid 22/24, 0 falls, unusually tight clean slip band) -- composing command-timing-irregularity (irr) jitter natively at 1g on top of the already-crossgrav-transferred medhead champion works at canary scale. Does the same recipe hold at full 40M acquisition budget, matching the campaign's own-checkpoint-continuation pattern already validated for every other crossgrav/irr rung?

**gate**: ACQ PASS if aggregate gait_valid stays >=17/24 with no NEW chronic (<0.10-duty every episode) single-leg sacrifice vs the 2M canary's transient legs-[2,5]-in-2/6-episodes flag; ACQ FAIL if a chronic sacrifice fingerprint emerges that wasn't present at 2M.

**refused_reason**: hexapod-mjx-train-4 already runs cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m — GPU pods host exactly one run; pick a free GPU pod.

