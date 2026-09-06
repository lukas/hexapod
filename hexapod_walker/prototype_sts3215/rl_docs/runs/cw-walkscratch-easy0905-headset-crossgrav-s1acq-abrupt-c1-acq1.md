# cw-walkscratch-easy0905-headset-crossgrav-s1acq-abrupt-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T02:38:22+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s1acq-abrupt-c1

**hypothesis**: Plain English: does the cleanest crossgrav-transfer canary yet (headset-halfgrav-s1acq abruptly jumped to 1g, gait_valid PERFECT 24/24, sac=[] every episode) hold at full 40M acquisition budget the same way every other healthy-source crossgrav canary has (5/5 PASS so far: medhead x2, widen2c1, irracq1, irr2acq1)? This is the campaign's best-ever source champion, so a clean ACQ PASS would be the strongest single confirmation of cross-gravity-transfer as a general base(1g) repair.

**gate**: ACQ PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with sac=[] at 40M, matching or improving the 2M canary's PERFECT 24/24 clean read, 0 falls, slip/m at/near the 2.9 teacher band. ACQ FAIL if walk/det or walk/sto regresses to majority failure or a chronic single-leg-park fingerprint emerges under longer 1g exposure. ACQ CONTINUE if reward still climbing with only borderline (not hard-park) duty, per the 08-21 ruling.

