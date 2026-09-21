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
