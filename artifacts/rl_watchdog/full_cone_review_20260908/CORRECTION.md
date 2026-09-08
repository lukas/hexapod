# Full-cone review correction — prepared for owner handoff

Prepared against code `d3b84761168db9f665feacaa313f35d0cbcfb4a6` in
an isolated local worktree. No controller source, model default,
training, live process, or canonical scientific verdict was changed.

## Replace the artifact headline and scientific conclusion

**Contact-wrench measurements and torsional-friction sensitivity on
the frozen steering baseline**

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

## Implemented local diagnostic repair

The CLI's `--engine audit` uses `pta.rollout(contact_audit=True)`
and `_ContactAudit`. The repair adds `traction.full_cone` there:
per-contact absolute wrench components normalized by their own
friction coefficient and compressive normal force; L2 for elliptic
cones, L1 for pyramidal cones; active dimensions only (1,3,4,6).
It reports tangent1/tangent2/spin/roll1/roll2 components, per-foot
load-weighted mean and contact-maximum statistics, cone type,
observed dimensions, and explicit invalid-contact reasons.
Zero-force zero-friction components consume no budget; nonzero force
on a zero coefficient makes the new result invalid rather than
silently reporting low usage. Noncompressive contacts have no defined
utilization. Legacy planar values and historical gate metrics remain.

Slip conditioning remains per-foot material-point XY speed with
contact-maximum utilization, explicitly documented; this is not a
same-contact dissipation estimate. No 2 N mask or solver/physics
semantics were changed.

## Validation

Before source edits, the four new spin/roll/anisotropic contact tests
failed on the baseline's missing full-cone result. Their existing
planar estimator simultaneously returned 0 for the pure torsion and
rolling cases and 0.5 for the anisotropic tangent case, despite each
being at its full cone boundary.

After the repair: **16 new tests passed**. Combined focused suite:
**64 passed in 10.15 s** (`test_contact_full_cone.py`,
`test_probe_turn_authority.py`, `test_probe_turn_traction.py`,
`test_probe_turn_stancearm.py`, `test_probe_turn_cadence.py`).
The tests exercise actual `_ContactAudit.mj_step/summary`, not only a
standalone formula. They cover torsion-only, both rolling axes,
anisotropic/diagonal cones, sliding-spin budget coupling, active
condim selection, contact permutation, zero normal/friction,
strict JSON output, and the actual CLI-used `pta.rollout` path.
Its short real MuJoCo audit-on/off behavior matches exactly, with
valid angular-momentum closure. No live diagnostic matrix was rerun.

Primary definitions:
[MuJoCo contact cones](https://mujoco.readthedocs.io/en/stable/computation/index.html#friction-cones),
[contact-frame and friction ordering](https://github.com/google-deepmind/mujoco/blob/main/include/mujoco/mjdata.h).
