# Joint coordinate contract

There is one logical 18-joint coordinate frame, `robot_abs`, governed by the
`robot_abs_tibia_v2` contract.

Each leg is ordered `[yaw, femur, tibia]`. Yaw is the coxa yaw angle;
femur and tibia are both absolute angles measured in the same leg plane.
This contract applies to complete logical hardware poses, gait inputs/outputs,
policy actions and observations, logical telemetry, motion libraries, and
experiment parameters. Raw servo diagnostics and raw calibration records use
`servo_relative`; raw registers and encoder counts are not logical poses.
Degrees/radians and the coordinate frame must be explicit at each boundary.

MuJoCo internally stores the knee as a hinge angle relative to the femur.
Only code that reads or writes MuJoCo qpos/ctrl may call the explicitly named
functions in `hexapod_core.joint_frame`:

- `robot_abs_rad_to_mujoco_rel_rad`
- `mujoco_rel_rad_to_robot_abs_rad`
- their degree/list counterparts

Physical knee servos also measure a hinge angle relative to the femur. The
hardware bus must independently convert logical poses before writes and raw
feedback before publishing logical observations. With zero software trims,
`raw_knee = absolute_tibia - hip` and `absolute_tibia = raw_knee + hip`.
The hardware boundary also applies servo trims/signs and validates physical
limits; see [HARDWARE_JOINT_FRAME.md](linux_control/HARDWARE_JOINT_FRAME.md).

For example, a logical robot plant `[0, 20, 80] deg` requires MuJoCo qpos
and raw servo angles `[0, 20, 60] deg` (before trims/signs). The old MuJoCo
`[0, 20, 80] deg` plant represented the
robot pose `[0, 20, 100] deg` and must not be used for robot-parity work.

Artifacts must declare:

```json
{
  "joint_frame": "robot_abs",
  "joint_contract": "robot_abs_tibia_v2"
}
```

Pre-v2 policies, CPG controllers, motion libraries, and warm starts are
rejected. They must be regenerated; relabeling them is not a conversion.
Reward rankings and gait gates measured with pre-v2 actions are historical
evidence only; establish new baselines before training or promoting a v2
policy.

The August 31 coordinate cleanup named these representations and enforced
artifact/simulation checks, but missed the physical servo conversion. The
H1 investigation on September 14 confirmed that omission; commits
`3840373e4` and `6ec97c406` correct and deploy it. Historical metadata labels
alone do not prove that a recording or command used the claimed frame.
Names and roundtrip tests cannot establish physical correctness: verify the
deployed implementation and compare predicted isolated motion with encoder
and camera observations before claiming hardware equivalence. The corrected
H1 feedback has been checked at rest; loaded motion remains unverified.

Scripted controllers now emit this contract directly, but their historical
performance/safety claims are not automatically transferred. Re-run their
trajectory and safety gates under v2 before treating those claims as current.

## Later physical verification, 2026-09-14

The recovery and stand/lower follow-up are recorded in [Angle-path verification](ANGLE_PATH_VERIFICATION_20260914.md). H1 completed normal STEP rise and lower; the earlier recovery restrictions above describe the earlier state. Exact loaded tracking and RL steering remain separate measurements.
