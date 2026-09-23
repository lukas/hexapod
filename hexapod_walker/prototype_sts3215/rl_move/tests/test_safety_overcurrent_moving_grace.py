"""RAIL_MOVING vs CORROBORATED_STALL over-current grace
(safety.over_current_moving_grace_s) — unit semantics.

2026-09-23, standwalk track: `audit_over_current.py`'s own classifier
distinguishes a hot joint that is genuinely moving/making progress
(RAIL_MOVING — a bridge-start rise pressing hard against gravity) from
one that is stalled/static under load (CORROBORATED_STALL — the real
burn/jam risk the over-current trip exists to catch). Three recent
standwalk FAIL verdicts (dr>=0.6 GRU/MLP rise lineages) were reclassified
RAIL_MOVING, not CORROBORATED_STALL, after a rollout-trace audit. This
adds an OPT-IN grace budget (ticks) that only ever extends the trip for
a joint that is itself still moving faster than a small floor; a static
hot joint trips at EXACTLY the pre-existing bound, unchanged.

Default off (over_current_moving_grace_s=0.0) must be bit-exact with the
pre-existing trip. Building this is a training/sim-side research lever;
enabling a nonzero grace for a real hardware deploy is a separate,
later Robot Lab safety decision, not implied by this test file.

Run: uv run python -m pytest rl_move/tests/test_safety_overcurrent_moving_grace.py -q
"""
from __future__ import annotations

import numpy as np

from rl_move.robot_state import RobotState
from rl_move.safety import N_JOINTS, SafetyLayer

HOT_J = 5


def _cfg(**safety_extra) -> dict:
    s = {"max_current_a": 2.5, "over_current_trip_s": 0.1}
    s.update(safety_extra)
    return {"safety": s, "control": {"hz": 25}}


def _state(current: float, qvel_hot: float) -> RobotState:
    cur = np.zeros(N_JOINTS)
    cur[HOT_J] = current
    qvel = np.zeros(N_JOINTS)
    qvel[HOT_J] = qvel_hot
    return RobotState(
        timestamp=0.0,
        joint_position=np.zeros(N_JOINTS),
        joint_velocity=qvel,
        imu_roll=0.0, imu_pitch=0.0, imu_yaw=0.0,
        imu_gyro=np.zeros(3), imu_accel=np.zeros(3),
        commanded_position=np.zeros(N_JOINTS),
        servo_current=cur,
    )


def _run(safety: SafetyLayer, n: int, current: float, qvel_hot: float):
    """Feed n identical health frames; return the first non-None status."""
    for _ in range(n):
        status = safety.check_servo_health(_state(current, qvel_hot))
        if status is not None:
            return status
    return None


def test_default_off_is_bit_exact_moving_or_not():
    """grace_s=0 (default): a MOVING hot joint still trips at exactly the
    base tick bound — the pre-existing behavior is unaffected either way."""
    cfg = _cfg()
    safety = SafetyLayer(cfg)
    assert safety._over_current_moving_grace_ticks == 0
    n = safety._over_current_trip_ticks
    # one tick short of the bound: no trip yet
    assert _run(safety, n - 1, 2.6, qvel_hot=1.0) is None
    status = safety.check_servo_health(_state(2.6, qvel_hot=1.0))
    assert status is not None and status.reason == "over_current"


def test_static_hot_joint_trips_at_the_unchanged_bound_even_with_grace_armed():
    """CORROBORATED_STALL: qvel below the floor never earns grace — a
    stalled joint trips at exactly the same tick as before, regardless of
    how large the grace budget is."""
    cfg = _cfg(over_current_moving_grace_s=1.0,
               over_current_moving_qvel_floor_rad_s=0.05)
    safety = SafetyLayer(cfg)
    n = safety._over_current_trip_ticks
    assert _run(safety, n - 1, 2.6, qvel_hot=0.0) is None
    status = safety.check_servo_health(_state(2.6, qvel_hot=0.0))
    assert status is not None and status.reason == "over_current"


