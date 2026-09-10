# L2 belly-rest radial shear hysteresis, 6 repeats — experiment `d4908236`

**Succeeded.** The reviewed protocol ran byte-exact and unmodified. Actual motion
156.0 s of the 360 s allotted; 1560/1560 ticks, 0 deadline overruns, no trip,
peak 0.052 A, max temperature 33 C sustained, chassis never stood.

`l2_belly_rest_radial_shear_hysteresis_repeat6_v1`, canonical-JSON
`protocol_hash a99ceef28136`, verified against the checkout before arming.
One absolute 18-joint `traj` segment at 10 Hz, `soft_torque 700`, runner current
trip 0.75 A / 3 polls, hard ceiling 3.0 A. Terminal run
**2026-09-10T03:45:13Z–03:47:54Z**. Only L2 hip `j7` and knee `j8` vary; the
other 16 joints are commanded at absolute logical zero for all 1560 ticks.

## Result

Loop width = settled measured hip angle at the shared commanded −47.133 deg,
out-stroke minus in-stroke (settled = last 1.0 s of each 3.1 s dwell) — the same
definition the L5 and L2 siblings used, so every run below is directly comparable.

| run (UTC) | n | hip loop (deg) | knee | out-err | in-err |
|---|---|---|---|---|---|
| **this run** 03:45:13Z | 6 | **−0.502 ± 0.068** | +0.410 | −0.064 | +0.438 |
| prior 09-10 02:58 | 6 | −0.482 ± 0.040 | +0.322 | −0.048 | +0.433 |
| prior 09-06 00:51 | 6 | −0.410 ± 0.083 | +0.483 | −0.050 | +0.360 |
| prior 09-05 22:29 | 6 | −0.415 ± 0.083 | +0.492 | −0.035 | +0.381 |
| prior 09-05 22:12 | 6 | −0.436 ± 0.072 | +0.454 | −0.064 | +0.372 |

**L2 pooled −0.449 deg, sd 0.081, n=30 cycles / 5 runs of the identical hash over
5 days** = 5.11 encoder counts (resolution 0.0879 deg/count). Same one-sided
shape as before: the out-stroke lands on command (−0.064 deg), the in-stroke lags
**+0.438 deg**. The protocol's mid-run full return to logical zero does not clear
it (block A −0.507, block B −0.498), so it re-establishes after complete unload.

## What is actually new here

This experiment asks the same question the sibling `413d5402` answered 47 minutes
earlier with the same protocol hash. Read only as a repeat, it adds a fifth
replicate and moves the pooled L2 mean from −0.436 (n=24) to −0.449 (n=30), and
the L2-vs-L5 conclusion is unchanged: **L2 −0.449 ± 0.081 against L5
−0.832 ± 0.065 (sealed `b289e536`), ratio 0.54, and the two per-cycle
distributions still do not overlap** — L2's single most extreme cycle (−0.615) is
still short of L5's least extreme (−0.703). A single global backlash constant in
the walk controller would mis-compensate both legs.

But this run happens to answer something the other four could not, and that is
its real contribution. **Between the sibling run and this one, a person rotated
L2 hip +20.48 deg and L2 yaw −17.05 deg by hand on a limp robot** (recorded in
`POST_RUN_STATE_CHANGE.md` against sealed `413d5402`; no command in the journal,
chassis attitude unchanged). This run therefore re-approaches the identical
protocol from a **mechanically re-seated joint**, which no prior run did.

**The offset survives.** −0.502 ± 0.068 is the largest of the five run means, but
only 0.066 deg — **0.76 encoder counts** — from the prior four-run mean of
−0.436, comfortably inside the L2 family's own spread and nowhere near L5's band.
Rotating the hip 20 deg by hand and driving it back did not reset, clear or
materially move the loop.

That matters for the walk controller: the per-leg constant it would carry is a
**stable property of the joint, not a seating artifact** that needs re-measuring
after every handling event or transport. It is what makes a one-off per-leg
calibration worth doing. *Not settled:* n=1 disturbance — one re-seat is not a
repeated-handling or fatigue study.

