# L4 belly-rest radial shear hysteresis, 6 repeats — experiment `7299f243`

**The six-leg ladder is complete. L4 = −0.703 deg = 8.0 encoder counts (6-cycle
mean, sd 0.088 deg = 1.0 count), which lands EXACTLY on L3's value — an adjacent
gap of 0.000 counts.** Run 2 completed 1560/1560 ticks with **zero `/api/errors`
rows**, no trip, and the robot left limp at logical zero.

**But L4 is not L3's twin, and the difference is the substantive result.** L3's
twelve settled windows landed on the same two encoder counts every cycle, sd
0.000. L4's six loop widths are each an *exact* encoder count too — and the count
**varies: 9, 8, 8, 6, 8, 9.** So L4 shares L3's central value while being the
markedly less repeatable of the two. **A replicate is needed.**

An earlier attempt (run 1) was halted at ~126 s of 156 s by the plan's own
second-`bus_timing`-row interlock. It is reported as corroboration, never as the
result, and both physical attempts are preserved.

## Result

Loop width = settled measured hip angle at the shared commanded −47.133 deg,
out-stroke minus in-stroke (settled = last 1.0 s of each 3.1 s dwell) — the
identical definition L0, L1, L2, L3 and L5 used.

| cycle | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| loop (deg) | −0.791 | −0.703 | −0.703 | −0.527 | −0.703 | −0.791 |
| loop (exact counts) | **9** | **8** | **8** | **6** | **8** | **9** |

**Mean −0.703 deg, sd 0.088 deg, n = 6. In counts: mean 8.0, sd 1.0, modal 8
(3 of 6), range 6–9.**

### Every cycle is an exact count, yet the count moves

All **12/12** settled windows held a *single* value across all ten of their 10 Hz
samples (sd 0.0), and all **6/6** loop widths land on an exact encoder count
(worst residual 0.005 count). This is real quantised per-cycle variation, not
averaging noise.

The asymmetry says where it comes from: the **out-stroke is identical in all six
cycles at −47.197 deg**, and every bit of the variation is in the **in-stroke**,
which takes three different values (−46.406, −46.494, −46.670). The loaded return
stroke is what fails to repeat.

*Methodological note.* The absolute settled angles sit a near-constant
0.056–0.060 count off the nominal grid on both strokes. That is the **zero-frame
offset**; it cancels in the difference. L3's sealed data carries the same
constant offset, so its "sits on an exact encoder count" was likewise a statement
about differences. The post-hoc check was corrected to test the loop-width
difference rather than the absolute angle, which otherwise reports a false
negative.

## Where L4 lands: the complete six-leg ladder

| leg | loop (deg) | counts |
|---|---|---|
| L1 | −0.330 | 3.75 |
| L2 | −0.4357 | 4.96 |
| L3 | −0.703 | 8.00 |
| **L4 (this run)** | **−0.703** | **8.00** |
| L5 | −0.832 | 9.47 |
| L0 | −0.967 | 11.00 |

Adjacent gaps, in counts: L1→L2 **1.20**, L2→L3 **3.04**, **L3→L4 0.00**,
L4→L5 **1.47**, L5→L0 **1.54**.

### Which bracket? The high one — and it is not separable from L3 at all

**L4 sits 0.000 counts from L3 and 1.467 counts from L5. L5 and L0 — the two legs
already accepted as one bracket — sit 1.536 counts apart.** L4's distance to the
bracket is far below the bracket's own internal spacing, so the same standard
that groups {L3, L5, L0} groups L4 with them. Its zero gap to L3 is stronger than
co-bracketing: the two central values coincide.

**Adding the sixth leg does not move the series' one real discontinuity**, which
remains **L2→L3 at 3.04 counts** — still more than double any other adjacent gap.
The completed six-leg picture is a **low pair {L1, L2}** at 3.75–4.96 counts and
a **high group {L3, L4, L5, L0}** at 8.00–11.00 counts.

Two questions kept apart, because conflating them is how one number becomes a
wrong bracket:

