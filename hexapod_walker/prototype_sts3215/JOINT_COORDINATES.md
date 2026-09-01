# Joint coordinate contract

There is one public 18-joint coordinate frame, `robot_abs`, governed by the
`robot_abs_tibia_v2` contract.

Each leg is ordered `[yaw, femur, tibia]`. Yaw is the coxa yaw angle;
femur and tibia are both absolute angles measured in the same leg plane.
This contract applies to hardware commands/readback, gait inputs/outputs,
policy actions and observations, telemetry, videos, calibration data, motion
libraries, and experiment parameters. Degrees/radians must still be named at
the API or field.

MuJoCo internally stores the knee as a hinge angle relative to the femur.
Only code that reads or writes MuJoCo qpos/ctrl may call the explicitly named
functions in `hexapod_core.joint_frame`:

- `robot_abs_rad_to_mujoco_rel_rad`
- `mujoco_rel_rad_to_robot_abs_rad`
- their degree/list counterparts

For example, a robot plant `[0, 20, 80] deg` is MuJoCo qpos
`[0, 20, 60] deg`. The old MuJoCo `[0, 20, 80] deg` plant represented the
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

Scripted controllers now emit this contract directly, but their historical
performance/safety claims are not automatically transferred. Re-run their
trajectory and safety gates under v2 before treating those claims as current.
