# Robot pose changed by hand AFTER the sealed window — read before the next run

Recorded 2026-09-10T03:22–03:25Z, after experiment `413d5402` was registered
(03:18:54Z) and sealed (03:19:53Z). The sealed evidence is unaffected: its
post-run samples were taken at 03:01Z and are correct as recorded. This note
exists because the Lab evidence is immutable and this happened afterwards.

## What changed

At 03:01Z the guarded run left every joint at logical zero (worst 0.44 deg).
At 03:22Z three joints read well off zero, on a robot that has been limp and
torque-off the whole time:

| joint | name | 03:01Z | 03:22Z |
|---|---|---|---|
| j3 | L1 yaw | ~0 | **−13.97** |
| j6 | L2 yaw | 0.00 | **−17.05** |
| j7 | L2 hip | −0.09 | **+20.48** |

All other 15 joints are still within 0.5 deg of zero.

## Attribution: hands, not a command and not a fault

- `GET /api/commands` shows **no command of any kind after 03:01:07Z**, when
  the guarded runner released its lease. Nothing was commanded.
- The robot has been `limp` / `armed:false` throughout, so the servos are
  back-driveable and hold no position.
- Currents 0.000 A, load 0 %, temperatures 30–33 C. No trip, no alarm, no new
  `/api/errors` row beyond the one transient `ascii_err` already reported.
- IMU roll −1.09 / pitch 2.29 deg, essentially the pre-run belly-rest
  attitude — the chassis did not tip, lift or shift.
- The overhead camera's mean luma jumped from 25.1 during the run to 99.8:
  **the room light that was out is back on.** Together with two adjacent legs
  being rotated about their yaw axes, this reads as a person in the room
  handling the robot.

`post_incident_cam0.png` / `post_incident_zoom.png` show the result: belly
down, flat, level, all six legs splayed, cables well clear of the robot. A
loose white printed part sits on the floor to the robot's right; the pre-run
frames are too dark to say whether it was already there.

## Consequence for the next run

**Not a hazard, and not an operator action** — nothing here needs hands to
fix, and the condition is fully characterized by camera plus telemetry.

But the robot is **no longer at `belly_rest_logical_zero`**, which is the
declared `start_pose` of the queued L1 and L2 belly-rest plans — and j3 is
*L1 yaw*, on the very leg the next queued plan sweeps. Two things follow:

1. Re-establish the start pose before the next sweep. The on-robot
   `sysid_runner` already glides to `home_deg` before its first segment, so a
   normal guarded run handles this by itself; a supervisor that gates on the
   start pose (as this job's runner does, tolerance 3 deg) will correctly
   refuse until it is re-zeroed.
2. Someone appears to be physically working at the robot right now. Re-check
   the camera and fresh telemetry immediately before commanding motion rather
   than trusting this note or the 03:01Z samples.

No re-pose was commanded from here: experiment `413d5402` is terminal and
sealed, so any motion now would be outside its authorization, and commanding
a leg while hands may be on the robot is the wrong call.
