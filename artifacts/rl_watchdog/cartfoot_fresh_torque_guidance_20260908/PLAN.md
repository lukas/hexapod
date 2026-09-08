# Fresh scratch seed7 fixed1x torque canary — frozen plan, 2026-09-08 (published before 08:01 UTC)

## Question and allocation
Does the fresh-learning Cartesian policy retain acquired walking when the EASY torque multiplier is removed, and how does it compare with the matched joint-space control? Run one matched seed7 canary pair, 2,000,000 additional requested steps per arm (normal rollout rounding recorded). This is an independent 4M-step hypothesis, not a refill of an old cycle's exhausted budget.

Use each arm's frozen 40M acquisition checkpoint:
- ON: cw-walkscratch-easy0905-cartfoot-freshinit-c1-s7-acq1
- OFF: cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s7-acq1
- Checkpoints are the corresponding ppo_goal_<underscore_run>.zip under rl_move/sim/policies.

Suggested unique children: append -torque1x-c1 to each exact source run. Before queuing, check ledger/backlog/live owners for duplicates and freeze each actual source SHA256, effective configuration and model provenance. Use launch_run.py respec/ops and normal capacity/lease/budget guards.

Change only dr.torque_scale=3,3 to dr.torque_scale=1,1. Keep seed7, each own checkpoint, PPO settings, rewards, Cartesian ON extents .06/.035/.04, OFF without those keys, fixed forward .06m/s, all noise/DR settings and the existing motor limits. Plain warm start preserves the saved policy's activation; do not reinitialize or transplant architecture. Prior-free lineage remains free of teacher/BC/gait clock/learned prior; the static analytic IK decoder is unchanged.

## Frozen evaluation and read
Before any result-based decision, register these exact rules in each run's gate. Evaluate the existing four panels (walk deterministic/stochastic, walk_startjitter deterministic/stochastic), six episodes each, using unchanged evaluator flags/episode logic and the same seeds/settings as the source gate. Also evaluate each frozen parent at the identical 1x configuration with zero further training; these CPU baselines may run alongside PPO. They distinguish zero-shot torque sensitivity from adaptation. Do not wait for all long videos as a new training-approval gate.

Measured 3x source counts are ON23/24 and OFF19/24, not24/24. Per-panel counts are ON6/6/5/6 and OFF6/6/1/6. Both have zero terminations. OFF already sacrifices leg4 in five deterministic jitter episodes; ON does so once. Exact reports are in ../cartfoot_easy_acquisition_read_20260908/.

- Health retained: zero terminations across24, median net forward >=.03m/s in at least one ordinary walk panel, and gait_valid >=own3x source count (ON23, OFF19), with no new recurring sacrificed-leg pattern. Define a new recurring pattern as a leg sacrificed in >=3/6 episodes of a panel where that same leg was sacrificed in <3/6 source episodes. Report every leg/panel count, including existing chronic deficits; do not hide them behind a PASS label.
- Negative health read: any termination or loss of the existing acquisition movement floor. If only ON fails while OFF retains health, this supports a differential Cartesian sensitivity in this seed/recipe.
- Partial: movement and no-term conditions hold but gait retention or the recurring-leg condition fails. Record exact affected episodes; no promotion or automatic extension.
- Separate slip hypothesis: report all four mean slip/m panels for source3x, zero-shot parent1x, and trained child1x. Show each child's change from its own zero-shot1x parent and trained ON/OFF ratios. Ratio <=1.2 in >=3/4 panels supports slip parity; missing that target does not alone mean torque removal failed. Report forward-speed costs, current, normalized reward trajectory, and actual non-log-std weight movement.
- Audit realized randomization/reset summaries and any RNG divergence after early termination. Same panel seed alone is not proof of identical full states. Do not claim a training gain from zero-shot transfer, or full draw parity from summary fields.

Close this finite2M read after comparison. No automatic40M continuation, extra seed, dose grid, inherited retrofit1.5/3x thresholds, altered reward or reduced success requirements. A later bounded extension needs a new recorded hypothesis from this result.

## Why this dose and why now
The exact fresh seed7 source pair meets its acquisition movement gate, zero terminations, and ON/OFF mean-slip ratios .988/.944/.979/.950. Current seed11 replication is also being independently reviewed. This avoids retrying the failed entrenched-policy Cartesian retrofit.

The historical torque ladder established a meaningful1x floor: rl_docs/runs/cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-torquefade1x-c1.md and ...torquefade1x-c1-acq1.md record24/24 gait and zero falls at canary/full40M, with slip/forward costs. Those are a different lineage, so justify the dose rather than predict a pass here. The old canary's prose claims zero retraining despite a2M allocation; do not reuse that prose as proof of zero-shot transfer. This new protocol records explicit frozen-parent1x baselines.

Depth owners remain separate:073301/074330 placed the seed7 unchanged3x +10M pair, both actually progressed and finished10,485,760;075357 owns seed11 unchanged3x depth continuation. Leave their runs and future seed10 triage untouched. The fixed1x source is the frozen40M parent, not a moving50M checkpoint.

## Scope
1x torque removes one idealization. EASY still uses4096 write speed/1000 acceleration/3.6deg per tick, safety.max_current_a=100, no sensor noise, fixed-forward commands and the MJX twin. This is not realistic motor/joystick/yaw or hardware qualification. The separate assisted contract is400/20/.375deg per tick with350counts/s velocity ceiling and2.5A current limit;350 is not current. No physical trials are authorized by this plan.

The latest assisted coordinated steering screen remains STOP: no tested global dose passed both yaw directions with retention. No steering PPO follows from its one-sign signal. A different state/support-conditioned mechanism requires a separate evidence-backed design.
