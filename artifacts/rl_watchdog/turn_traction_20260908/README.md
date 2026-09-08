# Direct contact-force / traction-budget diagnostic on the frozen full-mesh plant — the yaw deficit is OPPOSING-STANCE CANCELLATION at LOW friction-cone usage, with the net turn drive carried by (unphysically grippy) torsional pad couples; NOT cone saturation, NOT actuator rail

Executed 2026-09-08 (operator focus note 20260908T025454Z) after the
lift-lead / stance-arm / cadence closures each *inferred* — from
finite-difference pad speeds and LSQ residuals the pipeline review
explicitly disclaimed — that the remaining yaw deficit was
"traction-limited conversion". This probe measures the actual forces
for the first time. Zero training, zero robot work, nothing deployed.

## Instruments (all committed, all tested)

- `rl_move/sim/probe_turn_traction.py` (copy here) — two engines:
  - `tick`: per-control-tick sampler with fail-closed STATIC
    validation (1 s zero-command hold: Σ vertical contact force vs the
    pinned 4.80573 kg weight; solver normals vs the independent
    L{i}_foot_t touch sensors; empirical sign calibration).
  - `audit`: `probe_turn_authority._ContactAudit` per-substep wrench
    integration (impulse-closure validity gate), EXTENDED this cycle
    (additive fields only, 47/47 probe tests green) with per-contact
    friction-cone usage |Ft|/(mu*N), slip-conditioned cone stats,
    pos/neg yaw-moment cancellation, and actuator force-rail
    saturation.
  - `--foot-torsion-mu`: probe-local torsional-friction sensitivity
    dose (see below; the first attempt was silently WIPED by the env's
    DR pristine-copy restore at reset — caught because the results
    came back bit-identical, fixed + regression-tested
    `test_foot_torsion_dose_survives_reset_and_reaches_live_contacts`).
- `summarize_traction.py` — the comparison tables.

## Pinning

Same isolated worktree + frozen assets as the three closures:
full-STL `hexapod_mesh.xml` sha `7efb8e8a…` (34 meshes, 4.80573 kg,
100 Hz), corrected-audit cfg (`cfg_frozen_audit.json`), seed 0, 15 s,
cells (0.08, ±0.15) + straight guard (0.08, 0), starts 0/π, stock
stance/cadence, unchanged servo contract (write_speed 400, acc 20,
slew 0.375 deg/tick, ceiling 350) — hard-asserted per rollout.
Controllers: scripted TripodGait AND the retained-turns checkpoint
`ppo_goal_cw_robotwalk_turns_20260907_yawref_cont8m.zip`
(sha `4a902839…`, PIN-verified). 18 valid fullmesh rollouts
(6 tick-scripted, 6 audit-scripted, 6 audit-checkpoint) + 6
torsion-dose rollouts. ZERO falls anywhere.

## Coordinate/sign validation (focus-note requirement) — PASSED

- Static hold: Σ normal force / weight = 0.969, sign convention +1,
  touch-sensor vs solver-normal median rel. err. **0.7%**, contact
  frames orthonormal to 9e-16 (`scripted_tick_fm.json`).
- Impulse closure (audit engine): net external yaw impulse vs
  d(Lz) — slope **1.000**, relative RMS residual **0.0007–0.0012**,
  `valid=true`, on ALL 12 audit rollouts. A sign/frame error anywhere
  would flip or break this.
- Behavior-neutrality: instrumented rollouts reproduce the pinned
  baseline wz/vx medians bit-for-bit (wz +0.0642/vx 0.0372 first
  cell; test-asserted vs `probe_turn_stancearm.rollout`).

## Findings (scripted baseline; the RL checkpoint shows the SAME fingerprint)

1. **NOT friction-cone saturation.** Slipping loaded pads sit near the
   cone only 3–15% of slip substeps; P(usage<0.5 | slip) is 0.32–0.86.
   Median per-leg cone usage 0.17–0.73 with mu=2.0 and ~15 N normals —
   most of the tangential budget is never used. Actuators are nowhere
   near the force rail (yaw rail fraction 0.000 in every cell;
   medians ~0.00–0.03 of the 2.2 N·m rail).
2. **Opposing-stance cancellation is the operative structure.** Median
   net yaw moment ≈ 0 (steady state) but GROSS opposing moments are
   ±0.45–0.53 N·m — net/gross ≈ 0.05. Per-leg medians while loaded:
   during a +0.15 turn the +y middle leg (L1) BRAKES at −0.42 N·m
   (largest single term), mirrored by L4 at −0.15; for −0.15 the
   mirror pair flips (L4 +0.43, L1 +0.15). Phase-resolved: each middle
   leg brakes hardest in a phase-locked HALF of its own stance
   (L1 early stance −0.77…−0.40, flipping positive late; L4 the
   mirror), i.e. the commanded stance paths are mutually inconsistent
   with any single rigid twist — internal forces fight, pads drift
   BELOW the cone.
3. **The net turn drive is carried by TORSIONAL pad couples, and the
   linear forces net-BRAKE the turn.** Per-cell impulse decomposition
   (13 s scored): force-moment impulse **−2.96 to −3.30 Nms** (opposing
   the commanded turn) vs couple impulse **+2.90 to +3.30 Nms**
   (driving it), balancing at wz ≈ 0.063 = 43% of command; identical
   mirrored numbers for the − direction, and same structure for the
   RL checkpoint (−2.6/−3.1 vs +2.6/+3.1 at wz 0.047–0.058). Gross
   couple magnitude (15–17 Nms) exceeds gross force moments (11–14).
