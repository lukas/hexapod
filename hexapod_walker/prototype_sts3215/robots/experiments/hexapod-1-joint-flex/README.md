# `hexapod-1` joint-flex localization runbook

This is a restartable operator/LLM protocol for determining where the reported
joint looseness originates. Read [`status.yaml`](status.yaml) first and update
it after every completed phase. Raw recordings belong under the ignored
`artifacts/joint_flex/` tree, not in Git.

## Objective and current evidence

Separate motion in these possible sources:

1. servo output, shaft, gearbox, or bearing motion;
2. hidden horn/spline or horn-thread engagement;
3. accessible screw-head movement within the printed yoke holes;
4. yoke spreading/twisting;
5. femur beam flex;
6. time-dependent creep, clamp settling, or progressive wear.

The operator reports that the screws appear to rock with the femur, the horn
cannot be accessed, and looseness increases over time. `hexapod-1` is a legacy
assembly with a confirmed two-piece coxa and thinner yaw bearings. The exact
target leg and whether the reported femur motion is at the hip must be confirmed
before recording.

## Non-negotiable safety and authority boundary

- This document alone does **not** authorize gait, stand, plant, centering,
  joint, or other motor commands. Each powered run requires explicit operator
  authorization in the current conversation.
- The operator rigidly supports the chassis and keeps the test area clear.
  Tests may use operator-applied loads or an explicitly authorized, bounded
  motion protocol with current, feedback, geometry, and timeout limits.
- Stop immediately for a crack/snap, crack growth, sudden residual movement,
  heat, unexpected powered movement, moving supports, or tipping risk.
- Do not tighten, loosen, disassemble, or touch the hidden horn during the
  measurement series. Such a change invalidates the before/after comparison.
- For an automated supported single-joint ground probe, debounce current trips
  across three consecutive feedback polls. After a confirmed current trip,
  limp, wait for normal feedback/current, and retry once. If the restarted
  attempt trips again quickly, end the test and remain limp. Never retry a tip,
  brownout, hot motor, three consecutive missing-servo reads, support movement,
  stand/plant command, or gait failure. One dropped feedback sample is retried
  and does not limp or end the test.

## Handoff checklist for the next LLM

1. Read the repository `AGENTS.md`, `robots/hexapod-1.yaml`, this runbook, and
   `status.yaml`.
2. Ask the operator to identify the suspect leg (`L0`-`L5`) and joint
   (`hip`/`knee`), and record the answer in `status.yaml`.
3. Identify the two camera devices without opening the robot or commanding it.
   Record camera model/index, resolution, frame rate, and assigned view.
4. Ask which rigid part carries the existing side AprilTag. Record its tag ID,
   black-square size, and whether it is fixed-side or moving-side.
5. Confirm the marker layout below. A single robot tag is not sufficient.
6. Create a run directory and manifest from
   [`run-manifest-template.yaml`](run-manifest-template.yaml) before capture.
   Never overwrite an old run; use an ISO-like run ID such as
   `20260902T143000-static-hip-L2`.
7. Execute phases in order. Do not skip the stationary noise-floor phase.
8. Update phase state, artifact paths, numerical results, and the evidence-based
   conclusion in `status.yaml`.

## Camera and marker layout

Use rigid tripods, locked focus/exposure/white balance, bright lighting, and the
highest practical frame rate. Avoid digital stabilization. Put a ruler or a tag
of measured size near the joint plane.

- **Face camera:** optical axis approximately along the tested joint axis. It
  sees rotation of the joint face, screw circle, yoke, and femur in-plane.
- **Edge camera:** 60-90 degrees from the face camera. It sees screw tilt,
  axial gaps, yoke-arm spreading, and out-of-plane twist.
- **World reference:** a stationary floor/table marker visible in both views.
  The existing side AprilTag may serve as the fixed robot reference only if it
  is rigidly attached upstream of the suspect joint.

Apply small removable, high-contrast markers without changing clamp load:

