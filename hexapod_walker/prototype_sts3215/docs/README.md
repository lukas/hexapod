# STS3215 design documents

This directory is the maintained index for mechanical-design documentation.
Generated reports and historical campaign notes belong elsewhere; follow the
ownership map below before adding another top-level Markdown file.

## Production design

- [`../PROTOTYPE.md`](../PROTOTYPE.md) — current mechanical design, build
  workflow, printing, and assembly entry point.
- [`BOM.md`](BOM.md) — production bill of materials and generated fastener
  table.
- [`CAD_WORKFLOW.md`](CAD_WORKFLOW.md) — STEP-first source-of-truth and export
  workflow.
- [`CAD_AGENT_INSTRUCTIONS.md`](CAD_AGENT_INSTRUCTIONS.md) — constraints for
  agents editing production CAD.
- [`../JOINT_COORDINATES.md`](../JOINT_COORDINATES.md) — joint signs, frames,
  and pose conventions shared by CAD, simulation, and control.

## Visualization and variants

- [`BUILDVIZ.md`](BUILDVIZ.md) — current full-robot BuildViz contract and
  publish flow.
- [`CHORN_VARIANT.md`](CHORN_VARIANT.md) — C-horn variant notes that still
  apply to the production design.
- [`../concepts/README.md`](../concepts/README.md) — catalog of isolated
  mechanical and sensing experiments.

## Other work areas

- [`../rl_docs/README.md`](../rl_docs/README.md) owns RL campaign
  documentation.
- [`../linux_control/README.md`](../linux_control/README.md) owns robot-control
  and deployment documentation.
- [`../hexapod-tracker/README.md`](../hexapod-tracker/README.md) owns camera,
  AprilTag, and perception documentation in its standalone submodule.
- [`../archive/README.md`](../archive/README.md) explains frozen handoffs and
  historical records. Do not treat archived status files as current truth.
