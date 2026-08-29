# cw-walkcurr-pf-decleg-sv-s2-rr1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: LAUNCH_CRASH

**created**: 2026-08-29T15:38:07+00:00

**pod**: hexapod-mjx-train-1

**steps**: 20000000

**hypothesis**: Plain English: can six INDEPENDENT per-leg actor modules discover walking from scratch where every centralized policy froze? Operator-registered literature (Schilling IROS 2020) shows decentralized per-leg PPO escapes exactly the local-minimum freeze our 15 refuted centralized classes hit, using a plain-velocity discovery reward and a bigger budget. This arm: NEW --decleg actor (6 x 64,64 tanh towers over leg-local q/qd/prev-action + shared tilt/gyro/command, block-diagonal head -- cross-leg coupling impossible on the action path; centralized 128/64/32 critic) + simple-velocity diet (WALKCURR_SV bank: stride-EMA freeprog income at rscale50 scale + term_penalty 24, every other reward term zeroed) + actbias plant fix, from scratch on mesh/100Hz defaults, n-steps 96 preserves the ~1s rollout window, 20M steps, seed 2 of 3 (paper warns of high seed variance). Prediction-if-true: walk_freeprog_score escapes the static-basin band and real stepping appears on periodic video before 20M. Prediction-if-false: identical pinned-band static stand/crouch with flat-or-falling reward across all 3 seeds AND the centralized control -- escalating to the operator-named SAC/terrain-diversity fallbacks. Strongest alternative: diet+budget alone suffice and the centralized control walks too (decentralization not the lever).

**gate**: Rung-1 gate at 20M: C-env det fixed-forward panel (n>=6) -- zero tilt terminations, cmd_prog_frac >= 0.35, direction_err_deg <= 30, slip/m <= 3.0, gait_valid >= 4/6 with all six legs cycling, real stepping on video. Mid-run discovery litmus: env/walk_freeprog_score must escape the [-0.10,-0.05] static-basin band and trend toward/past 0; escape with rising reward but gate unmet at 20M = continue per 08-21; pinned band + flat/falling reward at 20M = aligned FAIL. Eval-side PASS still enforces the full WALKCURR_PF ranking behaviors (slip is priced at eval regardless of the simple training diet).

**verdict**: 0-step launch crash, not a science verdict. Died at env reset before a single training step: ValueError 'latency 106 ms too large for 12 pending-command slots at dt=0.01' (mjx_backend.py set_tick_params) -- bus.servo_params=loaded's ~106ms fitted latency exceeds the PENDING_SLOTS=12 ring buffer's window at the 08-24 mesh/100Hz control default (ring was sized for the retired 25Hz control tick). Same crash hit the base run (cw-walkcurr-pf-decleg-sv-s2), decleg-sv-s0/-s0-rr1, and central-sv-s0/-central-sv-s0-rr1 -- systemic, not arm-specific. Root-caused and fixed this cycle: PENDING_SLOTS 12->40 (mjx_backend.py), regression test added (test_mjx_backend_pending_slots.py), smoke-tested on hexapod-mjx-train-2 past the exact crash line before trusting it, snapshot 59227996. Relaunched with the fix as cw-walkcurr-pf-decleg-sv-s2-rr2 (VERIFIED RUNNING on hexapod-mjx-train-2).

