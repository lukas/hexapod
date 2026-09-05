# cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_PASS

**created**: 2026-09-05T20:26:33+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-medhead-acq1

**wandb_id**: 13ft549b

**hypothesis**: Plain English: does widening the heading set toward the full 8-way compass (adding the two reversal directions +-135deg/180deg on top of the already-PASSING 5-way quarter-turn set) work better if we start from a champion that ALREADY handles quarter turns, instead of jumping there straight from the narrow 3-way (0,+-45) champion? The prior direct jump (headset-halfgrav-fullhead-c1, from the 3-way champion) kept a real stable six-leg gait (gait_valid 22-24/24, 0 falls) but FAILED course-tracking specifically at the wide/reversal headings (direction_err 28-161deg episode-to-episode, degrading with distance from the trained set). This arm warm-starts from headset-halfgrav-medhead-acq1 (the 40M ACQ-PASS champion that already tracks 0/+-45/+-90 cleanly, gait_valid 22/24, slip near the 2.9 band) and adds ONLY the two untrained reversal headings (+-135, 180) to the command set -- same k_walk_freeprog mechanism, no new reward keys, bank-proved (EASY_HEADING_WIDE, 5/5 green). If direction_err/course_err at the new reversal headings comes in meaningfully tighter than fullhead-c1's own per-episode spread while gait_valid/falls stay clean, progressive widening (small step from a working champion) is the right curriculum shape and should replace cold full-set jumps everywhere in this ladder. If it degrades the same way regardless of starting point, the reversal-heading course-tracking gap is a fundamental limit of this observation/policy setup, not an initialization artifact, and needs its own design pass (e.g. heading encoded as sin/cos pair coverage, or a symmetry-augmented data mix) before further heading-set widening spend.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M) -- do not judge mature course-tracking at this checkpoint. PASS/INFORMATIVE if: gait_valid stays majority-valid (>=4/6 det, matching or beating fullhead-c1's own 22-24/24) with 0 falls, AND direction_err_mean_deg / course_err_1s_med_deg at the two NEW reversal headings (+-135,180) in the harness's per-episode breakdown come in tighter than fullhead-c1's own per-episode spread (28-161deg) for the matched heading bins. FAIL if gait_valid collapses (new leg sacrifice) or falls appear (widening broke something that was working). Either course-tracking outcome is informative -- this is a canary on the CURRICULUM-SHAPE question, not the final course-tracking bar.

**verdict**: CANARY PASS (mechanism-health, curriculum-shape signal POSITIVE). Widening from the mature 40M medhead-acq1 champion (not a cold 3-way jump) keeps the gait genuinely intact -- gait_valid 21/24 (majority every mode: 4/6,6/6,5/6,6/6), ZERO falls/terminations across all 24 episodes -- AND measurably tightens course-tracking at the two new reversal headings vs the fullhead-c1 cold-jump baseline (same halfgrav family, n=24 each): direction_err_mean_deg median 88.5->75.5 (range 29-144 -> 25-136), course_err_1s_med_deg median 94.9->57.9 (-39%), and most strikingly slip_per_m median 51.4->7.6 (6.8x lower, now near the 2.9 teacher band on the majority of episodes). Frame strips (walk_det_3, highest-slip episode) show genuine six-leg cycling through varied body poses, not a frozen/dragging gait. This supports the pre-registered curriculum-shape hypothesis: widening FROM an already-quarter-turn-capable champion is a better recipe than a cold full-8-way jump from the 3-way champion. NOT yet a design conclusion alone -- read together with widen2-c2 (this cycle): that arm shows no such improvement, but a provenance check found it warm-started from a 2M CANARY checkpoint (headset_halfgrav_medhead2_c1) rather than medhead2's own 40M champion (medhead2_acq1), so it is NOT a matched-budget second seed and cannot yet refute this result as a seed lottery. Launching a matched-budget corrected second-seed arm this cycle from medhead2_acq1 (40M) to give a clean apples-to-apples read.

