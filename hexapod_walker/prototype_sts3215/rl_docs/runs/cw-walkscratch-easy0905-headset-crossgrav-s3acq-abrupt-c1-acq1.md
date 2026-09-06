# cw-walkscratch-easy0905-headset-crossgrav-s3acq-abrupt-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T02:41:08+00:00

**pod**: hexapod-mjx-train-9

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s3acq-abrupt-c1

**wandb_id**: lp972djl

**hypothesis**: Plain English: does the 2nd-best 3-way halfgrav champion's crossgrav canary (headset-halfgrav-s3acq abruptly jumped to 1g, gait_valid 21/24, walk/det 6/6 clean, mild non-chronic leg-1 startjitter softening) hold at full 40M acquisition budget, matching the now-6/6 healthy-source crossgrav PASS pattern (medhead x2, widen2c1, irracq1, irr2acq1, s1acq)?

**gate**: ACQ PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with sac=[] at 40M, matching or improving the 2M canary's 6/6+6/6 clean primary-mode read, 0 falls, slip/m at/near the 2.9 teacher band; the known mild leg-1 startjitter softening may persist without failing the gate as long as it stays non-chronic (never <0.10 duty in ALL episodes). ACQ FAIL if walk/det or walk/sto regresses to majority failure or the softening hardens into a chronic single-leg-park fingerprint. ACQ CONTINUE if reward still climbing with only borderline duty, per the 08-21 ruling.

