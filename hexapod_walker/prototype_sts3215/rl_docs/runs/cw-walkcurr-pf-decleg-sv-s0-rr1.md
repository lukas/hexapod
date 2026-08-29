# cw-walkcurr-pf-decleg-sv-s0-rr1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: LAUNCH_CRASH

**created**: 2026-08-29T15:55:23+00:00

**pod**: hexapod-mjx-train-2

**steps**: 20000000

**hypothesis**: Plain English: can six INDEPENDENT per-leg actor modules discover walking from scratch where every centralized policy froze? Operator-registered literature (Schilling IROS 2020) shows decentralized per-leg PPO escapes exactly the local-minimum freeze our 15 refuted centralized classes hit, using a plain-velocity discovery reward and a bigger budget. This arm: NEW --decleg actor (6 x 64,64 tanh towers over leg-local q/qd/prev-action + shared tilt/gyro/command, block-diagonal head -- cross-leg coupling impossible on the action path; centralized 128/64/32 critic) + simple-velocity diet (WALKCURR_SV bank: stride-EMA freeprog income at rscale50 scale + term_penalty 24, every other reward term zeroed) + actbias plant fix, from scratch on mesh/100Hz defaults, n-steps 96 preserves the ~1s rollout window, 20M steps, seed 0 of 3 (paper warns of high seed variance). Prediction-if-true: walk_freeprog_score escapes the static-basin band and real stepping appears on periodic video before 20M. Prediction-if-false: identical pinned-band static stand/crouch with flat-or-falling reward across all 3 seeds AND the centralized control -- escalating to the operator-named SAC/terrain-diversity fallbacks. Strongest alternative: diet+budget alone suffice and the centralized control walks too (decentralization not the lever).

**gate**: Rung-1 gate at 20M: C-env det fixed-forward panel (n>=6) -- zero tilt terminations, cmd_prog_frac >= 0.35, direction_err_deg <= 30, slip/m <= 3.0, gait_valid >= 4/6 with all six legs cycling, real stepping on video. Mid-run discovery litmus: env/walk_freeprog_score must escape the [-0.10,-0.05] static-basin band and trend toward/past 0; escape with rising reward but gate unmet at 20M = continue per 08-21; pinned band + flat/falling reward at 20M = aligned FAIL. Eval-side PASS still enforces the full WALKCURR_PF ranking behaviors (slip is priced at eval regardless of the simple training diet).

**verdict**: LAUNCH_CRASH, not a hypothesis result: crashed in set_tick_params before any training (0 steps, W&B run 84gycsoz). Root cause: --cfg-set bus.servo_params=loaded's measured ~106ms per-axis latency exceeds the MJX backend's PENDING_SLOTS=12 ring buffer at control.hz=100 (dt=0.01s) -- identical defect to the parent s0 run and cw-standwalk-stance-mesh1 (08-25). Root fix (PENDING_SLOTS 12->40, mjx_backend.py) landed+pushed by a concurrent cycle at 59227996 with a new regression bank (test_mjx_backend_pending_slots.py, 4/4 relevant asserts incl. the exact loaded-latency-at-100hz case) -- verified present on HEAD. No verdict on the decentralized-vs-centralized hypothesis possible from this attempt; relaunching as -rr2 on the fixed code now that it's synced.

**failed_reason**: run never appeared as 'running' in W&B within 240s

