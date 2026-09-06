# cw-walkscratch-easy0905-headset-crossgrav-widenirrc3-abrupt-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T04:47:09+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widenirrc3-abrupt-c1

**hypothesis**: Plain English: the abrupt-1g crossgrav discovery canary off the widenirr-c3 halfgrav champion (CANARY PASS-INFORMATIVE, gait_valid 23/24, 0 falls, only 1 flagged episode with no chronic leg pattern) already showed six-leg walking survives an abrupt jump to full gravity on this widen+irr composite's 2nd seed, closing the widenirr-crossgrav axis at n=2 clean (unlike widen2's seed-split). This is the acquisition-scale (40M) confirmation: does that six-leg gait hold up at a full training budget at 1g on this seed, matching the medhead/widen2c1/s1acq/s3acq precedent of testing whether canary-clean crossgrav transfer survives ACQ-scale exposure (recall: healthy-source canaries have split roughly half PASS/half FAIL at ACQ scale on this campaign, so this is a genuine open question, not a rubber stamp)?

**gate**: ACQ PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with no chronic (<0.10-duty every episode) single-leg sacrifice at 40M, matching or improving the 2M canary's 23/24 read, 0 falls, slip/m at/near the 2.9 teacher band. ACQ FAIL if walk/det or walk/sto regresses to majority failure or the leg[1,4]-style chronic-park fingerprint emerges/hardens under longer 1g exposure (matching the irracq1/irr2acq1/s3acq entrenchment class already seen this campaign). ACQ CONTINUE if reward is still climbing with borderline (not hard-park) duty, per the 08-21 ruling.

**refused_reason**: acquisition runs require --evidence: name the healthy canary and a comparable full-budget learning precedent.