- **Is L4's *value* distinguishable from L3's?** *No.* Both are 8.0 counts, gap
  0.000, against L4's own within-run sd of 1.0 count.
- **Is L4 *separable from* the high bracket?** *No*, for the spacing reason
  above. It is the bracket's joint-lowest member alongside L3.

## Is a single run sufficient? No — a replicate is needed

The plan asks this explicitly. Four reasons, in order of weight:

1. **The rationale's own precondition is not met.** It expected one run to
   suffice "when the settled windows land on a single encoder count", as L3's
   did. L4's per-cycle widths are exact counts but span **6 to 9**.
2. **L4's own scatter is comparable to the ladder's spacings.** Its within-run sd
   is **1.0 count** — larger than the L1→L2 gap (1.20 is only marginally above
   it), and about two-thirds of both the L4→L5 (1.47) and L5→L0 (1.54) gaps. A
   single run's mean cannot cleanly separate L4 from L3 below or L5 above.
3. **L4 landed exactly ON another leg's value** — unanticipated, and the most
   consequential position available, because it invites a gait to share one
   backlash constant between L3 and L4. L3's own history is the warning: its
   run-1 reading was *reversed* by its replicate.
4. **The two L4 attempts agree on the centre but disagree on scatter** (run 1:
   five cycles, sd 0.08 count; run 2: six cycles, sd 1.0 count) — unresolved in
   its own right.

**What a replicate should answer:** whether the central value stays at 8.0 counts
and whether the per-cycle count genuinely wanders 6–9. If it reproduces, then L3
and L4 share a central constant but L4 is the less repeatable, and **a gait should
budget L4's 1-count spread rather than treat 8.0 as exact.**

## Run 1: halted by the plan's own interlock, and why it is not a hazard

