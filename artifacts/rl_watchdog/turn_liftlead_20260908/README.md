# Lift-only phase-lead comparison on the frozen full-mesh plant — CLOSED (no gain)

Completed 2026-09-08 ~02:4x UTC by cycle 20260908T005017, executing the
bounded experiment scoped by `../turnpipeline_review_20260908.md` (root
correction 860f498c + 00:58 frozen-assets addendum, fb_20260908T005811).
Zero training steps. Runner `probe_turn_liftlead.py` (copy here; committed
at `rl_move/sim/probe_turn_liftlead.py`). Controller copies:
`logs/ckpt_eval/turn_liftlead_20260908/`. Isolated experiment workspace
(git worktree @ f7d00ba5 + root's frozen assets): `/workspace/hexapod-turnphase-wt/`.

## Plant/config pinning (review correction #1)

PRIMARY plant = the root-supplied frozen full-STL model
(`/workspace/turnphase_frozen_20260908/assets.tar.gz`): all 38 XML/STL/
sim-model files verified sha256-identical to the corrected audit's
manifest after extraction (script check: 38/38, zero mismatches);
`hexapod_mesh.xml` = `7efb8e8a…`, 34 meshes, **4.80573 kg**, 100 Hz.
Every rollout hard-asserts variant `full_mesh`, nmesh 34, mass, dt, and
the unchanged contract: write_speed 400, write_acc 20, slew 0.375
deg/tick @100 Hz, profile ceiling 350 counts/s. cont8m checkpoint sha
`4a902839…` (frozen-manifest match). Cells: original arcs (0.08, ±0.15)
+ straight guard (0.08, 0), starts 0/π, 15 s, seed 0; cfg = the corrected
audit's exact cfg_set.

Files `*_fm.json` are the full-mesh results. The `scripted_baseline/
lead210/lead20/cont8m_baseline.json` files (no suffix) are the earlier
SEPARATELY-LABELLED exploratory twin runs (`hexapod_mesh_mjx.xml`
`a8a5ca8a…`, also 4.80573 kg — the pod training plant); they agree with
the full mesh on every conclusion below and serve as a plant-sensitivity
check, not as substitutes.

## Baseline measurements (full mesh)

- Scripted arcs: (vx +0.0363..0.0372, wz +0.0632/+0.0642 and
  −0.0631/−0.0651); straight vx 0.0401/0.0402 — reproduces the corrected
  audit within noise. cont8m: (+0.0324..0.0331, +0.0580) vs
  (+0.0338..0.0341, −0.0469..−0.0487) — the audit's direction asymmetry
  reproduces.
- Per-foot scuff (contact during PLANNED swing) 0.70 mean; achieved lift
  p90 3.5 mm (25 mm commanded); loaded-pad (>2 N) slip med ~0.012 m/s;
  per-foot LSQ residuals retained in the JSONs (review correction #4).
- NEW per-foot lag (xcorr, 10 ms resolution): contact timing lags the
  PLAN by median 215 ms; the executed tangential sweep lags by the same
  amount — **RELATIVE lag (contact minus executed sweep): median 0 ms,
  mean +5 ms** (per-leg medians +60/−60/+20/+15/−55/+70; legs 1,4 early,
  0,5 late).

So the executed gait — XY sweep, lift, contact — lags the plan by ~0.21 s
(~28% of the 0.75 s cycle) but is internally SELF-ALIGNED: achieved lift
already coincides with the achieved tangential sweep. The 65–70%
planned-swing contact is a symmetric whole-pipeline delay, NOT a
lift/sweep misalignment; during "scuffed" planned-swing ticks the lagged
foot is still executing its backward stance sweep (propelling). This also
explains the pipeline probe's planned-vs-actual contact-selector sign flip
(the review's causal-allocation warning, confirmed on both plants).

## Comparison arms (full mesh; XY foot path bit-exact — verified — plus
cadence, swing width, stance, ramp, all limits unchanged; only the
vertical dz profile timing shifts)

| arm | arc +0.15 wz (2 starts) | arc −0.15 wz | straight vx | mean scuff | lift p90 | loaded slip |
|---|---|---|---|---|---|---|
| baseline | +0.0642 / +0.0632 | −0.0631 / −0.0651 | 0.0401 / 0.0402 | 0.70 | 3.5 mm | 0.0121 |
| lead 0.21 s (plan-aligned; median contact lag) | **−0.0346 / −0.0389 (SIGN FLIP)** | **+0.0413 / +0.0372 (SIGN FLIP)** | 0.0018 / 0.0021 | 0.14 | ~9 mm | 0.0134 |
| lead 0.02 s (execution-relative residual) | +0.0572 / +0.0589 (−9%) | −0.0552 / −0.0546 (−13%) | 0.0396 / 0.0403 | 0.64 | 3.6 mm | 0.0120 |

- τ=0.21 achieves the timing goal (scuff 0.70→0.14, lift ~9 mm) yet
  DESTROYS locomotion: grounding now coincides with the executed FORWARD
  sweep — causal proof that contact must align with the EXECUTED sweep,
  which it already does at baseline.
- τ=0.02 — the only faithful positive dose once the estimator is
  corrected to execution-relative lag (the honest median selection is
  0 s = baseline): wz WORSE in BOTH directions, vx flat-to-worse, slip
  flat. Zero falls in all 24 full-mesh rollouts. Identical pattern on
  the twin (−2..−10% wz).

## VERDICT

**Lift-only phase lead is CLOSED on the frozen full-mesh plant — no dose
helps.** The review's pre-registered bar ("only a measured gain in BOTH
turn directions with retained gait/progress/slip justifies the next
bounded canary") is unmet in both directions at both doses on both
plants; **NO training canary launched** — by the rule, not by caution.

Combined-arc undertracking on the pinned plant is an AMPLITUDE
attenuation of the executed sweep under the unchanged (near-optimally
shaped) servo profile/slew contract, not a fixable timing misalignment —
and per the review, still not a proven any-controller impossibility.
Residual observables: per-leg DIFFERENTIAL lift timing scatter (±55–70 ms,
legs 1/4 early vs 0/5 late) — uniform-lead sensitivity at that scale
measured a few % and NEGATIVE, so not launch-worthy without a new
mechanism argument; physical contract/geometry levers remain operator
decisions (see `turnpipeline_20260908/README.md` §steering).

## Limits

- Single seed (0), starts 0/π, uniform (not per-leg) lead, scripted
  controller only for the lead arms (a frozen policy cannot take a
  teacher-timing dose).
- Twin runs retained as labelled exploratory plant-sensitivity evidence;
  they agree with the full mesh everywhere measured.
