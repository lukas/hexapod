# cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-05T23:58:33+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c1

**wandb_id**: f3h84106

**hypothesis**: Plain English: the widen-from-medhead heading-widen recipe (5-way -> full 8-way compass, added on top of the clean medhead_acq1 champion) already split 1 PASS / 1 FAIL at full 40M acquisition scale between its first two seeds (widen2-c1 ACQ PASS 21/24; widen2-c2b ACQ FAIL 14/24, but that seed's OWN medhead2_acq1 parent was itself only ACQ CONTINUE, not a clean PASS -- so the split may be parent-quality-driven, not seed-noise). This is the tie-breaking 3rd seed BOTH concurrent cycles' own STATUS notes flagged as the natural next step: a fresh seed off the SAME clean medhead_acq1 parent widen2-c1 used (not off the weaker medhead2_acq1 lineage), so a canary PASS/FAIL here cleanly separates 'parent quality determines outcome' (this new seed should PASS, matching its clean-parent sibling widen2-c1) from 'seed noise alone' (a coinflip regardless of parent).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY PASS/INFORMATIVE if gait_valid stays majority-valid (>=4/6 det) with 0 falls, matching or beating widen2-c1's own clean 2M canary numbers (21/24, 0 falls) -- MECHANISM-HEALTH ONLY, do not judge mature course-tracking at 2M. CANARY FAIL - MECHANISM if gait_valid collapses into minority or falls appear (would argue for seed-noise over parent-quality).

**verdict**: CANARY PASS: 3rd tie-breaking seed off the SAME clean medhead_acq1 parent widen2-c1 used. Harness gait_valid 20/24 (walk/det 5/6, walk/sto 6/6, walk_startjitter/det 5/6, walk_startjitter/sto 4/6), 0 falls in all 24 episodes, majority-valid on every mode -- matches/close to widen2-c1's own clean 21/24 2M canary per the gate's own PASS criterion (mechanism-health only, not judging mature course-tracking at 2M). Sacrificed-leg flags are scattered (pair [0,3] once, leg4 twice, leg3 twice), not chronic single-leg entrenchment; video (walk_det_0, walk_det_4) shows genuine six-leg cycling contact/swing in both clean and flagged episodes. Confirms the campaign's own parent-quality-vs-seed-noise question: built off the SAME healthy medhead_acq1 parent as widen2-c1 (PASS), this seed also PASSES, while widen2-c2b (built off the weaker medhead2_acq1 parent) FAILED -- supports 'parent quality determines outcome' over pure seed-noise. Slip is noisy in stochastic-mode outlier episodes (up to 128/m) but that's expected sto-mode variance at a 2M canary, not a gate criterion here. Next: promote to a 40M ACQ continuation matching the widen2-c1-acq1/irrwiden-c1-acq1 template.