Run 1 tolerated one self-recovered transient `bus_timing` row and halted on a
second at 16:47:45.294Z — exactly as the plan is written ("any new `/api/errors`
row **beyond a single** self-recovered transient bus_timing retry"). Both rows
were the same documented class: `bus_timing` / `src` mcu / level error (not
critical) / `ascii_err` with `n = 0` / bare `ERR` attributed by
`classify_bare_err_reply()` to the `desync_guard` torn-frame path. **Only the
count exceeded the allowance.**

Physically the attempt was pristine: peak current **0.0 A** (trip 0.75, ceiling
3.0), max temperature **32 C** unchanged, L4 knee rise **0 C**, roll/pitch
unchanged (−1.01/2.34 → −0.93/2.36), **18/18** servos before and after, 247
frames per camera with **0** frame errors, no chassis-tag trip (31.31 mm against
120 mm), and the other 16 joints within **0.44 deg** of logical zero. None of the
no-retry conditions occurred — no tip, brownout, hot motor, jam, surprise force,
sustained current or persistent servo loss. This is a transient MCU
serial-framing stop, and **the L1 sibling hit the identical interlock at the same
point of the same reviewed trajectory** and recovered the same way.

Recovery followed the contract: three fresh observation-camera frames read (robot
belly-resting, no tip/lift/shift, indistinguishable from preflight), three
advancing healthy 18/18 samples, and the declared start pose restored through the
robot's own collision-aware `/api/safe_zero` planner after inspecting its dry-run
plan. The zero frame was not touched and **the start-pose gate was not widened**.
Run 2 is retry 1 of the 2 permitted.

**The reviewed one-row tolerance was NOT widened and no interlock was weakened to
obtain this result.** Run 2 ran the identical protocol under the identical guard —
and spent none of its allowance. Why two rows was ordinary rather than a new
fault, and what should be done about it, is in
[`ADDENDUM_bus_tolerance_margin.md`](ADDENDUM_bus_tolerance_margin.md).

Run 1's `result.json` carries `final_protocol_tick: 0`; that is a stale field on
the abort path. Its 1230-of-1560 CSV rows and its post pose (hip −50.71, knee
34.54) both show ~126 s of real motion.

### Run 1's five complete cycles corroborate the number

−0.703, −0.703, −0.703, −0.721, −0.703 deg: **mean −0.7065 deg = 8.04 counts**,
agreeing with run 2's 8.0 to within 0.04 count. Four of five were exactly 8
counts; the fifth's settled window straddled two counts. Corroboration only — not
pooled as an equal run.

## Safety and supervision (run 2)

| check | outcome |
|---|---|
| ticks | **1560/1560**, worker done after 163.52 s, final state limp |
| new `/api/errors` rows | **0** — the single-row allowance was not spent |
| peak current | **0.149 A**, on the moving hip j13 — the highest of any joint, as expected since it is the only driven one (next highest: knee j14 at 0.019 A, then 0.013 A). Trip 0.75 A on three consecutive polls, ceiling 3.0 A: peak reached **20 %** of the trip. |
| max temperature | 32 C (trip 55) |
| L4 knee rise | **0 C** (baseline 29 C, post 29 C; trip +8 C) |
| servo health | 18/18 pre and post, three advancing healthy samples each |
| non-L4 joint departure | worst joint 16 at **0.439 deg** (trip 1.0) |
| tracking error | no trip (limit 30 deg) |
| tilt | roll/pitch −0.91/2.10 → −0.80/2.40 (trip 10) |
| commanded foot clearance | **65.95 mm** above the floor plane (requirement ≥ 15 mm) |
| cameras | 924 frames, **308 per camera**, span 176.5 s, max gap 0.645 s against a 2.0 s watchdog, 0 gaps over 2 s |
| chassis tag watch | **UNMEASURED** — the baseline did not resolve (0 of 12 attempts), which the plan expressly allows. 37 of 157 in-run samples resolved but there is no baseline to compare them against. Run 1 *did* resolve a 2-sample baseline and bounded gross motion at 31.31 mm / 4.62 deg with 0 trips, so the gross-motion bound for this experiment comes from run 1. |
| command lease | held by `guarded-runner-7299f243` for the whole window, released cleanly |
| final pose | hip −0.09, knee 0.18 — back at logical zero |

**Realtime vs post-hoc stop coverage** was declared and committed *before* arming
(`preflight_declaration.json`, commit `1ee1244b`): **12 of 17** conditions
enforced live in-loop, **5** post-hoc, each with its reason.

**Exclusivity** was demonstrated fresh under this run's own owner before arming:
direct motion routes (`/api/rl/stand`, `/lower`, `/walk`, `/api/standup`,
`/api/sysid/run`) *and* the same routes through the **:8898 hub** were all refused
**409**, while `/api/rl/stop`, `/api/standup/stop` and `/api/safe_zero` stayed
**200** — and the robot did not move (14/14 steps as expected).

Run 2 started from **armed-holding-zero** rather than limp, because
`/api/safe_zero` leaves torque enabled and this revision has no limp route. The
measured start pose was identical (worst joint 16 at 0.440 deg), and the loop
definition — settled windows at a shared waypoint reached after an 8.1 s dwell at
the outer extreme — is insensitive to the initial torque state.

## Byte-exactness

- Protocol `l4_belly_rest_radial_shear_hysteresis_repeat6_v1`, canonical
  `protocol_hash` **`a77e379c68c5`**, file sha256 `23b4e54b…`.
- **Derived from the reviewed L2 member `a99ceef28136`** by remapping only the
  two varying hip/knee columns 7,8 → 13,14. Verified rather than asserted:
  `l4[13] == l2[7]` and `l4[14] == l2[8]` at **all 1560 ticks**; `t_s` identical;
  every non-trajectory field equal to L2's (sysid_protocol 1, hz 10, write_speed
  180, write_acc 10, soft_torque 700, max_current_a 0.75, current_trip_polls 3,
  hard_current_a 3.0, home_deg all zero). **No parameter was edited.**
