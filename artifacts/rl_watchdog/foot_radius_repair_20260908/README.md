# Foot-radius compilation repair

Base: `5dcd8b50eded965827c2c9be272ff99e44c754fa`. The original failing helper is reproduced from `e56e535f48ea53a096b7ddfed525839880d948ec` in `baseline_failure.json`.

A positive diagnostic radius now changes the sphere geometry in an `MjSpec` and compiles a new model before private data creation or shared-model device conversion. The original compiled body masses, principal inertias and inertial frames are retained as explicit inertials. Friction, contact parameters, calibration and the default-off path remain unchanged. This uses MuJoCo's supported [model editing and compilation workflow](https://mujoco.readthedocs.io/en/stable/programming/modeledit.html), rather than repairing individual collision caches.

The old runtime setter intentionally rejects positive changes. Shared environment shims accept the prepared model without mutation after checking sphere type, radius, bounding sphere and AABB; the old size-only model is rejected. The upstream shared host and all three vector/sharded callers remain connected through the existing parameter.

## Evidence

- The exact old helper changed size to 12 mm but left 4.5 mm collision bounds. At a sphere center height of 10 mm it reported zero contacts, even after `mj_setConst`. The repaired compile reports one contact at distance −2 mm.
- 28 focused tests passed, 49 deselected, in 1.04 s on local MuJoCo 3.12.0. They include independently compiled collision references for plane, box and sphere surfaces at three radii, BVH/bound comparisons, inertial/friction preservation, invalid input/shape rejection, and private/shared constructor integration.
- Omitted radius and explicit zero have exactly equal model arrays and 20-step observation, reward, termination, position and velocity traces for primitive and mesh-MJX models.
- The exact new compiler helper also ran in memory on controller MuJoCo 3.11.0: one contact at −2 mm, with exact mass, inertia and friction equality. `cloud_api_smoke.json` records this compatibility check. No active controller source or workload was modified.

The command and count are in `tests.json`. The source test module is `hexapod_walker/prototype_sts3215/rl_move/tests/test_foot_geom_radius.py`.

## Scope and interpretation

Only named sphere feet are supported; missing targets, unsupported shapes, nonfinite/negative radii and `fusestatic` are rejected. Shared validation checks the normal precompiled caller contract; it does not repair arbitrary externally mutated models. No full policy assay, GPU qualification or hardware calibration was performed. This repair authorizes no new training or physical experiment.

Suggested correction for the earlier probe record: “The size-only radius probe is invalid because collision caches retained the old 4.5 mm bounds. A correctly compiled radius changes contact geometry and contact locations; it does not multiply fixed torsional or rolling friction coefficients by radius. Those coefficients already have length units. Treat a repaired rerun as simulation geometry sensitivity, not hardware calibration or qualified policy improvement.” The coefficient units are specified in MuJoCo's [contact model documentation](https://mujoco.readthedocs.io/en/stable/computation/index.html#contact). Preserve the old raw output as the failed-method receipt; a finite rerun is needed before interpreting its behavior.
