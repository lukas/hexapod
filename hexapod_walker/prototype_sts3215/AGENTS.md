# Agent conventions — prototype_sts3215

## Two parallel walking goals

Read [RL_GOALS.md](RL_GOALS.md) for purpose and priorities and
[RL_PLAN.md](RL_PLAN.md) for the operating plan. `any_means` delivers smooth
physical joystick walking using any effective method so physical builds
progress now. `rl_only` targets the same result with walking learned entirely
through RL, with no demonstrations anywhere in the policy's training lineage.
Teacher/BC/AMP/assisted methods serve `any_means`. Both goals proceed in
parallel. Each also requires an interactive joystick sim demo, viewable video
and reproducible launch path; report sim and physical readiness separately.
Simulation or method PASS does not establish physical completion.
Root `AGENTS.md` still governs observed, bounded hardware work and ownership.

## Python commands: use uv

Use `uv` for local Python work in this project. Do not run bare
`python3`, bare `python`, or direct `.venv/bin/python` paths for normal
development commands.

- Scripts: `uv run python path/to/script.py`
- Modules: `uv run python -m package.module`
- Tests: `uv run pytest ...` or `uv run python -m pytest ...`
- Dependencies: edit the repo-root `pyproject.toml`, then `uv lock` and
  `uv sync`. The venv is `<checkout>/.venv`; never `uv pip install` into it.

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

## Tests

`make test-fast` (parallel, skips `slow`) is the default loop; `make test`
runs everything. Rules for adding tests are in `RESEARCH_RULES.md`
"Tests" — under 5 s, mechanics only, mesh model via monkeypatch, no
generated artifacts, `rl_move/tests/` only, `main` green. Do not recreate
the retired `test_task_semantics.py` rollout bank.

## Orchestrator state is in `.state/`, not here

Ledger, launch queue, run stories, `RL_LOG.md`, and the machine-written
journals (`rl_docs/SKILLS.md`, `rl_move/orchestrator/OPERATOR_QUESTIONS.md`,
`rl_docs/tracks/*/STATUS.md`) live in the separate `lukas/hexapod-state`
repo, cloned at `<checkout>/.state` (`make state` here refreshes it). The
paths with those names in this tree are read-only symlinks into it; edit
the `.state/...` path. Details: `rl_move/orchestrator/state_dir.py` and the
repo-root `AGENTS.md`.

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
step; every step gets 3 attempts.

An actual tip, brownout, hot motor, jam, surprise force, or hard/sustained
current event stops the motion and then goes through the same 30-second
assessment as everything else: wait 30 s, take three fresh samples plus a
camera frame, and retry from a verified safe pose if the fault is gone. A hot
motor extends the wait until it reads cool. Excessive tilt that the camera
shows as level, or that a `sit` re-levels, is recoverable. Request hands-on
correction only when the fault is still present after 3 attempts. The root instructions' supported
single-joint grounded-current retry exception still applies. Ordinary deployment,
telemetry recovery, and bounded repeats do not need another permission question.
