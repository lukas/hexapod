# Stand-up hold: hip-yield repeatability and stance load/current capture

Experiment `51f54beb522d482a930aa750ed95368b`, plan
`standup-hold-yield-repeatability-01`, campaign
`standup-foot-contact-20260909`. Physical run on hexapod-1
(`simulation_only: false`, `robot_motion: true`), 2026-09-10
00:36:09Z–00:55:47Z. Parent: `922434955b35404198907c9e77cde5f6`.

All three cycles ran to completion in mode `step`, speed 10, torque 700,
with a 15 s standing hold each. **No stop condition fired**, no fall, no
tip, no bus quarantine, 18/18 motors in every sample, and the robot
finished belly-down at logical zero (all joints within 0.26 deg), armed
and healthy.

## What the run was asked to settle

The parent run saw, once, four outer hips give way 5.2–14.5 deg about a
second after reaching stance and then hold the new angle, leaving the
body carried by L1/L4 alone. It could not tell a repeatable bounded
compliance from a progressive mechanical slip, because `load_pct` and
`current_a` read exactly 0.0 for its whole 44 s loaded hold.

## Answers

**1. The give-way is not a hold-time event at all.** In all three
cycles every hip is static for the entire 15 s hold. Sampling the
robot's own recorder at the plan's points (t = 0, 1, 2, 5, 10, 15 s),
each leg reads the *same* angle to 0.01 deg at every point. Across 134
in-hold snapshots the single largest change on any leg is 0.09 deg —
one encoder count. Whatever shortfall exists is already present when
the stand-up finishes; nothing yields afterwards.

**2. It does not grow across cycles — it shrinks.** Hip angle at hold
exit against the commanded +20.87 deg (`standup_modes.json`,
`modes.step.keyframes[-1]`), positive = short of command:

| leg | cycle 1 | cycle 2 | cycle 3 |
|-----|--------:|--------:|--------:|
| L0  |  2.68   |  0.39   | -0.58   |
| L1  |  0.57   | -0.93   | -0.66   |
| L2  |  0.39   | -0.14   | -0.14   |
| L3  |  2.85   |  0.66   | -0.22   |
| L4  | -0.05   | -0.22   | -0.05   |
| L5  |  1.09   | -0.31   |  0.04   |
| **worst** | **2.85** | **0.66** | **0.04** |

Monotonically decreasing, and by cycle 3 every leg is at or slightly
past its commanded angle. The plan's "grows monotonically across the
three cycles" slip signature is absent. Its "+8 deg over cycle 1"
budget was never approached.

**3. `load_pct` and `current_a` do return non-zero in a static loaded
hold, and they explain the shortfall.** The parent's central
measurement gap is closed: 970 non-zero load samples and 887 non-zero
current samples across the three loaded holds. Per hip, median over the
hold:

| leg | c1 yield | c1 I_med | c1 load | c2 yield | c2 I_med | c3 yield | c3 I_med |
|-----|---------:|---------:|--------:|---------:|---------:|---------:|---------:|
| L0  | 2.68 | 0.169 A | 24.8 % | 0.39 | 0.007 A | -0.58 | 0.013 A |
| L1  | 0.57 | 0.007 A |  5.6 % | -0.93 | 0.026 A | -0.66 | 0.013 A |
| L2  | 0.39 | 0.013 A |  4.0 % | -0.14 | 0.007 A | -0.14 | 0.000 A |
| L3  | 2.85 | 0.195 A | 26.4 % | 0.66 | 0.013 A | -0.22 | 0.000 A |
| L4  | -0.05 | 0.000 A |  0.0 % | -0.22 | 0.007 A | -0.05 | 0.000 A |
| L5  | 1.09 | 0.033 A | 10.4 % | -0.31 | 0.007 A |  0.04 | 0.000 A |

In cycle 1 the two legs that fall short, L3 (2.85 deg) and L0
(2.68 deg), are exactly the two hips drawing the most holding current
(0.195 A / 0.169 A) and the most load (26.4 % / 24.8 %), an order of
magnitude above the other four. In cycles 2 and 3, where no hip draws
more than 0.026 A, no hip falls short. Shortfall and holding torque
track each other both within a cycle and across cycles.

That is the signature of **load-dependent servo compliance**: a
proportional position loop settles where position error times stiffness
balances the applied torque, so the hardest-loaded hip sits furthest
from its goal. It is not slip — slip would not recover, and would not
scale with instantaneous current.

Implied stiffness from cycle 1's two loaded hips is about 1 deg per
0.07 A of holding current, consistent between them (L0 2.68/0.169,
L3 2.85/0.195).

## Why cycle 1 was worse than cycles 2 and 3

