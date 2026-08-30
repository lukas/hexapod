# cw-walkcurr-pf-decleg-sv-s6-b100m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T04:10:01+00:00

**pod**: hexapod-mjx-train-4

**steps**: 100000000

**parent**: cw-walkcurr-pf-decleg-sv-s2-rr2

**wandb_id**: t6mqyye2

**hypothesis**: Plain English: is from-scratch decleg walking a seed lottery we have under-sampled? Schilling et al. (IROS 2020, the operator-registered decentralized-hexapod precedent) needed 15 seeds and warned of high seed variance; this track has sampled only 3 decleg seeds (s0/s1/s2, all FAIL at 20M), and the largest single effect ever measured on this track IS seed variance (SAC s0 instant-topple vs s1 real 6-leg stepping under an identical config). Operator-ordered overnight population sweep (MCP operator lane 20260830T035139Z): fresh seed 6 of the byte-identical decleg-sv recipe (clone of cw-walkcurr-pf-decleg-sv-s2-rr2, WALKCURR_SV bank green by construction) at the 5x budget (100M) the same order authorizes -- levers are seed + budget only, read jointly with the s2-b100m rerun and 3 sibling seeds as a 5-wide population. Prediction-if-true: at least one population member's env/walk_speed leaves the ~0.02 m/s floor with stable/rising ep_len and background over_current, and shows real six-leg stepping on video. Prediction-if-false: all 5 members converge to the same static-quiver-to-over_current basin at 100M -- the seed-lottery + raw-budget explanation is closed for the decleg family and the fork moves to the structural anti-freeze/balance pretrain curriculum (STATUS candidate 1). Strongest alternative: the centralized b100m control escapes too, meaning budget alone (not architecture or seed) was the constraint.

**gate**: Rung-1 C-env det fixed-forward panel (n>=6) at 100M: zero falls, cmd_prog_frac >= 0.35, direction_err <= 30 deg, slip/m <= 3.0, gait_valid >= 4/6 with all six legs cycling, real stepping on video. Corrected discovery litmus (decleg-sv dig-in, binding): env/walk_speed off its ~0.02 m/s floor AND stable-or-rising ep_len_mean AND terminations/over_current at background -- raw freeprog escape co-occurring with an over_current surge is the known episode-shortening artifact and does NOT count. Litmus met + rising reward but gate unmet at 100M = continue per 08-21. Selection discipline (operator 08-30): no promotion from the search eval alone -- any candidate must then pass held-out eval/command seeds and a replicate seed before a track-level claim.

