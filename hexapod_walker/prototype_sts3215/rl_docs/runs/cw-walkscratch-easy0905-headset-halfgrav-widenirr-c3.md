# cw-walkscratch-easy0905-headset-halfgrav-widenirr-c3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T02:20:21+00:00

**pod**: hexapod-mjx-train-11

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-widenirr-c1

**wandb_id**: mhn5rvg4

**hypothesis**: Plain English: widenirr-c1 (irr-timing-jitter added on top of the healthy widen2-c1 champion, widen-first order) CANARY PASSed cleanly (23/24), but the ONLY other widen-first composite arm tried, widenirr-c2b (jitter on top of the weak widen2-c2b seed), CANARY FAILed with a NEW leg-2 sacrifice pattern -- that verdict explicitly named 'a 3rd seed of the widen2 rung (not a jitter retrofit onto seed 2)' as the right tie-breaker, not yet launched because widen2-c3 (the 3rd, cleanly-PASSing widen2 seed) only just finished its own 40M ACQ PASS this cycle. This arm applies the SAME bank-proved jitter mechanism (goal.walk_cmd_resample_jitter=0.5) on top of widen2-c3's 2M checkpoint (clean-parent widen2 seed 3, matching widen2-c1's own health rather than widen2-c2b's) to test whether the widen-first composite edge is general across healthy widen2 seeds (matching widenirr-c1's clean read) or was itself specific to the widen2-c1 checkpoint.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M) -- do not judge mature course-tracking. PASS/INFORMATIVE if gait_valid stays majority-valid (>=4/6 det) with 0 falls, matching or beating widen2-c3's own clean 2M numbers (20/24 gait_valid, 0 falls) with no NEW leg sacrificed vs widen2-c3's own baseline pattern (legs 0/3/4 only, transient). FAIL if gait_valid collapses or a NEW leg (not 0/3/4) becomes chronically sacrificed, mirroring the widenirr-c2b FAIL trigger.

**verdict**: CANARY PASS. 3rd tie-breaking widenirr seed (native 0.5g, not a crossgrav test) matches/beats sibling widenirr-c1's own clean 2M canary numbers (20/24) and the gate's explicit PASS bar: gait_valid 23/24 (walk/det 5/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6), 0 falls/terminations in all 24 episodes. The lone flagged episode (walk/det/3, sac=[2,4,5]) is a SINGLE transient episode, not a chronic same-leg pattern across many episodes (all other 23 episodes show balanced duty across all six legs, 0.05-0.58) -- does not match the widenirr-c2b FAIL trigger (which required a NEW chronically-sacrificed leg). Checked the initially-alarming monotonic reward decline (-84.5->-520.6 across the 2M run) against BOTH siblings before treating it as signal: widenirr-c1 (PASS) shows the identical decline shape (-98.5->-568.4) and widenirr-c2b (FAIL) also shows it (-120.6->-548.9) -- this composite's reward config (walk_freeprog shortfall pricing under 8-way-heading+jitter resampling) is inherently negative/declining for ALL seeds regardless of outcome, so it is NOT diagnostic here; the real differentiator is the eval behavioral metrics, which read clean. Real caveat, consistent with the c2-acq1 course-tracking precedent already logged in STATUS: several stochastic/heading episodes show poor course obedience (wrong_direction_frac up to 0.54, course_err_mean up to 85deg) and correspondingly inflated slip/m (up to 201[unit] in the worst episodes) when the robot walks in the wrong direction relative to a freshly-resampled command -- a course-tracking-quality gap, not a gait-validity failure; flagged for follow-up if this seed advances to acquisition scale. This is the widenirr composite's tie-breaking 3rd seed after c1 PASS / c2b FAIL; result: 2/3 seeds clean at discovery scale.