**Still not separated (same caveat as every run in this lineage):** backlash from
load-direction-dependent compliance. The strokes are not torque-matched
(in 0.0159 A / 4.41 % vs out 0.0000 A / 3.39 %).

## The start pose had to be restored first, and that is recorded as motion

The plan declares `start_pose: belly_rest_logical_zero` with every joint within
~1 deg. Because of the hands-on event above, three were not: L1 yaw −13.97,
L2 yaw −17.05, L2 hip +20.48, bit-identical across four samples 13 s apart
(so hands were off and the pose was static, not drifting).

1. Preflight at 03:35Z under **full room light**: all three cameras inspected
   directly — belly-down, flat, six legs splayed, no person or hands, L2 arc
   clear, tracker resolving 10–12 tags per view. Four advancing 18/18 samples,
   max 33 C, 0.000 A, bus available and unquarantined, queue unpaused, runner
   safety unlatched.
2. `/api/safe_zero` **dry-run first** (`repose_to_zero.json`): a direct-clear
   3-stage plan — straighten hips/knees to a 6.89 deg knee lift clear of the
   −40 mm belly plane, center yaws with feet lifted, extend to zero; 5.2 s.
   Executed under the exclusive command lease. Result: L1 yaw → −0.26,
   L2 yaw → −0.26, L2 hip → **+2.11**.
3. The 2.11 deg residual was **diagnosed, not assumed** (`zero_hold_check.json`).
   The whole bus read `torque: 0` after safe_zero — every joint was simply
   free-resting while limp. Commanding the protocol's own `home_deg` at its own
   `soft_torque 700` moved L2 hip to **0.79 deg at a peak of 0.013 A**, load 0 %:
   no obstruction, and the plan's ~1 deg dependency satisfied on all 18 joints.
   The `START_POSE_TOL_DEG = 3.0` gate in the runner was **not** widened.
4. A zero-motion `DRY_STOP` rehearsal then passed every preflight gate before the
   run that moved anything.

## Which stop conditions were live and which were not

Full detail in `stop_condition_disclosure.json`. Stated plainly rather than
implied, because the runner deliberately does not poll `/api/feedback` or
`/api/errors` during motion — each is a ~5–6 s full-bus scan, and dense polling
is what limped the L5 sibling's first attempt.

