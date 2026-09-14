# Hardware joint coordinates

Complete robot poses use `absolute_tibia`: the femur and tibia angles are
both measured from the chassis reference. The physical knee servo measures
the tibia angle relative to its femur. For each leg, the bus boundary is:

```
raw_hip  = hip + hip_trim
raw_knee = absolute_tibia - hip + knee_trim

hip            = raw_hip - hip_trim
absolute_tibia = raw_knee - knee_trim + hip
```

Trims are physical servo offsets. Encoder count conversion also applies the
joint sign. Full-pose writes validate every logical angle, converted raw
hinge angle, trim and encoder count before queueing any servo write. An
unreachable knee must be refused rather than clipped. Complete authored
stand/recovery paths are checked before arming; some historical fold poses
are consequently rejected because their relative knee target exceeds its
limit.

Logical feedback requires a hip and knee from the same bulk acquisition.
If the hip is missing, its knee's logical angle is unknown; raw diagnostics
remain available. Logical knee velocity is the sum of signed raw hip and
knee velocities. `/api/pose` and normal control feedback use logical angles.
The register-level `/api/status` motor health table reports raw encoder
angles. Do not interchange these two representations.

Explicit `read_raw_*` and `write_raw_*` methods serve isolated servo
diagnostics. The legacy scalar `write_joint` is also a raw bench operation
with its historical trim behavior; it is not a complete logical leg command.
System identification and motor dynamics use explicit raw coordinates and
label their logs `servo_relative`. A hold must preload and verify present
raw goals before enabling torque.

## Evidence and readiness, 2026-09-14

On H1, an isolated hip move left the knee encoder unchanged while the femur
and tibia visually rotated together. A knee-only move changed their relative
angle by approximately the measured encoder change. The CAD serial chain
and the simulation's existing relative-knee conversion agree with this
observation. Previously the hardware applied independent scalar conversions
while describing its output as body-absolute, creating a simulation/hardware
command mismatch. This is direct H1 evidence; historical H2 recordings need
their own calibration and command audit.

The takeover evidence is saved in the project workspace at
`artifacts/h1-codex-takeover-20260914/`, including both camera recordings,
isolated-motion results and the L1 calibration records. Only L1 servos 6 and
7 were re-zeroed by Codex during this takeover. H1 was not stood or walked:
L0's obscured distal-foot clearance and small, springing-back low-force
probes require a hands-on clearance check and supported pose before loaded
recovery. Passing software checks does not establish physical readiness.

## Later physical verification, 2026-09-14

The recovery and stand/lower follow-up are recorded in [Angle-path verification](../ANGLE_PATH_VERIFICATION_20260914.md). H1 completed normal STEP rise and lower; the earlier recovery restrictions above describe the earlier state. Exact loaded tracking and RL steering remain separate measurements.
