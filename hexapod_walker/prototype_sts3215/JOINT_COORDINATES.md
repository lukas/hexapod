# Joint coordinate contract

Logical poses use `robot_abs`, governed by the executable
`robot_abs_tibia_v2` contract in `hexapod_core/joint_frame.py`.

Use that module's names and indexing functions. Hip and knee denote the
absolute femur and tibia angles. Complete hardware poses, policy actions,
observations and logical telemetry use these angles. Register diagnostics
and motor calibration use explicitly labeled `servo_relative` coordinates.
Degrees/radians must still be named at the API or field.

MuJoCo internally stores the knee as a hinge angle relative to the femur.
Only code that reads or writes MuJoCo qpos/ctrl may call the explicitly named
functions in `hexapod_core.joint_frame`:

- `robot_abs_rad_to_mujoco_rel_rad`
- `mujoco_rel_rad_to_robot_abs_rad`
- their degree/list counterparts

`walk_start_pose_degrees()` supplies the shared sim/hardware reset pose.
Its `[0, 20, 100]` absolute angles become `[0, 20, 80]` relative angles.
The hardware boundary in `motor_setup/feetech_bus.py` also converts the
relative knee, applies trims/signs, and validates physical motor limits.
Logical knee feedback requires its hip from the same acquisition.

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
