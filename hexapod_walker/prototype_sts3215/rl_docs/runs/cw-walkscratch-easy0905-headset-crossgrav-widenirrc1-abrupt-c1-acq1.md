# cw-walkscratch-easy0905-headset-crossgrav-widenirrc1-abrupt-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T02:01:34+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widenirrc1-abrupt-c1

**hypothesis**: Plain English: the abrupt-1g crossgrav discovery canary off the widen-first widen2+irr composite champion (widenirr-c1-acq1: full 8-way heading incl. reversals PLUS command-timing jitter) already CANARY PASSed (walk/det 6/6 gait_valid, sac=[] every episode, 0 falls) — this is the acquisition-scale (40M) confirmation of whether that clean six-leg gait holds under a full training budget at 1g, the 4th generality-check champion at full budget after medhead, widen2c1, and irracq1.

**gate**: ACQ PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with no chronic (<0.10-duty every episode) single-leg sacrifice at 40M, matching or improving the 2M canary's clean 6/6 walk/det+walk/sto read, 0 falls, slip/m at/near the 2.9 teacher band (or the 3.4-5.8 band already established by the other crossgrav siblings). ACQ FAIL if walk/det or walk/sto regresses to majority failure or the leg[1,4] chronic-park fingerprint emerges/hardens under longer 1g exposure. ACQ CONTINUE if reward is still climbing with borderline (not hard-park) duty, per the 08-21 ruling.

