# cw-walkcurr-pf-central-sv-s0-b100m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T04:19:11+00:00

**pod**: hexapod-mjx-train-6

**steps**: 100000000

**parent**: cw-walkcurr-pf-central-sv-s0-rr2

**wandb_id**: ha3nppmt

**hypothesis**: Plain English: the architecture CONTROL for the overnight 100M population sweep -- if 5x more budget unlocks walking, is decentralization even needed, or was budget the only constraint all along? Operator-ordered overnight population sweep (MCP operator lane 20260830T035139Z). Byte-identical config/diet/seed to cw-walkcurr-pf-central-sv-s0-rr2 (the centralized FAIL at 20M; WALKCURR_SV bank green by clone construction) -- the ONLY lever is budget 20M->100M; fixed-seed determinism reproduces the first 20M then trains 80M past it. Read jointly with the 5 decleg b100m siblings: decleg escapes while this stays pinned = Schilling's decentralization claim confirmed at scale; both escape = budget alone was binding; both pinned = the raw-budget axis is closed for BOTH architectures at 100M and the fork moves to the structural anti-freeze/balance pretrain curriculum (STATUS candidate 1). Prediction-if-true: walk_speed off the static floor with stable/rising ep_len and background over_current late in the run. Prediction-if-false: flat ~194 reward ridge and pinned walk_speed through 100M, the 16th-plus centralized refutation now at 50x the original discovery budget.

**gate**: Rung-1 C-env det fixed-forward panel (n>=6) at 100M: zero falls, cmd_prog_frac >= 0.35, direction_err <= 30 deg, slip/m <= 3.0, gait_valid >= 4/6 with all six legs cycling, real stepping on video. Corrected discovery litmus (decleg-sv dig-in, binding): env/walk_speed off its ~0.02 m/s floor AND stable-or-rising ep_len_mean AND terminations/over_current at background -- raw freeprog escape co-occurring with an over_current surge is the known episode-shortening artifact and does NOT count. Litmus met + rising reward but gate unmet at 100M = continue per 08-21. Selection discipline (operator 08-30): no promotion from the search eval alone -- held-out eval/command seeds plus a replicate seed before any track-level claim.

