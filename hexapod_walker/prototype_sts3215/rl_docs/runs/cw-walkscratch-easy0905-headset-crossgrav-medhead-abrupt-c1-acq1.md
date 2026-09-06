# cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T00:40:44+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1

**hypothesis**: Plain English: the abrupt-1g crossgrav discovery canary (CANARY PASS, gait_valid 20/24, walk/det+sto 12/12 clean, 0 falls) already showed six-leg walking survives an abrupt jump to full gravity from the leg-healthy halfgrav-medhead-acq1 champion. This is the acquisition-scale (40M) confirmation: does that six-leg gait, and the mild leg-4 softening seen only under start-pose jitter, hold up (or fully resolve) with a full training budget at 1g, closing cross-gravity transfer as a real repair path for the base(1g) family instead of reward-price mechanisms (closed 8/8) or reallocating everything to halfgrav?

**gate**: ACQ PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with sac=[] (no chronic <0.10-duty single-leg sacrifice) at 40M, matching or improving the 2M canary's clean 12/12 walk/det+sto read, 0 falls, and slip/m at/near the 2.9 teacher band. ACQ FAIL if walk/det or walk/sto regresses to majority failure or the leg[1,4] chronic-park fingerprint emerges under longer 1g exposure. ACQ CONTINUE if reward is still climbing with borderline (not hard-park) duty, per the 08-21 ruling. Either a clean PASS or a clean FAIL is the first acquisition-scale causal evidence on whether cross-gravity transfer is a viable base(1g) recipe.

**refused_reason**: acquisition runs require --evidence: name the healthy canary and a comparable full-budget learning precedent.

