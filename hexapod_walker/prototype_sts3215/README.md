# Hexapod STS3215 prototype

Tabletop 3D-printed hexapod driven by Feetech STS3215 bus servos and an
Arduino Uno Q. The work is split into four areas that share the robot; start
at the entry point for the one you're working on:

| You are here to… | Start at |
|------------------|----------|
| Design/print/assemble the robot (CAD, BOM) | [`PROTOTYPE.md`](PROTOTYPE.md) |
| Run the physical robot (firmware, control, safety) | `firmware/`, `linux_control/`, `rl_move/API.md` — **read the hardware-safety rules in the repo root `AGENTS.md` first** |
| Train it in simulation (RL campaign + autonomous agent loop) | [`RL_GOALS.md`](RL_GOALS.md) — the two goals in plain English; then [`rl_docs/README.md`](rl_docs/README.md) (doc index), `RL_PLAN.md`, `RL_LOG.md` |
| Track it with cameras and AprilTags | [`hexapod-tracker/README.md`](hexapod-tracker/README.md) — standalone submodule with its own package, configs, UI, tests, and agent instructions |

## Status URLs

- Agent/orchestrator dashboard:
  `https://hexapod.cwd1f0-new-cluster.coreweave.app/now`
  (token-gated).
- Agent/LLM-readable status index:
  `https://hexapod.cwd1f0-new-cluster.coreweave.app/llms.txt`
  (no token).
- Local robot/sim control UI:
  `http://localhost:8898/rl`
  via `make web-8898-start`.

## Layout

| Path | What |
|------|------|
| `hexapod_prototype.py` | Parametric constants + trimesh twins (probes, MuJoCo, BuildViz) |
| `cad_step_test/build_step_first_test.py` | Printable BREP builders (STEP-first geometry source) |
| `build_step_prototype.py` / `step_pipeline.py` | Print-set exporter + equivalence gates / shared plumbing |
| `design_spec.yaml` | Human-readable geometry contract |
| `build_all.py` / `Makefile` | Regenerate STEP + STLs + common targets |
| [`docs/`](docs/) | Maintained design-document index: BOM, CAD workflow, BuildViz, and variant notes |
| `concepts/` | Isolated mechanical and sensing experiments; see the [`concept catalog`](concepts/README.md) before choosing a variant |
| `scripts/` | CLI helpers (verify helpers, renders, print orientation, inspect) |
| `tools/` | Hexapod-specific BuildViz and diagnostic utilities; shared utilities live at the repository root `tools/` |
| `step_prototype/` | Per-printable `.step` CAD truth + BREP tessellations + manifest |
| `stl_prototype/` | Slicer-ready printables (healed BREP tessellations) |
| `stl_reference/` | Sim / viz meshes (not for printing) |
| `firmware/` / `linux_control/` / `motor_setup/` | On-robot software |
| `hexapod-tracker/` | Git submodule containing AprilTag tracking, camera server/UI, configs, and off-robot vision tests |
| `full_robot_viz/` | BuildViz scene + local `buildviz` npm dep |
| `rl_docs/` | RL campaign docs index: goal, operator wishlist, commands, log conventions |
| `RL_PLAN.md` / `RL_LOG.md` | Current RL plan + condensed campaign history (full history in `archive/`) |
| `rl_move/` | RL code: `sim/` (MuJoCo/MJX envs + training), `orchestrator/` (autonomous loop: watcher, launcher, guardrails), robot-side control |
| `logs/` | Eval artifacts + per-experiment summaries (`logs/experiments/<run>/`) |
| `archive/` | Dated reviews, rulings, full plan/log history — search, don't read |

## Quick commands

Local Python convention: use `uv run python ...` or `uv run python -m ...`;
do not copy old bare `python3` examples from logs/archive. The repo-root
`AGENTS.md` and this project's `AGENTS.md` record the rule. Native
MuJoCo GUI/viewer launches on macOS are the special exception: use
`uv run mjpython ...` or the Makefile viewer targets.

After a fresh clone, initialize the tracker with `git submodule update --init`.

```sh
make -C hexapod_walker/prototype_sts3215 help
make -C hexapod_walker/prototype_sts3215 build
make -C hexapod_walker/prototype_sts3215 verify-fast
make -C hexapod_walker/prototype_sts3215 robot-check       # safe local robot/web checks
make -C hexapod_walker/prototype_sts3215 robot-deploy      # check + SSH deploy + remote health
make -C hexapod_walker/prototype_sts3215 web-8898-restart  # Mac hub: HTTPS :8443 + HTTP :8898
```

Robot-control dev loop details live in `linux_control/README.md` and
`linux_control/dev_loop.sh`. Use `robot-resolve` for a temporary IP when
`hexapod.local` is flaky; do not commit fixed board IPs.

The canonical local browser/control surface is `make -C
hexapod_walker/prototype_sts3215 web-8898-start`. It runs on the Mac via
`uv run`, manages a `launchctl` job, dynamically resolves the robot's
`:8080` service unless `HEXAPOD_HOST` is set, and serves
`https://localhost:8443/rl` for gamepad access, with the legacy
`http://localhost:8898/rl` still available. Accept the self-signed certificate
warning once. Use `web-8898-status`, `web-8898-restart`, `web-8898-stop`, and
`web-8898-logs` for operations.
