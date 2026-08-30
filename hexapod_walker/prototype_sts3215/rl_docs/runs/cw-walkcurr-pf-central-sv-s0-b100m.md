# cw-walkcurr-pf-central-sv-s0-b100m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-30T04:19:11+00:00

**pod**: hexapod-mjx-train-6

**steps**: 100000000

**parent**: cw-walkcurr-pf-central-sv-s0-rr2

**wandb_id**: ha3nppmt

**hypothesis**: Plain English: the architecture CONTROL for the overnight 100M population sweep -- if 5x more budget unlocks walking, is decentralization even needed, or was budget the only constraint all along? Operator-ordered overnight population sweep (MCP operator lane 20260830T035139Z). Byte-identical config/diet/seed to cw-walkcurr-pf-central-sv-s0-rr2 (the centralized FAIL at 20M; WALKCURR_SV bank green by clone construction) -- the ONLY lever is budget 20M->100M; fixed-seed determinism reproduces the first 20M then trains 80M past it. Read jointly with the 5 decleg b100m siblings: decleg escapes while this stays pinned = Schilling's decentralization claim confirmed at scale; both escape = budget alone was binding; both pinned = the raw-budget axis is closed for BOTH architectures at 100M and the fork moves to the structural anti-freeze/balance pretrain curriculum (STATUS candidate 1). Prediction-if-true: walk_speed off the static floor with stable/rising ep_len and background over_current late in the run. Prediction-if-false: flat ~194 reward ridge and pinned walk_speed through 100M, the 16th-plus centralized refutation now at 50x the original discovery budget.

**gate**: Rung-1 C-env det fixed-forward panel (n>=6) at 100M: zero falls, cmd_prog_frac >= 0.35, direction_err <= 30 deg, slip/m <= 3.0, gait_valid >= 4/6 with all six legs cycling, real stepping on video. Corrected discovery litmus (decleg-sv dig-in, binding): env/walk_speed off its ~0.02 m/s floor AND stable-or-rising ep_len_mean AND terminations/over_current at background -- raw freeprog escape co-occurring with an over_current surge is the known episode-shortening artifact and does NOT count. Litmus met + rising reward but gate unmet at 100M = continue per 08-21. Selection discipline (operator 08-30): no promotion from the search eval alone -- held-out eval/command seeds plus a replicate seed before any track-level claim.

**verdict**: Aligned FAIL: the centralized-architecture control arm of the overnight population sweep lands in the identical static-quiver-to-over_current basin as every decleg-sv sibling (s2/s5/s6), confirming budget alone (100M) does not escape it either -- architecture was not the missing lever. Evidence: env/walk_speed pinned 0.012-0.03 m/s the whole 95.5M-step run (never off the ~0.02 floor); rollout/ep_len_mean spiked once to ~1182 at ~5M then collapsed to 350-440 and stayed there through 95M; terminations/over_current rose to ~1000-1200/window by ~10M and never returned to background; reward quarters [173.7,167.4,167.1,166.7] -- peak early, then flat/declining, not rising (not an 08-21 continue case). DR-0 gate n=24: prog med 0.00 (need >=0.35), slip/m med 4.96-6.44 (cap 3.0), fwd med 0.01-0.02m/25s, every episode TERM over_current across all 4 sub-panels; gait_valid nominally 6/6 on det/startjitter-det but that is the same paddle-creep false-positive seen on s6 -- contact-sheet frame strip confirms zero net translation, static splayed crouch across all 10 frames, robot does not move. Litmus (decleg-sv dig-in, binding) unmet on all 3 conditions. This is the centralized control leg of the 10-arm overnight population sweep (STATUS 2026-08-30 ~04:3x): with s2/s5/s6/central all FAIL (4 of 6 PPO population arms read so far, same basin every time), the raw budget/seed-population axis is closing for BOTH architectures at 100M -- only s3 (concurrent cycle) and s4 remain unread on the PPO side, plus the 4 SAC-tilt5-20M arms still training. Do not fund another same-class dose/seed/architecture arm off this read alone; if s3/s4 also FAIL this basin, the structural anti-freeze/balance-pretrain curriculum (STATUS candidate 1) becomes the track's next funded item.

