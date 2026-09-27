# Hardware joint coordinates: the servo boundary

Complete robot poses use `robot_abs` (`robot_abs_tibia_v2`): femur and tibia
angles are both measured from the chassis reference. The physical knee servo
is mounted on the femur and measures the tibia angle RELATIVE to it. So for
each leg the bus boundary is

```
raw_hip  = hip + hip_trim
raw_knee = tibia_abs - hip + knee_trim

hip       = raw_hip - hip_trim
tibia_abs = raw_knee - knee_trim + hip
```

MuJoCo's knee qpos is the same hinge angle. Both boundaries call the same two
functions, `hexapod_core.joint_frame.robot_abs_to_servo_relative` and
`servo_relative_to_robot_abs`; nothing else converts.

Where it is enforced (`motor_setup/feetech_bus.py`, `linux_control/mcu_feetech_bus.py`):

- every full-pose WRITE (`write_all`, `step_all`, the drive controller's bare
  SyncWrite fallback) converts through `robot_pose_to_raw_degrees`, which
  validates every logical angle, converted hinge angle and encoder count
  BEFORE any servo is written; an unreachable knee is refused, never clipped;
- every position READ (`step_all` snapshot, `read_snapshot`, `read_all_feedback`,
  `read_position_deg`) converts back with `raw_positions_to_robot_degrees`.
  A logical knee needs its hip from the SAME acquisition; without it the knee
  is unknown (absent / `None`), never guessed. Logical knee velocity is the sum
  of the signed raw hip and knee velocities;
- `raw_pos_deg` / `raw_speed_deg_s` / `raw_deg` / `raw_command_deg` stay in every
  snapshot, feedback and telemetry record, labelled `servo_relative`, so servo
  diagnostics are never lost. Telemetry records carry `joint_frame`.

Raw by nature, explicitly single-servo: `write_joint`, `read_raw_position_deg`,
`api/zero.py` (zero registers are not poses), `motor_setup_api`, `urt2_*`,
sysid / motor_dynamics bench moves.

Stored pose numbers: `standup_modes.json` is authored in the set_zero / hinge
frame (MuJoCo qpos from `compare_standup.py --export`) and is converted at load
AFTER the hinge fold caps are applied. `plant_pose.json` files written before
2026-09-27 are stamped `robot_abs` but hold hinge numbers; `load_plant_pose`
migrates them (knee += hip) unless the file carries `"servo_boundary": "robot_abs"`.
The default walk start is `joint_frame.walk_start_pose_degrees()` =
`[0, 20, 100]` robot_abs = the servo's historical "knee 80" stance.

## History (why this file exists)

- 2026-08-21/22: the mismatch was first root-caused; a software bridge was added
  with the PREMISE that the hardware frame is absolute.
- 2026-08-31: the v2 contract codified that premise.
- 2026-09-03: `test_joint_frame` xfail "third joint-frame instance".
- 2026-09-14: commit 4fcc7969 built this boundary with tests, on H1 evidence
  (an isolated hip move left the knee encoder unchanged while femur and tibia
  rotated together). It was carried onto the reduced runtime (53941139) and
  the 09-17 refactor (8e34d002) on `codex/h1-*` branches and never merged.
- 2026-09-27: the ceiling camera measured hexapod2's feet on a 164 mm circle at
  telemetry hip 19 / knee 78 (absolute-tibia FK: 230 mm; hinge FK: 181 mm), 113 mm
  at hip 19 / knee 98, 163 mm at hip 16 / knee 82. The robot had run every
  command 20 deg more knee-flexed than the simulator since the v2 contract.
  This port of the boundary onto main is that commit's spec.

A lab session start compares the camera foot radius against FK in the contract
frame; a disagreement above the threshold fails loudly. Do not remove that check.
