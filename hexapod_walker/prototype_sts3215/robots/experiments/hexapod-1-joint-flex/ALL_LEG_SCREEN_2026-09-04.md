# All-leg independent hysteresis screen

Campaign ID: `hexapod-1-all-leg-hysteresis-20260904`

## Question

Is L5 still an outlier when all six legs are tested in the same supported,
camera-observed session with the same radial-shear trajectories?

This is a descriptive hardware comparison, not a repair acceptance.  It uses
three within-run cycles per condition and reports L5 against the distribution
of the five peer legs.  A second block is run only if the first result is
ambiguous, interrupted, or contradicted by the camera evidence.

## Motion and camera scope

- The chassis remains rigidly supported for every job.
- Jobs are guarded-runner-started one at a time.  Robot Lab must show
  `waiting_for_operator`; its built-in simulated worker must not execute them.
- Only the selected leg's hip and knee command change during a trajectory.
  The other joint targets remain at the verified home pose.
- There is no autonomous whole-body turn.  After a job ends limp, the operator
  manually rotates the supported chassis to expose the next leg to the USB
  cameras, reseats the supports, and repeats every preflight gate.
- The complete air block must pass before any planted job is considered.

## Queue order

The air order runs around the body; the planted order reverses it to reduce
systematic time and temperature bias.

| Step | Profile | Leg | Protocol | Duration | Protocol hash |
|---:|---|---|---|---:|---|
| 1 | air | L0 | `l0_air_radial_shear_hysteresis_control_v1.json` | 78 s | `ba179b6004dc` |
| 2 | air | L1 | `l1_air_radial_shear_hysteresis_control_v1.json` | 78 s | `54e13e78078d` |
| 3 | air | L2 | `l2_air_radial_shear_hysteresis_control_v1.json` | 78 s | `0d527717ddee` |
| 4 | air | L3 | `l3_air_radial_shear_hysteresis_control_v1.json` | 78 s | `deafc345719f` |
| 5 | air | L4 | `l4_air_radial_shear_hysteresis_control_v2.json` | 78 s | `d80204caa013` |
| 6 | air | L5 | `l5_air_radial_shear_hysteresis_control_v1.json` | 78 s | `eacce87be616` |
| 7 | planted | L5 | `l5_ground_radial_shear_amplitude_ladder_v1.json` | 174 s | `c1cdf27da874` |
| 8 | planted | L4 | `l4_ground_radial_shear_amplitude_ladder_v2.json` | 174 s | `b8b2f4bf027e` |
| 9 | planted | L3 | `l3_ground_radial_shear_amplitude_ladder_v1.json` | 174 s | `1e2f65a90a91` |
| 10 | planted | L2 | `l2_ground_radial_shear_amplitude_ladder_v1.json` | 174 s | `a1cb453ad68b` |
| 11 | planted | L1 | `l1_ground_radial_shear_amplitude_ladder_v1.json` | 174 s | `b08cbbd244d5` |
| 12 | planted | L0 | `l0_ground_radial_shear_amplitude_ladder_v1.json` | 174 s | `dc61d4194c4c` |

The checked-in L4 v1 trajectories are not used: they yaw L3 and L5 for the
old camera placement.  The L4 v2 trajectories remove that camera-clearance
motion and assert that only L4 hip and knee vary.

## Required gate before every job

1. Confirm an operator is present and the physical e-stop/abort path is ready.
2. Confirm no robot/demo/sysid job is active.  Start from idle, disarmed, and
   limp; never preempt another job.
3. Confirm rigid supports are stable.  For the planted block, only the target
   foot receives the intended contact while the chassis support carries the
   robot.
4. Compare the physical pose with logical zero.  If they disagree, stop and
   perform the documented set-zero-here procedure before any absolute pose.
5. Require three fresh healthy samples: 18/18 servos, IMU healthy, normal
   electrical/current/temperature telemetry, and no persistent missing ID.
6. Verify both USB camera identities and live views after the manual rotation.
   The target hip/knee tag plus a body or floor reference must be visible; no
   support or camera may move during a trajectory.
7. Verify the protocol name and hash in this table.  The external supervisor
   must enforce these gates; `sysid.run_hw`'s built-in preflight alone is not
   sufficient.

## Stop and retry rules

Every completion, rejection, interrupt, or trip ends limp.  Stop without an
automatic retry for a tip, visibly bad posture, support movement, brownout,
hot motor, jam, surprise force, confirmed overcurrent, or camera evidence of
unsafe motion.  These trajectories coordinate hip and knee and hold all 18
targets, so the single-joint grounded-current auto-retry exception does not
apply.  Only a recoverable missing-feedback, camera, recorder, or framework
stop may retry: inspect the live cameras, require three fresh healthy samples,
and retry the complete leg job at most twice, following
`EMERGENCY_HANDLING.md`.

## Evidence and comparison

Capture the hardware CSV, exact protocol JSON/hash, result summary, synchronized
camera sidecar, start/end telemetry, and current tag-layout revision for every
job.  Analyze each CSV with `sysid.analyze_hysteresis`, preserving both signed
midpoint differences and the mean absolute hip/knee loop per condition.

Report, for air and for each planted amplitude:

- all six hip and knee loop values;
- L5's ratio to the peer median and to the largest peer;
- cycle-to-cycle range and any invalid camera or telemetry interval; and
- whether the encoder direction and visible tag motion agree.

Treat L5 as a contemporaneous outlier only when its separation from every peer
is larger than the within-run scatter/noise and repeats coherently across the
relevant conditions.  The pre-registered practical gate is at least four
encoder counts (0.352 degrees), preferably also at least 2x the largest peer,
in air and in at least three planted amplitudes.  Do not turn the six-leg
screen into an automatic stand, gait, or repair-acceptance decision.
