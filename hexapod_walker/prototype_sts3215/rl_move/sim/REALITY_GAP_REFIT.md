# Sim reality-gap refit (2026-09-21)

Refit of the MuJoCo twin's actuator + current model to match a real hexapod2
walk, so the sim predicts real motor behavior better. Validated by replaying a
real 6-min walk through the twin AND by a closed-loop rollout of the actual
deployed policy.

## What changed

**Per-axis actuator** (`sim_model.json`; old fit preserved verbatim as
`sim_model_air_20260807.json`, selectable via `bus.servo_params=air` for A/B):
- `vel_max_deg_s` 30.76 → **35.16** (all axes). It was clamped to a stale
  350-count value; the robot ran 400 counts/s (=35.2°/s), and the real joints
  were literally moving faster than the sim allowed. (`speed_counts_s` 350→400
  too, but that field is metadata only — `vel_max_deg_s` is the dynamics lever.)
- yaw `latency_ms` 29.7 → **130**, hip 25.6 → **125**. The sim tracked commands
  almost instantly; the real effective command→joint lag is ~256-273 ms. The
  latency param (~125 ms) plus the actuator's slew dynamics reproduce that
  ~250 ms effective lag. NOTE: it's not a fixed 250 ms dead-time — most of the
  lag is the servo slewing to a moving target at walking frequency.
- knee `kp` 43.8 → **250**. The sim knee under-tracked (too soft); loaded kp 915
  rings unstably in this dynamic replay, so 250 + short knee latency.

**Load/stall current** (`sim_env.py` `_read_state`): reported `servo_current` =
idle `0.19`/18 + `k`(0.02282)·|τ·q̇| + **`k_stall`(0.042)·relu(|τ|−`thr`1.2)**.
The old power model under-predicted real mechanical load ~4x; the winding/stall
term closes most of it. The over-current TRIP still rides the SEPARATE torque
proxy (`over_current_signal`) — a stalled joint still trips exactly as before.

## Why / evidence (before → after, vs real)
Chunked replay of the real combo walk (run 20260920-205326-b616) + closed-loop
rollout of the deployed policy in the twin:
- Joint-tracking RMSE (sim_q − real_q), sum over axes: 9.82 → **7.93 (−19%)**.
- Command→joint lag: hip/yaw now essentially match real (246/267 vs 256/273 ms).
- Body rock (gyro-RMS): 8.5 → 11.8 open-loop / 9.8 closed-loop (real 23.3) —
  ~a quarter of the gap closed.
- Current: gap 2.6x → **1.24x** under.
- Closed-loop: the refit beats the old sim on EVERY axis, and the policy walks
  stably (12/12 gait_valid) in it.
- Key finding: the gap is ACTUATOR dynamics + contact — NOT joint compliance /
  backlash / contact stiffness (all three probed, no effect).

## Caveats / known gaps (READ before relying on it)
- **One-tape fit** (a single combo walk). Needs proper multi-protocol sysid
  (`sysid/` package) + fresh hardware to confirm broadly — blocked while the
  L4 knee is down.
- **BLOCKING for one reward:** the higher latency raises the honest-walk
  torque-proxy p50 ~1.2 → 2.2 A, so the opt-in `reward.k_walk_move_current`
  2.2 A threshold now prices *honest* walking. RE-CALIBRATE that threshold
  before using that reward under the refit. (Default training does not use it.)
- **Body rock only ~half closed.** Bounded by the open-loop replay (can't
  reproduce the live policy reacting to its own rock) AND a physical residual:
  yaw-slip / veer (~10°/leg) the rigid contact doesn't model. Closed-loop
  confirmed the residual is physical, not a replay artifact.
- **Mass uncalibrated.** Twin assumes 3.49 kg total; the real robot is ~3 kg
  WITHOUT the battery (+~0.5 kg battery ≈ 3.5). If a walk was battery-out, the
  twin is ~0.5 kg too heavy (more inertia → less rock). Not fixed here — next
  lever. CoM is centered (robot is symmetric), so it's a total-mass/height item.
- **Forward speed** still over-progresses ~1.6x (real slip/veer; the friction
  fix that helps speed breaks the current match, so not adopted).

## A/B
- Refit is the default. `bus.servo_params=air` restores the pre-refit actuator
  (`sim_model_air_20260807.json`). The stall-current term is config-gated.

## Next levers
1. Set mass to 3 kg (no-battery) and test whether it closes more rock.
2. Yaw-slip / asymmetric-contact model (the physical rock+veer residual).
3. Proper multi-protocol sysid on fresh hardware once the knee is fixed.

Harness + traces: `/tmp/simgap/` (open-loop), `/tmp/closedloop/` (closed-loop).
Full session context: memory `hexapod2-imu-calibration-2026-09-19`.

## Per-leg footfall view of the same gap (2026-09-21, `sysid.gait_metrics --footfall`)

