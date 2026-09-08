# Turn-pipeline stage decomposition — where combined-command motion is lost

> Review correction, 2026-09-08 00:52 UTC: the universal impossibility,
> common 0.040 m/s bound, negligible-slip and assumed-derating conclusions
> below are superseded. These are internally matched measurements on a
> 3.494226 kg model, not the prior frozen 4.80573 kg plant.
> Original qualification and physical limits remain unchanged.
> See [independent review and next experiment](../turnpipeline_review_20260908.md).
> The original measurements and interpretation are retained below for provenance.


Completed 2026-09-08 ~00:4x UTC. Bounded follow-up to the corrected frozen
turn audit (`../turnauth_corrected_20260907/`), executing its named next
step: locate the loss of commanded motion along desired foot trajectory ->
IK joint target -> clipped/slew-limited command -> measured joint response
-> foot-vs-body motion -> body twist. Zero training steps; frozen seed-0
policies and the scripted TripodGait; full STL mesh model verified per
rollout (34 meshes, 100 Hz); isolated worktree at `99bb5c01` (contains the
validated probe repair 22554185); runner `probe_turn_pipeline.py` (copy
here; committed at `rl_move/sim/probe_turn_pipeline.py`). Controller
copies: `logs/ckpt_eval/turn_pipeline_20260908/`.

Method: at each pipeline stage, fit the planar body twist (vx, vy, wz)
implied by the stance/contact feet's body-frame velocities (no-slip
least squares, f_dot = -(v + w x p)), per tick, medians over the scored
window. Stages: `des` (scripted desired joint targets = plan+IK), `prop`
(post action conversion), `safe` (post SafetyLayer clip/slew), `act`
(measured joints, same FK), `pads` (true MuJoCo pad positions in the
chassis frame), `body` (measured body vx / wz). Plus per-joint-class
angular-rate stats vs the resolved motor contract.

## THE SUPPORTED MECHANISM

**Combined forward+yaw undertracking is lost at the joint-response stage:
the yaw servo's usable angular speed, times its small tangential moment
arm (~0.071 m at the WALK_PLANT stance), caps per-leg tangential foot
speed at ~0.04 m/s — a budget vx and w*r_foot must SHARE, because this
leg geometry routes ALL tangential foot motion through the yaw servo
(hip/knee are purely radial/vertical in the IK).** The plan and IK carry
the command EXACTLY (stage `des` = command to 4 decimal places at every
cell — the 09-04 "TripodGait foot-target formula is the bottleneck"
hypothesis is REFUTED), and ground slip is negligible at the twist level
(`pads` twist ~= `body` twist everywhere, <=10%). Learned policies ride
the same physical ceiling as the scripted controller (act-stage yaw rate
p90 pinned at 0.55 rad/s in every cell for both).

Budget arithmetic (scripted baseline, current contract: fitted servo
profile ceiling 30.76 deg/s = 0.537 rad/s; slew clip 0.375 deg/tick @
100 Hz = 0.654 rad/s; bus.write_speed 400 counts/s = 0.614 rad/s cruise;
x_yaw arm 0.0711 m, r_foot 0.1711 m -> cap ~0.038-0.047 m/s):

| cell (vx, wz) | demanded max per-leg tangential | achieved body (vx, wz) | achieved tangential magnitude |
|---|---:|---:|---:|
| 0.08, 0     | 0.080 | +0.041, +0.003 | 0.041 |
| 0, +0.30    | 0.051 | +0.000, +0.232 | 0.040 |
| 0, -0.30    | 0.051 | -0.000, -0.230 | 0.039 |
| 0.08, +0.15 | 0.106 | +0.038, +0.064 | 0.040 |
| 0.08, -0.15 | 0.106 | +0.038, -0.065 | 0.040 |

Every cell lands on the same ~0.040 m/s executed-budget line regardless
of demand — including straight walking (the fleet-wide "speed-soft" 50%
progress ratio at vx=0.08 is this same ceiling, not a gait/reward issue).

## Stage localization (scripted, arc +0.15 @ vx 0.08, baseline)

command (0.080, 0.150) -> des (0.080, 0.150) -> prop (identical) ->
safe (0.061, 0.039) -> act/contact (0.036, 0.058) -> pads (0.037,
0.059) -> body (0.038, 0.064). Demanded yaw rates med 0.76 / p90 1.45
rad/s vs executed p90 0.55. Commanded swing lift 25 mm executes as only
3-5 mm (hip demand p90 2.2 rad/s), so 65-69% of plan-swing ticks stay
in contact (duty 0.55-0.59) — drag, but small at the twist level.

