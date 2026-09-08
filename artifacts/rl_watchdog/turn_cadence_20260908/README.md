# Cadence (period_scale) vs turn authority on the frozen full-mesh plant — CLOSED (both-direction REGRESSION + new straight-line drift; lift/lag mechanism partially confirmed)

Completed 2026-09-08 (refill-cycle follow-up to the stance-arm closure,
`../turn_stancearm_20260908/README.md`), executing the stance-arm
closure's own nomination: **CADENCE — one slower `period_scale` (1.5,
inside `TripodGait.SCALE_PERIOD` 0.40..2.00) vs baseline (1.0)** at the
identical arc/straight cells, same both-signs bar. Reviewed first per
`fb_20260908T014636_88b7c1` (Codex): the diagnostic guard's raw-IK-None
rejection (commit 975d6c36) is a hard prerequisite — verified in force
here (`raw_ik_failures: 0` at both period_scales, `test_probe_turn_
cadence.py` 5/5 green including a dosed-cadence forced-failure test);
this probe reports fractional lag / reversal rate / lift tracking
specifically so a genuine per-cycle change is distinguishable from
"fewer, noisier cycles measured" (the review's 2nd point), and no claim
below goes beyond what is actually measured (3rd point).

Zero training steps, zero robot work. New runner
`rl_move/sim/probe_turn_cadence.py` (copy here; committed at
`rl_move/sim/probe_turn_cadence.py`), built by generalizing the shared,
already-guard-fixed `probe_turn_stancearm.feasibility_guard`/`rollout`
to accept `period_scale` (bit-exact at the default 1.0 — proven by
`test_probe_turn_cadence.py::test_period_scale_default_is_bit_exact_
with_stance_baseline` reproducing the stance-arm guard's own pinned
margins/tick-count). Executed in the same isolated worktree
(`/workspace/hexapod-turnphase-wt/` + root's frozen full-mesh assets,
`hexapod_mesh.xml` sha `7efb8e8a…` re-verified before launch).

## Plant/config pinning

Identical to the stance-arm/lift-lead closures: frozen full-STL plant
(34 meshes, 4.80573 kg, 100 Hz), corrected-audit cfg_set, seed 0, 15 s,
cells (0.08, ±0.15) + straight guard (0.08, 0), starts 0/π, stock
stance (hip 20°/knee 100°, `WALK_PLANT`). Every rollout hard-asserts
variant/nmesh/mass/dt and the unchanged servo contract (write_speed
400, write_acc 20, slew 0.375 deg/tick, ceiling 350). Nothing deployed;
cadence is a SCRIPTED-gait dose only (a frozen policy cannot take it).
Baseline (`cadence100_baseline_fm.json`) reproduces the stance-arm/
lift-lead baseline BIT-EXACTLY (wz +0.0642/+0.0632, vx 0.0372/0.0363
first cell) — the generalization is behavior-neutral at period_scale=1.

## Results (full mesh, 12 rollouts total, ZERO falls)

| arm | wz +0.15 (mean±sd over starts) | wz −0.15 | straight vx (mean) | straight \|wz\| max | dyn arm (loaded) | loaded resid (med) | lift p90 (med) | scuff (med) | reversal rate (Hz) | contact lag (frac of period) |
|---|---|---|---|---|---|---|---|---|---|---|
| period 1.0 (baseline) | +0.0637 ±0.0005 | −0.0641 ±0.0010 | 0.0402 | 0.0074 | 173.3 mm | 0.0108 m/s | 3.5 mm | 0.70 | 1.31 | 0.29 |
| period 1.5 | +0.0547 ±0.0046 | −0.0538 ±0.0032 | **0.0479** | **0.0329** | 172.4 mm | 0.0117 m/s | **13.1 mm** | **0.48** | 0.89 | **0.21** |

- **Yaw: BOTH directions REGRESS, not gain** — +0.15 arc −14% (0.0637→
  0.0547), −0.15 arc −16% magnitude (0.0641→0.0538). Opposite of the
  closure's own working hypothesis; decisively fails the pre-registered
  both-signs-gain bar (no ambiguity — both directions move the SAME way
  as each other and AWAY from the hoped effect, clear of the baseline's
  own ±0.0005-0.0010 start-to-start spread).
- **Mechanism partially CONFIRMED, but doesn't convert to yaw:**
  fractional touchdown/liftoff lag drops ~28% (0.29→0.21 of the
  effective period, the review's own diagnostic — a genuine per-cycle
  improvement, not a rate-relief artifact) and achieved swing-lift
  tracking nearly QUADRUPLES (3.5→13.1 mm p90, closer to the nominal
  25 mm swing target) with scuff fraction dropping 31% (0.70→0.48,
  less contact-during-planned-swing) — the servo-profile/lift-collapse
  mechanism named by the pipeline probe (00:52 UTC) genuinely responds
  to a slower cadence. **None of this recovers wz**: the executed
  tangential sweep's extra amplitude/cleaner lift does not translate to
  more body rotation — loaded-pad residual slip stays flat-to-slightly-
  worse (0.0108→0.0117 m/s) and dynamic arm is unchanged (173→172 mm,
  as expected — cadence doesn't touch geometry), so the conversion
  bottleneck stays where the stance-arm closure located it (traction-
  limited conversion of the executed sweep), not in swing execution.
- **NEW pathology, not present at baseline: straight-command yaw bias
  that FLIPS SIGN with starting tripod phase.** Baseline straight |wz|
  max 0.0074 (both starts negative, near zero as expected). At
  period 1.5, straight |wz| jumps to 0.0329 — 4.5x worse — AND the sign
  flips exactly with start phase (start 0: +0.0329, start π: −0.0329),
  meaning whichever tripod group leads at reset determines a persistent
  net rotation during a ZERO-wz command. This is a genuine new
  systematic defect at the slower cadence, not measurement noise
  (reproduces at both starts with matched magnitude and opposite sign)
  — it independently disqualifies the straight-guard leg of the bar,
  on top of the arc regression.
- **Side-finding (consistent with the stance-arm closure's own vx
  side-finding): straight vx +19% (0.0402→0.0479)** — but UNLIKE the
  stance-arm closure's speed side-finding (which HALVED straight yaw
  drift), this one WORSENS straight drift 4.5x, so it is NOT a clean
  speed-lever candidate on its own; any future speed-lever pursuit of
  cadence would need to separately diagnose/fix the phase-dependent
  straight bias first.
- Reversal rate drops 1.31→0.89 Hz, consistent with the mechanical
  fact of a 1.5x longer period (predicted ratio 0.67, measured 0.68) —
  confirms the comparison is genuinely period-driven, not an
  under-sampling artifact (still >=0.85 Hz, >=12 reversals per 15 s
  episode per leg, an adequate sample per the review's own concern).

## VERDICT

**Cadence (period_scale) is CLOSED on the frozen full-mesh plant: the
pre-registered both-signs-gain bar is unmet — REGRESSED in both
directions, not just "no gain" — plus a new straight-line drift defect
appears. NO 2M training canary launched (by the rule, and doubly so
given the regression).** This is the 3rd of 3 in-limits, measured
turn-authority levers (lift-phase timing, stance-posture moment arm,
cadence) nominated after the pipeline-review correction, and the 3rd to
close against the both-signs bar. Each closure narrowed the diagnosis
further: lift-lead showed the executed gait is already phase-aligned;
stance-arm showed a bigger moment arm sheds into loaded-pad slip
instead of rotation; cadence shows that even genuinely fixing the
swing-execution symptoms (lag, lift height, scuff) named by the
original pipeline probe does not unlock more body yaw — the bottleneck
is downstream of both timing and swing quality, consistent with (not
newly proving, per the review's 3rd caution) a traction/force-budget
limit on converting the executed sweep into rotation at these
command amplitudes.

## Next

No further in-limits kinematic/timing/geometry lever is currently
nominated — lift-phase, stance-posture, and cadence are now all closed
against the identical bar. A genuinely new mechanism (not a 4th
rotation/schedule variant on the same scripted-gait dial) would need
either (a) a direct traction/force-budget diagnostic (e.g. measuring
peak required lateral pad force vs available friction cone at the
turning cells, distinct from the finite-difference/LSQ speeds already
used and disclaimed here), or (b) accepting the current turn-authority
envelope as this controller's operating limit and scoping the
`todaypolicy` demo commands to derated turn cells (the STOP-turn-
authority-GPU-arms assume-and-go already recorded, q_20260908T0050Z).
The NEW straight-line phase-dependent drift is itself a separate,
narrow, worth-a-look artifact (only reproduced at period_scale=1.5,
2 starts, seed 0) — not chased further here since cadence itself is
already closed and this does not bear on the registered bar.

## Limits

Single seed (0), starts 0/π only, one dosed period_scale (1.5),
scripted controller only (a frozen policy cannot take a cadence dose),
15 s episodes, one plant (frozen full-mesh; not cross-checked against
the MJX twin this time since the two closures preceding this one always
agreed and budget favored covering the new metrics instead).
