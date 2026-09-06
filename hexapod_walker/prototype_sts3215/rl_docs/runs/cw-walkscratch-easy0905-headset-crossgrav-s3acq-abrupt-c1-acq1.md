# cw-walkscratch-easy0905-headset-crossgrav-s3acq-abrupt-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T02:41:08+00:00

**pod**: hexapod-mjx-train-9

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s3acq-abrupt-c1

**wandb_id**: lp972djl

**hypothesis**: Plain English: does the 2nd-best 3-way halfgrav champion's crossgrav canary (headset-halfgrav-s3acq abruptly jumped to 1g, gait_valid 21/24, walk/det 6/6 clean, mild non-chronic leg-1 startjitter softening) hold at full 40M acquisition budget, matching the now-6/6 healthy-source crossgrav PASS pattern (medhead x2, widen2c1, irracq1, irr2acq1, s1acq)?

**gate**: ACQ PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with sac=[] at 40M, matching or improving the 2M canary's 6/6+6/6 clean primary-mode read, 0 falls, slip/m at/near the 2.9 teacher band; the known mild leg-1 startjitter softening may persist without failing the gate as long as it stays non-chronic (never <0.10 duty in ALL episodes). ACQ FAIL if walk/det or walk/sto regresses to majority failure or the softening hardens into a chronic single-leg-park fingerprint. ACQ CONTINUE if reward still climbing with only borderline duty, per the 08-21 ruling.

**verdict**: ACQ FAIL - MECHANISM: aggregate gait_valid 17/24 at 40M -- walk/det 6/6 clean, walk/sto 6/6 clean (both primary modes hold), but walk_startjitter/det collapses to 2/6 (sac=[1] in 4/6 episodes) and walk_startjitter/sto to 3/6 (sac=[1] in 3/6 episodes). This is a CHRONIC single-leg-park fingerprint, not transient softening: leg-1 duty across ALL 6 walk_startjitter/det episodes is 0.03/0.20/0.04/0.04/0.14/0.05 (low in 4/6, never healthy) vs the OTHER 5 legs' 0.15-0.74 range every episode; leg-1 duty across walk_startjitter/sto is 0.07/0.13/0.19/0.08/0.06/0.14 (low in 3/6). Direct regression from this run's own 2M canary, which had the SAME leg softened but milder (leg-1 duty 0.07-0.24, median ~0.15-0.19, only 3/6 flagged) -- median leg-1 duty roughly HALVED (0.15-0.19 -> 0.08) with more 1g training, i.e. the entrenchment got WORSE, not better. The exact 'leg-1 in 4/6 and 3/6 episodes' numerical fingerprint matches the ALREADY-CLOSED widen2c2b-abrupt-c1-acq1 ACQ FAIL precedent verbatim. 0 falls/terminations in all 24 episodes; reward net-rising in the back half (quarters -400.8,-433.1,-129.3,125.0) but per CURRENT_TRUTHS this reward-misalignment class (base(1g) middle-leg-pair favoritism) is already closed after 9 repair mechanisms with a STRUCTURAL fix required -- rising reward does not override a hardening chronic-park fingerprint (same read as irracq1-abrupt-c1-acq1's ACQ FAIL this cycle). This is the SECOND healthy-source (22/24 canary, not the unhealthy widen2c2b case) crossgrav champion to entrench at ACQ scale under startjitter specifically, alongside irracq1 -- confirms the risk is not confined to unhealthy sources; a clean-ish 2M canary does not guarantee 40M durability even from a genuinely six-leg-healthy source. Tally now: 4 ACQ PASS (medhead-abrupt, medhead-ramp, widen2c1, s1acq) vs 2 healthy-source ACQ FAIL (irracq1, s3acq) plus 1 unhealthy-source ACQ FAIL (widen2c2b, already explained) -- roughly half of healthy-source champions entrench under longer 1g exposure specifically in the startjitter panel. Video confirms genuine body translation even in flagged episodes (a favoritism issue, not a freeze/paddle).

