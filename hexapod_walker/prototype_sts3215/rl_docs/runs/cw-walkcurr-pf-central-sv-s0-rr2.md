# cw-walkcurr-pf-central-sv-s0-rr2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-29T16:20:13+00:00

**pod**: hexapod-mjx-train-3

**steps**: 20000000

**parent**: cw-walkcurr-pf-central-sv-s0-rr1

**wandb_id**: 4yaoiolg

**hypothesis**: Plain English: mechanical retry, not a new science question -- the base + rr1 attempts of this arm (the CENTRALIZED architecture control for the decleg-sv wave, simple-velocity discovery diet, 20M) never logged a single training step: both crashed at env reset with ValueError 'latency ... too large for 12 pending-command slots at dt=0.01' (mjx_backend.py set_tick_params) -- a launch-time infra bug (PENDING_SLOTS=12 ring buffer sized for the 25Hz-era control tick, never re-derived for the 08-24 mesh/100Hz default), not a training or reward failure. Root-caused and fixed this cycle (PENDING_SLOTS 12->40, restores the >=2x latency margin at 100Hz; regression test added; smoke-tested on hexapod-mjx-train-2 past the exact crash point before this relaunch; snapshot 59227996). Same config as cw-walkcurr-pf-central-sv-s0 otherwise -- see that run's hypothesis for the actual science question (does diet+budget alone unlock discovery for the centralized architecture).

**gate**: Rung-1 gate at 20M: C-env det fixed-forward panel (n>=6) -- zero tilt terminations, cmd_prog_frac >= 0.35, direction_err_deg <= 30, slip/m <= 3.0, gait_valid >= 4/6 with all six legs cycling, real stepping on video. Mid-run discovery litmus: env/walk_freeprog_score must escape the [-0.10,-0.05] static-basin band and trend toward/past 0; escape with rising reward but gate unmet at 20M = continue per 08-21; pinned band + flat/falling reward at 20M = aligned FAIL. Eval-side PASS still enforces the full WALKCURR_PF ranking behaviors (slip is priced at eval regardless of the simple training diet).

**verdict**: The centralized-MLP control arm of the 20M simple-velocity wave did not learn to walk: it converges to a static leg-sacrifice stance and dies by a real servo over-current trip every eval episode. Evidence: DR-0 det gate 0/6 (fwd 0.01m/ep at 0.05-0.06 m/s cmd, slip med 5.72 vs cap 3.0, legs [0,4] sacrificed in all 6 det episodes, 24/24 over_current terminations across walk+startjitter det+sto); det frame strip shows zero translation across all 10 frames. Training: reward FELL 200->167 then pinned exactly there while ep_len collapsed 931->397 and terminations/over_current surged 3->~1000/window; walk_speed flat 0.017-0.02 m/s all run. The freeprog litmus escape (-0.025->-0.010) is an ARTIFACT, not discovery: across report windows it correlates POSITIVELY with the over_current surge (r=+0.37) and NEGATIVELY with walk_speed (r=-0.78). Root cause chain: the stride-EMA freeprog income pays ~+0.4/tick to a stationary micro-quiverer (the WALKCURR_SV bank's own tally gave park 202 vs gait 220 - a 9% margin), term_penalty 24 is negligible per-tick so the discounted objective is nearly indifferent to the over_current death, and the 3.5kg mesh plant + loaded servo fit puts the leg-sacrifice stance on a servo current limit - the same mesh-family over_current/leg-sacrifice basin the joystick track closed after refuting current-pricing at 1x/2x/5x across MLP/hist64/transformer. Genuine aligned FAIL per 08-21 (reward falling then flat, task metrics flat/degrading, full 20M acquisition budget) - not a continue case. Wave 2x2 answer: central(1 seed) == decleg(3 seeds), all 4 FAIL with the same signature -> Schilling-style decentralization is refuted as the lever at this diet/budget; the pre-registered ALL-FOUR-pinned fallback fires: operator-named ladder (a) off-policy SAC probe, then (b) Heess terrain diversity. Also recorded: freeprog-escape alone is no longer a valid discovery litmus - future gate text must corroborate with walk_speed and stable ep_len.

