# cw-walkcurr-pf-decleg-sv-s2-rr2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-08-29T16:15:51+00:00

**pod**: hexapod-mjx-train-2

**steps**: 20000000

**parent**: cw-walkcurr-pf-decleg-sv-s2-rr1

**hypothesis**: Plain English: mechanical retry, not a new science question -- the base + rr1 attempts of this arm (decentralized per-leg PPO, seed 2, simple-velocity discovery diet, 20M) never logged a single training step: both crashed at env reset with ValueError 'latency 106 ms too large for 12 pending-command slots at dt=0.01' (mjx_backend.py set_tick_params) -- a launch-time infra bug (PENDING_SLOTS=12 ring buffer sized for the 25Hz-era control tick, never re-derived for the 08-24 mesh/100Hz default), not a training or reward failure. Root-caused and fixed this cycle (PENDING_SLOTS 12->40, restores the >=2x latency margin at 100Hz; regression test added; smoke-tested on hexapod-mjx-train-2 past the exact crash point before this relaunch; snapshot 59227996). Same config as cw-walkcurr-pf-decleg-sv-s2 otherwise -- see that run's hypothesis for the actual science question (decentralized-vs-centralized discovery escape).

**gate**: Rung-1 gate at 20M: C-env det fixed-forward panel (n>=6) -- zero tilt terminations, cmd_prog_frac >= 0.35, direction_err_deg <= 30, slip/m <= 3.0, gait_valid >= 4/6 with all six legs cycling, real stepping on video. Mid-run discovery litmus: env/walk_freeprog_score must escape the [-0.10,-0.05] static-basin band and trend toward/past 0; escape with rising reward but gate unmet at 20M = continue per 08-21; pinned band + flat/falling reward at 20M = aligned FAIL. Eval-side PASS still enforces the full WALKCURR_PF ranking behaviors (slip is priced at eval regardless of the simple training diet).

