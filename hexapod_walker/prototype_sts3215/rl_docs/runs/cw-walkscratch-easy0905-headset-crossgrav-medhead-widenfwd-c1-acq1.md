# cw-walkscratch-easy0905-headset-crossgrav-medhead-widenfwd-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T03:05:46+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-widenfwd-c1

**hypothesis**: Plain English: the medhead-widenfwd-c1 2M canary just PASSed (gait_valid 23/24, 0 falls) -- composing the full widen2 8-way heading set natively at 1g on top of the already-crossgrav-transferred medhead champion works at canary scale. Does the same recipe hold at full 40M acquisition budget, matching the campaign's own-checkpoint-continuation pattern already validated for every other crossgrav/widen2 rung?

**gate**: ACQ PASS if aggregate gait_valid stays >=18/24 with no NEW chronic (<0.10-duty every episode) single-leg sacrifice vs the 2M canary's transient ep4-only flag; ACQ FAIL if a chronic sacrifice fingerprint emerges that wasn't present at 2M.

**refused_reason**: acquisition runs require --evidence: name the healthy canary and a comparable full-budget learning precedent.

