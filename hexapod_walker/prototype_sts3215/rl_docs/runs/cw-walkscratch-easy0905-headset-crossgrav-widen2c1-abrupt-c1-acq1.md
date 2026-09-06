# cw-walkscratch-easy0905-headset-crossgrav-widen2c1-abrupt-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T01:37:38+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widen2c1-abrupt-c1

**wandb_id**: 03yp0fch

**hypothesis**: Plain English: the abrupt-1g crossgrav discovery canary off the full-8-way-heading (incl. reversals) widen2-c1 champion (CANARY PASS-INFORMATIVE, gait_valid 19/24, 0 falls, only mild leg-4 softening under start-pose jitter) already showed six-leg walking survives an abrupt jump to full gravity from a 2nd, materially different leg-healthy halfgrav champion (not just medhead). This is the acquisition-scale (40M) confirmation: does that six-leg gait hold up (or fully resolve the mild leg-4 softening) with a full training budget at 1g on this 2nd recipe, further closing cross-gravity transfer as a general base(1g) repair path rather than a medhead-specific fluke?

**gate**: ACQ PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with no chronic (<0.10-duty every episode) single-leg sacrifice at 40M, matching or improving the 2M canary's 19/24 read, 0 falls, slip/m at/near the 2.9 teacher band. ACQ FAIL if walk/det or walk/sto regresses to majority failure or the leg[1,4] chronic-park fingerprint emerges/hardens under longer 1g exposure. ACQ CONTINUE if reward is still climbing with borderline (not hard-park) duty, per the 08-21 ruling.

