# FLIP_LAB - MuJoCo-only flip/righting feasibility

`rl_move.sim.flip_lab` is a simulation harness for the flip question. It
does not touch robot hardware. It loads the campaign MuJoCo plant, fitted
servo parameters, contact softening, and the control-slew contract, then
runs:

- `impulse`: external roll-torque sweep from the plant stance. This maps
  the physics barrier: how much torque produces 90/120/180 degrees of body
  tilt under the current contact and mass model.
- `search`: cross-entropy search over an explainable side-roll joint
  program: tuck the roll-side legs, brace/kick the opposite legs, coast,
  and see whether the body reaches/stays inverted without relying on
  impossible current or violent contact.
- `rock-search`: repeated leg-only side rocking. Use `--start-pose rock`
  with an initial tilt window when testing a real side-rest start instead
  of a tilted no-settle continuation.
  `--goal side-to-side` scores signed side transfer: one side down at the
  start, the opposite side down at the end.

`flipped` is only the kinematic fact that the chassis passed through an
inverted attitude. `realistic_flipped` is the useful claim: no MuJoCo
warnings, no direct body-assist torque, peak/sustained current inside the
robot safety envelope, and bounded contact/body velocities.
For side-to-side trials, `side_z` distinguishes which side is down:
negative and positive signs are opposite sides. `side_swapped` requires a
strong side-rest start, a strong opposite-side finish, and a final tilt near
90 degrees rather than upright or inverted.

Example:

```bash
uv run python -m rl_move.sim.flip_lab impulse \
  --source mesh_mjx \
  --torque-nm 0,1.5,2.5,3.5,4.5,6.0 \
  --out logs/flip_lab/impulse_mesh_mjx.json

uv run python -m rl_move.sim.flip_lab search \
  --source mesh_mjx \
  --iterations 4 \
  --population 16 \
  --out logs/flip_lab/search_mesh_mjx.json

uv run python -m rl_move.sim.flip_lab search \
  --source mesh_mjx \
  --iterations 2 \
  --population 8 \
  --assist-torque-nm 8 \
  --out logs/flip_lab/search_mesh_assisted_8nm.json \
  --video logs/flip_lab/search_mesh_assisted_8nm.mp4

uv run python -m rl_move.sim.flip_lab rock-search \
  --source mesh_mjx \
  --write-speed 1500 \
  --write-acc 80 \
  --servo-vel-max-counts-s write_speed \
  --max-delta-q-deg 8 \
  --iterations 8 \
  --population 32 \
  --total-s 10 \
  --out logs/flip_lab/rock_mesh_raise_flat.json \
  --video logs/flip_lab/rock_mesh_raise_flat.mp4

uv run python -m rl_move.sim.flip_lab rock-eval \
  --source mesh_mjx \
  --candidate logs/flip_lab/rock_mesh_side_start_80.json \
  --start-roll-deg 80 \
  --settle-s 0 \
  --write-speed 1500 \
  --write-acc 80 \
  --servo-vel-max-counts-s write_speed \
  --max-delta-q-deg 8 \
  --real-sustained-current-a 3.0 \
  --max-real-over-current-s 30 \
  --max-real-lin-vel 1.5 \
  --total-s 6 \
  --out logs/flip_lab/rock_mesh_side_start_80_confirmed.json \
  --video logs/flip_lab/rock_mesh_side_start_80_confirmed.mp4

uv run python -m rl_move.sim.flip_lab rock-search \
  --source mesh_mjx \
  --start-pose rock \
  --start-roll-deg -90 \
  --settle-s 2 \
  --goal invert \
  --write-speed 1500 \
  --write-acc 80 \
  --servo-vel-max-counts-s write_speed \
  --max-delta-q-deg 8 \
  --real-sustained-current-a 3.0 \
  --max-real-over-current-s 30 \
  --max-real-lin-vel 1.5 \
  --min-real-initial-tilt-deg 75 \
  --max-real-initial-tilt-deg 125 \
  --iterations 10 \
  --population 36 \
  --total-s 8 \
  --out logs/flip_lab/rock_mesh_side_rest_to_invert_strict.json
```