4. **The plant's torsional friction is unphysical.** Foot geom
   friction = `2.0 0.1 0.001`: mu_torsion = 0.1 m ⇒ torsion cap
   0.1×15 N = **1.5 N·m per foot**. A physical estimate for the 9 mm
   boot ((2/3)·a·mu_slide with a ≈ 3.5 mm) is **~0.005 m ⇒ ~0.07 N·m**
   — the plant is ~20x too grippy in torsion, and the measured
   sustained couples (0.1–0.3 N·m/foot) exceed the physical cap 2–4x.
   The sim's turning equilibrium rests on a torsion channel the real
   robot cannot have.

## Torsional sensitivity A/B (mu_t 0.1 -> 0.005, both signs + straight)

Probe-local dose (foot+terrain mu_t -> 0.005 m, the physical
estimate; nothing fleet-wide changed), same 6 cells, impulse closure
still valid (slope 1.000, relRMS 0.0007–0.0011), ZERO falls:

| cell | wz base -> mu_t 0.005 | vx base -> dosed | force imp -> | couple imp -> |
|---|---|---|---|---|
| +0.15 @0  | +0.0642 -> +0.0565 (−12%) | 0.0372 -> 0.0446 (+20%) | −2.96 -> −0.13 | +2.96 -> +0.14 |
| +0.15 @π  | +0.0632 -> +0.0578 (−9%)  | 0.0363 -> 0.0453 | −3.18 -> −0.10 | +3.18 -> +0.10 |
| −0.15 @0  | −0.0631 -> −0.0570 (−10%) | 0.0364 -> 0.0456 | +2.90 -> +0.14 | −2.90 -> −0.15 |
| −0.15 @π  | −0.0651 -> −0.0562 (−14%) | 0.0370 -> 0.0448 | +3.30 -> +0.14 | −3.30 -> −0.14 |
| straight @0 | −0.0002 -> −0.0109 | 0.0401 -> 0.0470 (+17%) | +0.74 -> +0.01 | −0.74 -> −0.00 |
| straight @π | −0.0074 -> +0.0124 | 0.0402 -> 0.0469 | +0.18 -> −0.00 | −0.18 -> +0.00 |

- With physical torsion the phantom channel disappears as predicted
  (couple impulses 3.0 -> 0.1 Nms) and the linear-force moments
  reorganize from net-braking (−3.0) to near-zero — the equilibrium
  moves DOWN ~9–14% in BOTH turn directions (well outside the ±0.001
  start-to-start spread): sim turn authority at these cells is ~38% of
  command instead of 43%, i.e. the current plant OVERSTATES what the
  real boot can do.
- Side-findings: straight/arc vx +17–20% (torsional anchoring was
  costing forward progress), but straight-line yaw drift WORSENS to a
  phase-dependent ±0.011–0.012 (sign flips with start phase, the same
  defect class the cadence closure saw) — the dose is NOT a behavior
  lever, it is a fidelity question.
- Slip becomes more honestly cone-adjacent (P(near-cone|slip) rises to
  0.15–0.49) but still mostly sub-cone; the per-leg moment pattern
  becomes the left/right propulsion dipole (left legs +, right legs −,
  nearly identical across commands), i.e. the turn signal is a small
  residual on top of large canceling propulsion moments.

## Verdict

**The three closures' "traction-limited conversion" inference is
CORRECTED, not confirmed: the deficit is NOT a friction-budget wall.**
Measured, on both controllers, both directions, both starts:
(1) friction-cone usage stays low even while slipping (no saturation),
(2) actuators never touch the force rail,
(3) gross opposing stance moments cancel ~20:1 (commanded stance paths
    mutually inconsistent with the achievable twist), and
(4) the net turn drive in the CURRENT plant is carried by a torsional
    contact channel ~20x stronger than the physical boot allows; with
    a physical mu_t the equilibrium drops another ~12%.

By the pre-registered rule: NO 2M canary — no in-limits corrective
dose exists yet with a passed both-signs preflight (the torsion dose
itself regresses wz in both directions, and it is a fidelity change,
not a lever). The concrete measured next steps, in order:

1. OPERATOR-SCOPED (fleet plant contract, filed in
   OPERATOR_QUESTIONS.md): decide foot torsional friction for the
   mesh-family plants. Evidence here: mu_t=0.1 m is ~20x a physical
   boot estimate, carries the ENTIRE net sim turn drive at these
   cells, and its removal changes wz −12%/vx +20% — i.e. today's sim
   turn behavior (and anything trained on it) leans on a channel the
   hardware cannot supply. Transfer-risk for every turn gate.
2. In-limits gait-side design candidate (NOT one of the closed
   phase/posture/cadence dials): a stance-path twist-consistency dose
   — derate the commanded STANCE sweep twist toward the achievable
   equilibrium (swing/touchdown targets untouched) so simultaneous
   stance legs stop fighting; preflight it on the identical
   both-signs-gain + straight-health bar under BOTH mu_t values
   before any canary.
3. walkcurr cross-link (their 9-arm slip-floor closure demanded a
   structural contact lever): measure the ~5–6/m slip floor's
   sensitivity to mu_t 0.1 vs 0.005 before funding any policy-side
   slip mechanism on the mesh lineage.

## Limits

Single seed (0), starts 0/π, 15 s episodes, one plant family
(frozen full mesh; twin used for tests), scripted + one checkpoint;
LOAD_N=2 N, SLIP=0.02 m/s, NEAR_CONE=0.9 thresholds (reported, not
tuned); physical mu_t estimate is analytic (no bench measurement).