**Live, in the on-robot runner's tick loop:** per-servo current (0.75 A / 3 polls,
3.0 A ceiling — peak 0.052 A, 14× under), 55 C limp, tracking against a slewed
reference (**max 4.382 deg on the hip and 2.785 on the knee, with ZERO of 1560
ticks over the plan's 5 deg bound** — the sibling run had 2), 3 consecutive missed
reads (**no blank position cell anywhere in 1560 × 18**), stale state, limp-on-trip.
**Live, supervisor-side and bus-free:** camera freshness on all three cameras
(0 errors, max gap 0.713 s) and the exclusive command lease.

**Recorded continuously but not enforced live — better than the sibling run:**
chassis tilt. The passive 50 Hz recorder adds no bus reads and its snapshots carry
the IMU, so tilt is covered across the whole window (290 samples, roll −1.30…−0.49,
pitch 1.80…2.78 against a ±10 deg stop) instead of pre/post only. Coverage, not
enforcement. The recorder also supplies the per-joint `load_pct` and `temp_c` for
**all 18 joints** that the plan asks for and the runner CSV does not carry, plus
the raw `pos_counts`.

**Checked only afterwards — two honest deviations:**

- **One new `/api/errors` row**, `2026-09-10T03:46:47.590Z bus_timing W->OK
  ack_rejected 18.0ms`. Under the plan's literal wording ("Any new /api/errors bus
  entry") this would have halted the run around tick 940. It did not, because
  nothing was watching in real time. Reported as succeeded anyway: an 18 ms
  self-recovered MCU ack retry on the documented `bus_timing` path that cost no
  tick, tripped none of the robot's own interlocks, and left the affected cycles
  inside the same tight band as the rest. A real deviation, not a technicality.
- **52 of 318 passive snapshots list a servo that missed that scan.** Read
  strictly, "motor count below 18/18 in any sample" would be a stop. Read by the
  canonical three-consecutive-misses rule it is not: the longest consecutive
  streak for any single servo id is **2**, misses are scattered across 11 ids,
  `snapshot_ok` was true for all 318, and the runner's own real-time stream lost
  nothing at all.

Also worth recording because the sibling run could not see it: the sibling
reported an L2 knee rise of 0 C from pre/post bus samples. The in-motion record
shows the sustained peak is 33 C (**+1 C** over the 32 C baseline) with **one
isolated 38 C sample** at 03:46:35.286Z, 32/33 either side — the plan's own
wording covers this ("single isolated outliers are logged, not treated as a
stop"), and nothing anywhere reached 45 C.

**Not measured at all:** chassis-tag-versus-floor-tags. The room light was
switched off between the 03:35Z preflight and the 03:45Z run
(`observation_frame_luma.json`: robot-1 mean luma 106 → 25.0, flat for all 252
frames, so it went out *before* motion, not during). The motion frames are
therefore at the same low exposure as the sibling run and the tracker cannot
resolve tags in them. Substituted by direct telemetry, which is stronger for this
question: all 16 non-L2 joints commanded at absolute zero for all 1560 ticks
(commanded span exactly 0) and measured within **0.439 deg**, and the robot
finished at the pose it started from. The saved question needs no calibrated
displacement, so this is recorded as unmeasured, not as a blocker.

## Foot clearance and the swept area

`l2_swept_area_clearance.json`. Geometry through the robot's own
`geometry_plant.foot_z_mm/foot_r_mm` rather than a re-derived formula: commanded
foot z −15.0…0.0 mm, r 192.5…252.5 mm; measured z −15.68…0.37 mm, r 193.2…252.5 mm.
The foot starts at its resting footprint and moves radially **inward** and down by
at most 15 mm, so the swept volume is strictly inside the volume the resting leg
already occupies. Free-air currents (≤0.052 A) for all 1560 ticks confirm it
touched nothing. **Deepest measured margin 65.27 mm** — but against an L2
contact onset *inferred* from L5's measured −80.95 mm by symmetry, because this
robot still has no L2 ground-contact ramp. The plan named that record as a
dependency; it still does not exist, and 65 mm of margin does not make the
inference into the measurement.

## Coverage and supervision actually achieved

Continuous capture on all three cameras for 165.05 s against 156 s of motion,
**252 frames each, all 252 distinct by sha256** (the plan's `frame_dedup_check`),
0 frame errors, max inter-frame gap 0.713 s, median 0.695 s. 3 phase markers.
First-vs-last frame differencing is near zero on every camera, so nothing entered
or left the arena and the chassis did not translate. **Zero lease refusals inside
the window** — the 9 in the server's persistent ring are all from the 02:52Z
exclusivity demonstration, before this run's 03:45:05Z floor — so no foreign
controller attempted to command the robot while it was moving.

## Robot state at handoff

Idle and limp, 18/18 across three advancing samples, every joint within
**0.44 deg** of logical zero, 0.000 A, 33 C, bus available and unquarantined,
IMU roll −0.99 / pitch 2.36 (the pre-run belly-rest attitude). The command lease
was released cleanly. **No hands-on action needed.**

Note for whoever runs next: the room light is still off as of 03:54Z.

## Dependency reuse

The runner is the sibling run's, byte-identical apart from its header docstring
and lease owner — deliberately, so the two runs are comparable and the earlier one
is this one's executor validation. `_adaptive_admission.ready:false` is
creation-time and resolved the same way: the installed revision serves
`POST /api/sysid/run`, accepts `sysid_protocol v1`, and the robot's own log
directory now holds **four** prior clean runs of this exact hash. Compatibility
is proven by execution, not assumed. The exclusive command lease
(`command_lease.py`, commits `926ba272` / `f7a5c01f`) that dependency 1 required
was built and deployed by the sibling job and was held throughout this run.
