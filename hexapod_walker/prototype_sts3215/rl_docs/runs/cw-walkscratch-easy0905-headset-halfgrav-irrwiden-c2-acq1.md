# cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c2-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T02:03:41+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c2

**hypothesis**: Plain English: the jitter-first widen+irr composite's 2nd seed (irrwiden-c2, respec off irr2-acq1) CANARY PASSed its 2M mechanism-health check (gait_valid 22/24 aggregate, 0 falls, beating the irr2-acq1 baseline of 19/24). This is the acquisition-scale (40M) confirmation of the composite's 2nd seed, mirroring the n=2 seed-confirmation discipline already applied to every other rung in this campaign (medhead, widen2, irr-timing) and giving the widen+irr composite its 2nd-seed acquisition-scale read alongside the concurrently-running widen-first widenirr-c1-acq1.

**gate**: ACQ PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with no chronic (<0.10-duty every episode) single-leg sacrifice at 40M, matching or improving this run's own 2M canary read (22/24 aggregate), 0 falls, slip/m at/near the 2.9-6/m band already established by the sibling irrwiden-c1-acq1. ACQ FAIL if walk/det or walk/sto regresses to majority failure or a new chronic single-leg sacrifice pattern emerges. ACQ CONTINUE if reward is still climbing with borderline (not hard-park) duty, per the 08-21 ruling.

