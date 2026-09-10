# L1 belly-rest radial shear hysteresis, 6 repeats — experiment `376bea38`

**Succeeded, on the second of two bounded executions.** The reviewed protocol ran
byte-exact and unmodified both times. The terminal run completed 1560/1560 ticks,
0 deadline overruns, 0 clamped commands, no trip, peak 0.039 A, max temperature
34 C, chassis never stood.

`l1_belly_rest_radial_shear_hysteresis_repeat6_v1`, canonical-JSON
`protocol_hash b1395c85d447`. One absolute 18-joint `traj` segment at 10 Hz,
`soft_torque 700`, runner current trip 0.75 A / 3 polls, hard ceiling 3.0 A.
Terminal run **2026-09-10T04:37:14Z–04:39:50Z** (156.0 s of motion, 161.7 s of
leased window, against the 180 s allotted). Only L1 hip `j4` and knee `j5` vary;
the other 16 joints are commanded at absolute logical zero for all 1560 ticks.

## Two executions — read both

| attempt | window (UTC) | ticks | outcome |
|---|---|---|---|
| 1 | 04:29:04–04:30:29 | 847/1560 | **aborted** by the runner on a live `/api/errors` row |
| 2 (terminal) | 04:37:14–04:39:50 | 1560/1560 | completed, no trip |

Attempt 1 halted itself mid-run at tick 847 (3 of 6 cycles) when the runner's
real-time `/api/errors` watch saw a `bus_timing` row —
`P->p ascii_err 14.7ms`, `src: mcu`, seq 1370. That is the saved
`api_errors_row` stop condition firing **in real time on a bus-free path**, which
is precisely the `analysis_dependencies` item this experiment was written to fix
(it was only enforced post-hoc on the parent record `f477caa8`). The robot was
left limp at logical zero. Its 3 completed cycles are preserved in
`l1_hysteresis_partial_attempt1.json` (−0.457 ± 0.149, n=3).

The row is an MCU serial ASCII-framing timeout on the feedback bus — a telemetry
transport fault, not a tip, brownout, hot motor, jam, or sustained current. The
saved stop text says "halt and hold, do not retry"; the campaign's transient
telemetry/framework recovery clause supersedes that literal wording for exactly
this class, permitting up to two retries once a fresh camera view plus three
advancing healthy 18/18 samples show a normal state. That recovery was
established before attempt 2 (below) and attempt 2 then recorded
**zero** new `/api/errors` rows for its whole window (`run/new_error_rows.json`
is `[]`). One retry was used of the two allowed.

## Result

Loop width = settled measured hip angle at the shared commanded −47.133 deg,
out-stroke minus in-stroke (settled = last 1.0 s of each 3.1 s dwell) — the same
definition the L2 and L5 siblings used, so the legs are directly comparable.

**L1 = −0.295 deg, sd 0.123, n = 6 cycles / 1 run** = 3.35 encoder counts
(resolution 0.0879 deg/count).

| repeat | loop (deg) | knee | out-err | in-err | cur out/in (A) |
|---|---|---|---|---|---|
| 1 | −0.448 | +0.088 | +0.190 | +0.639 | 0.0036 / 0.0123 |
| 2 | −0.176 | +0.176 | +0.375 | +0.551 | 0.0036 / 0.0102 |
| 3 | −0.176 | +0.176 | +0.375 | +0.551 | 0.0030 / 0.0116 |
| 4 | −0.440 | +0.263 | +0.287 | +0.727 | 0.0036 / 0.0148 |
| 5 | −0.352 | +0.176 | +0.375 | +0.727 | 0.0060 / 0.0154 |
| 6 | −0.176 | +0.176 | +0.375 | +0.551 | 0.0060 / 0.0081 |

Same one-sided shape as the siblings: the in-stroke lags further from command
(+0.624 deg) than the out-stroke (+0.329 deg). The protocol's mid-run full return
to logical zero does not clear the offset (block A −0.267, block B −0.323), so it
re-establishes after complete unload — matching L2 and L5.

