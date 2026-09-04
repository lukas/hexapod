# Walk-only RL hardware session — 2026-09-03

## Outcome

`hardware-walk-noyaw-v2-canary` completed bounded forward, backward, left,
right, and direction-changing hardware pilots at its trained 0.08 m/s command.
No pilot produced a visible tip, brownout, confirmed thermal trip, hard-current
trip, or persistent servo loss during the walking phase. The policy has no yaw
authority and every command in this session used `wz = 0`.

This is a viable hardware canary, not a promotion candidate. The robot walks in
all four directions, but the first measured forward leg was slow and wandered:
45.9 mm forward and 20.1 mm lateral in approximately 2.35 s of wall-clock
motion, with -2.68 degrees of yaw. Effective progress was 19.5 mm/s.

## Hardware results

| Pilot | Result | In-motion relative tilt | Peak servo current | Notes |
|---|---:|---:|---:|---|
| Forward | completed | 2.9 deg | 0.55 A | One isolated ID-5 feedback miss recovered immediately; the original local wrapper incorrectly failed the otherwise successful run. |
| Backward | completed | 1.9 deg | 0.92 A | Clean controlled lower and limp. |
| Left | completed | 5.4 deg | 0.58 A | One isolated 136 ms host timing bubble; no stale stream tick or physical disturbance. |
| Right | completed | 6.4 deg | 0.14 A | Camera remained upright; clean controlled lower and limp. |
| Forward-left-backward-right course | completed | 15.5 deg | 0.14 A | Camera remained upright; the old tail path falsely stamped `fell=true` after changing to a stale second IMU estimator. |

The 3 s cardinal requests only yielded approximately 1.9--2.2 s of active
walking because the live-drive arming/startup interval was included in the
requested wall time. Treat these as short canaries, not full 3 s performance
acceptance trials.

## MuJoCo comparison

The deterministic eight-heading MuJoCo screen for this exact exported policy
had zero falls. At the same 0.08 m/s command it achieved approximately
34.6--43.9 mm/s (reported velocity error 0.0361--0.0454 m/s), with
0.1402--0.1624 m progress over six seconds and slip/m of 1.309--1.634.

The measured hardware forward speed of 19.5 mm/s is therefore only about
44--56% of the simulated achieved speed and about 24% of the requested speed.
The simulator also under-achieves the requested 80 mm/s, so this is both a
policy limitation and an additional sim-to-real loss.

The result agrees with the matched scripted-gait evidence. Across the gait-14
acceptance campaign, mean joint trajectory RMSE was 2.123 degrees, while mean
peak hardware IMU tilt was 10.279 degrees versus 0.275 degrees for the MuJoCo
rigid body (0.724 degrees for the simulated estimator). Actuator command
tracking is already close; the dominant mismatch is contact, body compliance,
directional friction, and body attitude dynamics.

The RL canary's 19.5 mm/s forward measurement is only modestly above gait 9's
roughly 15.9 mm/s four-run forward median, despite the RL policy requesting
80 mm/s versus the scripted gait's 30 mm/s command. Gait 14 remains rejected as
the scripted incumbent: its four-run paired bidirectional median was 0.8925 of
gait 9 (-10.75%).

## Model-selection conclusion

The 2M PPO child used on hardware slightly regressed from its frozen
behavior-cloning parent in MuJoCo: the parent achieved 0.1586--0.1661 m progress
with slip/m 1.17--1.26, while the child achieved 0.1402--0.1624 m with slip/m
1.31--1.63. Do not spend another continuation on the current nominal twin.

First encode the observed per-leg deadband/compliance, body tilt, and
directional contact/friction fit. Then preregister a single controlled
continuation, `cw-hardware-walk-noyaw-v2-realfit-dr035-canary`, from the exact
hardware-tested checkpoint with a modest DR 0.35 envelope and a frozen-parent
matched control. The acceptance gate must cover progress, course-angle error,
tilt, slip/current, zero falls, and old-model retention rather than reward
alone.

## Experiment-framework findings

- The raw AVFoundation camera ignored the requested 30 fps and delivered about
  120 fps. Writing every capture into a 30 fps MP4 made videos play about four
  times slow. The recorder now resamples by wall clock; a camera-only check
  produced 3.03 s of video for a 3.00 s timestamp span.
- Live drive used a background estimator, but the old post-motion tail switched
  to an idle foreground estimator. Its stale complementary filter created the
  course's discontinuous -3 to -56 degree roll report. The tail now stays on
  the live estimator; raw peaks remain recorded and a recovered excursion is
  distinguished from a persistent fall.
- One missing feedback sample is now retained as telemetry noise. Three
  consecutive fresh misses are required before treating servo loss as
  confirmed.
- An attempted post-fix validation on 2026-09-03 stopped before gait motion:
  after a clean tuck acquisition, stand preflight confirmed servo IDs 5 and 6
  missing across three scans. The robot was explicitly limped and no walking
  retry followed.

## Evidence

- Forward run: `20260903_v2_canary_forward_drive_v2hold/rl_walk_trial_20260903_225538`
- Backward run: `20260903_v2_canary_backward_drive/rl_walk_trial_20260903_225857`
- Left run: `20260903_v2_canary_left_drive_retry2/rl_walk_trial_20260903_230557`
- Right run: `20260903_v2_canary_right_drive/rl_walk_trial_20260903_230649`
- Direction course: `20260903_v2_canary_direction_course/rl_walk_trial_20260903_230755`
- Forward AprilTag analysis: the forward run's `analysis_report.md`
- Gait-14 reliability aggregate:
  `artifacts/gait14_acceptance/gait14_vs_gait9_reliability_20260903.json`

All paths above are under `artifacts/rl_policy_hardware/` unless stated
otherwise. UTC robot log filenames roll over to 2026-09-04 during this local
2026-09-03 session.
