# Robotics projects

This repository contains the current hexapod work plus a small collection of
related robot builds and shared tooling. The hexapod history was extracted
(with full Git history and `exp/*` provenance tags) from the `weird_objects`
monorepo on 2026-08-29.

The top-level `hexapod_walker/` directory is kept intentionally — the RL
orchestrator, Makefiles, and provenance records use repo-root-relative
paths like `hexapod_walker/prototype_sts3215/...`, and preserving the
layout kept the extraction risk-free.

## Project families

- [`hexapod_walker/`](hexapod_walker/) — active hexapods, earlier actuator
  variants, and frozen walker generations.
- [`vehicles/`](vehicles/) — wheeled robot projects that do not share the
  hexapod architecture. The TT-motor kid truck lives here.
- [`tools/`](tools/) — repository-wide utilities used by more than one project.
- [`media/`](media/) — checked-in media referenced by project records.
- [`experiment_lab/`](experiment_lab/) — authenticated robot experiment queue,
  MCP/REST API, evidence recorder, and human results site.

The current robot is
[`hexapod_walker/prototype_sts3215/`](hexapod_walker/prototype_sts3215/): an
18-servo Feetech STS3215 hexapod with CAD, MuJoCo/RL, robot control, and an
AprilTag tracker submodule. Start with that project's `README.md` and
`AGENTS.md`.

`pyproject.toml` and `uv.lock` at the repository root define the ONE Python
environment for the whole repo: `uv sync` creates `.venv`, and `uv run ...`
uses it from any directory. The prototype packages are installed editable,
so `import rl_move` / `import hexapod_core` / the bare-module style used by
`linux_control/` and `motor_setup/` work without `sys.path` shims. `run.sh`
is the script runner the Makefiles use (it syncs the env, then runs a script
from its own directory).

The RL orchestrator's runtime state (ledger, run stories, cycle log) is a
separate repo, `lukas/hexapod-state`, cloned at `.state/` by
`make -C hexapod_walker/prototype_sts3215 state`. See `AGENTS.md`.

After a fresh clone, initialize the tracker submodule:

```sh
git submodule update --init --recursive
```

## Conventions

See `AGENTS.md` (uv, BuildViz, hardware safety) and `.cursor/rules/`
(local dev environment, worktrees, STS3215 hardware safety).
