# Yaw-moment-arm vs stance posture on the frozen full-mesh plant — CLOSED (no yaw gain; vx side-finding)

Completed 2026-09-08 ~03:3x UTC by the operator-requested follow-up cycle
after the lift-lead closure (`../turn_liftlead_20260908/README.md`),
executing the focus-note-scoped experiment (fb operator lane
20260908T011913Z): a bounded SIM-only kinematic/contact feasibility bank
for baseline vs ONE extended nominal knee stance selected by Jacobian
reach analysis. Zero training steps, zero robot work. Runner
`probe_turn_stancearm.py` (copy here; committed at
`rl_move/sim/probe_turn_stancearm.py`). Controller copies:
`logs/ckpt_eval/turn_stancearm_20260908/`. Same isolated worktree
(`/workspace/hexapod-turnphase-wt/` + root's frozen assets).

## Plant/config pinning

Identical to the lift-lead closure: frozen full-STL plant
(`hexapod_mesh.xml` sha 7efb8e8a…, 34 meshes, **4.80573 kg**, 100 Hz,
re-verified before launch), corrected-audit cfg_set, seed 0, 15 s,
cells (0.08, ±0.15) + straight guard (0.08, 0), starts 0/π. Every
rollout hard-asserts variant/nmesh/mass/dt and the unchanged contract:
write_speed 400, write_acc 20, slew 0.375 deg/tick, ceiling 350.
Nothing deployed; bus/firmware/CAD/stance defaults untouched.

## Stance selection (Jacobian reach analysis, this cycle)

Stock stance hip 20°/knee 100° (WALK_PLANT): planar yaw-axis→foot reach
71.0 mm, foot radius 171.0 mm, slew-limited body-yaw arm gain
reach/(LEG_RADIAL+reach) = 0.415. Candidates knee 95/90/85/80 all
IK-feasible with ≥17.7° margin on every commanded joint over the full
arc/straight gait sweep. Selected the focus-note candidate **knee 90°**:
reach 97.1 mm (+37%), foot radius 197.1 mm, arm gain 0.493 (+19%);
commanded yaw amplitude SHRINKS ±15.4°→±11.8° (limit ±35°), hip
3.7..20.4° (limits −80..40), knee 84.7..94.9° (limits −20..150), body
height +2.3 mm; foot separation ~197 mm — no collision exposure. A
fail-closed `feasibility_guard` sweeps the commanded gait per stance and
aborts if IK fails or any joint margin <2° (it passed; margins are in
each JSON). The probe's baseline arm reproduces the lift-lead baseline
BIT-EXACTLY (vx 0.03722/wz 0.06424 first cell) — harness change is
behavior-neutral at the stock stance.

## Results (full mesh, 12 rollouts, ZERO falls)

| arm | wz +0.15 (mean, spread over starts) | wz −0.15 | straight vx | straight \|wz\| max | dyn arm (loaded pads) | loaded-pad resid med | lift p90 | scuff |
|---|---|---|---|---|---|---|---|---|
| knee 100 | +0.0637 ±0.0010 | −0.0641 ±0.0020 | 0.0401/0.0402 | 0.0074 | 173 mm | 0.0117 m/s | 3.5 mm | 0.70 |
| knee 90 | +0.0651 ±0.0042 | −0.0645 ±0.0041 | **0.0487/0.0483** | 0.0036 | **198 mm** | 0.0136 m/s | 4.1 mm | 0.69 |

- **Yaw: NO measured gain outside noise in either direction** (+2.1% and
  +0.7%, both smaller than the candidate's own start-to-start spread).
  The wz deficit stays ~57% of command in both arms.
- The mechanism DID engage as designed: realized loaded-pad moment arm
  matches plan (173→198 mm) and the executed FK tangential sweep twist
  rose +15% (0.0568→0.0653) — but the increment is absorbed by
  loaded-pad residual slip (+16%, 0.0117→0.0136 m/s) instead of
  converting to body rotation. At these amplitudes the yaw bottleneck is
  TRACTION-LIMITED CONVERSION of the executed sweep, not joint-rate/arm
  limits and not timing (lift-lead closure).
- **Side-finding (consistent, 6/6 rollouts): forward progress improves
  +12% on arcs (vx 0.037→0.042) and +21% straight (0.040→0.0487), with
  straight-guard yaw drift HALVED (0.0074→0.0036), slip still low, gait
  retained, zero falls, all joint margins ≥19.6°.** A candidate speed
  lever for the speed-soft todaypolicy walk stack — as a training/eval
  stance for future runs only; deployed stance defaults untouched per
  the focus note.

## VERDICT

**Extended-stance yaw-arm lever is CLOSED on the frozen full-mesh plant:
the pre-registered bar (wz gain in BOTH directions with retained
gait/progress/slip) is unmet — NO 2M training canary launched (by the
rule).** This is a narrow finding: knee-90 stance at these arc cells on
this plant; it does not close stance posture as a SPEED lever, and it
does not assert any-controller impossibility.

## Next justified current-limit mechanism (nomination, not a launch)

Measured facts: yaw deficit is invariant to arm/amplitude scaling
(this bank) and to lift timing (lift-lead closure); the executed sweep
increment sheds into traction slip. Both point at the stride FREQUENCY:
first-order servo-profile lag attenuates a fixed FRACTION of the sweep
at the gait's stride frequency, and higher tangential accelerations cost
traction. The one in-limits, untested lever distinct from the closed set
(stance-radius ±5%, yaw-gain/omega scaling, lift phase lead, stance
posture): **CADENCE — period_scale within the gait's existing
SCALE_PERIOD bounds (0.40..2.00)** at fixed commanded twist: longer
period = larger per-cycle sweep at lower angular frequency = less
fractional lag attenuation and lower tangential acceleration. A future
bounded bank should compare baseline vs ONE slower cadence (e.g.
period_scale 1.5) at the same cells/starts/plant/contract, same
feasibility-guard discipline, same both-signs bar.

## Limits

Single seed (0), starts 0/π, scripted controller only (a frozen policy
cannot take a stance dose), one candidate stance, 15 s episodes.
