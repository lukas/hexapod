# Contact-wrench measurements and torsional-friction sensitivity

Review corrected2026-09-08 03:31 UTC; replaces the initial interpretation.
Raw measurement JSON is retained unchanged. The archived probe_turn_traction.py
is a historical source copy from before the reset-survival fix; reproduce with
the current repository runner instead.

The audited force/couple decomposition passes the existing substep
angular-momentum closure check. Opposing per-leg yaw moments and large
contact-couple contributions are measured properties of these rollouts.
They do not uniquely establish inconsistent commanded stance paths:
small net torque also accompanies approximately steady angular
momentum. Same-phase commanded/actual path evidence is needed for that
causal attribution.

The original statistics called "cone usage" measured only
`hypot(tangent1,tangent2)/(slide_mu_1*normal_force)`. They omit the
second tangent's own coefficient, torsion, rolling, and the distinction
between elliptic and pyramidal constraints. They therefore cannot rule
out saturation of the full condim=6 contact cone. Existing JSON values
remain valid as **planar slide projections**; saturation conclusions
must use newly computed full-cone fields. Angular-momentum closure
validates wrench accounting, not the completeness of a friction-budget
projection.

In the corrected probe-local sensitivity test, changing torsional
friction from 0.1 to 0.005 m changed scripted arc yaw magnitude by
approximately -9% to -14%, increased forward speed by roughly 17–20%,
and changed straight yaw drift, with no observed falls in these
six cells. This establishes sensitivity to the assumed contact
coefficient. These are modified-contact-model rollouts, separate from
qualification under the frozen plant contract.

The 0.005 m value is an **assumed contact-patch estimate, not measured
calibration**. For a uniformly pressured circular patch of radius
a=3.5 mm and sliding coefficient 2, integrating Coulomb friction gives
`torsional_mu = (2/3)*a*sliding_mu ~= 0.0047 m`. Neither that pressure
profile nor that effective contact radius was measured here. The
experiment does not establish an absolute physical torque cap, prove
the real boot cannot supply the measured couples, or qualify the
existing 0.1 m coefficient as unphysical. It identifies a consequential
parameter for future calibration.

No controller canary or qualification improvement follows from this
sensitivity alone. The original command targets, qualification
criteria, and physical/motor limits remain unchanged.

## Exact smaller wording changes

- Replace "NOT cone saturation", "NOT a friction-budget wall", and
  "low cone usage proves opposing-stance cancellation" with:
  **"The original planar usage statistic does not decide full-cone
  saturation; opposing moments are observed, while their causal origin
  remains unresolved."**
- Replace "physical torsion", "phantom torsion", "20x too grippy", and
  "hardware cannot supply" with:
  **"the lower assumed torsional coefficient used for sensitivity."**
- Label the audit's load selection accurately:
  **"any active positive-normal-force foot contact; no 2 N threshold."**
  The legacy `LOAD_N=2` tick-engine threshold does not describe the
  audit engine's mask.
- Treat net/gross and couple/net ratios carefully when the net impulse
  is close to zero. Report signed force/couple contributions directly;
  large ratios are not evidence of a dominant energy source.
- Preserve the earlier wiped-dose experiment as invalid activation
  evidence. Only the reset-surviving rerun tests coefficient sensitivity.


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


## Corrected probe-local sensitivity measurements

These modified-parameter rollouts are separate from frozen-plant qualification.
The first wiped-dose attempt was invalid; the table is its reset-surviving rerun.

| cell | wz base -> mu_t 0.005 | vx base -> dosed | force imp -> | couple imp -> |
|---|---|---|---|---|
| +0.15 @0  | +0.0642 -> +0.0565 (−12%) | 0.0372 -> 0.0446 (+20%) | −2.96 -> −0.13 | +2.96 -> +0.14 |
| +0.15 @π  | +0.0632 -> +0.0578 (−9%)  | 0.0363 -> 0.0453 | −3.18 -> −0.10 | +3.18 -> +0.10 |
| −0.15 @0  | −0.0631 -> −0.0570 (−10%) | 0.0364 -> 0.0456 | +2.90 -> +0.14 | −2.90 -> −0.15 |
| −0.15 @π  | −0.0651 -> −0.0562 (−14%) | 0.0370 -> 0.0448 | +3.30 -> +0.14 | −3.30 -> −0.14 |
| straight @0 | −0.0002 -> −0.0109 | 0.0401 -> 0.0470 (+17%) | +0.74 -> +0.01 | −0.74 -> −0.00 |
| straight @π | −0.0074 -> +0.0124 | 0.0402 -> 0.0469 | +0.18 -> −0.00 | −0.18 -> +0.00 |

## Next action

Rerun full-cone accounting on the original scripted/checkpoint baseline.
A stance-path candidate needs same-phase commanded/actual path evidence and
the unchanged original both-signs-gain/straight-health preflight before one
bounded existing-seed canary. Lower-torsion rows remain separate sensitivity.
No operator reply is required for these authorized simulation diagnostics.