Initial mesh-MJX smoke findings, 2026-08-26:

- A 1 s external side-roll pulse at 6 N*m tilted only about 9 degrees.
- A 1 s external side-roll pulse at 8 N*m reached and stayed inverted
  in this MuJoCo twin, but the richer diagnostics mark it outside the
  believable envelope: about 32 rad/s body spin and about 1179 N peak
  contact force.
- A small leg-only CEM run, 4 iterations x 16 candidates, found a clean
  25 degree tilt but no flip.
- The same CEM shape with an 8 N*m assisted roll pulse found a clean
  inverted result, no MuJoCo warnings, `final_up_z=-0.983992`. This is
  not a realistic maneuver because the chassis received external body
  torque and contact/spin were too high; it is only an energy-threshold
  diagnostic.
- A stricter leg-only CEM run, 8 iterations x 32 candidates over 5.5 s,
  found a realistic best candidate but only reached about 25.2 degrees of
  tilt. Current conclusion: this open-loop side-roll family has not found
  a believable upside-down flip.
- `rock-search` adds a repeated leg-only rocking program and an optional
  all-leg pre-raise. With the faster real write profile used by the gait
  verifier (`write_speed=1500`, `write_acc=80`, velocity ceiling tied to
  write speed), a flat start still only reached about 31-35 degrees of
  tilt in mesh-MJX.
- From an 80 degree side-start, `rock-eval` confirms a leg-only continuation
  that rolls through to inverted: `roll_gain_deg=99.938`,
  `final_up_z=-0.931892`, no MuJoCo warnings, no external body torque,
  peak contact about 411 N, peak body angular velocity about 8.7 rad/s.
  This is a real side-roll continuation hypothesis, not a flat-ground
  self-flip. It is also not the same as starting from a settled side-rest.
- From a settled side-rest (`--start-pose rock --start-roll-deg -90
  --settle-s 2` with an accepted initial tilt window of 75-125 degrees),
  the best current leg-only inversion starts at `initial_tilt_deg=83.145`,
  reaches `max_tilt_deg=179.859`, and finishes inverted with
  `final_up_z=-0.965342`. It uses no external body torque, has no MuJoCo
  warnings, and stays inside the current and body angular velocity limits.
  It is still not marked `realistic_flipped` because peak contact is about
  747 N, above the current 450 N impact gate. A stricter contact-aware
  search found low-impact side-rest motions, but those fell back upright
  instead of flipping.
- A broader open-loop phase search found the user-requested side-to-side
  transfer under the stricter servo write profile (`write_speed=1500`,
  `write_acc=80`, `max_delta_q_deg=8`): `initial_side_z=-0.964647`,
  `final_side_z=0.887545`, `final_tilt_deg=97.432`, no MuJoCo warnings,
  peak current `2.64 A`, peak contact about `314 N`, peak body angular
  velocity about `4.89 rad/s`. It does not pass fully upside-down
  (`min_up_z=-0.401`, `max_tilt_deg=113.647`); it is a side-to-side roll
  landing, not an over-back somersault. This is saved in
  `logs/flip_lab/side_to_side_strict_servo_best.json`; the preview video is
  `logs/flip_lab/side_to_side_strict_servo.mp4`.
- A follow-up 700-sample search that explicitly rewarded over-back motion
  found two clean side-to-side landings but zero candidates that both passed
  near upside-down and finished on the opposite side.
- Very violent settings can trigger MuJoCo warnings. The harness records
  `unstable` and `warning_count`; those candidates are not treated as
  successful flips.

Interpretation rule: a found sim candidate is only a MuJoCo hypothesis.
Before any hardware thought, re-run it across friction, torque scale, mass,
self-collision/contact variants, and current limits, then inspect video.
No physical flip attempt is implied by this file.
