# cw-walkcurr-pf-decleg-sv-s4-b100m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-30T04:02:17+00:00

**pod**: hexapod-mjx-train-2

**steps**: 100000000

**parent**: cw-walkcurr-pf-decleg-sv-s2-rr2

**wandb_id**: 6ogllxfh

**hypothesis**: Plain English: is from-scratch decleg walking a seed lottery we have under-sampled? Schilling et al. (IROS 2020, the operator-registered decentralized-hexapod precedent) needed 15 seeds and warned of high seed variance; this track has sampled only 3 decleg seeds (s0/s1/s2, all FAIL at 20M), and the largest single effect ever measured on this track IS seed variance (SAC s0 instant-topple vs s1 real 6-leg stepping under an identical config). Operator-ordered overnight population sweep (MCP operator lane 20260830T035139Z): fresh seed 4 of the byte-identical decleg-sv recipe (clone of cw-walkcurr-pf-decleg-sv-s2-rr2, WALKCURR_SV bank green by construction) at the 5x budget (100M) the same order authorizes -- levers are seed + budget only, read jointly with the s2-b100m rerun and 3 sibling seeds as a 5-wide population. Prediction-if-true: at least one population member's env/walk_speed leaves the ~0.02 m/s floor with stable/rising ep_len and background over_current, and shows real six-leg stepping on video. Prediction-if-false: all 5 members converge to the same static-quiver-to-over_current basin at 100M -- the seed-lottery + raw-budget explanation is closed for the decleg family and the fork moves to the structural anti-freeze/balance pretrain curriculum (STATUS candidate 1). Strongest alternative: the centralized b100m control escapes too, meaning budget alone (not architecture or seed) was the constraint.

**gate**: Rung-1 C-env det fixed-forward panel (n>=6) at 100M: zero falls, cmd_prog_frac >= 0.35, direction_err <= 30 deg, slip/m <= 3.0, gait_valid >= 4/6 with all six legs cycling, real stepping on video. Corrected discovery litmus (decleg-sv dig-in, binding): env/walk_speed off its ~0.02 m/s floor AND stable-or-rising ep_len_mean AND terminations/over_current at background -- raw freeprog escape co-occurring with an over_current surge is the known episode-shortening artifact and does NOT count. Litmus met + rising reward but gate unmet at 100M = continue per 08-21. Selection discipline (operator 08-30): no promotion from the search eval alone -- any candidate must then pass held-out eval/command seeds and a replicate seed before a track-level claim.

**verdict**: Dig-in resolved: the anomalous 0.30-0.55 DR-0 progress_ratio is a metric artifact, not a partial escape. Root cause: progress_ratio=along_dist/cmd_dist_m, and episodes that die to over_current FASTEST get the SMALLEST cmd_dist_m denominator (walk/det eps 0,1,5: cmd_dist_m 0.06-0.066m, course_windows_1s=6 -> episode cut off almost immediately) while eps 2,3,4 ran ~25s (cmd_dist_m 0.15-0.19m) before dying. Absolute along_dist_m is UNIFORMLY tiny across ALL 24 episodes regardless of length (0.007-0.037m total displacement, i.e. ~1-2mm/s) -- identical static-quiver magnitude to every sibling; the short episodes just divide by a smaller number. Training-curve litmus confirms non-escape: env/walk_speed oscillates 0.018-0.028 for the entire 100M steps (never decisively clears the 0.02 floor), terminations/over_current stays 600-1000/window throughout (not background), ep_len_mean bounces 390-670 with no clean rising trend, env/walk_freeprog_score hovers ~0 (-0.09 to +0.02). Same static-quiver-to-over_current basin as s2/s3/s5/s6/central-sv-s0 -- closes the 6/6-arm PPO population/budget-seed sweep at FAIL. No promotion (operator 08-30 selection discipline moot -- there is no candidate). NEXT: the graduated step-completion shaping bank (partial credit for sub-10mm forward-projecting swings, tapering to zero at zero motion) that the prior triage cycle deferred -- building it now.

