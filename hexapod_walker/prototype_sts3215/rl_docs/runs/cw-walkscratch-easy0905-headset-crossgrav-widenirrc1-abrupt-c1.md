# cw-walkscratch-easy0905-headset-crossgrav-widenirrc1-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T01:42:19+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-irrwidenc1-abrupt-c1

**hypothesis**: Plain English: 5 champions have now been tested for cross-gravity transfer (medhead abrupt+ramp PASS, widen2c1 abrupt PASS this cycle, irracq1-abrupt PASS, widenirrc1(jitter-first)-abrupt running) but the WIDEN-FIRST widen+irr composite champion (headset-halfgrav-widenirr-c1-acq1, ACQ PASS this campaign, gait_valid 23/24, BEATS both plain widen2-c1-acq1 and the jitter-first irrwiden-c1-acq1 sibling) has never itself been tested -- it is the cleanest-scoring halfgrav champion built so far and the composition order (widen-then-jitter vs jitter-then-widen) is the one remaining un-varied axis. Does the abrupt 1g transfer repair hold on this specific, best-scoring composite recipe too?

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10-duty every episode) single-leg sacrifice -- extends cross-gravity-transfer to the best-scoring composite champion, a 6th confirming data point. FAIL/INFORMATIVE-NEGATIVE if it collapses to the leg[1,4] chronic-sacrifice fingerprint -- would mean even the highest-quality halfgrav source doesn't guarantee transfer, pointing at a property of gravity/1g dynamics rather than source-champion quality. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

**refused_reason**: W&B already has a run named cw-walkscratch-easy0905-headset-crossgrav-widenirrc1-abrupt-c1 (names are append-only; pick a new one)