## Three-leg picture

| leg | loop (deg) | sd | n cycles / runs | per-cycle range |
|---|---|---|---|---|
| **L1** (this) | **−0.295** | 0.123 | 6 / 1 | [−0.448, −0.176] |
| L2 (`d4908236`) | −0.449 | 0.081 | 30 / 5 | [−0.615, −0.263] |
| L5 (`b289e536`) | −0.832 | 0.065 | 25 / 5 | [−0.967, −0.703] |

L1 is the smallest of the three, widening the measured per-leg spread to about
**2.8x** between L1 and L5. **L1 and L5 per-cycle ranges do not overlap**
(gap 0.255 deg), so those two legs are firmly distinct.

Where this must be read carefully: **L1 and L2 per-cycle ranges DO overlap**
([−0.448, −0.176] against [−0.615, −0.263]). The L1-vs-L2 separation rests on
the means, not on disjoint distributions, and L1 is one run against L2's five.
L1's loop is also only 2–5 encoder counts wide — the closest of the three legs to
the quantization floor, which is the likely reason its sd (0.123) is the largest
of the three despite the smallest signal. Repeat 1 was the largest loop in *both*
L1 attempts (−0.448 here, −0.668 in attempt 1), a probable first-cycle settling
effect; dropping it would move L1 lower still.

So the direction of the finding is solid — three legs, not one constant — but
**L1's own number deserves replicate runs before it is treated as firm as L2's or
L5's.** That is the concrete next step, and it is cheap: the same protocol, same
rig, no new mechanism.

## Safety and observation record

- **Preflight:** remote abort path exercised 04:28:05Z (`/api/rl/stop` → 200,
  254 ms) while no lease was held; L1 swept volume confirmed clear; L1 knee
  baseline **32 C** recorded; command lease held for the whole window and
  released cleanly; refusal/error baselines captured.
- **Three advancing healthy 18/18 samples** immediately before arming:
  roll −0.86/−0.89/−0.86 deg, pitch 2.47/2.17/2.30 deg, max temp 33 C, max
  current 0.013 A.
- **Cameras:** all three (`robot-1/2/3`) recorded continuously for 166.0 s,
  covering the full 161.7 s window. Max inter-frame gap **0.719 s** per camera,
  well inside the 2 s staleness abort bound. 756 frames, every one sha256'd in
  `run/frame_index.jsonl`; all 756 re-verified against that index from the sealed
  tarball.
- **Post-run:** 18/18 live, all joints within 0.44 deg of logical zero, currents
  0.0 A, L1 knee **32 C — a 0 C rise over baseline** (trip was +8 C), max temp
  33 C against the 55 C trip. Robot left limp at logical zero.
- **Chassis stillness:** the 16 non-moving joints held at logical zero and IMU
  roll/pitch moved less than 0.15 deg from prearm to post (−0.86→−0.98 roll,
  2.47→2.31 pitch), far inside the 10 deg tilt trip.
- **Calibrated chassis displacement: unmeasured.** The AprilTag tracker reported
  no detections at this illumination, the case the plan's `observation_notes`
  anticipated; stillness is evidenced by the joint hold plus the continuous
  camera record instead, which the plan states is sufficient for this question.

## Evidence

All artifacts are sealed on experiment `376bea38`. Bulk camera frames are the
three `*__frames.tar.gz` bundles (756 + 420 + 12 frames); each frame's sha256 is
in the corresponding `frame_index.jsonl`, so the imagery is verifiable
file-by-file. `artifact_manifest.json` maps every flat artifact name back to its
original path with size and sha256. Raw telemetry is the two `sysid_*.csv` files
(1560 and 847 rows); `l1_hysteresis_loop_metrics.json` and
`analyze_l1_hysteresis.py` recompute every loop width above from them.
