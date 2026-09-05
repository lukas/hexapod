# cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_PASS

**created**: 2026-09-05T20:30:14+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-medhead2-c1

**wandb_id**: yz196tgc

**hypothesis**: Second-seed twin of fullhead-widen2-c1, same design question (does widening from an already-quarter-turn-capable champion fix the reversal-heading course-tracking gap fullhead-c1 showed), on a DIFFERENT champion lineage: headset-halfgrav-medhead2-c1 (the second-seed 2M medhead canary, CANARY PASS, 24/24 gait_valid, cleaner than the first seed) instead of the 40M first-seed medhead-acq1 champion widen2-c1 uses. Confirms whether any widen-from-medhead improvement is recipe-level (both seeds show it) or one lucky champion.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M), same bar as widen2-c1: gait_valid majority-valid (>=4/6 det) with 0 falls, and direction_err/course_err at the new +-135/180 headings tighter than fullhead-c1's own spread (28-161deg). Read together with widen2-c1: both improve = recipe-level curriculum finding; only one improves = seed-lottery, not yet a design conclusion; neither improves = reversal-heading gap is fundamental, not an init artifact.

**verdict**: CANARY PASS on the pre-registered mechanism bar only (gait_valid stays majority 23/24: 6/6,6/6,5/6,6/6, ZERO falls -- widening did not reintroduce leg sacrifice), but the course-tracking half of this canary is INCONCLUSIVE and CONFOUNDED -- do not read it as refuting widen2-c1's positive signal. direction_err_mean_deg median 89.5 (vs fullhead-c1 cold-jump baseline 88.5, essentially flat) and course_err_1s_med_deg median 87.9 (vs baseline 94.9, marginal) show no clear improvement, and slip_per_m WORSENS sharply (median 124.4 vs baseline 51.4, vs widen2-c1's own 7.6 -- a 16x gap between the two nominal 'seeds' of the identical recipe). Root cause found on a provenance check of the ledger's own extra_args (not just the notes text, per the respec-provenance gotcha in CURRENT_TRUTHS): this arm's --init-from is ppo_goal_cw_walkscratch_easy0905_headset_halfgrav_medhead2_c1.zip -- medhead2's 2M CANARY checkpoint -- not medhead2_acq1 (medhead2's own 40M ACQ-continuation champion, matching what widen2-c1 used for seed 1: medhead_acq1, also 40M). This is a checkpoint-MATURITY confound (2M vs 40M training budget on the base skill being widened), not a clean matched second seed of the widen2 recipe -- the worse course-tracking/slip may reflect widening from a less-settled base policy, not the widen2 recipe failing to generalize to a second seed. Refill: launched a corrected matched-budget arm (widen2-c2b) from medhead2_acq1.zip (40M) this cycle for a true apples-to-apples second-seed read before drawing any curriculum-shape conclusion from this pair.

