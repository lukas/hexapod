# Agent conventions — prototype_sts3215

## Python commands: use uv

Use `uv` for local Python work in this project. Do not run bare
`python3`, bare `python`, or direct `.venv/bin/python` paths for normal
development commands.

- Scripts: `uv run python path/to/script.py`
- Modules: `uv run python -m package.module`
- Tests: `uv run pytest ...` or `uv run python -m pytest ...`
- Dependencies and venvs: `uv pip ...` and `uv venv ...`

Exceptions are narrow: historical logs/generated run records, vendored
code, and shebangs. Native MuJoCo GUI/viewer launches on macOS are the
special live exception: use `uv run mjpython ...` or the Makefile
viewer wrapper, because Cocoa needs `mjpython`.
The Uno Q is not an exception: its service/deploy path should use
`/home/arduino/.local/bin/uv run python ...`.

## RL orchestrator status URLs

For the autonomous RL agent/orchestrator dashboard, use the public status host
first:

- Human dashboard: `https://hexapod.cwd1f0-new-cluster.coreweave.app/now`
  (token-gated; append `?key=<status-token>` on first visit).
- Agent/LLM index: `https://hexapod.cwd1f0-new-cluster.coreweave.app/llms.txt`
  (no token required).
- Local fallback: port-forward `hexapod-sweep-friction` with
  `kubectl --kubeconfig=$HOME/.kube/coreweave.yaml port-forward hexapod-sweep-friction 8090:8090`
  and open `http://127.0.0.1:8090/now`.

Do not confuse this with the Mac-side robot/sim web hub at
`http://localhost:8898/rl`.

## Local web hub on :8898

The canonical Mac-side browser/control surface is:

```sh
cd ~/hexapod/hexapod_walker/prototype_sts3215
make web-8898-start       # serves http://localhost:8898/rl
make web-8898-status
make web-8898-restart
make web-8898-stop
```

This is a local Mac `launchctl` job that runs
`uv run python -m rl_move.sim.web_server`; it is not an on-robot service.
The script is `sim_viewer/hexapod_web_8898.sh`. It resolves the current
robot IP for the `:8080` target unless `HEXAPOD_HOST` is set. Use this
instead of direct `.venv/bin/python`, ad hoc `nohup`, or a random worktree.

## MuJoCo robot simulation

When asked to run or show the STS3215 robot in MuJoCo, start with
[`sim_viewer/README.md`](sim_viewer/README.md). From this directory, the
canonical foreground MuJoCo + real web UI entrypoint is:

```sh
sim_viewer/sim_web.sh
```

It opens the native MuJoCo viewer and serves the controller at
`https://localhost:8443/rl` (with `http://localhost:8898/rl` as the HTTP
fallback). On macOS it deliberately launches through `uv run mjpython`.
For the one-window interactive policy/gamepad player, use
`sim_viewer/sim_play.sh`.

When asked to show a recent walking checkpoint being driven around, use the
orchestrator wrapper rather than reconstructing the run configuration by hand:

```sh
bash rl_move/orchestrator/ops.sh drivevideo <run-name> \
  --script human_turn --seconds 29 --policy-mode deterministic
```

`drivevideo` resolves or pulls the checkpoint, carries forward the run's own
configuration stack, verifies the full-mesh model, and writes `drive.mp4` plus
its rollout metadata under `logs/manual_drive/` by default.

Every command-bearing MuJoCo render path automatically draws render-only
command cues from `rl_move/sim/command_indicator.py`: green for planar
joystick direction, amber for clockwise/counterclockwise yaw, and blue for
rise/lower. The off-screen/browser integration is in `sim/sim_env.py`; the
native web viewer and direct policy viewer integrations are in
`sim/web_session.py` and `sim/view.py`. The decorations never enter MuJoCo
physics. These commands are simulation-only and require no robot control or
SSH access.

## Robot safety

No physical robot motion unless the user explicitly asks for it in the
current turn. Local checks, deploys, and service restarts are okay when
requested; motion endpoints are not.

For any anomaly during an authorized run, follow
[`EMERGENCY_HANDLING.md`](EMERGENCY_HANDLING.md). In particular, a single
missing servo reply is telemetry noise, not permission to sit or limp. Require
three consecutive incomplete scans with distinct fresh timestamps. Ordinary
camera, recorder, or framework failures stop active motion neutrally and hold
the current stable pose; they do not trigger a posture transition. When the
camera and three fresh telemetry samples are normal, retry the complete failed
step up to twice before ending it.
