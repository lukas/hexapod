# cw-walkscratch-easy0905-headset-crossgrav-medhead-widenirr-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T03:56:14+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-widenfwd-c1-acq1

**hypothesis**: Plain English: both single-axis 1g-native crossgrav extensions off the medhead champion already PASSED at full 40M acquisition (medhead-widenfwd-c1-acq1: 8-way heading breadth; medhead-irrfwd-c1-acq1: command-timing jitter) -- does composing them TOGETHER (the widenirr order: start from the mature widen champion, add irr jitter on top) survive as cleanly as either axis alone, mirroring the halfgrav-family widenirr/irrwiden composite work but built natively at 1g this time instead of via cross-gravity transfer?

**gate**: CANARY PASS if aggregate gait_valid stays majority-clean (>=20/24) with 0 falls and no NEW chronic leg sacrifice beyond what either single-axis parent already showed; FAIL if it collapses toward chronic leg-1/4 sacrifice or falls appear.

