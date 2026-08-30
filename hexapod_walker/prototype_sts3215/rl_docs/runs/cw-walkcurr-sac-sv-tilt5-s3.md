# cw-walkcurr-sac-sv-tilt5-s3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-08-30T04:32:07+00:00

**pod**: hexapod-mjx-train-9

**steps**: 20000000

**parent**: cw-walkcurr-sac-sv-tilt5-s1

**hypothesis**: Plain English: seed lottery at the best dose -- SAC seed variance is the largest single effect this track has measured (seed 0 instant-topple vs seed 1 real six-leg stepping under an IDENTICAL config), and the tilt5 dose (the only config that ever kept stepping most episodes, fwd median 0.055m) has only ever been run on seed 1. Operator-ordered overnight population sweep (MCP operator lane 20260830T035139Z, Lukas: branch many rollouts on the idle fleet and select the best honestly): fresh seed 3 of the byte-identical SAC tilt5 recipe (clone of cw-walkcurr-sac-sv-tilt5-s1, WALKCURR_SV_TILT bank green at dose 5.0) at 10x the original budget (20M) -- levers are seed + budget only, read jointly with the s1-b20m extension (concurrent cycle, same operator order) and 2 sibling seeds as a 4-wide SAC population. Prediction-if-true: at least one seed both steps AND balances -- fall rate off 24/24, forward_dist past 0.06m and climbing, walk_speed in the 0.05-0.08 band with rising ep_len. Prediction-if-false: every seed reproduces the step-then-stumble ceiling (or seed-0-style instant topple) at 20M with flat reward -- the seed axis at this dose is closed and the fork moves to the structural anti-freeze/balance pretrain curriculum (STATUS candidate 1). Strongest alternative: only the extended seed 1 improves (consolidation, not seed lottery, is the lever).

**gate**: Rung-1 C-env det+sto fixed-forward panel (n>=6 each) at 20M: PASS needs progress_ratio >= 0.35, slip/m <= 3.0, gait_valid >= 4/6, falls on <= 1/6 det episodes. PARTIAL/continue (08-21): fall rate below 24/24 or forward_dist median clearing 0.06m with reward not declining. FAIL: seed-0-style instant topple or the unchanged 24/24 stumble ceiling at 20M with flat/declining reward. Discovery litmus per the corrected standard: env/walk_speed in the cmd band AND ep_len stable/rising AND over_current at background -- freeprog escape alone is the known artifact. Selection discipline (operator 08-30): no promotion from the search eval alone -- held-out eval/command seeds plus a replicate seed before any track-level claim.

**refused_reason**: hexapod-mjx-train-9 already runs cw-walkcurr-sac-sv-tilt5-s3 — GPU pods host exactly one run; pick a free GPU pod.

