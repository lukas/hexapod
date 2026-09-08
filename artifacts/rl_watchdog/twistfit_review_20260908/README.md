# Twist-fit diagnostic review and repair

Base: `046c708a4`. Diagnostic-only repair; no gait, environment, model, contact,
servo, reward, training, or physical changes. S1/S2/S3 values and their historical
thresholds remain descriptive and are preserved as `bar`, `checks`, and
`legacy_bar_supported`.

## What changed

- Reported joints and true mesh pad transforms now share the post-control-step
  endpoint. Pad transforms are computed by `mj_kinematics` on private `MjData`,
  including copied mocap poses; the live simulation is never refreshed. Contact
  sensors still describe the last physics solve, one physics timestep before
  that endpoint. The output names these distinct timestamps and semantics.
- Added eroded `plan_contact` fits and `duty_plan_contact`: planned stance AND
  last-solve loaded contact. Existing plan-only and contact-only summaries remain.
  Contact-only populations may contain planned swing scuffs; the intersection is
  not a claim that endpoint contact was recomputed.
- The CLI requires exactly the original six unique cells: vx0.08, wz±0.15 and0,
  phases0 andpi. Missing/duplicate cells or references, nonfinite data, falls,
  inadequate fits, failed feasibility, and failed parity reject support. Reference
  policy, per-row seed, optional outer seed/duration/config, exact body medians,
  scored count, and fall status are checked. The JSON explicitly labels historical
  reference parity as summary parity, not full-trajectory evidence.
- `supported` additionally requires simultaneous best-fit normalized residual
  >0.10 in all four arc cells. This is a separately named, review-added diagnostic
  threshold, not a retrospective change to the historical bar. S1/S2 can reflect
  one common wrong rigid twist; S3 can reflect different feet sampling different
  phases of a common time-varying twist. Neither establishes mutually inconsistent
  stance paths without simultaneous residual evidence.

## Validation

Focused suite: 46 passed, including34 matrix/actual-CLI cases,9 retained math
cases,1 real MuJoCo endpoint test, and2 actual rollout parity cases. The latter
run4.1 seconds at100Hz, phasepi, on the portable mesh twin and local full-STL
model. The full-mesh case retains all production assertions:34 meshes,4.80573kg,
100Hz and the unchanged motor contract. It reads existing assets via the opt-in
`HEXAPOD_TWISTFIT_TEST_MESH_ROOT` test variable; no assets are changed or committed.

For each plant, revised versus original `pta.rollout` matches every action,
qpos, qvel, ctrl, warm-start acceleration, reward, and termination/truncation tick
exactly. Every private endpoint sample leaves the live arrays unchanged. A moving
distal-pad test explicitly distinguishes the corrected endpoint position from
the old cached solve-time position. The full-mesh case skips when local STL
assets are unavailable; portable twin and endpoint coverage still run.

Baseline failure evidence: the exact old046c708a4 module was loaded from a
temporary file, without changing production or worktree source. Four actual CLI
regressions failed in0.12s: missing reference, missing straight cells, duplicate
straight cells, and repeated phase0 instead of0/pi all returned exit0,
`supported=true`, and `parity_fail_cells=0`. All four pass with the repair.

## Scientific limits and corrected wording

The owner's negative command-path result remains negative: reported command yaw
gain about0.9998 and residual0.015–0.018 do not justify reopening the command
correction candidate merely because diagnostic bookkeeping changed. No new
scientific rollouts, training, or qualification claims follow from this repair.

Use: “The measured commanded paths do not meet the preregistered evidence bar
for this stance-path correction. Differences in later summaries are descriptive;
they do not uniquely localize execution loss or establish that friction-cone
engagement is secondary.”

Nominal FK versus true mesh body origins, finite control-rate differences,
solve-time contact selection, and roll/pitch contributions to planar pad motion
limit causal stage attribution. Friction and kinematic incompatibility need not
be mutually exclusive. A future correction must itself pass the actual-path IK,
limit and touchdown/liftoff continuity guard: integrating an exact arc generally
moves the endpoints of the old chord. No correction is implemented here, and the
existing stock-gait feasibility guard is unchanged.

## Deployed matrix verification

Root deployed7ca821fb1 and repeated the original six-cell frozen15s
matrix in the existing isolated steering worktree. All six body medians,
scored counts and fall statuses match the original reference exactly;
validation passes with zero failures. Both legacy and reviewed support
remain false. The reviewed result is twistfit_fm.json in this directory.
No plant/config/assets were changed. This rerun validates diagnostic
sampling and negative support; it does not establish causal localization.