| ID | Location | Purpose |
| --- | --- | --- |
| `R` | fixed servo housing/cradle or chassis | upstream rigid reference |
| `C` | center spline-screw head, only if already visible | horn/output surrogate; optional |
| `S` | one accessible perimeter screw head | screw motion |
| `Y` | printed yoke immediately beside `S` | screw-versus-hole motion |
| `F1` | proximal femur just beyond the yoke | proximal link angle |
| `F2` | distal femur | beam bending relative to `F1` |

Draw a fine witness line continuously across the accessible screw head and
adjacent print. Do not turn the screw. If the existing tag is moving-side,
add a fixed-side marker; if it is fixed-side, add a moving-side marker.

The existing local tree may contain `knee_yoke_apriltag_flag/`. That accessory
was designed for a production tibia knee yoke and follows the four screw heads.
It may be used there after an unpowered clearance sweep. Do not assume it fits a
legacy hip/femur yoke without a separate physical clearance check.

## Run directory contract

Create:

```text
artifacts/joint_flex/hexapod-1/<run-id>/
  manifest.yaml
  face_raw.mp4
  edge_raw.mp4
  encoder.jsonl                 # optional, read-only
  measurements.csv
  analysis.yaml
  face_annotated.mp4            # optional
  edge_annotated.mp4            # optional
```

Initialize a run only after the operator has identified the target leg and
joint. The helper refuses to overwrite an existing run:

```bash
uv run python robots/experiments/hexapod-1-joint-flex/joint_flex_run.py init \
  --leg L2 --joint hip
```

After filling in `manifest.yaml`, check that the documented Phase 0 capture
prerequisites are present. This performs no robot I/O:

```bash
uv run python robots/experiments/hexapod-1-joint-flex/joint_flex_run.py check \
  artifacts/joint_flex/hexapod-1/<run-id>/manifest.yaml
```

`manifest.yaml` must contain the robot ID, leg, joint, timestamp/time zone,
camera metadata, tag/marker dimensions and locations, lever arm, operator-set
force ceiling, servo power/torque state, and every file name. Synchronize the
two videos with one visible LED flash at the start and another at the end. Do
not claim stereo/3-D accuracy unless both cameras have individual intrinsic
calibrations and a measured common-world extrinsic calibration.

If `linux_control/track_apriltags.py` exists in the checkout, it may record one
camera per process and optionally collect read-only feedback. Use a separately
calibrated config for each camera. `--robot-url`, when supported by that local
version, must remain GET/read-only; inspect the implementation before use. An
example camera-only command is:

```bash
cd hexapod_walker/prototype_sts3215
uv run python linux_control/track_apriltags.py \
  <camera-specific-config.json> \
  --camera <index> --duration <seconds> --processing-width 0 \
  --raw-output <run-dir>/face_raw.mp4 \
  --pose-output <run-dir>/face_pose.jsonl
```

If that tool is absent, native camera recordings are sufficient. The LED sync,
stationary reference, measured scale, and manifest are mandatory either way.

## Phase 0 — preflight

The operator must confirm:

- chassis is rigidly supported and the tested leg is off the ground;
- no support or camera moves under a gentle preliminary touch;
- tested joints are power-off or confirmed limp/torque-disabled;
- no visible crack already requires stopping;
- all markers are rigid and visible in both assigned views;
- load point and joint-axis-to-load-point lever arm are marked and measured;
- a safe maximum force below normal service load has been chosen by the
  operator.

Record a spoken or written load cue visible/audible in both videos. Never infer
force from hand position alone; use a force gauge or known hanging mass.

## Phase 1 — stationary noise floor

Record 15-20 seconds with no contact and no load. For every tracked coordinate
or angle, calculate median, peak-to-peak range, and robust spread (MAD or
standard deviation). Also measure apparent relative motion for `R-S`, `S-Y`,
`Y-F1`, and `F1-F2`.

Do not interpret later deflection unless it clearly exceeds this measured noise
and both cameras agree on the direction expected from their view.

## Phase 2 — bidirectional quasi-static load sweep

At the marked lever arm, the operator performs five slow cycles:

