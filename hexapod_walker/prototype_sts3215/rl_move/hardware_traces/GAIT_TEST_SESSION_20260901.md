# Scripted-gait sim-to-real session — 2026-09-01

## Final robot state

- Collision-aware STEP-lower recovery completed after five consecutive cool
  readings and explicit operator authorization.
- Post-recovery verification: 18/18 live, maximum absolute encoder error
  0.26 degrees, 34 C maximum, then `X` limp.
- Deployed watchdog reports `temp_trip_reads: 3`.
- After the rotated repeats: 18/18 live, maximum absolute zero error 0.26
  degrees, 35 C maximum, and limp/disarmed.

## Gait 10 vs gait 0 — three complete paired surveys

All three surveys completed without recovery or safety trip:

- `scripted_gait_suite_20260901_114217`
- `scripted_gait_suite_20260901_115050`
- `scripted_gait_suite_20260901_115532`

At a 30 mm/s command, AprilTag floor-projected chassis speed was:

| Direction | Gait 0 median | Gait 10 median | Paired gait-10 / gait-0 |
|---|---:|---:|---:|
| Forward | 14.853 mm/s | 10.973 mm/s | 0.744 median |
| Backward | 8.327 mm/s | 16.726 mm/s | 1.921 median |
| Two-direction mean | — | — | 1.166 median, 1.178 mean |

Conclusion: gait 10 transfers as a strong robot-local reverse gait, but is
not a general forward-speed improvement. The paired average improvement was
13.2–23.6% across the three runs. The direction dependence is too large to
attribute to random camera noise.

Aggregate: `gait_reliability_20260901_gait0_vs_gait10.json`.

## Gait 9 exploration

The first complete paired run, `scripted_gait_suite_20260901_120420`, measured:

| Direction | Gait 0 | Gait 9 | Paired gait-9 / gait-0 |
|---|---:|---:|---:|
| Forward | 18.483 mm/s | 16.669 mm/s | 0.902 |
| Backward | 10.235 mm/s | 18.682 mm/s | 1.825 |
| Two-direction mean | 14.359 mm/s | 17.676 mm/s | 1.231 |

Gait 9 is the best candidate for the next session: its first real run retained
most baseline forward speed while producing the same large reverse gain. It is
not yet reliable evidence because only one complete trial exists.

The second attempt, `scripted_gait_suite_20260901_120655`, stopped before gait
9 completed. Joint 1 temperature changed 32 -> 83 -> 102 C in 0.67 seconds and
returned to 31–34 C afterward. This is thermally impossible and consistent
with corrupt bulk-feedback bytes, but it satisfied the old two-read cutoff.
The partial speeds remain in the artifact directory and are excluded from the
aggregate because its manifest status is `failed`.

Aggregate: `gait_reliability_20260901_gait0_vs_gait9.json`.

## Gait 9 after a physical 180-degree rotation

The robot was turned approximately 180 degrees while the camera and all floor
tags stayed fixed, then manually repositioned toward the middle of the camera.
Three complete paired six-second surveys were recorded:

- `scripted_gait_suite_20260901_124147`
- `scripted_gait_suite_20260901_124426`
- `scripted_gait_suite_20260901_124810`

| Direction | Gait 0 median | Gait 9 median | Paired gait-9 / gait-0 |
|---|---:|---:|---:|
| Forward | 16.181 mm/s | 15.129 mm/s | 0.928 median |
| Backward | 7.000 mm/s | 15.512 mm/s | 2.216 median |
| Two-direction mean | — | — | 1.454 median, 1.421 mean |

Gait 9 backward was especially repeatable: 15.04--15.65 mm/s, CV 0.021.
Across the original complete run plus the three rotated runs, gait 9 measured
15.899 mm/s forward and 15.579 mm/s backward by median. Its median paired
two-direction improvement over gait 0 was 36.8%, with all four complete runs
positive (23.1--52.6%).

The basic gait remained robot-local forward-biased after rotation: its
four-run medians were 16.535 mm/s forward and 7.956 mm/s backward. Therefore
the garage grade is not the dominant explanation for the asymmetry. It may
still account for a smaller absolute-speed shift.

Aggregates:

