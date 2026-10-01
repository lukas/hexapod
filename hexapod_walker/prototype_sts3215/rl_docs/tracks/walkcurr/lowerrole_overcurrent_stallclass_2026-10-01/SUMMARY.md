# rl_only lower-role over_current STALL-CORROBORATION (2026-10-01)

Scoped item: walkcurr/STATUS.md Next(1)'s open question after the
2026-10-01 forensics doc and its entry-state-vs-trip null close --
"the remaining live hypothesis is the DESCENT DYNAMICS ... rather than
anything fixable by conditioning on ... the handoff pose. No new
lower-role stabilization idea is scoped from this result alone."
Before designing a new mechanism, this item applies a tool and a
standing operator directive that the forensics work never actually
used on its own data: `audit_over_current.py`'s own docstring records
an OPERATOR DIRECTIVE (2026-09-04, fb_20260904T074505_6a3ac9) that "a
bit-exact 2.64 A trip is NOT dispositive evidence a policy is unsafe"
and defines a 4-way classification (NO_RAIL / RAIL_TRANSIENT /
RAIL_MOVING / CORROBORATED_STALL) where **CORROBORATED_STALL is the
only class that corroborates "unsafe"**. The 2026-10-01 forensics doc
counted all 37 over_current terminations as equally-weighted failures
without ever running this classification on them.
Zero GPU spend (CPU MuJoCo eval only, reused the exact same bus-
profile-fixed protocol/checkpoints/seeds as the prior forensics doc).

## Tool extension
`eval_lifecycle_handoff_rlonly.py`'s `lower_phase()` now also captures
a per-tick actuated-joint qvel trace and chassis-height trace (same
format `audit_over_current.classify_trace` reads, no floating-base
offset needed since the capture already slices `data.qvel[6:6+18]`)
whenever `--current-trace-dir` is set (bit-exact/no-op otherwise).
`trip_summary()` gained optional `qvel_trace`/`height_trace_mm` params
that, when both given, classify the trailing hot-run window on
`final_joint` directly (no lowpass deconvolution needed -- this trace
already IS the exact trip signal, not an npz torque proxy) into
`CORROBORATED_STALL` (joint essentially static AND body made no
height progress over the window) or `RAIL_MOVING` (still turning
and/or body still progressing -- generalized from audit_over_current's
rising-only height check to a magnitude check, since this is a
DESCENT). 8 new tests (`test_eval_lifecycle_handoff_rlonly.py`), all
green; reran the full n=18x2-seed x2-checkpoint protocol and confirmed
the s0_seed0 arm reproduces the prior forensics doc's `lower_falls`
counts bit-exactly (3 direct / 4 plant) -- the new capture changes
nothing about episode outcomes, only what gets recorded.

## Finding: the raw "37 multi-joint over_current failures" count was never corroborated -- only 5/37 (14%) are genuine stalls
Over all 144 composed/plant lower attempts (4 checkpoint x seed
combinations, n=18 each, direct+plant arms): 93 ended clean (no
termination), 37 over_current, 9 tilt_roll, 5 tilt_pitch. Classifying
the 37 over_current traces:

- **RAIL_MOVING: 32/37 (86%)** -- the hot joint was still clearly
  turning (median |qvel| during the trailing hot window typically
  0.13-0.6 rad/s, far above the 0.05 rad/s stall bar) and/or the
  chassis height was still changing meaningfully during that window.
  Per the classifier's own documented rule, this is high modeled load,
  NOT corroborated as an unsafe stall.
- **CORROBORATED_STALL: 5/37 (14%)** -- joint median |qvel| < 0.05
  rad/s AND |height change| <= 5mm over the trailing hot window: a
  genuine dead-stall-while-terminating. Breakdown: **L1 hip 4/5**, L2
  knee 1/5.

This REVERSES the raw per-joint framing: the earlier doc's "L5 hip 41%
of 37 fails, 5 other joints the rest, NOT a single-joint signature" is
true of the raw over_current COUNT, but almost all of L5 hip's share
(15/37 raw) is RAIL_MOVING (the rearmost leg's hip still working hard
late in a real descent, not stalling) -- when you restrict to the
subset the classifier actually corroborates as unsafe, the picture
flips to a small, STRONGLY single-joint-dominated signature (L1 hip,
4/5). s1_seed100 carries 4 of the 5 corroborated stalls (and the
single L2-knee one); s0 has ZERO corroborated stalls across both its
seed draws -- reinforcing, via an independent measure, the existing
s0-over-s1 seed recommendation.

Evidence: `current_trace_{s0,s1}_seed{0,100}/*_over_current.json`
(`trip_summary.stall_classification` field), aggregate script output
preserved in this doc's own derivation (rerunnable from the raw trace
files with the `trip_summary`-emitted per-file JSON, no separate
script committed -- the classification is now computed inline by
`eval_lifecycle_handoff_rlonly.py` itself for any future trace dump).

## What this does and does not change
Does NOT mean "the lower role is basically fine" -- RAIL_MOVING is
"not corroborated as unsafe BY THIS TEST", not "proven safe": running
a real servo at its modeled torque rail continuously, even while still
producing motion, is a plausible real thermal/protection concern on
physical hardware, and the episode still terminated early either way
(the composed/plant pass-rate numbers in the prior forensics doc and
`bundle_rlonly_lifecycle_v2/transfer_manifest.json` are UNCHANGED by
this doc -- it does not claim a higher lower_ok rate). What it DOES
change is which mechanism question is worth pursuing next:

1. The GENUINE-stall problem (5/144 ~= 3.5% of composed attempts) is
   much smaller and much more concentrated (L1 hip, 4/5) than "an
   arbitrary leg's hip/knee" -- a future targeted mechanism (if one is
   designed) should look at WHY L1 hip specifically goes fully static
   under load late in descent (L1 is a front-ish leg, not the
   rearmost L5 the raw count suggested), not design for an
   undifferentiated 6-joint vulnerability.
2. The RAIL_MOVING majority (32/37, 22% of all composed attempts) is a
   DIFFERENT, so-far-unasked question: is a ~2.6-2.9A sustained
   torque demand during descent actually the expected/necessary load
   for this motion (in which case the fix is recalibrating
   `safety.max_current_a`/`safety.over_current_trip_s` for the lower
   role specifically -- system identification, an explicitly allowed
   lever per tracks.json's walkcurr contract), or is the lower-role
   policy using more torque than the motion requires (a genuine
   control-quality/reward-shaping question)? NEITHER sub-question has
   been scoped or answered here -- this doc narrows the target, it
   does not resolve it.
3. The 9 tilt_roll + 5 tilt_pitch non-current falls (14/144, ~10%)
   remain entirely unanalyzed by this item; they are current-uninvolved
   per the original forensics doc and still open.

## Recommendation
Do NOT launch a new reward/mechanism arm from this doc alone -- it
closes a corroboration gap, it does not open a scoped lever. The two
live, UNSCOPED next questions are (1) above (an L1-hip-specific
investigation: per-leg torque/geometry asymmetry at that stage of
descent -- note L1 hip is a DIFFERENT joint than the k_torque_headroom
dose sweep's framing implicitly targeted) and (2) above (a current-cap
system-ID check: what sustained torque does the scripted/stance
baseline itself draw during an equivalent load phase, to tell whether
2.6-2.9A is normal-for-this-motion or policy-specific excess). Next
cycle: scope (2) first (cheaper, zero GPU, reuses
`probe_lower_achievability.py`/`audit_over_current.py`-style tooling)
before scoping (1).
