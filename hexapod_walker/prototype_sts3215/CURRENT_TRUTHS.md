# CURRENT TRUTHS - accepted facts and rulings

Last compacted: 2026-08-30 for the `todaypolicy` sixth-track update.
Archive copy: `archive/CURRENT_TRUTHS_2026-08-30_pre_todaypolicy_compaction.md`.
Accepted facts, not narrative. If old prose disagrees, this file wins.

## Mission
Six registered tracks live in `rl_move/orchestrator/tracks.json`:
- `joystick`: RL from scripted gait to joystick control.
- `amp`: from-scratch AMP program; done at MuJoCo transfer M5.
- `cpg`: direct low-dimensional CPG/SE2 controller search.
- `walkcurr`: prior-free PPO walking; no BC, gait clock, or motion prior.
- `standwalk`: keep trying for ONE mesh/100 Hz policy that can sit,
  rise, joystick-walk, and lower.
- `todaypolicy`: deliver a useful policy-controlled MuJoCo/controller
  bundle today. It may compose policy+state pieces and does not mark
  `standwalk` green.
Out-of-scope operator runs get honest triage but no agent follow-ups.

## Today Answer
- DELIVERED 2026-08-30: `todaypolicy-mlpsf-tuck-v1` packaged, all TODAY
  bars PASS on a fresh controller-side full-mesh regen; GO for
  controller handoff. Durable evidence + GO/NO-GO + selector path:
  `rl_docs/tracks/todaypolicy/bundle_mlpsf_tuck_v1/`.
- Bundle candidate: `todaypolicy-mlpsf-tuck-v1`.
- Stand/lower role: scripted tuck by default; compare learned
  `stand_stancemix_tuckclock_scratch8m{,_s1}` when useful.
- Walk role: `cw-walk-allheading-mlp-singleframe-acq1-stdanneal`,
  exported as `linux_control/policies/walk_allheading_mlp_singleframe_acq1_stdanneal.json`.
- Full-mesh evidence:
  `logs/manual_drive/cw_walk_allheading_mlp_singleframe_stdanneal_hybrid_tuck_ux_human28/`
  had zero falls, no sacrificed legs, `walk_progress_ratio=0.418`,
  `course_err_1s_med_deg=2.57`, `wrong_course_frac_1s=0.0`,
  `cur_max_a=2.64`. Verdict: stable and directionally obedient, but
  speed-soft.
- Upgrade candidate: `cw-walkteach-scripted-allhead-acq12m{,-s1}` is
  running for better all-heading joystick authority.

## Model And Control Contracts
- New PPO/MJX launches use mesh-family 100 Hz unless a registered
  legacy exception says otherwise.
- Checkpoints started before the 2026-08-24 mesh flip are
  primitive-family 25 Hz policies. Do not warm-start or evaluate them
  as mesh/100 Hz unless explicitly proven.
- `control_hz` metadata must match the runner; missing metadata means
  legacy 25 Hz. Policies output 18 raw joint targets through SafetyLayer.
- Long PPO acquisition launches should set `--log-std-final` from the
  start; uncapped `train/std` repeatedly ruined stochastic rollouts.

## Run Interpretation
- Video and gate eval outrank reward alone.
- Compare reward trend to gate/eval trend before spending more. Rising
  reward with flat/bad eval means audit reward, eval, simulator, or
  tooling before same-recipe seed sweeps.
- Bad eval with both reward and eval improving may justify continuation.
- Known exploit on video is a metric/tooling bug to repair, not a
  lineage kill by itself.

## Known Tooling Gotchas
- Recurrent checkpoints must use `rl_move.sim.gru_policy.RecurrentPredictor`;
  raw per-tick `model.predict(obs)` resets hidden state.
- Some post-2026-08-24 100 Hz evals before the `pod_eval.py` fixes may
  have wrong timeout or slew-contract evidence; re-run suspicious gates.
- Train pods have non-uniform `/dev/shm`; route obs-heavy launches to
  4.0G pods or let `_check_shm_budget` refuse them.

## Real Robot Boundary
- The robot is operator-owned. No physical motion without an explicit
  current-turn operator ask.
- For web/control code only, use HTTP/dev-loop helpers:
  `make robot-check`, `robot-unit-check`, `robot-status`, `robot-deploy`.

## Startup And Status
- Orchestrator dashboard: `https://hexapod.cwd1f0-new-cluster.coreweave.app`.
- Startup packet: `STATUS.md`, this file, `RL_PLAN.md`, the relevant
  `rl_docs/tracks/<track>/STATUS.md`, `RESEARCH_RULES.md`,
  `RUN_INTERPRETATION_RULES.md`, and `rl_docs/COMMANDS.md`.
- Budgets: `STATUS.md` <=100 lines, track STATUS <=120,
  `RL_PLAN.md` <=150, this file <=80. Long audits go to `archive/`.
