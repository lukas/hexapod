# Review record — `l3_belly_rest_radial_shear_hysteresis_repeat6_v1`

Protocol content hash (canonical JSON, `sysid_protocol.protocol_hash`):
**`c3727df8dc7e`**. File sha256
`192a73a2fa054abd9b96be531f5f95c1a21066f53e3a8e393af3f9c11fddac63`.
Reviewed 2026-09-10 for experiment `7b565e2a4be14fd298db47a2c6aaac2b`
(engineering job `ccbdce004d80484ab2f9151917f06e49`).

## Trusted deterministic executor

`POST /api/sysid/run` on the robot web server, accepting `sysid_protocol`
schema version 1 (`linux_control/sysid_protocol.py` +
`linux_control/sysid_runner.py`, the streaming executor with in-loop
current/temperature/tracking/missing-feedback trips and a final limp). This is
the same named executor that ran the L5, L2, L1 and L0 members of this family
byte-exact, and it is byte-identical between this checkout and the revision
currently installed on the robot (`71459673`, deployed 14:48:25Z, branch
`robot-deploy/l0-lease-on-d54d81e4`): `sysid_runner.py`,
`sysid_protocol.py`, `command_lease.py`, `mcu_feetech_bus.py`,
`web_server.py` and `async_bus_guard.py` all compare equal. Runtime
compatibility is therefore reused rather than re-proved, and no deployment is
required for this run.

This is the current evidence that resolves the saved plan's creation-time
`_adaptive_admission.ready: false` — its two stated reasons were that the
proposal "has not proved current runtime compatibility" and "does not yet name
an available trusted deterministic executor". Both are answered above; the
plan's historical parameters are unchanged.

## How it was produced

`sysid/generate_l5_leg_variant.py --leg 3 --strict-independent`, applied to the
already-reviewed `l5_belly_rest_radial_shear_hysteresis_repeat6_v1.json` (the
same route that produced the reviewed L0 and L1 members). The generator moves
the source leg's three joint columns onto leg 3 and asserts every other joint
stays at home; strict-independent was chosen over `--clear-adjacent` because
the saved plan requires the five stationary legs to remain belly-resting.

The saved plan states the derivation as "from `a99ceef28136` by remapping only
the two varying hip/knee command columns to L3 joints 10 and 11".
`a99ceef28136` is the canonical hash of
`l2_belly_rest_radial_shear_hysteresis_repeat6_v1.json`, and the generator only
accepts an `l5_`-named source, so that claim is proved **directly against L2**
rather than by the generator's provenance — see the identity rows below. The
result is the same either way, because the whole family shares one command path.

## Qualification evidence

| Check | Result |
|---|---|
| `sysid_protocol.validate` | `[]` (no findings) |
| Shape | 1 `traj` segment, 1560 rows, 10 Hz, `t_s` 0.0–155.9 → 156.0 s (plan `motion_seconds` 156.0) |
| Moving joints | exactly `{10, 11}` = L3 hip / L3 knee (plan `hip_joint` 10, `knee_joint` 11); the other 16 columns are 0.0 in **every** row |
| First / last row | all-zero (logical zero in, logical zero out) |
| **Commanded path identity vs L2** | L3 `j10`/`j11` columns are **byte-identical** to L2 `j7`/`j8` (and to L5 `j16`/`j17`); `t_s` identical to L2's |
| **Non-trajectory field identity vs L2** | every field except `name`/`description`/`created`/`segments` compares **equal** to L2's — `sysid_protocol` 1, `hz` 10, `home_deg` all-zero (18), `write_speed` 180, `write_acc` 10, `soft_torque` 700, `max_current_a` 0.75, `current_trip_polls` 3, `hard_current_a` 3.0 |
| Hip span | 51.143 deg peak-to-peak (plan: 51.14) |
| Dwell angles | −51.143 / −47.133 / −42.955 deg; centre −47.049, ±4.094 (plan: waypoint −47.133, sweep ±4.09) |
| Hip slew | 15.86 deg/s peak on the ramps, 5.76 deg/s median while moving (family's "~10 deg/s") |
| Foot depth (`geometry_plant.foot_z_mm`) | deepest commanded **−15.00 mm**, and the whole z profile is identical to L2's (plan: 15 mm clearance) |
| Foot radial travel | 252.50 → 192.50 mm, i.e. 60 mm inward — the family's radial shear stroke |
| Floor margin | L5's measured belly-rest contact ramp puts first floor contact at −80.95 mm, so −15.00 mm is 65.95 mm clear; the chassis rests flat and every leg is geometrically identical, so this carries to L3 |
| Tests | `sysid/tests`, `linux_control/test_sysid_protocol.py`, `test_sysid_runner_guards.py`, `test_command_lease.py` → **86 passed**; whole `linux_control` + `sysid` → 415 passed, 5 skipped |

## One qualifier defect found and fixed while reviewing this protocol

The four suites above did **not** start green. `sysid/qualify_repeat_runner.py`
proves a fault injection is covered by grepping
`linux_control/test_sysid_runner_guards.py` for a test *name*, and commit
`71459673`/`66e22bdf` — the debounce of the two pre-motion telemetry gates,
which is the revision now installed on the robot — renamed both of the tests it
was looking for. So `stale_state_timestamp` and `incomplete_servo_sample`
reported `passed: false` while the guards behind them were untouched and in
fact better covered than before. That was a false negative on two safety
interlocks in the one tool that certifies this experiment family's runner, so
it was repaired rather than worked around: the qualifier now references the
current names, and a new test pins the direction that broke (a referenced name
that resolves to no defined test fails, while a legitimate prefix such as the
voltage gate's `..._out_of_bounds` → `..._out_of_bounds_immediately` still
resolves). All eight fault injections now pass.

## Scope

Bounded single-leg characterization from a belly-resting pose. No chassis stand,
no rise, no lower, no learned motion. Only the L3 foot leaves the floor, and it
stays 15 mm clear of it throughout.
