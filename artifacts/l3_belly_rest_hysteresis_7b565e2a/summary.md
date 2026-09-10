# L3 belly-rest radial shear hysteresis, 6 repeats — experiment `7b565e2a`

**The run completed on the first attempt: 1560/1560 ticks, all six measured
cycles, no trip, not one `/api/errors` row, robot left limp at logical zero.
L3's loop width is −0.674 deg (sd 0.066, n = 6 cycles / 1 run), and the whole
of that sd is a single 2-encoder-count difference on cycle 1 — cycles 2 to 6
are byte-identical at −0.703 deg.**

The plan's hypothesis was that L3 would fall into one of the two brackets the
family had established. **It does not, and this single run cannot settle where
it does belong.** That is the substantive result and it is worked through below.

## Result

Loop width = settled measured hip angle at the shared commanded −47.133 deg,
out-stroke minus in-stroke (settled = last 1.0 s of each 3.1 s dwell) — the
identical definition L0, L1, L2 and L5 used, so the numbers are directly
comparable.

| cycle | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| loop (deg) | −0.527 | −0.703 | −0.703 | −0.703 | −0.703 | −0.703 |
| loop (counts) | 6.0 | 8.0 | 8.0 | 8.0 | 8.0 | 8.0 |

**L3 = −0.674 deg, sd 0.066, n = 6 cycles / 1 run** — the statistic directly
comparable to the other legs. The settled value from cycle 2 onward is
**−0.703 deg = exactly 8.0 encoder counts** at 0.0879 deg/count.

### The sd is one 2-count event, and it is on the loaded stroke only

Checked rather than reported. All **12** settled windows hold a *single* value
across all ten of their 10 Hz samples (sd 0.000 in every window), and each of
those values sits within 0.06 counts of an exact encoder count:

- **out-stroke: −47.285 deg (count 538) in all six cycles** — identical every time.
- **in-stroke: −46.758 (count 532) on cycle 1, then −46.582 (count 530) on cycles 2–6.**

So the only quantity that varies anywhere in the run is where the *loaded*
in-stroke settles on the first cycle, and it varies by exactly 2 counts.
538−532 = 6 counts; 538−530 = 8 counts. The loop widths are exact count
differences, not averages of a drifting joint.

**This is not presented as a seating effect, because the family's own data do
not support that reading.** Per-cycle loops exist for three other runs and the
first-cycle behaviour is inconsistent: L1 run 1 is −0.641 against a −0.352 mode
and its parent run is −0.448 against a −0.176 mode (both *wider* on cycle 1),
L2 shows no first-cycle outlier at all, and L0's six cycles are identical. L3's
cycle 1 is *narrower*. One 2-count event in one run is a fact about this run,
not an established mechanism.

### Where L3 sits — and why one run cannot place it

| leg | loop (deg) | counts | sd | n cycles / runs |
|---|---|---|---|---|
| L1 | −0.330 | 3.8 | 0.153 | 18 / 3 |
| L2 | −0.4357 | 5.0 | 0.077 | 24 |
| **L3 (this run)** | **−0.674** | **7.7** | **0.066** | **6 / 1** |
| L5 | −0.832 | 9.5 | 0.065 | 25 |
| L0 | −0.967 | 11.0 | 0.000 | 6 / 1 |

L3 lands **between** the two brackets: 0.238 deg above L2 and 0.158 deg below
L5. The L2→L3 gap is the largest gap anywhere in the five-leg series, and the
L3→L5 gap (0.158) is *larger* than the L5→L0 gap (0.135) that sits **inside**
the supposed high bracket. On the numbers alone the two-bracket picture does
not survive L3; five legs read as a graded ladder — 3.8, 5.0, 7.7, 9.5, 11.0
counts — rather than two clusters.

**But the honest limit is decisive here, and it is quantitative.** L1
established that three replicate runs of a byte-identical protocol on one leg,
same rig, same hour, span **0.230 deg**. L3's distance to L5 is **0.158 deg —
smaller than that demonstrated between-run spread.** So this run *cannot
distinguish* "L3 is a third, intermediate value" from "L3 belongs to the L5/L0
high bracket and happened to read low this run." Its distance to L2 (0.238 deg)
only just exceeds the spread, so even excluding it from the low bracket is
marginal.

**Verdict on the plan's hypothesis: not supported as stated, and not resolvable
by this run.** What is established is that L3 sits near neither bracket's
centre. What is not established is a third bracket.

