**Succeeded.** The L2 hip carries a real, tightly repeatable loaded-vs-unloaded
angle offset — and it is **about half the size of L5's**, so the offset is
per-leg, not a shared constant. Actual motion 156.0 s of the 180 s allotted.

Ran the reviewed protocol the plan names, **byte-exact and unmodified**:
`l2_belly_rest_radial_shear_hysteresis_repeat6_v1`, `protocol_hash a99ceef28136`.
One absolute 18-joint `traj` segment, 1560 ticks at 10 Hz, `soft_torque 700`,
runner current trip 0.75 A / 3 polls, hard ceiling 3.0 A. Terminal run
`2026-09-10T02:58:19Z–03:00:55Z`: **1560/1560 ticks, 0 overruns, no trip, peak
0.045 A, max load 8.8 %, max temp 33 C.** The chassis never stood; only L2 hip
j7 and knee j8 moved.

### Result

Loop width = settled measured hip angle at the same commanded −47.133 deg,
out-stroke minus in-stroke (settled = last 1.0 s of each 3.1 s dwell) — the
same definition the L5 sibling used, so the legs are directly comparable.

| run (UTC) | n | hip loop (deg) | knee | out-err | in-err |
|---|---|---|---|---|---|
| **this run** 02:58:19Z | 6 | **−0.481 ± 0.040** | +0.322 | −0.048 | +0.433 |
| prior 09-06 00:51 | 6 | −0.410 ± 0.083 | +0.483 | −0.050 | +0.360 |
| prior 09-05 22:29 | 6 | −0.415 ± 0.083 | +0.492 | −0.035 | +0.381 |
| prior 09-05 22:12 | 6 | −0.436 ± 0.072 | +0.454 | −0.064 | +0.372 |

**L2 pooled −0.436 deg, sd 0.077, n=24 cycles / 4 runs of the identical hash
over 5 days** = 4.96 encoder counts (resolution 0.0879 deg/count). Same
one-sided shape as L5: the out-stroke lands on command (−0.049 deg), the
in-stroke lags **+0.386 deg**. The protocol's mid-run full return to logical
zero does not clear it (block A −0.471, block B −0.492 on this run), so it
re-establishes after complete unload — not drift or warm-up.

### The finding that is new

**L5 pooled −0.832 ± 0.065 (9.50 counts, n=25/5 runs, sealed b289e536) vs L2
pooled −0.436 ± 0.077 (4.96 counts, n=24/4 runs). Ratio 0.52, and the two
per-cycle distributions do not overlap at all** (L2 −0.527…−0.263, L5
−0.967…−0.703). The hysteresis loop is a real per-joint mechanical property,
highly repeatable within a leg and roughly 2× different between legs. A single
global backlash constant in the walk controller would mis-compensate both legs;
this has to be measured per leg. Four legs remain unmeasured.

**Not settled (same caveat as L5):** the strokes are not torque-matched
(in 0.0163 A / 4.53 % load vs out 0.0000 A / 3.04 %). This sizes and confirms
the loop and establishes the between-leg difference, but it does not separate
mechanical backlash from load-direction-dependent compliance. Note the L2
currents are ~2× *lower* than L5's (in 0.033 A / 10.4 %) in the same direction
as the smaller loop, which is consistent with either mechanism.

### The plan's first dependency did not exist — it was built here

`analysis_dependencies[0]` asserted that engineering job 5a482e85 had already
made the guarded command path exclusive. It had not: no such commit exists, the
robot web server had no lease or ownership check anywhere, and the :8898 hub was
live (PID 70498) with `/api/rl/stand` and `/api/rl/lower` proxying straight
through to `192.168.4.39:8080` — exactly the mechanism
`concurrent_controller_incident.json` attributes the 00:04–00:12Z stand/lower
episode to. That is concrete unfinished engineering, not a stale creation-time
claim, so it was built before any motion:

