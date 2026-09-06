# cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c3-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-06T01:01:58+00:00

**pod**: hexapod-mjx-train-5

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c3

**hypothesis**: Plain English: widen2-c3's 2M canary just PASSed (20/24 gait_valid, 0 falls, matches widen2-c1's own clean canary numbers), confirming this 3rd tie-breaking seed off the SAME clean medhead_acq1 parent as widen2-c1 (ACQ PASS) behaves like a healthy seed rather than the weak medhead2_acq1-parented widen2-c2b (ACQ FAIL). This continuation tests whether that health holds at the full 40M acquisition budget, matching the widen2-c1-acq1/irrwiden-c1-acq1 template -- does the widen2 recipe now read 2 PASS / 1 FAIL (parent-quality-driven, closeable) or does a 3rd seed regress at acq scale too (would reopen the seed-noise explanation)?

**gate**: ACQ PASS if gait_valid stays majority (>=18/24) with 0 falls and no leg chronically sacrificed (flagged in >=1/3 of episodes matching the widen2-c2b-acq1 entrenchment fingerprint); slip/m should be flat-or-better vs this run's own 2M canary read (walk/det med 2.77, overall spread 2.3-11.5). ACQ FAIL if gait_valid drops into minority or a leg chronically parks. ACQ CONTINUE if reward still climbing with gait valid but course-tracking still ambiguous at 40M.

**refused_reason**: acquisition runs require --evidence: name the healthy canary and a comparable full-budget learning precedent.