- Moving joints exactly **{13, 14}**, matching the plan's hip 13 / knee 14; **j12
  constant 0** in all 1560 rows; the other 16 joints exactly `0.0`; first and last
  rows all-zero. The remap is **axis-preserving** (`axis_of(j) = AXES[j % 3]`).
- The generator was first proved to reproduce the **committed L3 protocol
  byte-for-byte** before being trusted for L4.
- Runner sha256 `e5d2bdf1…`. It is **not** byte-identical to L3's — retargeting
  is real code — so the diff was taken line-by-line: `MOVING_LEG`,
  `HIP_J/KNEE_J/YAW_J` 10/11/9 → 13/14/12, the moving-leg temperature key names,
  the default lease owner, **and nothing else**, at the same 881 code lines with
  no logic change.
- Installed robot source **md5-identical** to this checkout across
  `sysid_runner`, `sysid_protocol`, `command_lease`, `mcu_feetech_bus` and
  `async_bus_guard`, verified **fresh** over ssh against the live install at
  `/home/arduino/hexapod_sts/linux_control`. **Nothing was deployed.**
- 81 runner-guard, command-lease and sysid tests pass.

## Corrections recorded

1. **The plan's relative-knee warning is inverted for this family.** It says "a
   relative-knee reconstruction gives a wrongly deep answer". Measured, the
   relative reconstruction is *shallower* at all 1560 ticks and never deeper. The
   consequence is conservative: the mandated **absolute** convention gives the
   deeper reading, so the 15 mm gate is judged against the stricter number and
   still passes at 65.95 mm.
2. **A hand-written pre-arm line in this run's own declaration** first reported
   L4's j12/j13/j14 as 0.00 / −0.09 / 0.26 deg — the `degrees[]` window shifted
   one index. Correct: **j12 = −0.09, j13 = 0.26, j14 = 0.00**, as recorded
   programmatically and confirmed by the runner's own log. No gate was affected.
   Recorded rather than quietly amended because it is the same
   transcription-by-hand error class this family has published before.
3. **Three L3-specific carryovers were removed** from the post-hoc script before
   the run so it could not report L3's conclusions as L4's: a pre-baked "cycle 1
   differs from cycles 2–6" question, an *asserted* single-value/on-grid finding
   (now computed from the data, and it duly reported the honest mixed answer for
   run 1), and a stale `q10_deg` print label.
4. **A stale `~/linux_control` directory on the robot** holds an old
   `mcu_feetech_bus.py` and none of the other four executor files; md5summing
   that path reports a mismatch that looks like deployment drift and is not. The
   live install is the service's own `WorkingDirectory`.
5. **`/api/safe_zero` is asynchronous** — it returns as soon as the motion
   *starts*. The inherited `repose_to_zero.py` post-sampling raced the 4.8 s
   motion and crashed on an empty mid-motion `/api/status` scan *after* the
   motion had been commanded. Fixed in three places; the re-pose itself completed
   correctly.

## The two plan questions

**1. Loaded-versus-unloaded offset per cycle?** Yes, all six. Out-stroke error is
**−0.064 deg on every cycle**; in-stroke error is **+0.639 deg** on the four
8-count cycles and tracks the loop width on the others (+0.727 at 9 counts,
+0.463 at 6). Peak current on the moving joint **0.034 A** against a 0.75 A trip.
The loaded return stroke draws all of the measurable settled current
(0.017–0.034 A in-stroke versus **0.000 A** out-stroke) at loads of 4.8–7.2 % versus
2.8–4.0 %. (Those are settled-window figures; the whole-window peak on the moving
hip was 0.149 A, still only 20 % of the trip.)
The whole hysteresis lives in the loaded stroke — consistent with the in-stroke
being the only settled value that moves.

**2. Does hysteresis drift across repeats?** **No.** The declared post-hoc
monotonicity check reports no growth: the sequence 9, 8, 8, 6, 8, 9 counts is
non-monotonic in both directions, and the first and last cycles are equal.
Block means are −0.732 (cycles 1–3) and −0.674 (4–6) — the scatter is not a trend.
