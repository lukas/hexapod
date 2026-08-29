# cw-walkcurr-pf-central-sv-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAILED

**created**: 2026-08-29T15:29:13+00:00

**pod**: hexapod-mjx-train-3

**steps**: 20000000

**hypothesis**: Plain English: the architecture CONTROL -- does the simple-velocity diet plus a 10x budget alone (no architecture change) unlock from-scratch discovery? Identical diet/budget/seed to cw-walkcurr-pf-decleg-sv-s0 but the standard CENTRALIZED 128/64/32 tanh MLP actor. If this walks too, decentralization was not the lever (diet/budget was); if it freezes while the decleg arms walk, Schilling's decentralization claim transfers to our plant; if all four freeze, the task is not budget-capped-at-2M for either architecture and the SAC/terrain fallbacks open. Prediction-if-true: freeprog escape + stepping on video. Prediction-if-false: pinned static basin with flat/falling reward -- the 16th centralized refutation, now at 10x budget, closing the budget-cap hypothesis for the centralized family.

**gate**: Rung-1 gate at 20M: C-env det fixed-forward panel (n>=6) -- zero tilt terminations, cmd_prog_frac >= 0.35, direction_err_deg <= 30, slip/m <= 3.0, gait_valid >= 4/6 with all six legs cycling, real stepping on video. Mid-run discovery litmus: env/walk_freeprog_score must escape the [-0.10,-0.05] static-basin band and trend toward/past 0; escape with rising reward but gate unmet at 20M = continue per 08-21; pinned band + flat/falling reward at 20M = aligned FAIL. Eval-side PASS still enforces the full WALKCURR_PF ranking behaviors (slip is priced at eval regardless of the simple training diet).

**verdict**: LAUNCH_CRASH, not a hypothesis result: same defect as the decleg-sv-s0 sibling (see its verdict) -- ValueError in set_tick_params, 0 training steps; this is the architecture CONTROL arm, so the decentralized-vs-centralized question is still fully open, not refuted. Its retry (central-sv-s0-rr1) crashed identically before the fix landed. Relaunch after the concurrent cycle's PENDING_SLOTS fix is committed.

**failed_reason**: run never appeared as 'running' in W&B within 240s

