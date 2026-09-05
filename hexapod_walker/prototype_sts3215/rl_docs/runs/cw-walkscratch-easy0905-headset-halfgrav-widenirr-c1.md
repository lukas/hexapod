# cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-05T22:52:45+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c1

**wandb_id**: uia75k9z

**hypothesis**: Plain English: the mirror-image test of irrwiden-c1 (same cycle): does adding IRREGULAR direction-change timing on top of an ALREADY heading-widened (8-way fullhead) champion work, i.e. does curriculum order matter? widen2-c1 is the CANARY-PASS 2M champion that curriculum-widened from medhead (5-way quarter-turn) to the full 8-way compass and measurably tightened reversal-heading tracking vs a cold jump. This arm keeps that widened heading set fixed and adds ONLY goal.walk_cmd_resample_jitter=0.5 (the same jitter mechanism already ACQ-PASSed in headset-halfgrav-irr-acq1 on a narrow heading set) -- no new reward keys, same bank-proved mechanism, opposite composition order from irrwiden-c1. Together the two arms test whether combining heading-breadth + timing-irregularity (the two rungs closest to the actual DONE-gate composite panel) composes regardless of which axis is trained first, or whether one order is measurably more robust.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M) -- do not judge mature course-tracking. PASS/INFORMATIVE if gait_valid stays majority-valid (>=4/6 det) with 0 falls, matching or beating widen2-c1's own clean numbers (21/24 gait_valid, 0 falls), and wrong_course_frac/direction tracking doesn't blow up under the added timing jitter. FAIL if gait_valid collapses (new leg sacrifice vs widen2-c1's own baseline) or falls appear.

**verdict**: CANARY PASS: widen-first composition (widen2-c1 heading-widen + irr timing-jitter, added on top) is mechanism-healthy at 2M and BEATS its own parent widen2-c1's clean canary numbers. Evidence: harness gait_valid 23/24 (walk/det 5/6 sacrificed[2,4,5], walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6) vs widen2-c1's own 21/24 (4/6,6/6,5/6,6/6), 0 falls/terminations in all 24 episodes (both runs), mean wrong_course_frac_1s only rises modestly under the added jitter (0.285->0.367, not a blowup). All det modes clear the >=4/6 majority-valid bar with room. Why: matches the gate's own PASS/INFORMATIVE criterion exactly (gait_valid stays majority-valid, 0 falls, matches-or-beats parent, course tracking doesn't blow up) -- a clean pass, not a borderline call. This is a 2M mechanism-health canary only; no claim about mature course-tracking. What's next: promote to full 40M ACQ (mirrors widen2-c1-acq1's own clean ACQ PASS this cycle) to test whether the composition benefit holds at full budget -- launched cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1-acq1 this cycle.

