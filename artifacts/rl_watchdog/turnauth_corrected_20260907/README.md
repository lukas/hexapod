# Corrected frozen turning diagnostic

Completed 2026-09-07 23:58 UTC. This closes the measurement repair;
the existing yaw qualification failures remain open.

Code: `dbedfdfe9f6a8efc33e46de41714d077fd97eb76`, containing the
validated probe repair `22554185432e1ea896aa6740085052fe30a76274`.
The focused physics suite passed 29 tests; independent review found no
blocker. The runner, exact configuration, checkpoint hashes and results
are included here. Full manifests and raw reports are retained on the
controller under `logs/ckpt_eval/turnauth_repaired_20260907_{scripted,cont8m,cigate8m}/`.

## Protocol and validation

Frozen checkpoints, seed 0, 15 seconds per rollout, seven command cells
and two actual tripod starts (0 and pi): 42 rollouts, no training steps.
Full STL mesh was required and measured: 34 meshes, 159 geoms, 4.80573 kg,
100 Hz control. Missing assets could not silently select the MJX twin.
All 42 rollouts had no falls and valid scored-window gait. All 42 angular
impulse checks passed with no unaccounted terms; worst relative RMS
residual was 0.001494 (0.150%).

The table reports ranges of median achieved yaw rate across the two starts,
in rad/s. Forward command for arc cells was 0.08 m/s.

| Command | Scripted | cont8m | cigate8m |
|---|---:|---:|---:|
| Turn in place +0.30 | +0.234 | +0.212 to +0.213 | +0.215 to +0.218 |
| Turn in place -0.30 | -0.234 | -0.210 to -0.209 | -0.198 to -0.194 |
| Arc +0.15 | +0.063 to +0.064 | +0.05795 to +0.05802 | +0.062 to +0.065 |
| Arc -0.15 | -0.065 to -0.063 | -0.049 to -0.047 | -0.048 to -0.045 |
| Arc +0.30 | +0.080 to +0.082 | +0.081 to +0.084 | +0.082 to +0.085 |
| Arc -0.30 | -0.081 to -0.077 | -0.086 to -0.085 | -0.081 to -0.080 |

## Interpretation and next work

The scripted baseline also substantially undertracks combined forward/yaw
commands. The course-income gate does not consistently improve both turn
directions. These results do not establish seed-history causation or a
single culpable braking leg. Per-foot force and contact-couple impulses can
be large and opposing; use their sum, actual turn sign and momentum closure.
Near-zero net yaw impulse at steady turning is expected.

The next bounded steering investigation should locate the loss of commanded
motion along the controller path: desired foot trajectory, inverse-kinematic
joint target, clipped/slew-limited command, measured joint response and
body motion. Compare straight, in-place and the actual +/-0.15 arc cells
under the existing limits. Use the present frozen policies and scripted
control first. Any training continuation needs a measured mechanism and
an explicit budget; do not substitute a fresh seed or another already
closed radius/price sweep for that diagnosis.

## Limits

- This is a frozen diagnostic, not a rerun or pass of the qualification gate.
- BC-anchor residual is explicitly unavailable. Observation/internal-teacher
  clocks were not proven aligned; scripted and learned phase labels do not
  establish phase-matched teacher transmission.
- Auxiliary gait/slip summaries use post-2-second walk rows and are distinct
  from the standard gate. Filtered-row differences must not bridge non-walk
  gaps when interpreting future mixed-mode uses.
- Compare historical reports only when actual model variant and conditions
  match. Scratch gate results on `mesh_mjx_twin` are a separate experiment.
- Initial isolated launch attempts failed before rollouts because two runtime
  dependencies were omitted. They were supplied from the unchanged project
  sources, the full-mesh environment was verified, and all three final runs
  completed. No active trainer source or robot files were overwritten.