```text
zero -> +F1 -> +F2 -> ... -> +Fmax -> zero
     -> -F1 -> -F2 -> ... -> -Fmax -> zero
```

Hold each step for about five seconds. `Fmax` and the step sizes are selected by
the operator, not by the LLM. Record actual force at every plateau and compute
joint torque as `force_N * lever_arm_m`.

For every plateau, estimate:

- encoder angle, if read-only feedback is safely available;
- `R -> C`, `R -> S`, `R -> Y`, `R -> F1`, and `R -> F2` angles;
- axial separation or yoke-arm spread from the edge view;
- witness-line rotation or discontinuity.

Plot angle versus torque for loading and unloading separately. Retain signed
data; do not average the two directions before measuring backlash/hysteresis.

## Phase 3 — constant-load creep and recovery

The operator applies one modest, repeatable load and holds it for 60-120
seconds, then removes it while recording at least 120 seconds of recovery.
Measure:

- immediate deflection;
- additional deflection versus log time while force is constant;
- residual deflection immediately after unload;
- recovered fraction after 30 and 120 seconds.

Growing displacement at constant force supports creep or settling. Complete
recovery supports elastic compliance. A persistent zero shift supports slip,
hole enlargement, local crushing, or fastener seating.

## Phase 4 — cycle sensitivity

After the earlier phases are safe, the operator performs 25-50 gentle manual
load reversals below `Fmax`. Repeat Phases 1 and 2 without changing cameras,
markers, fasteners, supports, or load point.

- Same slope with shifted zero: interface slip/settling.
- Softer angle-versus-torque slope: progressive damage or preload loss.
- Same slope and zero within noise: no measurable progression at this dose.

## Phase 5 — optional edge-view isolation

Only if the preceding phases are safe, apply a very small operator-controlled
load along the joint axis while the edge camera watches. This is not the main
joint-torque test. It checks whether one yoke arm opens, a screw head tilts, or
the two-piece coxa/bearing stack moves axially. Stop at the first visible gap or
nonlinear movement; do not use this phase to proof-load the part.

## Derived signals and interpretation

Use consistent signed angles. Define:

```text
screw_in_hole_motion = theta_S - theta_Y
proximal_link_motion = theta_F1 - theta_Y
femur_bend           = theta_F2 - theta_F1
post_encoder_motion  = theta_Y - theta_encoder
```

| Observation above noise | Strongest implication |
| --- | --- |
| Fixed marker `R` moves with the support/world marker | Invalid setup; support or camera contamination |
| Encoder changes with the visible output/link | Servo output, geartrain, shaft, or bearing motion participates |
| Encoder and `C` stay fixed while `S` and `Y` move together | Hidden perimeter screw-to-horn engagement is favored |
| `S` moves relative to adjacent plastic `Y` | Printed-hole clearance, local crushing, or screw-head seating |
| Witness line rotates across head/print boundary | Screw unwinding |
| Witness line stays aligned while head and yoke rock together | Rocking/clearance rather than screw rotation |
| `F2-F1` grows with torque | Femur beam flex |
| Edge view shows asymmetric arm separation | Yoke spreading/twist or clamp-stack compliance |
| `C`, `S`, and `Y` move together relative to `R` | Horn/spline, output shaft, gearbox, or upstream bearing motion |
| Deflection grows at constant force | Creep or progressive seating |
| Nonzero displacement remains after unload | Slip, wear, crushing, or lost preload |

If `C` cannot be seen, video cannot fully distinguish horn-to-spline motion
from horn-thread/screw engagement. Record that limitation instead of claiming a
unique root cause.

## Completion criterion

The manual force-localization experiment is complete only when:

1. both cameras pass their stationary noise-floor check;
2. at least three valid bidirectional cycles agree;
3. creep/recovery is measured or explicitly ruled unsafe;
4. the conclusion names the measured relative motion and uncertainty;
5. raw data and a manifest are preserved;
6. `status.yaml` records the result and the next reversible test or repair.

Do not install compression spacers, replace bearings, or redesign the yoke as
part of this diagnostic. Those are separate interventions to compare only after
a valid baseline exists.
