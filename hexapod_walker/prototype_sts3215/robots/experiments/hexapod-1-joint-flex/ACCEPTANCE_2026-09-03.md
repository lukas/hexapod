# L5 supported acceptance retest — 2026-09-03

## Disposition

**L5 is not demonstrated repaired; the measured residual was explicitly
accepted by the operator for this campaign on 2026-09-03.** The supported air
control improved, but the planted ladder reproduced the previously abnormal
L5 hip/knee hysteresis. The robot returned limp at zero with all 18 servos
present and no visible support or geometry change. That acceptance cleared the
campaign's process gate for guarded whole-body gait and walk-only policy tests;
it does not erase or reclassify the hardware finding.

## Runs

| Test | Result | Control ticks | Camera samples | Peak current |
|---|---|---:|---:|---:|
| L5 air radial-shear control | clean completion | 780/780 | 759 | 0.039 A |
| L5 planted 3.75–15 mm ladder | clean completion | 1,740/1,740 | 1,660 | 0.0845 A |

Both protocols used soft torque 700, a three-consecutive-sample trip at
0.75 A, and an immediate 3.0 A ceiling. Neither run aborted or clamped a
command. The planted run had 12 catch-up overruns in one 0.15-second cluster
near 62.2 seconds; none fell in a measurement dwell window.

The final independent health check reported 18/18 servos, zero current,
11.2 V minimum, 32 °C maximum, no alarms, and at most 0.26 degrees from the
zero pose. The CSV temperature field contained intermittent impossible
single-sample values up to 132 °C. These conflict with the fresh per-servo
status scan before and after the run and are not treated as confirmed
temperatures; the telemetry decoder/freshness path needs correction before a
gait temperature claim relies on that field.

## Encoder hysteresis

Equal-command loop magnitude in the unloaded control was:

| Run | L5 hip | L5 knee |
|---|---:|---:|
| 2026-09-03 acceptance | 0.830° | 0.181° |
| previous 2026-09-03 repeat | 1.143° | 0.352° |
| previous L4 reference | 0.059° | 0.088° |

The knee improved substantially and the hip improved modestly, but the hip
loop remains about fourteen times the L4 reference.

The planted ladder measured:

| Radial command | L5 hip | L5 knee |
|---:|---:|---:|
| 3.75 mm | 0.776° | 0.688° |
| 7.5 mm | 1.045° | 0.835° |
| 11.25 mm | 1.271° | 1.085° |
| 15 mm | 1.091° | 0.967° |

This is materially unchanged from the previous L5 ranges of 0.645–1.259° hip
and 0.586–1.113° knee, and remains well above the prior L4 planted range of
0.088–0.351°.

## Vision and model-fit limits

The standalone camera server and guarded runner captured synchronized state
documents with zero HTTP capture errors and camera-1 JPEGs that were assembled
into MP4s. The existing camera joint estimator tracked L5 hip in 1,257/1,660
planted samples, but did not track L5 knee. The newly configured L5 component
tags 48, 58, 63, and 64 were not visible in any captured pose document from
the current camera geometry. Camera-derived L4/L5 compliance therefore cannot
be fit defensibly from this acceptance run.

Robot feedback exposed through the camera server also became stale while the
exclusive sysid trajectory owned the robot API, so its apparent IMU range is
not a synchronized body-tilt measurement. These two gaps must be fixed or the
robot/camera geometry changed before fitting per-leg visual compliance and body
tilt. Directional friction likewise requires the paused forward/backward gait
run.

## Gait-14 simulation screen

The proposed 2.65-second, 16 mm, continuous-timing gait passed the requested
MuJoCo joint-rate/workspace screen in both directions at 30 mm/s for 6 seconds:

| Direction | Travel/command | Joint rate p95 / max | Workspace fallbacks | Limit clips | Min limit margin | Max tilt |
|---|---:|---:|---:|---:|---:|---:|
| Forward | 0.118/0.140 m | 32.1/71.8°/s | 0 | 0 | 6.1° | 0.3° |
| Backward | 0.115/0.140 m | 31.5/71.8°/s | 0 | 0 | 6.1° | 0.3° |

The primitive-collision model still showed 264–269 mm of scrub, reinforcing
the known contact/body-dynamics reality gap rather than invalidating the
joint-rate/workspace screen.

Gait 14 was subsequently deployed with the documented helper after installing
a dedicated robot SSH identity. The first clean hardware pilot and two complete
paired repeats were recorded; the final repeat and policy walk remain in
progress at the time of this acceptance-note update.

## Evidence directories

- `sysid/datasets/l5_air_radial_shear_hysteresis_control_v1_20260903_183326/`
- `sysid/datasets/l5_ground_radial_shear_amplitude_ladder_v1_20260903_183816/`
- `artifacts/gait14_acceptance/20260903_sim_screen/`

Each hardware directory contains the protocol, raw CSV, full pose-state JSONL,
camera frames, run summaries, and a `camera1.mp4` recording.
