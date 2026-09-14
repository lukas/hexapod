# Agent conventions — prototype_sts3215

The repo-root `AGENTS.md` governs everything here: subtract first, goals
(`RL_GOALS.md`, `RL_PLAN.md`), worktrees, `uv`, tests, standing authorization
and hardware safety (`EMERGENCY_HANDLING.md`; before a new recovery routine also
`RECOVERY_LESSONS.md` and `linux_control/ROBOT_OBSERVE.md`). Orchestrator state lives in
`.state/` (`rl_move/orchestrator/state_dir.py`), not in this tree.

## MuJoCo robot simulation

Start with [`sim_viewer/README.md`](sim_viewer/README.md). From this
directory, the canonical foreground MuJoCo + web UI entry point is:

```sh
sim_viewer/sim_web.sh
```

It opens the native MuJoCo viewer and serves the controller at
`https://localhost:8443/rl` (`http://localhost:8898/rl` as the HTTP fallback),
launching through `uv run mjpython` on macOS. The one-window interactive
policy and gamepad player is `sim_viewer/sim_play.sh`.

To show a recent walking checkpoint being driven, use the orchestrator
wrapper rather than reconstructing the run configuration by hand:

```sh
bash rl_move/orchestrator/ops.sh drivevideo <run-name> \
  --script human_turn --seconds 29 --policy-mode deterministic
```

`drivevideo` resolves the checkpoint, carries the run's own configuration,
verifies the full-mesh model and writes `drive.mp4` under `logs/manual_drive/`.

Command-bearing render paths draw render-only cues from
`rl_move/sim/command_indicator.py` (green planar direction, amber yaw, blue
rise/lower); they never enter the physics.