Same policy (armcombo), same real tape family (hexapod2 endurance runs 16:43 /
16:55 / 17:06 on 2026-09-20, three sessions agree within ~1 mm), scored per leg
by foot kinematics: `rl_move.body_ik.fk_all_feet` -> ground plane through the
lowest feet -> clearance; contact = clearance < 5 mm (91 % tick agreement with
the MuJoCo touch sensors, 84 % at 10 mm). Sim rows: 10 s rollouts, fwd/back +
3 DR seeds (A/B rows 3 runs), written in the robot's CSV format so sim and
hardware go through identical code (`sysid.rollout_policy_csv` +
`sysid.gait_metrics --footfall`). The table was produced by the pre-merge
harness (`~/.hexapod/gait_metrics/*.json`); the committed tool, which adds the
100 mm chassis radius to the plane fit, reproduces it within ~0.02 duty,
2 mm lift and 4 mm/s. "weak" = legs 0/2/4, "strong" =
legs 1/3/5 (index + mount azimuth; L/R depends on which side +y is).

| variant | chassis mm/s | duty weak / strong | lift weak / strong mm | swing weak / strong s | cmd->q lag | slew-cap sat |
|---|---|---|---|---|---|---|
| sim, pre-refit params (`air`) | 49 | 0.63-0.65 / 0.57-0.62 | 17-19 / 19-23 | 0.50-0.54 / 0.55-0.60 | 200 ms | 68 % |
| sim, refit (default) | 52 | 0.64-0.69 / 0.52-0.60 | 17-19 / 22-26 | 0.42-0.51 / 0.58-0.70 | 270 ms | 70 % |
| **real hexapod2** | 27 | 0.67-0.75 / 0.42-0.53 | 15-18 / 29-33 | 0.40-0.53 / 0.71-0.86 | 150-300 ms | 56 % |
| sim air + bus profile 800/60 | 57 | 0.58-0.66 / 0.55-0.61 | 15 / 25-28 | 0.48-0.59 / 0.57-0.62 | 80 ms | 66 % |
| sim air + 800/60 + slew 1.5 | 57 | 0.67-0.68 / 0.59-0.60 | 19-21 / 26-31 | 0.25-0.31 / 0.52-0.57 | 113 ms | 34 % |
| sim air + slew 1.5 only | 44 | 0.63-0.64 / 0.57-0.60 | 17-18 / 20-22 | 0.51-0.53 / 0.57-0.63 | 333 ms | 20 % |

What it adds to the joint-level gap above:
- **The real gait is a lopsided tripod.** Legs 1/3/5 take a 0.7 s, 30 mm step;
  legs 0/2/4 hop 16 mm for 0.3 s and are planted ~70 % of the time. The
  commanded joints show the same split, so it is the policy's closed-loop
  output on the real state, not servo tracking. This is what "some legs drag"
  looks like in numbers; side2 video confirms it frame by frame
  (`~/.hexapod/gait_metrics/20260920-170655-5261_side2_cycle_40s.jpg`).
- **Mild bias as trained, amplified ~4x on hardware.** Pre-refit sim already
  favours 1/3/5 (lift gap 3 mm, duty gap 0.05); the refit gets to 5 mm / 0.12;
  hardware is 14 mm / 0.2+. So the refit closes part of this too, but a policy
  retrained on it alone probably will not remove the split.
- **Short stride and slew-cap saturation are learned**: even pre-refit the
  policy commands only ~57 mm/s of stance kinematics for a 100 mm/s command and
  sits at the 0.75 deg/tick cap on ~68 % of ticks; on hardware it backs off
  further to ~40 mm/s commanded. The 1.6x speed over-progression noted above is
  then, at a 10 mm contact threshold: 57 -> 43 -> 49 in sim (no slip) vs
  40 -> 31 -> 27 real (cmd-FK -> q-FK -> chassis; at 5 mm read 60/46 and 44/35).
- **Real servos reach full command amplitude** (q/cmd p5-p95 range ratio ~1.0)
  while both sim parameter sets attenuate to 0.76-0.86, and lag 150-300 ms. A
  faster sim profile (800/60) reproduces the real lift split (15 vs 25-28 mm)
  but not the shortened weak-tripod swing: the amplitude mismatch is a lever,
  not the whole story. Candidate next refit item alongside mass and yaw-slip.
- **Deployment knobs do not fix the gait**: 800/60 buys ~8 mm/s with the same
  split; lifting the slew clamp alone is slower (servo cannot follow, lag 333
  ms). Servo profile 400 counts/s = 35.2 deg/s and acc 20 = 176 deg/s^2
  (0.2 s to profile speed) account for ~60 % of the lag (200 -> 80 ms in sim).

Hardware target for a smoother policy, measurable with the same command on the
robot's `robot_telemetry/rl_drive_*.csv`: legs 0/2/4 lift >= 25 mm and duty
<= 0.6 at 5 mm, all-six-down <= 10 % of ticks, stance-consensus speed within
15 % of the tag tracker.