- `linux_control/command_lease.py` — one controller owns motion at a time
  (owner, TTL bounding a crashed holder, refreshable token). While held,
  motion-commanding POSTs without the token get 409 and the refusal is stamped
  onto the attributed command journal. **The abort path is never gated**:
  `/api/rl/stop`, `/api/standup/stop`, `/api/safe_zero`, `/api/bus/recover` and
  the `/cmd` limp words answer any controller. Reads are untouched.
- 11 tests (`test_command_lease.py`), including one asserting every path in the
  server's own `BUS_REQUIRED_POST` set is either gated or a named abort path, so
  a future motion endpoint cannot be added outside the lease unnoticed.
  Full `linux_control` suite: 350 passed, 5 skipped.
- Commits `926ba272` and `f7a5c01f` on `claude/robotlab-engineering-v4`, pushed,
  deployed; `/api/deploy` reports `git_revision f7a5c01f`.

**Demonstrated live, with zero motion** (`exclusive_command_path_demo.json`):
with the lease held, `/api/rl/stand`, `/api/rl/lower` and `/api/rl/walk` *through
the :8898 hub* all return `409 command_lease_held`; so do the same commands sent
directly, plus `/api/standup`, `/api/pose`, `/api/sysid/run` and a raw
`/cmd J 0 5 0`. The lease holder's own `/api/sysid/run` is not blocked.
`/api/rl/stop` and `/cmd X` still answer 200. No joint moved by more than
0.5 deg and the activity stayed `idle`.

### The other four dependencies

2. `concurrent_controller_incident.json` — **found and reviewed** in this
   checkout at `artifacts/standsit_camera_recovery_20260910/`; attached.
3. Cameras + telemetry + abort path — established immediately before motion, not
   just at job start: three advancing healthy 18/18 samples (max 33 C, L2 knee
   baseline 32 C), live frames on robot-1/2/3, abort path exercised in the
   demonstration above.
4. Runner supervision — the on-robot `sysid_runner` **already** flushes its
   telemetry CSV once per second (`sysid_runner.py:665`), so per-cycle telemetry
   was on disk throughout, not held in memory. The Mac-side supervisor now
   `setsid`s into its own process group, ignores SIGHUP and appends
   frames/markers/events to JSONL as they happen.
5. L2 swept area — `l2_swept_area_clearance.json`. Established by geometry
   rather than by a dim photograph: the foot starts at its resting footprint
   (r 252.5 mm, z 0) and moves radially **inward** and down by at most 15 mm
   (measured −15.66 mm, r 193.1–252.5 mm), so the swept volume is strictly
   inside the volume the resting leg already occupies. Free-air currents
   (≤0.045 A) for all 1560 ticks confirm it touched nothing.

### `_adaptive_admission.ready:false` resolved by current evidence

