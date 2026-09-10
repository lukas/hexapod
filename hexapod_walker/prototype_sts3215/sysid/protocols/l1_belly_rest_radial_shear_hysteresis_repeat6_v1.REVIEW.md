# Review record — `l1_belly_rest_radial_shear_hysteresis_repeat6_v1`

Protocol content hash (canonical JSON, `sysid_protocol.protocol_hash`):
**`b1395c85d447`**. Reviewed 2026-09-10 for experiment
`376bea3896674378976e10f045b05bb8` (engineering job
`182326d7c0d64187829fdbdfb1ea29b6`).

## Trusted deterministic executor

`POST /api/sysid/run` on the robot web server, accepting `sysid_protocol`
schema version 1 (`linux_control/sysid_protocol.py` +
`linux_control/sysid_runner.py`, the 25 Hz streaming executor with in-loop
current/temperature/tracking/missing-feedback trips and a final limp). That is
the same named executor that ran the L2 and L5 members of this family
byte-exact on the installed robot revision, so runtime compatibility is
reused rather than re-proved.

## How it was produced

`sysid/generate_l5_leg_variant.py --leg 1 --strict-independent`, applied to
the already-reviewed `l5_belly_rest_radial_shear_hysteresis_repeat6_v1.json`.
The generator moves the source leg's three joint columns onto leg 1 and
asserts that every other joint stays at home; the strict-independent mode was
chosen over `--clear-adjacent` because the saved plan requires the five
stationary legs to remain belly-resting.

## Qualification evidence

| Check | Result |
|---|---|
| `sysid_protocol.validate` | `[]` (no findings) |
| Shape | 1 `traj` segment, 1560 rows, 10 Hz, `t_s` 0.0–155.9 → 156.0 s |
| Moving joints | exactly `{4, 5}` = L1 hip / L1 knee; the other 16 columns are 0.0 in every row |
| First / last row | all-zero (logical zero in, logical zero out) |
| Commanded path identity | L1 j4/j5 columns are **byte-identical** to L5 j16/j17 and to L2 j7/j8 — the same reviewed command path, only remapped |
| Hip span | 51.143 deg peak-to-peak (plan: 51.14) |
| Dwell angles | −51.143 / −47.133 / −42.955 deg; centre −47.049, ±4.094 (plan: waypoint −47.133, sweep ±4.09) |
| Hip slew | 15.86 deg/s peak on the ramps, ~5.8 deg/s median (family's "~10 deg/s") |
| Foot depth (`geometry_plant.foot_z_mm`) | deepest commanded **−15.00 mm**, identical to L2 and L5 (plan: 15 mm clearance) |
| Floor margin | L5's measured belly-rest contact ramp puts first floor contact at −80.95 mm, so −15.00 mm is 65.95 mm clear; the chassis rests flat and every leg is geometrically identical, so this carries to L1 |
| Guards | `soft_torque` 700, `max_current_a` 0.75 over 3 polls, `hard_current_a` 3.0 — unchanged from L2/L5 |
| Tests | `sysid/tests`, `linux_control/test_sysid_protocol.py`, `test_sysid_runner_guards.py`, `test_command_lease.py` → 82 passed |

## Scope

Bounded single-leg characterization from a belly-resting pose. No chassis
stand, no rise, no lower, no learned motion. Only the L1 foot leaves the
floor, and it stays 15 mm clear of it throughout.
