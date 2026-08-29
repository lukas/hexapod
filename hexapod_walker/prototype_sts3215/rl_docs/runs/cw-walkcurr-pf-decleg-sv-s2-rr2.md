# cw-walkcurr-pf-decleg-sv-s2-rr2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-29T16:15:51+00:00

**pod**: hexapod-mjx-train-2

**steps**: 20000000

**parent**: cw-walkcurr-pf-decleg-sv-s2-rr1

**wandb_id**: ptm6a234

**hypothesis**: Plain English: mechanical retry, not a new science question -- the base + rr1 attempts of this arm (decentralized per-leg PPO, seed 2, simple-velocity discovery diet, 20M) never logged a single training step: both crashed at env reset with ValueError 'latency 106 ms too large for 12 pending-command slots at dt=0.01' (mjx_backend.py set_tick_params) -- a launch-time infra bug (PENDING_SLOTS=12 ring buffer sized for the 25Hz-era control tick, never re-derived for the 08-24 mesh/100Hz default), not a training or reward failure. Root-caused and fixed this cycle (PENDING_SLOTS 12->40, restores the >=2x latency margin at 100Hz; regression test added; smoke-tested on hexapod-mjx-train-2 past the exact crash point before this relaunch; snapshot 59227996). Same config as cw-walkcurr-pf-decleg-sv-s2 otherwise -- see that run's hypothesis for the actual science question (decentralized-vs-centralized discovery escape).

**gate**: Rung-1 gate at 20M: C-env det fixed-forward panel (n>=6) -- zero tilt terminations, cmd_prog_frac >= 0.35, direction_err_deg <= 30, slip/m <= 3.0, gait_valid >= 4/6 with all six legs cycling, real stepping on video. Mid-run discovery litmus: env/walk_freeprog_score must escape the [-0.10,-0.05] static-basin band and trend toward/past 0; escape with rising reward but gate unmet at 20M = continue per 08-21; pinned band + flat/falling reward at 20M = aligned FAIL. Eval-side PASS still enforces the full WALKCURR_PF ranking behaviors (slip is priced at eval regardless of the simple training diet).

**verdict**: Decentralized per-leg PPO seed 2 - the wave's best-looking litmus trace - is still not walking, and the deep read shows its late freeprog zero-crossing is the episode-shortening artifact, not discovery, so this is a FAIL and not an 08-21 continue. Evidence FOR the continue case, honestly stated: freeprog reached +0.006 at 19.3M (only run of the wave to cross 0) and walk/sto + startjitter/sto gait_valid hit 5/6. Why it fails anyway: (1) the crossing is a wobble, not a trend - final window -0.006, and freeprog correlates +0.68 with the over_current termination surge while walk_speed stays flat at 0.02 m/s all 20M (corr -0.19); (2) the DETERMINISTIC policy - what the litmus is supposed to predict - moves BACKWARD (det prog med -0.05, fwd 0.01m, legs [1,4] sacrificed 6/6, gait_valid 0/6, 24/24 over_current across modes; det strip shows zero translation and one leg-pair held unloaded); the sto 'gait_valid' episodes are exploration noise jiggling planted legs past the detector while the robot still goes nowhere (fwd 0.01-0.04m); (3) reward is NOT rising - fell 201->168 by 9M then pinned exactly at the wave-wide 167.6 attractor while ep_len collapsed 1644->434 - the 08-21 continue clause requires rising reward and this is the opposite. Root cause identical to siblings (see central-sv verdict): stride-EMA freeprog income pays stationary quiver ~+0.42/tick (final env/reward_walk=0.416 with zero locomotion), term_penalty negligible per-tick, mesh 3.5kg + loaded servos put the sacrifice stance on a current limit. Completes the wave: 4/4 aligned FAIL (decleg s0/s1/s2 + central), decentralization refuted as the lever; pre-registered fallback fires - next is the operator-named ladder (a) off-policy SAC probe (trainer-side build), then (b) Heess-style terrain diversity. Any successor gate text must require walk_speed + stable ep_len corroboration alongside freeprog.

