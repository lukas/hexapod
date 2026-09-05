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

## Robot safety

The user grants standing authority for bounded physical experiments,
necessary deployment (including relevant firmware), and routine recovery within
an active robot task without repeated authorization questions. Work in the
known test area with live observations and an available abort path. This does
not authorize unrelated work or motion in an unknown, unobserved environment.
Use HTTP for robot control and the documented deployment/service helpers for
necessary updates. Do not change unrelated firmware or CAD as a side effect.

A live camera view plus three distinct fresh healthy telemetry samples counts
as supervision and inspection for routine motion and recovery when it establishes
normal pose and state. Request hands-on help only when those observations are
unavailable or inconclusive, or when they show a persistent condition that
actually requires physical correction.

Establish correct logical zeros, live servo feedback, and basic joint control
before loaded motion; once established, proceed within the active task without
an additional operator-request gate. This standing authority supersedes older
per-turn permission wording in project runbooks; their technical checks and
emergency responses still apply.

For any anomaly during an authorized run, follow
[`EMERGENCY_HANDLING.md`](EMERGENCY_HANDLING.md). In particular, a single
missing servo reply is telemetry noise, not permission to sit or limp. Require
three consecutive incomplete scans with distinct fresh timestamps. Ordinary
camera, recorder, or framework failures stop active motion neutrally and hold
the current stable pose; they do not trigger a posture transition. When the
camera and three fresh telemetry samples are normal, retry the complete failed
step up to twice before ending it.

An actual tip, brownout, hot motor, jam, surprise force, or hard/sustained
current event requires a stop and fresh inspection before retry. A conclusive
camera view plus recovered electrical, thermal, pose, and motor telemetry may
clear the event remotely; request hands-on correction only when the condition
persists or the evidence remains inconclusive. The root instructions' supported
single-joint grounded-current retry exception still applies. Ordinary deployment,
telemetry recovery, and bounded repeats do not need another permission question.
