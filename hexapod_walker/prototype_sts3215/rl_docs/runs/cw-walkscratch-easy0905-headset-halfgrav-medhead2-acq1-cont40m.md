# cw-walkscratch-easy0905-headset-halfgrav-medhead2-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-05T20:42:35+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-medhead2-acq1

**wandb_id**: cj3fxcgy

**hypothesis**: headset-halfgrav-medhead2-acq1 (5-way medium-heading, halfgrav 0.5g, 2nd seed) read CONTINUE not FAIL/PASS at 40M: walk_startjitter/det only 2/6 gait_valid (below the >=4/6 bar) but the flagged legs' duty_cycle is borderline (0.06-0.11, matching the first-seed champion's own accepted-as-PASS 0.08-0.09 range, not the base family's chronic 0.0-0.02 hard park), which leg gets flagged varies across episodes rather than one leg every time, and ep_rew_mean is still genuinely climbing (quarters -401,-419,-183,+30, noisy but net upward in the last 10M) with v_along_cmd stable/not collapsing. Same checkpoint, same recipe, another 40M (80M total) to let the marginal gait resolve one way or the other before re-judging the halfgrav medhead rung's 2nd-seed status.

**gate**: ACQUISITION CONTINUATION (80M total): PASS if walk/det AND walk_startjitter/det each clear >=4/6 gait_valid with no leg holding duty<0.10 across a majority of episodes, slip_per_m near the 2.9 band, zero falls -- closes the halfgrav medhead rung at n=2 seeds. FAIL if gait_valid regresses further or the same legs entrench into a hard 0.0-0.02 duty park like the base family. Still-CONTINUE only if truly still climbing with no plateau -- do not fund a 3rd continuation past this one on reward-climbing alone.

**verdict**: ACQ FAIL vs the continuation's own pre-registered gate. Result: walk/det improved 4/6->5/6 gait_valid (0 falls, slip med 2.25, near the 2.9 band) but walk_startjitter/det stayed flat at 2/6 (same as the pre-continuation checkpoint) despite doubling budget 40M->80M -- the AND-bar needs BOTH modes >=4/6. Flagged legs sit at duty 0.05-0.08 (borderline, not the base family's hard 0.0-0.02 park) and which leg gets flagged still varies episode-to-episode (2; 1; 1; [1,4]), so this is a plateau on the start-jitter perturbation specifically, not a regression or new entrenchment. ep_rew_mean quarters [126.5,310.1,413.1,514.4] are still rising but decelerating (+184,+103,+101) -- exactly the reward-climbing-alone shape this gate's own text preemptively barred from funding a 3rd continuation ('do not fund a 3rd continuation past this one on reward-climbing alone'). Zero falls both modes. Verdict: closes this continuation lineage now per its own stopping rule rather than extending further. Net effect on the rung: n=2 seeds on halfgrav+medhead2 is now MIXED, not confirmed -- seed1 (headset-halfgrav-medhead-acq1) PASSED cleanly at 40M; seed2 (this checkpoint's lineage) needed a continuation and still fails specifically on the start-jitter robustness axis after 80M total. The gap looks perturbation-specific (initial-joint-offset robustness) rather than the base family's chronic single-leg duty park, so it doesn't reopen the closed per-leg-utilization mechanism question -- it flags a narrower open question (robustness to start-jitter) for a future targeted look, not an immediate repair spend.

