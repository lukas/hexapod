# L5 belly-rest radial shear hysteresis, 6 repeats — b289e536

**Verdict: succeeded. The hypothesis is REFUTED.** The L5 hip does not follow a
single repeatable command-to-angle path: at the identical commanded angle it
settles **0.83 deg** apart depending on which direction it arrived from, and the
loop does not close. Reproduced on 5 runs of the same protocol hash across 3 days.

## What ran

The reviewed protocol named by the plan, byte-exact, recovered from the robot's
own prior run records: `l5_belly_rest_radial_shear_hysteresis_repeat6_v1`,
`protocol_hash dbc4d64c333a`. One absolute 18-joint `traj` segment, 1560 ticks
at 10 Hz (155.9 s), `soft_torque 700`, runner current trip 0.75 A over 3 polls.

Only j16/j17 move; the other 16 joints are held at absolute logical zero. The
chassis never stands. Structure: ramp in to hip −51.143 deg, 8 s settle, **3**
out-in shear repeats, a full return to logical zero, re-approach, **3 more**
repeats, ramp out. Each repeat dwells 3 s at hip −51.143 / −47.133 / −42.955 deg
(centre −47.049, span 8.188 deg) while the knee compensates to hold the foot at
a constant `foot_z = −15.00 mm`, producing a 15.00 mm pure radial shear.

Terminal run: `2026-09-10T02:17:59Z–02:20:35Z`, **1560/1560 ticks, 0 overruns,
0 clamped commands**, no trip, peak per-servo current **0.0325 A**, max load
13.2 %, max temp 37 C (plan stop 45 C, limp 55 C).

## The hysteresis loop

Loop width = settled measured hip angle at the same commanded −47.133 deg,
out-stroke minus in-stroke. Settled = mean of the last 1.0 s of each 3 s dwell.

| run | hip loop (deg) | knee loop | out-stroke err | in-stroke err | peak A |
|---|---|---|---|---|---|
| **this run** 09-10T02:17:59Z | **−0.826 ± 0.070** | +0.439 | −0.118 | +0.629 | 0.0330 |
| this job 09-10T02:09:36Z | −0.756 ± 0.070 | +0.299 | −0.037 | +0.607 | 0.0260 |
| prior 09-06T00:54:45Z | −0.849 ± 0.038 | +0.386 | +0.031 | +0.601 | 0.0330 |
| prior 09-05T22:25:49Z | −0.851 ± 0.032 | +0.457 | −0.003 | +0.612 | 0.0390 |
| prior 09-05T22:15:55Z | −0.879 ± 0.000 | +0.421 | +0.025 | +0.640 | 0.0330 |

**Pooled: −0.832 deg, sd 0.065, range −0.967..−0.703, n = 25 cycles over 3 days.**
Encoder resolution is 360/4096 = 0.0879 deg/count, so the loop is **9.5 counts** —
an order of magnitude above quantisation.

The asymmetry is stark and one-sided: on the out-stroke the hip settles
essentially on command (−0.118 deg), while on the in-stroke it lags by
**+0.629 deg**. The mid-protocol full return to logical zero does not clear it —
block A averages −0.879 deg and block B −0.762 deg, so the effect re-establishes
after a complete unload and re-approach rather than being drift or warm-up.

## What this means, and the one thing it does not settle

The hypothesis was that hip/knee follow a repeatable bounded path with no
significant hysteresis, so the 0–2.9 deg stance shortfall measured on the parent
experiment would be fully explained by load-dependent position-loop compliance.
That is now refuted: a 0.83 deg direction-dependent loop is present and highly
repeatable, and it is the same order as L5's own 1.09 deg cycle-1 stance
shortfall. So compliance alone does not explain the shortfall, and — this is the
part that matters for walking — **re-commanding a static stance cannot remove it**.
During a gait each leg reverses hip direction at every stance-swing transition,
so this puts a fixed ~0.8 deg placement error into every step.

**Honest limit.** The rationale's compliance prediction was conditioned on the
out- and in-strokes being compared *at matched applied torque*. They are not
matched here: the in-stroke holds 0.0330 A at 10.4 % load versus the out-stroke's
0.0130 A at 7.2 %. So this establishes that the loop exists, its size, and its
repeatability, but it does **not** cleanly separate pure mechanical backlash from
load-direction-dependent compliance. Discriminating those two needs a protocol
that reaches the same commanded angle from both directions at equal holding
torque. The operational conclusion above holds under either mechanism.

## Deviations from the saved parameter block (protocol kept unedited)

The saved `parameters` are an analysis paraphrase that does not match the
reviewed protocol it names. The protocol was run unmodified; the differences are:

- `hip_center: belly_rest_measured_j16` — actual sweep centre is **−47.049 deg**,
  not the belly-rest j16 (0.09 deg). "Belly-rest" refers to the *chassis* not
  standing, which held throughout.
- `hip_amplitude_deg: 8.0` — actual span is 8.188 deg peak-to-peak (±4.094).
- `dwell_s: 1.5` — actual dwells are **3.0 s** (more quasi-static, better for this
  measurement).
- `telemetry_hz: 50` — the runner's own synchronized log is **10 Hz** (protocol
  rate); the passive 50 Hz recorder ran alongside at `max_hz 50.0`.
- `current_stop_a: 4.0` — the reviewed protocol's own trip is **stricter**, 0.75 A
  over 3 polls, and governed.
