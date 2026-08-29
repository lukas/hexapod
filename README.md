# hexapod

Hexapod walker robot: CAD, MuJoCo simulation, RL training, and robot
control. Extracted (with full git history and `exp/*` provenance tags)
from the `weird_objects` monorepo on 2026-08-29.

The top-level `hexapod_walker/` directory is kept intentionally — the RL
orchestrator, Makefiles, and provenance records use repo-root-relative
paths like `hexapod_walker/prototype_sts3215/...`, and preserving the
layout kept the extraction risk-free.

## Layout

- `hexapod_walker/prototype_sts3215/` — the current robot (18x Feetech
  STS3215 servos, Arduino Uno Q). CAD, sim, RL, web control, docs.
  Start with its `README.md` / `AGENTS.md`.
- `hexapod_walker/prototype_sts3215/rl_move/` — RL training + the
  CoreWeave orchestrator (`rl_move/orchestrator/`, `RL_PLAN.md`,
  `RL_LOG.md`).
- `hexapod_walker/prototype_v1/`, `prototype_ak40/`, `fullsize_v1/`,
  `rideable_v1/`, `rideable_v2/`, `concepts/` — earlier prototypes and
  design studies.
- `run.sh` / `requirements.txt` — venv-managed script runner used by the
  Makefiles (`../../run.sh` from `prototype_sts3215`).

## Conventions

See `AGENTS.md` (uv, BuildViz, hardware safety) and `.cursor/rules/`
(local dev environment, worktrees, STS3215 hardware safety).
