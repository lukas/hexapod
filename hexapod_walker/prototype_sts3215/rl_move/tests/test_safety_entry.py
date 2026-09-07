"""Entry slew ramp (safety.entry_slew_ramp_s) — unit semantics.

The 08-11 bench tapes show the walk policy saturating the full
1.5 deg/tick slew on all 18 joints from tick 0 at zero command (the
takeoff posture snap). The entry ramp throttles the per-tick rate
limit right after set_nominal(), ramping linearly back up to
max_delta_q_deg. Default OFF must be bit-exact.

Run: uv run python -m pytest rl_move/tests/test_safety_entry.py -q
"""
from __future__ import annotations

import math

import numpy as np

from rl_move.robot_state import RobotState
from rl_move.safety import N_JOINTS, SafetyLayer

DEG = math.pi / 180.0


def _state(q: np.ndarray) -> RobotState:
    return RobotState(
        timestamp=0.0,
        joint_position=q.copy(),
        joint_velocity=np.zeros(N_JOINTS),
        imu_roll=0.0, imu_pitch=0.0, imu_yaw=0.0,
        imu_gyro=np.zeros(3), imu_accel=np.zeros(3),
        commanded_position=q.copy(),
    )


def _cfg(**safety_extra) -> dict:
    s = {"max_delta_q_deg": 1.5, "max_roll_deg": 25,
         "max_pitch_deg": 25}
    s.update(safety_extra)
    return {"safety": s, "control": {"hz": 25}}


def _run_deltas(layer: SafetyLayer, n: int) -> list[float]:
    """Ask for a huge jump every tick; return achieved per-tick deg."""
    q0 = np.zeros(N_JOINTS)
    layer.set_nominal(q0)
    target = np.full(N_JOINTS, 45.0 * DEG)
    out = []
    prev = q0.copy()
    for _ in range(n):
        q_safe, status = layer.filter(target, _state(prev))
        assert status.ok
        out.append(float((q_safe - prev)[0]) / DEG)
        prev = q_safe
    return out


def test_default_off_bit_exact():
    """entry_slew_ramp_s absent -> full max_dq from tick 0."""
    layer = SafetyLayer(_cfg())
    deltas = _run_deltas(layer, 5)
    assert all(abs(d - 1.5) < 1e-9 for d in deltas)


def test_ramp_throttles_then_recovers():
    layer = SafetyLayer(_cfg(entry_slew_ramp_s=1.0,
                             entry_slew_start_deg=0.25))
    deltas = _run_deltas(layer, 30)
    # tick 0: exactly the start rate
    assert abs(deltas[0] - 0.25) < 1e-9
    # monotone non-decreasing through the ramp
    assert all(b >= a - 1e-12 for a, b in zip(deltas[:25], deltas[1:26]))
    # tick 12 (~mid-ramp): strictly between start and max
    assert 0.25 + 0.1 < deltas[12] < 1.5 - 0.1
    # after ramp_s (25 ticks at 25 Hz): full rate again
    assert all(abs(d - 1.5) < 1e-9 for d in deltas[25:])


def test_set_nominal_restarts_ramp():
    layer = SafetyLayer(_cfg(entry_slew_ramp_s=1.0,
                             entry_slew_start_deg=0.25))
    _run_deltas(layer, 30)          # exhaust the ramp
    deltas2 = _run_deltas(layer, 3)  # set_nominal inside restarts it
    assert abs(deltas2[0] - 0.25) < 1e-9


def test_start_rate_never_exceeds_max():
    """Misconfigured start > max clamps to max (min())."""
    layer = SafetyLayer(_cfg(entry_slew_ramp_s=1.0,
                             entry_slew_start_deg=5.0))
    deltas = _run_deltas(layer, 3)
    assert all(d <= 1.5 + 1e-9 for d in deltas)