## Software lever matrix (scripted, all 5 cells each) — none recovers

| config | straight vx | in-place wz (+/-) | arc +0.15: (vx, wz) |
|---|---:|---:|---:|
| baseline | 0.041 | +0.232 / -0.230 | (0.038, +0.064) |
| slew 0.375->3.0 deg/tick only | 0.038 | +0.209 / -0.209 | (0.032, +0.052) WORSE |
| vel-ceiling 350->1500 counts/s only | 0.044 | +0.244 / -0.243 | (0.040, +0.066) |
| both raised (write_speed still 400) | 0.033 | +0.169 / -0.175 | (0.030, +0.043) WORSE |
| full fast profile (write_speed=1500 + ceiling=write_speed), slew pinned 0.375 | 0.047 | +0.253 / -0.252 | (0.043, +0.063) |
| full fast profile + slew 3.0 | 0.035 | +0.220 / -0.222 | (0.034, +0.048) WORSE |

The 09-04 "raising the slew clip barely moves combined wz" null is
reproduced and explained: under it the servo profile (min(write_speed
0.614, ceiling 0.537) rad/s) still binds. Conversely the full fast
profile under the pinned slew lands exactly on the slew-budget
prediction (0.654 rad/s x 0.0711 m = 0.0465: straight 0.047, in-place
0.253*0.171 = 0.043). Removing ALL software shaping lets the servo reach
p90 ~0.8 rad/s but tracking of the now-infeasible raw commands degrades
coordination and the body twist gets WORSE — the slew clip is currently
a near-optimal trajectory shaper for this actuator, not the villain.
There is NO software configuration that recovers the (0.08, +/-0.15)
arc cells: they demand ~2.3x the physical budget.

## Within-envelope check (baseline contract, derated cells)

Partial confirmation with an honest second-order residual: scripted at
(0.03, +/-0.08) tracks wz 88%/76% and vx 60%/57% (vs 43% wz at the 0.15
arcs); (0.02, +/-0.10) only ~50% both axes. cont8m derated cells:
43-91%, direction-asymmetric. So inside the budget the CEILING no longer
dominates, but a periodic-small-stroke execution loss (servo deadband
0.35-0.5 deg, ~26-30 ms latency, trapezoid accel, stroke reversals every
0.375 s, plus swing-scuff drag from the lift collapse) still costs
~10-50%. Perfect in-envelope tracking is NOT established.

## Steering consequences (todaypolicy / turn qualification)

1. STOP reward/curriculum/seed spend on turn authority at the current
   arc cells: (0.08, +/-0.15) is kinematically infeasible for ANY
   controller under EVERY tested software configuration. This is
   consistent with (and explains) all 8+ refuted turn-authority reward
   and gait-reshaping candidates since 09-03.
2. Demo guidance: command inside the measured envelope (max per-leg
   tangential demand |vx| + 0.171*|wz| <~ 0.04 m/s), e.g. turn-in-place
   <= 0.23 rad/s, or vx 0.03 + wz 0.08 arcs (scripted tracks 76-88% wz
   there). Expect vx ~50-60% everywhere at the current contract.
3. Physical recovery levers are operator/contract decisions, not runs:
   a larger tangential arm (more extended stance — reach term
   `0.0125 + 0.09cos(hip) + 0.15cos(knee)`; knee 100->80 deg nearly
   doubles the arm) is the strongest untested lever; the
   stance_radius_scale +-5% sweep (closed 09-07) could not move it
   materially. Servo speed alone (fast profile) was measured
   insufficient at the pinned slew (+~15%), and raising the slew
   contract degrades execution.

## Limits

- Single seed (0), phase offset 0 only (the corrected audit showed
  phase-start insensitivity), 15 s episodes, zero falls everywhere.
- FK stage twists use the hexapod_core leg geometry (the plan's own
  convention); validity is cross-checked by `pads` (true mesh pad
  positions) agreeing with `fk_act` at every cell.
- The fast-profile arms are DIAGNOSTIC doses; the qualification safety
  contract (0.375 deg/tick @ 100 Hz, operator order fb_20260824T174619)
  and all cfg defaults are untouched.
- cont8m/cigate8m were probed at baseline only; raised-profile evals of
  policies TRAINED under the old contract would be out-of-distribution
  and were deliberately skipped.
