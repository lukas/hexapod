# Physical robot registry

This directory records how each named physical robot is actually assembled.
It is separate from `design_spec.yaml`, which describes the latest CAD. A
physical robot may remain on an older or mixed revision.

## Robots

- [`hexapod-1.yaml`](hexapod-1.yaml) — original/legacy STS3215 assembly.

## Active diagnostics

- [`hexapod-1 joint-flex localization`](experiments/hexapod-1-joint-flex/README.md)
  — two-camera, static-load protocol for separating servo, horn/screw, yoke,
  and femur compliance.

## Recording rules

- `confirmed`: directly reported or physically checked on that robot.
- `inferred`: reconstructed from matching historical CAD; verify before
  buying parts or assuming interchangeability.
- `unknown`: not yet inspected or associated with this robot.
- Planned parts and experiments are never recorded as installed hardware until
  installation is explicitly confirmed.
- Robot-wide `defaults` apply to all six legs unless a key in
  `per_leg_overrides` says otherwise. Use leg IDs `L0` through `L5`.
- Append dated history entries rather than erasing an earlier assembly state.