def test_set_nominal_rereads_cfg_schedule():
    """The in-run scheduler mutates cfg (sched.key=safety.entry_slew_
    start_deg); set_nominal must pick the new value up per episode —
    the entry-slew CURRICULUM enabler (RISE_WALK_NEXT_48H P2)."""
    cfg = _cfg(entry_slew_ramp_s=1.0, entry_slew_start_deg=0.25)
    layer = SafetyLayer(cfg)
    deltas = _run_deltas(layer, 3)
    assert abs(deltas[0] - 0.25) < 1e-9
    # scheduler anneals the start rate toward full authority
    cfg["safety"]["entry_slew_start_deg"] = 1.0
    deltas2 = _run_deltas(layer, 3)   # set_nominal inside re-reads
    assert abs(deltas2[0] - 1.0) < 1e-9
    # ...and can disable the ramp entirely (stage 4: normal authority)
    cfg["safety"]["entry_slew_ramp_s"] = 0.0
    deltas3 = _run_deltas(layer, 3)
    assert all(abs(d - 1.5) < 1e-9 for d in deltas3)


def test_health_sample_rate_sets_physical_current_dwell():
    layer = SafetyLayer({
        "control": {"hz": 100},
        "safety": {"over_current_trip_s": 2.0},
    })

    ticks = layer.set_health_sample_hz(10.0)

    assert ticks == 20
    assert layer._over_current_trip_ticks == 20  # noqa: SLF001


def test_legacy_safe_current_clears_prior_streak():
    q = np.zeros(N_JOINTS)
    layer = SafetyLayer(_cfg(over_current_trip_s=0.12,
                             max_current_a=2.5))
    layer.set_nominal(q)

    high = _state(q)
    high.servo_current = np.full(N_JOINTS, 4.0)
    safe = _state(q)
    safe.servo_current = np.full(N_JOINTS, 0.4)

    _q, status = layer.filter(q, high)
    assert not status.terminate
    assert layer._over_current_ticks == 1  # noqa: SLF001
    _q, status = layer.filter(q, safe)
    assert not status.terminate
    assert layer._over_current_ticks == 0  # noqa: SLF001
    _q, status = layer.filter(q, high)
    assert not status.terminate
    assert layer._over_current_ticks == 1  # noqa: SLF001


def test_explicit_partial_safe_current_does_not_clear_prior_streak():
    q = np.zeros(N_JOINTS)
    layer = SafetyLayer(_cfg(over_current_trip_s=1.0,
                             max_current_a=2.5))
    layer.set_nominal(q)

    def state(current: float, seq: int, ids: list[int]):
        sample = _state(q)
        sample.servo_current = np.full(N_JOINTS, current)
        sample.timing = {
            "feedback_sample_seq": seq,
            "feedback_complete": len(ids) == N_JOINTS,
            "feedback_valid_ids": ids,
        }
        return sample

    all_ids = list(range(N_JOINTS))
    partial_ids = list(range(N_JOINTS - 1))
    layer.filter(q, state(4.0, 1, all_ids))
    assert layer._over_current_ticks == 1  # noqa: SLF001
    layer.filter(q, state(0.4, 2, partial_ids))
    assert layer._over_current_ticks == 1  # noqa: SLF001
    layer.filter(q, state(0.4, 3, all_ids))
    assert layer._over_current_ticks == 0  # noqa: SLF001


def test_boolean_only_explicit_partial_does_not_clear_prior_streak():
    q = np.zeros(N_JOINTS)
    layer = SafetyLayer(_cfg(over_current_trip_s=1.0,
                             max_current_a=2.5))
    layer.set_nominal(q)

    high = _state(q)
    high.servo_current = np.full(N_JOINTS, 4.0)
    layer.filter(q, high)
    assert layer._over_current_ticks == 1  # noqa: SLF001

    partial = _state(q)
    partial.servo_current = np.full(N_JOINTS, 0.4)
    partial.timing = {
        "feedback_sample_fresh": True,
        "feedback_complete": False,
    }
    layer.filter(q, partial)

    assert layer._over_current_ticks == 1  # noqa: SLF001
    assert layer._incomplete_feedback_ticks == 1  # noqa: SLF001