**A replicate L3 run is the next measurement.** The saved plan pre-registered
exactly this ("a replicate is the cheap follow-up if L3 lands near a bracket
boundary"), and it matters more for L3 than it did for L0, because L3's gap to
the nearest bracket is *smaller* than the family's own known between-run
spread. L0's gap to L5 was 0.135 deg and had the same problem; L3's is 0.158.
Neither single-run number should be compensated in a gait as a per-leg constant
yet.

## The two plan questions, answered

**1. Is the loaded-versus-unloaded offset quantified per cycle?** Yes, all six.
Loaded (in-stroke) error against the slewed command averages **+0.521 deg** and
unloaded (out-stroke) **−0.152 deg**; the out-stroke error is identical
(−0.152) on every one of the six cycles, and the in-stroke is +0.375 on cycle 1
then +0.551 on cycles 2–6. Peak current on the moving joint was **0.026 A**
against a 0.75 A trip, and the loaded stroke draws roughly 5–10x the unloaded
stroke (0.008–0.012 A vs 0.000–0.004 A) at loads of 4–5 % vs 3 %.

**2. Does hysteresis drift across repeats?** No. The declared post-hoc
monotonicity check finds cycles 2–6 exactly equal, so there is no growth of any
kind, let alone monotonic growth beyond the reviewed bound. The one difference
is cycle 1 being *narrower* than what follows, i.e. the opposite direction from
the growth the stop condition guards against. The L3 knee did not move off its
29 C baseline (**0 C rise** against an 8 C bound), so nothing was heating or
binding across the repeats.

## Safety and observation record

- **Chassis never stood and never moved.** IMU roll moved 0.19 deg and pitch
  0.23 deg across the whole window against a 10 deg trip. The worst *measured*
  non-L3 joint stayed **0.439 deg** from logical zero across all 1560 ticks
  against the plan's 1.0 deg bound, with zero missing measured cells. Pose
  before and after is identical: worst joint j16 at 0.440 deg both times.
- **L3 returned to within 2 counts of logical zero**, not exactly onto it: hip
  j10 reads 0.00 deg before the run and −0.18 deg (2 counts) after. That
  residual is the same 2-count scale as the loop measurement itself, which is
  what a backlash measurement on a leg with an 8-count loop should be expected
  to leave behind. It is well inside the 1.0 deg start-pose gate, so a
  replicate run can start from here without re-zeroing.
- **Chassis-tag-versus-floor-tags watch: UNMEASURED.** Reported plainly because
  it is a real reduction in evidence against the L0 run, which had this watch
  enabled and clean at a 6.18 mm median offset. The chassis tag was not
  resolvable when the pre-run baseline was taken (0 resolved samples), so the
  runner recorded the condition as unmeasured rather than inventing a baseline;
  only 6 of 144 samples resolved during the window. It *was* resolvable four
  minutes earlier during the zero-motion dry run (1 sample at (470, 599) mm,
  yaw 80.9 deg), so this is a marginal-resolvability boundary at this pose, not
  a lighting or camera failure — all three cameras served fresh frames
  throughout, at the brightest illumination this family has run at. The saved
  plan anticipates this exactly: the watch "bounds gross motion only and the run
  does not depend on it — joint telemetry answers the pose-held question
  directly, as it did for L0." The joint telemetry above does answer it, and
  more precisely than a tag whose own error_95 is ~93 mm.
- **Cameras:** all three recorded continuously from the `:8766` camera server
  for the whole window — 270 frames each over 175.2 s (protocol window 156.0 s),
  zero capture errors, every frame sha256 distinct, **max inter-frame gap
  0.738 s** against the 2 s staleness abort bound.
- **Thermal / electrical:** peak current 0.026 A on any joint (per-servo trip
  0.75 A, hard ceiling 3.0 A); max logged temperature 33 C (trip 55 C); L3 knee
  29 C → 29 C, a **0 C rise** against the +8 C bound. Bus voltage 11.2–11.4 V.
- **Not one `/api/errors` row.** The plan's single self-recovered transient
  `bus_timing` allowance was carried by this runner and went **entirely unused**
  — cleaner than the L0 run, which spent it once on the recurring host-MCU
  bare-ERR row. A second row, or any row of another kind, would have halted the
  run immediately.
- **Exclusive command lease** held by `guarded-runner-7b565e2a` for the whole
  window and released cleanly. Its exclusivity was demonstrated for this run
  rather than cited: all five direct motion routes (`/api/rl/stand|lower|walk`,
  `/api/standup`, `/api/sysid/run`) and all three `:8898` hub motion routes
  refused **409 `command_lease_held`**, while `/api/rl/stop`,
  `/api/standup/stop` and `/api/safe_zero` all still answered **200** with the
  lease held. The pose was unchanged by the demonstration. No foreign command
  was observed during the window.
- **Three advancing healthy 18/18 samples** before arming, taken in three
  attempts with no resampling needed; L3 knee baseline 29 C; start pose worst
  joint 0.44 deg against the plan's **1.0 deg** gate.
- **Passive recorder confirmed, not assumed.** All three markers (`pre_run`,
  `protocol_tick0`, `post_run`) were accepted by the on-robot 50 Hz recorder
  with `writer_alive` true and `queue_dropped` 0 / `capture_errors` 0 /
  `uncaptured_bytes` 0 at every one, which is the plan's persist-to-disk
  requirement met with evidence.

## No deployment, and the lease was already there

`/api/command-lease` answered **200** at preflight. The plan's own automation
note flagged the risk that a clean-`main` deploy would remove it again, as
happened before the L0 run — it had not. The installed revision is
`71459673` on `robot-deploy/l0-lease-on-d54d81e4`, deployed 14:48:25Z, and
`sysid_runner.py`, `sysid_protocol.py`, `command_lease.py`,
`mcu_feetech_bus.py`, `web_server.py` and `async_bus_guard.py` are all
**byte-identical** between that revision and this checkout. Nothing was
deployed for this run and nothing needed to be.

**That is still not a durable fix.** These lease commits remain off `main`, so
the next clean-`main` deploy will drop `/api/command-lease` a third time.
Merging them is the fix; this run simply got there before the next deploy did.

That same file identity is the current evidence resolving the plan's
creation-time `_adaptive_admission.ready: false`, whose two stated reasons were
that the proposal "has not proved current runtime compatibility" and "does not
yet name an available trusted deterministic executor". The executor is
`POST /api/sysid/run`, `sysid_protocol` v1, which ran the L5, L2, L1 and L0
members byte-exact on this same installed revision. The plan's historical
parameters were not edited.

## One qualifier defect found and fixed before arming

The four qualification suites did not start green, and the cause was ours.
`sysid/qualify_repeat_runner.py` proves a fault injection is covered by
grepping `linux_control/test_sysid_runner_guards.py` for a test *name*, and
commit `71459673` — the debounce of the two pre-motion telemetry gates, i.e.
the revision now installed — renamed both tests it was looking for. So
`stale_state_timestamp` and `incomplete_servo_sample` reported `passed: false`
while the guards behind them were untouched and in fact better covered than
before: a false negative on two safety interlocks, in the one tool that
certifies this family's runner.

It was repaired rather than worked around. The qualifier now references the
current names and states what they now mean (rejection after three consecutive
reads, not on one sample), and a new test pins the direction that broke — a
referenced name resolving to no defined test fails, while a legitimate prefix
such as the voltage gate's `..._out_of_bounds` against the real
`..._out_of_bounds_immediately` still resolves. Verified by reinstating the
stale name, which fails both that test and the requalification test. All eight
fault injections now pass. Committed in `eb623144` before arming.

## Protocol identity and admission

The reviewed document was submitted **byte-exact and unmodified** to
`POST /api/sysid/run` (`sysid_protocol` v1), no parameter edits. Canonical
`protocol_hash` **`c3727df8dc7e`**; file sha256
`192a73a2fa054abd9b96be531f5f95c1a21066f53e3a8e393af3f9c11fddac63`. The plan
derives it from `a99ceef28136` (L2) by remapping only the two varying hip/knee
columns; the generator only accepts an `l5_`-named source, so the review proves
the claim directly instead — L3's `j10`/`j11` columns are byte-identical to
L2's `j7`/`j8` (and L5's `j16`/`j17`), `t_s` matches, and every non-trajectory
field compares equal to L2's. Moving joints are exactly `{10, 11}`, matching
the plan's `hip_joint` 10 / `knee_joint` 11; the other 16 columns are 0.0 in
every one of the 1560 rows. The L3 yaw column `j9` is constant 0, so the leg
does not sweep laterally at all.

