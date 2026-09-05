# Hardware walking benchmark, version 1

The first recovery experiment is one forward three-second command window using
the already tested `hardware-walk-noyaw-v2-canary`, at its trained 0.08 m/s with
zero yaw. It uses the existing drive path, STEP walk-ready acquisition, and
planned STEP lower. It is a timing canary. The existing runner includes arming
in the command window and permits only 3–20 seconds; this specification does
not queue or authorize a 60-second run.

Generate reviewable Robot Lab payloads from the current source tree:

```sh
uv run python -m rl_move.scripts.hardware_walk_benchmark plan --output /tmp/hardware-walk-plan.json
```

By default the JSON `queue_payloads` list contains only the timing canary and
requires no optional sysid protocol files. Add `--include-planted` to also
generate the six separate supported planted comparisons, L5 through L0, when
that complete protocol set is installed and reviewed. Each item matches Robot Lab's
experiment creation fields and requires `execution_mode=external_guarded`.
Queueing leaves it `waiting_for_operator`; this program has no network or motion
code. The operator supervises walking with the existing controller stop protections.
Continue repetitions within the authorized motion scope after a stable stop.
Resolve the current robot address and camera identity at execution;
the command placeholders deliberately contain no stale IP address.

The canary records the known checkpoint/export hashes, observation and motor
contract, and controller source hashes for interpreting results. Record the actual
versions used; a reviewed source change is not itself a reason to block an experiment.
Tag-layout calibration, additional timing reports, and long-duration acceptance
are not prerequisites for a walking comparison. Missing measurements limit what
we can conclude from a run, rather than making the run worthless.
Use a validated direct camera with source capture timestamps. The legacy HTTP
JPEG endpoint does not prove frame freshness from receipt time alone and is not
the camera source for this plan.

The planted jobs reuse the exact versioned 174-second radial-shear protocols.
Generation checks that only the selected hip/knee targets vary across home
acquisition and every segment boundary, rejects unaudited segment types, and records the
file SHA-256. L4 uses version 2, without the older adjacent-leg yaw movement.
These are supported characterization jobs, not walking or repair acceptance.
`sysid.run_hw` alone does not enforce all support/camera gates: the external
supervisor must do so. Coordinated hip/knee current trips do not use the
single-joint automatic current-retry exception. The canonical stop rules remain
in `EMERGENCY_HANDLING.md`.

Audit saved recordings without contacting the robot:

```sh
uv run python -m rl_move.scripts.hardware_walk_benchmark analyze \
  rl_move/hardware_traces/rl_walk_trial_20260904_232355 \
  --output /tmp/hardware-walk-baseline.json
```

The report separates requested command duration, host command wall window,
scheduled policy `t_s`, and actual continuous engaged wall time. Only advancing
per-tick `mono_s`, `wall_elapsed_s`, or `unix_s` plus explicit `walk_engaged` or
`learned_policy_active` can establish actual engagement. The sampled span is a
lower bound; no final tick is extrapolated. Interrupted engagement (including
hold rows between walking segments) or logging gaps over 250 ms cannot establish
continuity. Split interrupted runs before scoring. Legacy traces remain useful for service/write
time, overruns, attitude and repeated feedback, but their nominal clock never
proves actual cadence or active duration. Repeated joint values may mean cached
feedback or stillness; they are not an independent sensor-age or stall measure.

New episode logging should provide `mono_s`, `walk_engaged`, `state_age_ms`,
`position_age_ms`, `imu_age_ms`, and `bus_write_due`. Missing fields remain null
or empty statistics; they never become zero error. Summary current/tilt maxima
remain explicitly recorded values and require normal telemetry/video review.

Metric progress requires a separately validated floor-pose measurement. Put
`calibrated_motion.json` (or `calibrated_motion_forward.json`, etc.) beside a
saved trial, using this schema. The trace hash binds it to that exact episode;
times must share the engagement clock and cover its entire interval.

```json
{
  "schema": "hexapod.calibrated_motion.v1",
  "calibration_status": "validated",
  "calibration_id": "the-real-calibration-record-id",
  "frame": "floor",
  "units": "m",
  "trace_sha256": "SHA256_OF_THE_RAW_EPISODE_CSV",
  "clock": "mono_s",
  "samples": [
    {"t": 100.0, "x": 0.0, "y": 0.0, "yaw_deg": 0.0},
    {"t": 102.0, "x": 0.04, "y": 0.01, "yaw_deg": 1.0}
  ]
}
```

These numbers illustrate the file format, not a hardware result. A validated
calibration identifier must refer to an actual calibration reviewed separately;
the analyzer does not authenticate that record. Motion is projected onto the
initial body heading plus the constant commanded direction; course error is
the angle of net displacement, and yaw change is reported separately. A
direction-changing course needs per-segment analysis and is not scored by this
constant-direction calculation. Video alone does not supply metric distance.

The future duration criterion is three distinct, continuous 60-second trials,
each with actual engagement timestamps, no recorded fall, and calibrated motion.
Three short clips cannot be concatenated, and one folder or duplicate raw trace
cannot count as three repeats. Even that criterion is only duration/pose
evidence: smoothness, foot clearance/slip, course control, current/thermal
behavior, reliable start/stop and the chosen acceptance thresholds still require
review. This fixed-speed no-yaw policy cannot demonstrate steering or
variable-speed competence.

The next useful comparison keeps the policy, gait, speed, and 100/50/10 Hz rates
fixed and changes only `velocity_filter.alpha` from `0.3` to `0.8`.
The existing runner now accepts `--walk-transport drive --velocity-filter-alpha 0.8`;
use `0.3` for its baseline. The robot drive API accepts `velocity_filter_alpha`
on `/api/rl/drive/start`. The override lasts only for that session and the actual
value is recorded in the episode result; omission preserves `rl_move/config.yaml`.
This needs the updated controller installed once, then no config edits or service
restarts between comparisons. Compare the same
direction, floor and starting posture; keep the change if repeated physical
walks improve. This experiment does not depend on another gait comparison or a
six-leg characterization campaign. Both remain separate questions.
