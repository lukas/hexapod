# cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-05T22:52:45+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c1

**hypothesis**: Plain English: the mirror-image test of irrwiden-c1 (same cycle): does adding IRREGULAR direction-change timing on top of an ALREADY heading-widened (8-way fullhead) champion work, i.e. does curriculum order matter? widen2-c1 is the CANARY-PASS 2M champion that curriculum-widened from medhead (5-way quarter-turn) to the full 8-way compass and measurably tightened reversal-heading tracking vs a cold jump. This arm keeps that widened heading set fixed and adds ONLY goal.walk_cmd_resample_jitter=0.5 (the same jitter mechanism already ACQ-PASSed in headset-halfgrav-irr-acq1 on a narrow heading set) -- no new reward keys, same bank-proved mechanism, opposite composition order from irrwiden-c1. Together the two arms test whether combining heading-breadth + timing-irregularity (the two rungs closest to the actual DONE-gate composite panel) composes regardless of which axis is trained first, or whether one order is measurably more robust.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M) -- do not judge mature course-tracking. PASS/INFORMATIVE if gait_valid stays majority-valid (>=4/6 det) with 0 falls, matching or beating widen2-c1's own clean numbers (21/24 gait_valid, 0 falls), and wrong_course_frac/direction tracking doesn't blow up under the added timing jitter. FAIL if gait_valid collapses (new leg sacrifice vs widen2-c1's own baseline) or falls appear.

