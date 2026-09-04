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

`run.sh` and `requirements.txt` at the repository root provide the shared
Python runner used by the hexapod Makefiles.

After a fresh clone, initialize the tracker submodule:

```sh
git submodule update --init --recursive
```

## Conventions

See `AGENTS.md` (uv, BuildViz, hardware safety) and `.cursor/rules/`
(local dev environment, worktrees, STS3215 hardware safety).
