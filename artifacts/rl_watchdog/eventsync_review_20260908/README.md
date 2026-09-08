# Event-sync diagnostic review and repair

Base: `2858d37fa`. Isolated diagnostic-only repair. No gait, physics, reward,
servo contract, training, qualification, or physical changes. No new simulation
bank was run for this repair. The live owner files were not edited.

## Correctness changes

The old matcher wrapped every actual event in the entire episode modulo the
period before finding the closest offset. One favorable touchdown could be
reused for every cycle, hiding missing events and jitter. The new matcher
preserves chronological order, uses each actual event at most once, and only
permits matches with real-time absolute separation strictly below half a gait
period. A dynamic program maximizes match count then minimizes total offset.
Unmatched planned and actual events, matched pairs and counts are explicit.
Circular medians, IQRs and leg spread are computed only AFTER event pairing;
the wrap seam cannot fabricate a nearly full-period inter-leg difference.

Concrete old-source reproduction (period75ticks; planned events0/75/150/225):

- Actual events10/100/175/250 produce old offsets `[10.0, 10.0, 10.0, 10.0]`; corrected
  offsets are10/25/25/25. The old calculation erased within-leg jitter.
- Only one actual event10 produces old offsets `[10.0, 10.0, 10.0, 10.0]`; the corrected
  matcher reports one match and missing planned events75/150/225.

The CLI now requires the exact six unique original cells (vx0.08, wz±0.15/0,
starts0/pi), frozen fullmesh34/4.80573kg, seed0,15seconds, finite data,
nonempty per-leg event evidence, no falls, valid feasibility, and exact pinned
body-median/tick-count parity. It independently checks body values against
PARITY_REF, so `parity.ok=true` cannot hide changed measurements. Incomplete
matrices, duplicate cells, failed pins/parity/feasibility and nonfinite outputs
produce strict JSON with failed validation and a nonzero exit code.

## Interpretation changes

Historical S1/S2/S3 thresholds and arithmetic remain descriptive under
`historical_bar_supported`. Complete valid evidence may yield
`observational_screen_passed`. The causal/intervention `supported` field remains
false: this screen cannot establish an intervention's efficacy or a class closure.

The original “counterfactual” algebra equals the observed majority-tripod
population's mean yaw. Conditioning on support state does not hold phase,
velocity history, load, contact wrench, or controller state fixed. Reweighting
those observed samples neither predicts a controller intervention nor bounds
its best possible performance. A failed screen is insufficient evidence for
this proposed mechanism, not proof that event-based synchronization cannot work.
The existing negative command-path result and other closed recipe results are
not reopened by this accounting repair.

Legacy `pureA/pureB` population names are preserved but explicitly mean at least
two loaded feet from one tripod and at most one from the other. This includes
two-foot support; it is not guaranteed complete three-foot tripod support.
Contacts use the last physics solve (endpoint minus the physics timestep),
sampled at the control rate. Event threshold is0.5N; loaded-state threshold
is2N. These are threshold crossings, not measured per-leg joint lag, and not
recomputed endpoint contacts. Sampling semantics are included in each row.

The screen leaves the original continuous joystick commands and qualification
gates unchanged. It neither proves preserved forward progress/slip nor licenses
an alternative averaged-course gate. Any future intervention still requires the
original matched both-signs/straight-health preflight and original criteria.

## Validation

57 focused tests passed:9 retained descriptive-bar tests,36 actual CLI/matrix
tests,12 event-matching regressions. Covers cross-cycle event reuse, missed
cycles, chatter, chronological assignment, ambiguous half-period matches,
circular seam handling, sparse event counts, exact parity, bad physics/seed/
duration, nonfinite strict JSON and feasibility/pin failures.

Baseline CLI receipt: loading the exact old2858d37fa source into a temporary
module, the missing-straight and failed-parity cases both fail their regression
assertion because old `main()` returns0. Two failures in0.06seconds; the repaired
cases pass. Nine old pure tests did not exercise the actual CLI or event jitter.
No extra simulation, gate rerun, or training was performed.
