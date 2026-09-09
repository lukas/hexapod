# Stand-up / sit-down foot contact — why don't all six feet load the floor?

Experiment `922434955b35404198907c9e77cde5f6` · plan `standup-foot-contact-20260909-01` ·
robot `hexapod-1` · mode `step`, speed 10, torque 700.

**Terminal outcome: PARTIAL — 1 of 4 cycles completed, 2 started.** The question is
answered from cycle 1's 44 s stance. Attempt 1 of engineering job
`7276f3501bc64ef9abb7d90d102d63d8` moved the robot 23:22:26–23:26:12 UTC and then ended
without writing its result file. Attempt 2 (this one) is completion-only: **no motion**,
no robot commands — the record below is recovered from the robot's own 50 Hz telemetry
recorder, the `hexapod-web` journal, `/api/errors` and the camera frames attempt 1 saved.

## Answer

**At stance the body is carried by the middle pair L1/L4 alone. Four seconds after a
symmetric, correctly-reached stance, the four outer hips (L0, L2, L3, L5) yield 5.2–14.5°
with no command, which lifts those four feet 4.5–20 mm off the floor. Foot height at
stance is a monotone function of per-leg hip yield — nothing else.**

Separately, **cycle 2's stand-up never happened**: it self-aborted 1.76 s in, on the
stand-up current guard, against a peak of **106.50 A** — a corrupted bus read, not a real
current (see "Second finding").

## Cycle 1 stance table (medians over the 44 s hold, 23:22:55–23:23:39 UTC)

Commanded pose was identical for all six legs: yaw 0.00°, hip **+20.83°**, knee **+82.18°**.
Kinematic foot clearance was commanded to **−2.1 mm** (2 mm of press) on every leg.

| Leg | hip act | hip gap | knee act | knee gap | est. foot clearance | load % | current A | contact |
|-----|---------|---------|----------|----------|---------------------|--------|-----------|---------|
| L0  | 10.37 | **−10.46** | 85.87 | +3.69 | **+12.7 mm** | 0.0 | 0.0 | no |
| L1  | 20.13 | −0.70 | 85.08 | +2.90 | **−1.9 mm** | 0.0 | 0.0 | **yes** |
| L2  | 10.90 | **−9.93** | 87.54 | +5.36 | **+11.6 mm** | 0.0 | 0.0 | no |
| L3  | 6.33 | **−14.50** | 81.74 | −0.44 | **+20.1 mm** | 0.0 | 0.0 | no |
| L4  | 20.13 | −0.70 | 88.86 | +6.68 | **−2.4 mm** | 0.0 | 0.0 | **yes** |
| L5  | 15.56 | −5.27 | 87.19 | +5.01 | **+4.5 mm** | 0.0 | 0.0 | marginal |

Yaw tracked within 0.44° on every leg. Clearance is the robot's own FK-derived contact-observer
estimate (`measured_clearance_mm`), not a force measurement.

**The rank order of hip shortfall and the rank order of foot height are identical**
(L3 > L0 > L2 > L5 > L4 ≈ L1). One variable explains the whole pattern.

### The yield is a single abrupt event, not a slow settle

Per-joint hip trace across the settle (deg):

```
 t (UTC)      L0     L1     L2     L3     L4     L5
 23:22:41.5   18.0   20.3   20.2   17.5   21.0   19.2   <- all six AT target (cmd 20.8)
 23:22:43.5   18.3   20.3   20.5   18.1   20.9   19.9   <- standup reports "end err 2.8deg"
 23:22:44.3   11.0   20.3   13.4    8.0   20.4   16.1   <- four hips give way, no command issued
 23:22:44.6   10.5   20.1   11.2    6.3   20.1   15.6
 23:23:38.7   10.5   20.1   11.0    6.3   20.1   15.6   <- frozen to 0.1 deg for the next 54 s
```

The last servo write of the stand-up was 23:22:43.574 (the final hold pose); the next write
of any kind was 23:23:52.682 (the sit-down). **Nothing commanded the 23:22:44.3 step.** The
robot genuinely reached a level six-leg stance and then lost four legs to hip give-way
within ~1 s of the hold torque being applied.

## Hypotheses

**(1) Per-leg logical-zero offset — RULED OUT.** All 18 joints read within 0.35° of zero
before the run and within 0.44° after it; no `set_zero`/`POST /api/zero` in the journal for
23:11–23:30Z; no `*zero*.json` modified since 2026-08-27. **The zero frame was not changed
by this experiment.** L1 knee — the joint behind today's earlier `suspect_zero` refusals —
behaved normally throughout (0.09° pre, +2.90° stance gap, 0.09° post). A static zero offset
also cannot produce a pose that is correct for 4 s and then steps 10–14° with no command.

**(2) Stand-up mode keyframe geometry — NOT the cause.** The `step` mode delivered a
symmetric stance correct to 2.8° worst-joint error at 23:22:43. The keyframes are fine; the
stance is lost *after* they finish. (`blend`'s documented foot-dragging is a different mode
and was not used.) The step fold geometry *is* implicated in the cycle-2 abort below.