def test_moving_hot_joint_earns_extra_ticks_then_still_trips_if_sustained():
    """RAIL_MOVING: a joint moving above the floor earns exactly
    grace_ticks extra ticks past the base bound before it finally trips,
    if the over-current condition is sustained that long too."""
    hz = 25.0
    cfg = _cfg(over_current_moving_grace_s=0.2,  # 5 ticks @ 25 Hz
               over_current_moving_qvel_floor_rad_s=0.05)
    safety = SafetyLayer(cfg)
    assert safety._hz == hz
    base = safety._over_current_trip_ticks
    grace = safety._over_current_moving_grace_ticks
    assert grace == 5
    # Reach the base bound with no trip (grace consumed silently).
    assert _run(safety, base, 2.6, qvel_hot=1.0) is None
    # Exactly `grace` further over-threshold moving ticks still don't trip.
    assert _run(safety, grace - 1, 2.6, qvel_hot=1.0) is None
    status = safety.check_servo_health(_state(2.6, qvel_hot=1.0))
    assert status is not None and status.reason == "over_current"


def test_moving_joint_that_stops_moving_trips_immediately_not_after_grace():
    """A joint that STOPS moving before its grace budget is spent (a
    stall setting in mid-press) trips on its very next over-threshold
    tick — unused grace never protects a real stall."""
    cfg = _cfg(over_current_moving_grace_s=1.0,  # 25 ticks @ 25 Hz
               over_current_moving_qvel_floor_rad_s=0.05)
    safety = SafetyLayer(cfg)
    base = safety._over_current_trip_ticks
    # Reaching the base bound itself already spends grace tick #1 (the
    # tick where `_over_current_ticks` first reaches `base` is the first
    # one the grace logic evaluates).
    assert _run(safety, base, 2.6, qvel_hot=1.0) is None
    assert safety._over_current_moving_grace_used == 1
    # A couple more moving grace ticks spent...
    assert _run(safety, 1, 2.6, qvel_hot=1.0) is None
    assert safety._over_current_moving_grace_used == 2
    # ...then the joint stops moving: trips on the very next tick, well
    # before the 25-tick grace budget would have been exhausted.
    status = safety.check_servo_health(_state(2.6, qvel_hot=0.0))
    assert status is not None and status.reason == "over_current"


def test_dropping_below_threshold_resets_both_counters():
    cfg = _cfg(over_current_moving_grace_s=1.0)
    safety = SafetyLayer(cfg)
    base = safety._over_current_trip_ticks
    assert _run(safety, base, 2.6, qvel_hot=1.0) is None
    assert _run(safety, 2, 2.6, qvel_hot=1.0) is None
    assert safety._over_current_moving_grace_used == 3
    # A single safe (below-threshold) sample resets both accumulators.
    status = safety.check_servo_health(_state(0.1, qvel_hot=1.0))
    assert status is None
    assert safety._over_current_ticks == 0
    assert safety._over_current_moving_grace_used == 0
    # ...so the full base+grace budget is available again from here.
    grace = safety._over_current_moving_grace_ticks
    assert _run(safety, base + grace - 1, 2.6, qvel_hot=1.0) is None
    status = safety.check_servo_health(_state(2.6, qvel_hot=1.0))
    assert status is not None and status.reason == "over_current"


def test_set_health_sample_hz_rescales_grace_ticks_too():
    cfg = _cfg(over_current_moving_grace_s=0.4)
    safety = SafetyLayer(cfg)
    assert safety._over_current_moving_grace_ticks == round(0.4 * 25)
    safety.set_health_sample_hz(10.0)
    assert safety._over_current_moving_grace_ticks == round(0.4 * 10)


def test_set_nominal_resets_grace_used():
    cfg = _cfg(over_current_moving_grace_s=1.0)
    safety = SafetyLayer(cfg)
    base = safety._over_current_trip_ticks
    assert _run(safety, base, 2.6, qvel_hot=1.0) is None
    assert _run(safety, 2, 2.6, qvel_hot=1.0) is None
    assert safety._over_current_moving_grace_used == 3
    safety.set_nominal(np.zeros(N_JOINTS))
    assert safety._over_current_moving_grace_used == 0
    assert safety._over_current_ticks == 0
