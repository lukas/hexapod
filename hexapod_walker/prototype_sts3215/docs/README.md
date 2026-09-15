# STS3215 design documents

Mechanical design, CAD, BOM, printing and BuildViz moved to their own repo on
2026-09-15: https://github.com/lukas/hexapod-cad (`PROTOTYPE.md` there is the
build entry point). This directory keeps the robot-side notes that code or the
orchestrator still reference.

- [`../JOINT_COORDINATES.md`](../JOINT_COORDINATES.md) — joint signs, frames,
  and pose conventions shared by CAD, simulation, and control; the executable
  form is `hexapod_core/joint_frame.py`.
- Dated `*_2026-09-*.md` notes here are referenced from tracks or code; new
  journal entries go to the state directory (`RL_LOG.md`, `CURRENT_TRUTHS.md`,
  `rl_docs/meta/`), not here.

## Other work areas

- [`../rl_docs/README.md`](../rl_docs/README.md) owns RL campaign
  documentation.
- [`../linux_control/README.md`](../linux_control/README.md) owns robot-control
  and deployment documentation.
- [`../hexapod-tracker/README.md`](../hexapod-tracker/README.md) owns camera,
  AprilTag, and perception documentation in its standalone submodule.
- Frozen handoffs and historical status snapshots were retired from the tree
  2026-09-14; use git history. Do not treat archived status files as current truth.