- `record_fields` — `goal_deg`, `present_deg`, `load_pct`, `current_a`, `temp_c`
  and derived raw counts are all in the runner CSV for all 18 joints.
  `imu_roll_deg`/`imu_pitch_deg` are **not** in that log: IMU comes only from
  `/api/feedback`, which is a full bus scan costing ~5.1 s per call, so it was
  sampled before and after rather than during (see below). Recorded as sparse.
- Camera-derived hip/knee angles are **unmeasured**: the tag pose service reports
  `calibration_unavailable` for hip and knee (`no intrinsic calibration ... for an
  active camera`); only leg yaw is tracked. No calibrated displacement was needed
  for this question.

## Clearance — measured, not assumed

The plan requires the moving foot to stay ≥15 mm clear of the floor. Rather than
assume, this was read off the robot's own `l5_ground_contact_ramp_v1` record: the
L5 foot first loads the floor at measured `foot_z ≈ −80.95 mm` and bottoms out at
−105.74 mm. The hysteresis protocol never commands past **−15.00 mm**, leaving
**~66 mm** above contact onset — over 4x the requirement. The arc also moves the
foot radially *inward* (252 → 192 mm), never outside its own resting footprint.
Corroborated in-band: currents stayed ≤0.0325 A for all 1560 ticks with no
contact signature anywhere.

This also corrects an early misreading of mine: the feet are **not** resting on
the floor at belly-rest — they hang ~80 mm above it. A low-angle camera view made
them look grounded; the contact ramp and the post-run frames settle it.

## Three physical attempts, reported in full

1. **Lift-direction probe** (01:49:06Z, 10 s, 250/250 ticks, no trip, peak
   0.006 A). Bounded knee-only move to verify the foot-lift sign before sweeping.
2. **First sweep attempt** (02:04:41Z) — **tripped at 349/1560 ticks**:
   `joint 1 (ID 3) missed 3 consecutive reads`, preceded in `/api/errors` by
   `bus_timing P->p no_a5 1002.9ms`. Correctly limped. **Cause was mine**: my
   supervisor polled `/api/feedback`, which is a full 18-servo bus scan holding
   the bus lock for ~5.1 s, and it starved the runner's own position read. The
   three prior clean runs of this hash had no concurrent poller. Electrically and
   mechanically benign — peak 0.0325 A, joint 1 is not even on the tested leg.
   Recovery per contract: fresh frames on all three cameras plus three distinct
   advancing healthy 18/18 samples (joint 1 reading normally, 33 C, IMU
   unchanged), then retried.
3. **Retry** (02:09:36Z) — **1560/1560 ticks, 0 overruns, ok**. Bus polling
   removed during motion. But the harness trusted `/api/calibrate`'s `running`
   flag, which read false at t+18 s of a 156 s protocol, so the recorder stopped
   early and left a 98 s camera gap. Telemetry is complete and its loop numbers
   are in the table above.
4. **Terminal run** (02:17:59Z) — **1560/1560 ticks, 0 overruns, ok**, with the
   exit logic fixed to hold for the protocol's deterministic duration and to
   detect a trip from the bus-free progress string. **Continuous coverage on all
   three cameras, 19:17:46–19:21:59 local, max inter-frame gap 0.71 s**, 1146
   frames, **all 1146 distinct by sha256** (frame dedup check passes).

## Supervision actually achieved

`/api/feedback` costs ~5.1 s and `/api/errors` ~6.0 s per call *even on an idle
bus*, so an external 5 Hz monitor is not physically possible and dense polling
actively causes the fault seen in attempt 2. Final design: the runner's own
in-loop interlocks are the real-time layer (0.75 A over 3 polls, 55 C over 3
polls, 30 deg tracking against a slewed reference, 3 missed reads, stale-state,
limp on trip); supervision is the bus-free continuous camera record plus a
freshness watchdog; bus telemetry is read before and after.

The plan's stricter 5 deg / 45 C bounds were supervisor-side intentions rather
than runner interlocks. Post-hoc against the full 10 Hz log: max temp 37 C
(bound 45). Max settled dwell tracking error **0.815 deg** (bound 5.0). Max
|cmd − measured| at any single tick is 6.10 deg, and every tick above 5 deg
(5 of 2500 in the sweep window, 0.2 %) falls on a commanded fast re-pose ramp at
~10 deg/s, never during a shear dwell or the quasi-static sweep — it is servo lag
behind a deliberately fast slew, which is why the runner compares against a
slewed reference. The same 5.5–7.9 deg ramp lag appears in all three prior clean
runs of this protocol, so it is inherent to the reviewed protocol's ramp rate.

## Robot state at handoff

Idle and limp at logical zero (j16 0.44, j17 0.26), 18/18 live across three
advancing samples, max temp 33 C, max current 0.000 A, bus available and not
quarantined, IMU roll ≈ 0.0 / pitch ≈ 2.1 deg — indistinguishable from the
pre-run baseline, so the chassis never lifted, shifted or tipped. **Zero new
`/api/errors` rows across both successful runs.** No hands-on action is needed.

Observation frames are dim (mean luma 15.2; the room light is on a sensor and
went out mid-run). They are sufficient to confirm the chassis stayed belly-rested
and that L5 alone retracted radially, and bright reference frames from
18:35/19:00/19:07Z document the arena and start pose.

## Next measurement this implies

A torque-matched reversal test on the L5 hip: approach the same commanded angle
from both directions while equalising holding current (e.g. by choosing a knee
compensation that balances the gravity torque at the shared waypoint, or by
approaching from both sides at the arc's mid-load point). That is what separates
mechanical backlash from load-direction-dependent compliance, which this run
deliberately did not claim to resolve.
