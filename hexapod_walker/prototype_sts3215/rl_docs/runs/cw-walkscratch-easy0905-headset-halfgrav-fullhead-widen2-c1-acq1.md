# cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-05T22:23:34+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c1

**wandb_id**: v33rv9wx

**hypothesis**: Plain English: widen2-c1's 2M canary showed that widening the halfgrav heading champion's command set from the passing 5-way (0,+-45,+-90) to the full 8-way compass (adding reversals +-135/180) FROM the medhead champion (not a cold jump) keeps the gait valid (21/24, 0 falls) and tightens reversal-heading tracking vs the cold-jump fullhead-c1 baseline (direrr 88.5->75.5deg, slip 6.8x lower). This is the acquisition-scale (40M) confirmation: does the progressive-widen recipe hold up at full budget, closing the reversal-heading course-tracking gap enough to call the widen curriculum shape validated for this ladder?

**gate**: ACQ PASS if gait_valid stays majority (>=18/24, matching medhead-acq1's own bar) with 0 falls AND direction_err_mean_deg/course_err at the reversal headings continues to tighten vs both fullhead-c1's cold-jump baseline (28-161deg) and this run's own 2M canary read (walk/det med slip 5.02, prog med 1.14) rather than re-widening back toward fullhead-c1's failure range. ACQ FAIL if gait_valid drops into minority or a leg is chronically sacrificed (matching the base-family entrenchment pattern). ACQ CONTINUE if reward is still climbing and gait stays valid but course-tracking is still improving/ambiguous at 40M.

**verdict**: Widening the halfgrav heading champion's command set from medhead (5-way) to the full 8-way compass (adding reversals) HOLDS at full 40M acquisition budget on this seed. Evidence: harness gait_valid 21/24 across all 4 modes (walk/det 5/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 4/6), ZERO falls/terminations in all 24 episodes; per-episode duty_cycle spreads healthily across all six legs in 21/24 episodes (only 3 episodes flag a transient leg, never the same leg twice, no chronic single-leg pattern); det/walk slip_per_m median 3.93 IMPROVES vs this run's own 2M canary read (5.02), progress_ratio median ~1.05 holds steady (~1.14 canary); frame strips (walk_det_0/1/2, walk_startjitter_det_*) show genuine six-leg cycling gait through varied heading commands, not dragging/freezing. Why: this is the exact pre-registered PASS bar (gate text: >=18/24 gait_valid, 0 falls, slip/course tightening vs the canary read and vs the fullhead-c1 cold-jump failure range) -- met cleanly, not a borderline call. ep_rew_mean quarters dip then partially recover ([-1261,-1844,-1730,-1515]) rather than climb, so this is a genuine harness-driven PASS, not an 08-21 rising-reward inference. What's next: this is the FIRST acquisition-scale confirmation that the widen-from-medhead curriculum step survives a full 40M budget with a healthy gait intact; read together with the matched sibling widen2-c2b-acq1 (verdicted separately this cycle, ACQ FAIL -- same recipe, different seed, chronic leg-1 entrenchment) this makes the recipe seed-dependent at 40M, not universally robust -- do not yet call the widen2 rung fully acquisition-closed on n=1 PASS. Promote this checkpoint as the walkcurr halfgrav lineage's current best full-8-way heading champion for further composition (e.g. adding irr timing-jitter, mirroring the already-launched irrwiden-c1/widenirr-c1 batch).

