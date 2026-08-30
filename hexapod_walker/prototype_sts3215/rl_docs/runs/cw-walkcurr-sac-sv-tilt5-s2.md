# cw-walkcurr-sac-sv-tilt5-s2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-30T04:27:14+00:00

**pod**: hexapod-mjx-train-8

**steps**: 20000000

**parent**: cw-walkcurr-sac-sv-tilt5-s1

**wandb_id**: iwkcn4f7

**hypothesis**: Plain English: seed lottery at the best dose -- SAC seed variance is the largest single effect this track has measured (seed 0 instant-topple vs seed 1 real six-leg stepping under an IDENTICAL config), and the tilt5 dose (the only config that ever kept stepping most episodes, fwd median 0.055m) has only ever been run on seed 1. Operator-ordered overnight population sweep (MCP operator lane 20260830T035139Z, Lukas: branch many rollouts on the idle fleet and select the best honestly): fresh seed 2 of the byte-identical SAC tilt5 recipe (clone of cw-walkcurr-sac-sv-tilt5-s1, WALKCURR_SV_TILT bank green at dose 5.0) at 10x the original budget (20M) -- levers are seed + budget only, read jointly with the s1-b20m extension (concurrent cycle, same operator order) and 2 sibling seeds as a 4-wide SAC population. Prediction-if-true: at least one seed both steps AND balances -- fall rate off 24/24, forward_dist past 0.06m and climbing, walk_speed in the 0.05-0.08 band with rising ep_len. Prediction-if-false: every seed reproduces the step-then-stumble ceiling (or seed-0-style instant topple) at 20M with flat reward -- the seed axis at this dose is closed and the fork moves to the structural anti-freeze/balance pretrain curriculum (STATUS candidate 1). Strongest alternative: only the extended seed 1 improves (consolidation, not seed lottery, is the lever).

**gate**: Rung-1 C-env det+sto fixed-forward panel (n>=6 each) at 20M: PASS needs progress_ratio >= 0.35, slip/m <= 3.0, gait_valid >= 4/6, falls on <= 1/6 det episodes. PARTIAL/continue (08-21): fall rate below 24/24 or forward_dist median clearing 0.06m with reward not declining. FAIL: seed-0-style instant topple or the unchanged 24/24 stumble ceiling at 20M with flat/declining reward. Discovery litmus per the corrected standard: env/walk_speed in the cmd band AND ep_len stable/rising AND over_current at background -- freeprog escape alone is the known artifact. Selection discipline (operator 08-30): no promotion from the search eval alone -- held-out eval/command seeds plus a replicate seed before any track-level claim.

**verdict**: FAIL. Evidence: DR-0 gate 24/24 episodes end in a fall (roll_class=fell/terminated) across all 4 sub-panels; walk/det is a literal seed-0-style instant topple (cmd_dist_m 0.011-0.013 -> episode dies via tilt_pitch within ~0.2s of reset, along_dist negative, prog med -0.58). sto/startjitter panels look better on the two gate scalars quoted in the PARTIAL clause (fwd med 0.084m>0.06, some prog>0.35) but that is a metric artifact, not real walking: forward_dist_m is straight-line net displacement (start->end), not along-command distance, and direction_err_mean is 50-98deg (near/over the wrong-direction threshold) on nearly every episode while along-command progress_ratio is near-zero or negative -- the displacement comes from the topple/wobble itself. Contact-sheet frame strips (walk_det_0, walk_sto_2) show the robot static on the same tile for 8-9/10 frames then falling in the last 1-2, zero net translation, confirming no sustained gait exists. Training reward is flat/noisy the entire 20M run (quarters 145.8/151.5/151.1/150.6, ep_rew_mean bounces 130-160 from step ~11k to 175k with no rising trend) -- an aligned FAIL under the 08-21 ruling, not a continue-for-budget case. Why: SAC+anti-tilt(k_roll=k_pitch=5.0) at seed 2 reproduces the fresh-seed instant-topple failure mode this dose was funded to rule out, not tilt5-s1's partial six-leg stepping -- narrows the tilt5-s1 read toward seed lottery over diet-driven. What's next: 1 of 4 tilt5-20M arms in (s1-b20m + s3/s4 still training, s1-b20m owned by the concurrent cycle) -- do not close the population question yet; STATUS already has the pre-committed next-step text for when all 4 land. No relaunch from this arm alone.