- `gait_reliability_20260901_rotated_gait0_vs_gait9.json`
- `gait_reliability_20260901_gait0_vs_gait9_all_complete.json`

## Recovery and infrastructure findings during the rotated test

- `scripted_gait_suite_20260901_123228` retained its recordings after two
  identical -179.87-degree IMU Euler samples caused a false tilt stop. The
  robot was visibly upright and immediately returned to about -3 degrees.
  Tilt now requires three valid samples, and a discontinuous near-180-degree
  jump with a quiet gyro is logged but cannot accumulate stop votes.
- Explicit collision-aware zero recovery completed from the interrupted gait
  pose after five stable health readings; zero error was at most 0.53 degrees.
- `scripted_gait_suite_20260901_123747` stopped when the chassis was 0.29 m
  from its anchor, beyond the centering controller's 0.25 m trusted range. The
  ordinary-failure recovery correctly lowered to zero and limped. The partial
  run is excluded from reliability aggregation.
- Continuity Camera sometimes fails to reacquire its native 420v stream after
  a recorder subprocess exits. Restarting only the local Mac `:8898` service
  restores it; the robot remains zero and limp during that restart.
- `/api/measure/walk` could previously mark a disarmed zero pose as a stand
  without physically acquiring walk-ready. It now always runs validated
  zero-to-stand acquisition when disarmed.
- The completed rotated runs contained isolated impossible temperature bytes
  as high as 68 C, but no joint produced three consecutive hot readings. The
  confirmed temperatures stayed at or below 38 C.

## Candidate-screen conclusion

A matched MuJoCo screen at 30 mm/s ranked gait 9 ahead of fluid variants
11--13. Gait 10 was faster than gait 9 in idealized MuJoCo (about 20.7 versus
18.7 mm/s), but its earlier hardware average was slower and strongly
directional. Raising gait 9's command to 40 mm/s did not increase simulated
speed because its fixed period/stride envelope was already saturated.

The next useful speed experiment is an intermediate fluid preset between gait
9 (2.9 s period, 18 mm lift) and gait 10 (2.4 s, 14 mm), followed by the same
three-run paired hardware protocol. The simulator objective must penalize
direction asymmetry and body motion; speed-only MuJoCo ranking currently
prefers gait 10 for the wrong reason.

## What the matched MuJoCo replay says

For the complete gait-9 run, MuJoCo predicted approximately 18.94 mm/s forward
and 19.50 mm/s backward for gait 9; hardware measured 16.67 and 18.68 mm/s.
That candidate transferred surprisingly well in absolute speed. Gait 0 did
not: simulation predicted 11.18/10.36 mm/s, while hardware measured
18.48/10.24 mm/s.

Joint trajectory RMSE was only about 2.1–2.6 degrees, so motor command tracking
is not the dominant mismatch. The larger residuals are contact/body dynamics:
hardware IMU peak tilt was roughly 7–15 degrees while MuJoCo rigid-body tilt
was only 0.3–0.5 degrees, and MuJoCo peak-current estimates were much larger
than measured servo currents. Do not compare the two tilt signals as an exact
residual, but their scale difference shows that the simulated chassis is much
more settled than the real robot.

## Original follow-up protocol (completed in this session)

1. Physically rotate the robot 180 degrees while leaving the camera and floor
   tags fixed; capture a new image anchor.
2. Collect three complete paired gait-0/gait-9 surveys at 30 mm/s. Do not raise
   speed until all three finish without recovery or safety trip.
3. If the fast physical direction stays fixed in the garage, fit floor grade
   and directional/anisotropic friction. If the advantage stays robot-local
   backward, focus on gait geometry, leg compliance, and mass asymmetry.
4. Fit MuJoCo against AprilTag progress, lateral drift, yaw, body tilt, and
   joint tracking together. Add plane tilt, friction spread/anisotropy, foot
   compliance, actuator lag/deadband, and per-leg asymmetry to domain
   randomization. Ranking on speed alone will overfit the current idealized
   contact model.

The stationary IMU reading during this session was typically about 1–3 degrees
from level, which is compatible with a modest garage grade but is not proof;
the 180-degree paired test is the discriminating experiment.