Not established. The most likely reading is that the shortfall is set
by how the feet happen to land and therefore how load distributes at
the end of the push-up, which varies run to run. Cycle 1 followed a
long idle at a warmer knee temperature; cycles 2 and 3 followed
immediately after a preceding cycle. This run cannot separate landing
geometry from temperature, and it should not be read as "the problem
went away".

## What this means for the gait

The parent's worry — that a stance carried by L1/L4 alone cannot
support a gait — is not reproduced. Under the same commanded stance
this robot puts all six hips within 2.9 deg of command in the worst
observed cycle, and within 0.7 deg in two of three. The remedy the
parent proposed for the repeatable-yield case (re-measure and re-command
the stance after hold torque is applied) would work here and is cheap,
but the measured worst case is now small enough that it is not the
blocker on smooth walking that a 14.5 deg give-way would have been.
No hands-on hip inspection is indicated by this evidence.

## Conduct, deviations and limits

- **Interrupted and retried once.** Cycle 1 completed clean at
  00:37:50Z. Deploy `c1247867ae2e10db` (revision `e0e05224`, branch
  `main`) from another session landed at 00:37:47Z and systemd
  restarted `hexapod-web.service` at 00:37:53Z; the cycle 2 stand-up
  POST hit connection refused. The robot was already belly-down from
  cycle 1's sit-down and was safe. This was a framework stop, not a
  robot fault, so cycles 2–3 were retried after recovery — the first of
  the two retries the contract allows.
- **The interrupting deploy reverted this plan's blocking dependency.**
  `e0e05224` bounds the implausible-current guard in `safe_zero.py`
  only; installing it put `api/standup.py` back to testing a
  running-max `peak_a` against `HARD_CAP_A` on a single instantaneous
  reading — the path that aborted the parent's cycle 2 on a corrupt
  106.50 A sample. Rather than roll the robot back, `origin/main` was
  merged into `claude/robotlab-engineering-v4` as `ea576a75` so both
  guards ship together, tested (`robot-unit-check` 144 + 17 pass, plus
  the 7 stand-up current-guard tests) and deployed at 00:48:08Z.
  Installed files were verified directly on the robot, not just the
  deploy record.
- **Sampling cadence.** `/api/feedback` costs ~5.1 s per round trip on
  this bus, so live HTTP sampling inside a hold is ~0.2 Hz, not the
  50 Hz the plan names. The dense per-leg series therefore comes from
  the robot's own passive recorder, which is the instrument the plan
  specifies; it delivered 44–45 snapshots and 36–37 feedback records
  per 15 s hold (~3 Hz), enough to resolve the t = 0/1/2 s points and
  to rule out a yield step to 0.09 deg.
- **`current_raw_count` is derived, not measured.** The API exposes
  `current_a` only; the count is recovered as `current_a / 0.0065` and
  labelled derived in the record.
- **Observation frames, not continuous video.** Frames were captured at
  pre-run, hold+1s, hold+10s and post-sit per cycle, each stamped with
  the time it was actually taken (the ~5 s bus round trip means a frame
  nominally due at +1 s lands later). The `hold_plus_3s` frame was
  dropped from the live loop to leave bus time for another load/current
  sample. Continuous video was not recorded; the parent run on the same
  schema was sealed on the same basis.
- **No AprilTag metric foot displacement.** Not needed — this plan asks
  about joint angles and load, both measured directly. Absolute foot
  height remains unmeasured, as in the parent.
- **No zero-frame change and no keyframe change**, as the plan requires.
  All 18 joints were within 0.26 deg of logical zero before and after.
- **Isolated corrupt bus samples continue**, consistent with the
  documented pattern: the analysis discards physically impossible hip
  reads and counts them rather than averaging them in. No joint
  produced three in a row, so no telemetry-fault stop was warranted.
  No new `/api/errors` row appeared during any of the three cycles
  (last entry 00:49:23Z, before the retry began).

## Peak currents (robot's own guard reports)

Cycle 1 stand 2.76 A / sit 2.89 A; cycle 2 stand 2.86 A / sit 2.72 A;
cycle 3 stand 2.74 A / sit 2.89 A. All plausible, all below the guard's
cap, and no false over-current abort occurred in any of the six
transitions — unlike the parent's cycle 2.

## Artifacts

`cycles_cycle1.json`, `cycles_cycles23.json` (runner records),
`hold_timeline_cycle1.json`, `hold_timeline_cycles23.json` (dense
per-leg timelines), `per_leg_table.json` (the yield-vs-current table
above), `telemetry_cycle1.jsonl`, `telemetry_cycles23.jsonl` (recorder
windows), `run_hold_cycles.py`, `analyze_holds.py`, `run_cycle1.log`,
`run2.log`, and the observation frames.