**(3) Servo compliance / torque limit under load — LEADING CAUSE, partially measured.**
Four hips yield 5.2–14.5° from a symmetric command with no intervening write and then hold
the new angle rigidly — that is give at the hip under body load. **But the direct evidence
the plan asked for is UNMEASURED: `load_pct` and `current_a` read exactly 0.0 on all 18
joints for the entire 44 s stance.** Motion currents were captured fine (2.88 A peak during
the push-up), so the channel works; it returns nothing usable for a static loaded hold. The
compliance-vs-torque-saturation distinction cannot be closed without that.

**(4) Uneven floor / leg-length or assembly variance — NOT SUPPORTED.** Every leg reached
the same commanded geometry simultaneously (spread ≤3° at 23:22:41–43). A short leg or a low
floor patch would prevent a leg from reaching the common commanded angle in the first place;
the divergence appears only once the hold begins. `touchdown_zero` and `foot_tip_tracking`
were not run — **unmeasured**, but not needed to reject this as the primary cause.

## Second finding: cycle 2's stand-up aborted on a corrupted current sample

`23:24:35 [standup] step stand-up x10: ... stream 1.76s (sched 4.77s, 31 ticks ...), peak 106.50A`

The stream stopped at tick 31 of 62: tripod A folded, tripod B's fold truncated at
hip −67.2/knee 112.7, and the push-up phase never ran. The robot stayed folded, belly low,
all feet off the floor (camera frame `c2_stance_robot-3.jpg` shows this directly), until a
`safe_zero` ramp returned it to zero at 23:26:05.

**106.50 A is not a real current.** 106.50 / 0.0065 A-per-count = **16384 counts = 0x4000** —
exactly one set bit 14. The highest genuine current anywhere in the run was 2.88 A, and the
robot's 12 V supply cannot deliver 106 A. Four other single-sample corruptions appear in the
same window on the temperature field (j2 42/50 °C, j8 41/42 °C, j4 57 °C — 5 outliers out of
16 272 readings, each surrounded by 31–34 °C on the same joint). The host↔MCU link has
documented `ascii_err`/`no_a5` framing events today at 18:06Z and 19:18Z.

`linux_control/api/standup.py` trips unconditionally on `tracker.peak_a > HARD_CAP_A (4.0)`
with no plausibility bound, and `linux_control/mcu_feetech_bus.py:1001` decodes
`current_a = cur * 0.0065` with **no mask on the raw count** — unlike the adjacent
`load_pct`, which masks `& 0x3FF`. One corrupted sample therefore aborts a stand-up
outright. The same unmasked value feeds the `> 4.0 A` trips in
`linux_control/api/demos.py:1012,1056` and `linux_control/safe_zero.py`.

## Smallest recommended fixes

**A — unblock repeats (do this first).** Reject physically impossible current samples
instead of tripping on them: mask the raw current count the way `load_pct` is masked, and/or
discard any sample above a physical ceiling (~8 A — far above the genuine 4 A stall-fight cap,
far below 106 A). This **tightens** the interlock: the real 4 A trip and the two-sweep
stall-fight rule are untouched; only the single-corrupt-sample false abort goes away.
Not applied here — this attempt is completion-only and a safety-interlock change should ship
with a physical retry that validates it.

**B — the actual foot-contact fix.** The stand-up's corrective re-command loop finishes
*before* the yield happens (settle converges at 23:22:43, the hips give way at 23:22:44.3 and
are never re-checked). Extend the stand-up settle to re-measure and re-command the stance
~2 s **after** `_set_torque_limit(1000)` is applied — by 23:22:44.6 the yield is complete and
static, so the correction the code already implements would catch all of it.

**C — prerequisite for closing hypothesis 3.** Find out why `load_pct`/`current_a` read 0.0
for a loaded static hold. Without it there is no quantitative torque evidence at stance.

## Safety record

- No `stop_on` condition triggered. Zero new `/api/errors` entries after 19:18:05Z.
- Bus never quarantined; 18/18 motors live in every sample; no servo alarm.
- Peak real current 2.88 A (cycle 1 stand-up), 2.84 A (cycle 1 sit-down) — normal for this
  robot (historical range 0.35–2.9 A) and under the 4.0 A cap.
- Sustained temperatures 29–34 °C throughout; the five ≥40 °C samples are isolated
  single-sample corruptions, corroborated by the live robot reading 29–34 °C afterwards.
- No tip, brownout, jam or surprise force. Robot ended and remains armed, stationary, at
  logical zero (all 18 joints within 0.44°), verified by fresh camera plus healthy telemetry
  at 23:27Z.
- **The zero frame was not modified.**

## Not measured

Cycles 3 and 4; `/api/measure/touchdown_zero`; `foot_tip_tracking`; AprilTag metric foot
positions; per-leg stance load/current (channel returned 0.0).

## Files

- `cycles_recovered.json` — reconstructed per-cycle record, timeline, stop_on evaluation.
- `stance_windows.json` — per-joint medians/min/max and per-leg contact features per window.
- `keyframe_writes.json` — every servo write and IMU sample, 23:22:25–23:26:30 UTC.
- `frames/` — observation-camera frames at pre-run, cycle 1 stance, cycle 2 (folded).
- `run_cycles.py` — attempt 1's guarded driver.