Realtime-versus-post-hoc stop coverage was declared **before arming**
(`preflight_declaration.json`, committed in `eb623144`): 12 realtime, 5
post-hoc, with the reason each post-hoc item cannot be enforced live without
adding the bus load it exists to detect. All the post-hoc checks were run and
all pass.

**L3 swept volume: clear.** The deepest commanded foot point of the whole
trajectory is −15.00 mm against a measured first-floor-contact of −80.95 mm, so
it is **65.95 mm above the floor plane** and a cable lying on the floor cannot
enter the swept volume by construction; only an object standing more than ~66 mm
tall directly beneath the resting L3 leg could. The three preflight frames were
inspected for exactly that at the brightest illumination this family has run at
(mean luma 83.6 / 43.0 / 47.6 against L0's 49.8 / 23.0 / 24.4 and L1/L2/L5's
24.9 / 4.6 / 4.4): all six legs splayed and belly-resting flat, feet down,
chassis flat, bare carpet around every foot, every visible cable strand lying
flat on the floor. L3 was identified directly rather than by inference — the
tracker tracks `L3_yaw` at this pose and reports `leg_zero_azimuth_body_deg`
210.0, matching the mesh's own `L3_yaw` position (−0.087, −0.05) → 209.9 deg —
which is better than the L0 run managed, where L0's coxa tag was invisible to
every calibrated camera.

## Evidence

`sysid_..._20260910_153015.csv` is the run's own 10 Hz synchronized telemetry
(all 18 measured angles, all 18 currents, load, temperature).
`l3_run1_loop_metrics.json` recomputes the six per-cycle loop widths from it and
`l3_run1_posthoc.json` recomputes every declared post-hoc check, including the
12 settled windows and their exact encoder-count arithmetic.
`l3_vs_other_legs.json` carries the five-leg comparison and the between-run
spread test behind the verdict above. `analyze_l3_hysteresis.py` and
`posthoc_checks_l3.py` are sealed alongside, so every number here is
reproducible from the artifacts. `camera_and_tag_coverage.json` carries the
per-camera frame accounting and the tag-watch scope; `run1/frame_index.jsonl`
carries every frame's sha256. `l3_swept_area_clearance.json` and
`exclusive_command_path_demo.json` carry the two preflight demonstrations.
