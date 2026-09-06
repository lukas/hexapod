# cw-walkscratch-easy0905-headset-crossgrav-widen2c1-irrfwd-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T04:49:30+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widen2c1-irrfwd-c1

**hypothesis**: Plain English: forward-composing the irr-timing jitter axis onto the widen2c1 crossgrav champion (already transferred to full 1g) CANARY PASSed at 2M (gait_valid 21/24, no chronic leg pattern, but 1 genuine fall + slower/noisier than the medhead-based siblings). This is the acquisition-scale (40M) confirmation matching the medhead-{widenfwd,irrfwd}-c1-acq1 precedent (both held clean at 40M): does this harder/slower 2nd base champion's composed gait hold, entrench, or resolve its single fall/noise under a full training budget?

**gate**: ACQ PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with no chronic (<0.10-duty every episode) single-leg sacrifice at 40M, matching or improving the 2M canary's 21/24 read, and no MORE than the canary's 1 fall (ideally 0). ACQ FAIL if walk/det or walk/sto regresses to majority failure, the leg[1,4]-style chronic-park fingerprint emerges/hardens, or falls increase under longer 1g exposure. ACQ CONTINUE if reward is still climbing with borderline (not hard-park) duty, per the 08-21 ruling.

**refused_reason**: acquisition runs require --evidence: name the healthy canary and a comparable full-budget learning precedent.

