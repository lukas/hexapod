# Scripted-gait sim-to-real session — 2026-09-01

## Final robot state

- Collision-aware STEP-lower recovery completed after five consecutive cool
  readings and explicit operator authorization.
- Post-recovery verification: 18/18 live, maximum absolute encoder error
  0.26 degrees, 34 C maximum, then `X` limp.
- Deployed watchdog reports `temp_trip_reads: 3`.

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

## Follow-up protocol

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
