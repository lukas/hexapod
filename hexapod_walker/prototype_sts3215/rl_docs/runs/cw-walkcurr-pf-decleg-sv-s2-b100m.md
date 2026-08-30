# cw-walkcurr-pf-decleg-sv-s2-b100m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-30T03:57:55+00:00

**pod**: hexapod-mjx-train-1

**steps**: 100000000

**parent**: cw-walkcurr-pf-decleg-sv-s2-rr2

**wandb_id**: 0mfa0z00

**hypothesis**: Plain English: does the least-bad decleg seed just need 5x more training time? Operator-ordered overnight population sweep (MCP operator lane 20260830T035139Z, Lukas: use the idle fleet, bigger budget is fine, branch many rollouts and select honestly). The operator and the track STATUS both name the decleg-sv-s2 lineage as the cleanest partial signal so far; every prior arm on this diet stopped at 20M, a budget the operator-registered literature (Heess 2017) says can be orders of magnitude too small for from-scratch locomotion. Byte-identical config/diet/seed to cw-walkcurr-pf-decleg-sv-s2-rr2 (FAIL at 20M; WALKCURR_SV bank green by clone construction) -- the ONLY lever is budget 20M->100M; decleg refuses --init-from, so under fixed-seed determinism this reproduces s2's own first 20M exactly and then trains 80M past where it stopped (same workaround precedent as sac-sv-s1-budget10m). Prediction-if-true: env/walk_speed leaves the ~0.02 m/s static floor toward the 0.05-0.06 cmd band somewhere in the extra 80M, with ep_len stable/rising and over_current at background. Prediction-if-false: ep_rew stays pinned on the ~167 reward-indifferent ridge with the over_current surge through 100M -- closes the raw-budget lever for the decleg family and the fork moves to the structural anti-freeze/balance pretrain curriculum (STATUS candidate 1). Strongest alternative: a fresh-seed sibling (s3-s6 arms, same wave) escapes while s2 does not -- seed lottery, not budget, is the binding constraint.

**gate**: Rung-1 C-env det fixed-forward panel (n>=6) at 100M: zero falls, cmd_prog_frac >= 0.35, direction_err <= 30 deg, slip/m <= 3.0, gait_valid >= 4/6 with all six legs cycling, real stepping on video. Corrected discovery litmus (decleg-sv dig-in, binding): env/walk_speed off its ~0.02 m/s floor AND stable-or-rising ep_len_mean AND terminations/over_current at background -- raw freeprog escape co-occurring with an over_current surge is the known episode-shortening artifact and does NOT count. Litmus met + rising reward but gate unmet at 100M = continue per 08-21. Selection discipline (operator 08-30): no promotion from the search eval alone -- any candidate must then pass held-out eval/command seeds and a replicate seed before a track-level claim.

**verdict**: Aligned FAIL, same basin as s5/s6: static-quiver-to-over_current. env/walk_speed pinned 0.02-0.03 m/s the WHOLE 90M steps (never off the ~0.02 floor), rollout/ep_len_mean spiked to ~1210-1249 at 5-10M then collapsed to 300-450 and stayed there through 85M, terminations/over_current rose 15->~1000-1200/window by ~15M and never returned to background, reward peaked 200 at ~5M then declined/flattened to 165-167 (quarters [175.6,167.6,166.6,165.7]). DR-0 gate n=24: prog med -0.09 to -0.18 (need >=0.35), slip/m med 4.1-4.6 (cap 3.0), gait_valid 0-1/6, every episode TERM over_current. Litmus (decleg-sv dig-in, binding) unmet on all 3 conditions -- not an 08-21 continue case (reward flat/declining, not rising). 2nd of 5 decleg-100M seeds in the overnight population sweep; matches s5's read exactly. Next: wait for remaining sweep arms (-s3/-s4/central-sv-s0-b100m/sac-tilt5) before closing the population-sweep question jointly per the Now entry's own instruction.