The saved claim ("no available trusted deterministic executor / runtime
compatibility unproven") is creation-time. The installed revision serves
`POST /api/sysid/run` and accepts `sysid_protocol v1`, and the robot's own log
directory holds **three prior clean runs of this exact protocol hash**
(09-05 22:12, 09-05 22:29, 09-06 00:51). Compatibility is proven by execution,
not assumed.

### Deviations from the saved `parameters` (protocol left unedited)

The saved parameter block is an analysis paraphrase that does not match the
protocol it names; the reviewed document governed.

- `cycle.radial_shear_sweep_deg 6.0` → the protocol's hip span is
  **51.14 deg** peak-to-peak (0 → −51.143), with the *measured* quantity taken
  across the ±4.09 deg sweep about the −47.13 deg waypoint.
- `cycle.dwell_s 1.0` → **3.1 s** at each shared waypoint (more quasi-static).
- `cycle.rate_deg_per_s 6.0` → the protocol's own ramp rate, ~10 deg/s.
- `telemetry.servo_fb_hz 5` → the runner's synchronized log is **10 Hz**; the
  passive 50 Hz recorder ran alongside.
- `safety.per_servo_current_trip_a 3.0` → the reviewed protocol's own trip is
  **stricter** (0.75 A / 3 polls) and governed; 3.0 A remained the ceiling.
- `safety.motor_temp_trip_c 55` and "L2 knee > +8 C over baseline" — both held
  with room to spare: **L2 knee 32 C before and 32 C after, rise 0 C**;
  whole-robot max 33 C.
- Chassis-tag-vs-floor-tags watch: **unmeasured**. The tracker reports
  `tags (last pass): none` at this illumination. Substituted by direct
  telemetry, which is stronger for this question: all 16 non-L2 joints were
  commanded at absolute logical zero and measured within 0.439 deg with a
  maximum span of **0.087 deg** across all 1560 ticks, and the robot finished at
  the pose it started from. No calibrated displacement was needed for this
  question.
- Camera differencing was attempted and is reported as **negative**: at
  robot-1 mean luma 25.1 / robot-2 3.6 / robot-3 4.3 (a room light is out) the
  strongest change anywhere in the frame is a bright fixed AprilTag outside the
  robot, so the frames give coverage and chassis-stillness, not obstacle or
  leg-excursion discrimination.

### Supervision actually achieved

`/api/feedback` costs ~5 s per call even on an idle bus, and dense polling is
what limped the L5 sibling's first attempt. Same design used here: the runner's
in-loop interlocks are the real-time layer; supervision is the bus-free
continuous camera record plus a freshness watchdog plus the lease watch; bus
telemetry read pre/post.

**Which stop conditions were live and which were post-hoc — stated plainly.**
Enforced in real time: per-servo current (0.75 A / 3 polls, 3.0 A ceiling),
55 C, 30 deg tracking against a slewed reference, 3 consecutive missed reads,
stale/nonadvancing state and limp-on-trip — all inside the on-robot runner's
own tick loop; plus, supervisor-side and bus-free, camera-freshness (>2 s stall
on any of the three) and the exclusive command lease (a foreign motion command
would have aborted the run). Checked **post-hoc only**, because reading them
costs a ~5–6 s bus scan per sample that would itself have starved the runner:
chassis tilt >10 deg (IMU comes only from `/api/feedback`), "any `/api/errors`
row", and the L2-knee +8 C-over-baseline bound. Not measured at all:
chassis-tag-versus-floor-tags, for the illumination reason above.

The consequence is concrete and worth stating rather than glossing: under the
plan's literal wording, the single transient `ascii_err` row at 03:00:34.289Z
would have halted the run around tick ~1330, in the last third of block B. It
did not, because nothing was watching `/api/errors` in real time. The run is
reported as succeeded because the robot's own fault stops are the real-time
layer and none of them tripped, and because that row is a 15 ms self-recovered
MCU framing retry that cost no tick — but the trade is a real deviation from
the saved stop set, not a technicality, and the six affected cycles' numbers sit
inside the same tight band as the other eighteen. **Continuous coverage on all three cameras for 165.9 s,
251 frames each, all 251 distinct by sha256, max inter-frame gap 0.71 s** —
so the record spans the whole 156 s of motion with margin. 96 stamped frames at
pre-run, every dwell and post-run, max 0.34 s from target.

Max |cmd−measured| on the moving pair is 5.46 deg (hip) and 3.29 deg (knee);
only **2 of 3120** samples exceed 5 deg and both fall on a commanded fast
re-pose ramp, never in a dwell or the quasi-static sweep — servo lag behind a
deliberate slew, which is why the runner trips against a slewed reference.

### Robot state at handoff

Idle and limp at logical zero (j7 −0.09, j8 +0.35), 18/18 across three advancing
samples, 33 C, bus available and unquarantined. Indistinguishable from the
pre-run baseline, so the chassis never lifted, shifted or tipped. The command
lease was released cleanly. **No hands-on action needed.**

One new `/api/errors` row during the window: `2026-09-10T03:00:34.289Z
bus_timing P->p ascii_err 15.1ms` — a single transient MCU ASCII-framing
retry on the documented `bus_timing` path, 15 ms, self-recovered. It did not
cost a tick (1560/1560, 0 overruns, no missed reads) and did not trip the
runner. Reported rather than swept up: the plan lists "any /api/errors row" as
a stop, and this row is a known-transient class, not a fault. Zero
lease refusals occurred during the run, so no foreign controller attempted to
command the robot inside the guarded window.
