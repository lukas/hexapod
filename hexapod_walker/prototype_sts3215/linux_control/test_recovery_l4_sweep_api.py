"""Off-robot mechanics for the bounded L4-only outward sweep."""
from __future__ import annotations

import pytest

from feetech_bus import COUNTS_PER_DEG, JOINT_SIGN, STS_CENTRE_COUNT
from test_recovery_effort_api import active_fault
from test_recovery_nudge_api import expected_target, rig  # noqa: F401


HOLDS = [10, 11, 13, 16, 17]
JOINTS = (10, 11, 13, 14, 16, 17)
IDS = tuple(j + 2 for j in JOINTS)
REQUEST = {"effort_profile": "l4_sweep50", "deltas_deg": {"14": -30},
           "hold_joints": HOLDS}


def valid_raw_start(bus):
    count = round(STS_CENTRE_COUNT + 40 * COUNTS_PER_DEG * JOINT_SIGN[14])
    bus.position[16] = count
    return count


@pytest.mark.parametrize("delta", [-5, -30])
def test_l4_sweep_bounds_preload_all_supports_and_move_only_knee(rig, delta):
    api, bus, _clock = rig
    home = valid_raw_start(bus)
    result = api.recovery_nudge({**REQUEST, "deltas_deg": {"14": delta}})
    assert result["ok"] and result["torque_off"]
    assert result["effort_profile"] == "l4_sweep50"
    assert result["active_time_limit_s"] == 6
    assert bus.groups == [{16: (home + expected_target(14, delta) - 2000, 90, 4)}]
    first_enable = next(i for i, event in enumerate(bus.events)
                        if event[0] == "torque" and event[2])
    before = bus.events[:first_enable]
    for joint in JOINTS:
        row = result["joints"][str(joint)]
        knee = joint == 14
        cap = 500 if knee else 200
        assert row["applied_torque_limit"] == cap
        assert row["current_soft_limit_a"] == (.75 if knee else .25)
        assert row["load_soft_limit_pct"] == (53 if knee else 23)
        preload = ("position", joint + 2, home if knee else 2000, 90, 4)
        assert preload in before
        assert ("read", joint + 2, 42) in before[before.index(preload) + 1:]
        assert ("limit", joint + 2, cap) in before
    assert {event[1] for event in bus.events if event[0] == "torque" and event[2]} == set(IDS)
    assert all(bus.goal[j + 2] == 2000 for j in HOLDS)
    last_disable = max(i for i, event in enumerate(bus.events)
                       if event[0] == "torque" and not event[2])
    assert not [event for event in bus.events[:last_disable]
                if event[0] == "limit" and event[2] == 700]
    assert all(bus.limit[sid] == 700 for sid in IDS)
    assert not bus.on


@pytest.mark.parametrize("payload", [
    {**REQUEST, "deltas_deg": {"14": 5}},
    {**REQUEST, "deltas_deg": {"14": -4.9}},
    {**REQUEST, "deltas_deg": {"14": -30.1}},
    {**REQUEST, "deltas_deg": {"2": -5}},
    {**REQUEST, "deltas_deg": {"2": -5, "14": -5}},
    {**REQUEST, "hold_joints": [10, 11, 13, 16]},
    {**REQUEST, "hold_joints": [1, 11, 13, 16, 17]},
    {"effort_profile": "l4_sweep50", "hold_joints": HOLDS,
     "phases": [{"deltas_deg": {"14": -10}}, {"deltas_deg": {"14": -5}}]},
])
def test_l4_sweep_rejects_other_shapes_before_writes(rig, payload):
    api, bus, _clock = rig
    valid_raw_start(bus)
    with pytest.raises(ValueError):
        api.recovery_nudge(payload)
    assert not [event for event in bus.events if event[0] != "read"]


def test_l4_sweep_does_not_bypass_raw_limits_or_other_motor_torque_state(rig):
    api, bus, _clock = rig
    # Default raw knee -4.2 would cross its -20-degree physical limit.
    with pytest.raises(ValueError):
        api.recovery_nudge(REQUEST)
    assert not [event for event in bus.events if event[0] != "read"]
    valid_raw_start(bus)
    bus.on.add(2)
    with pytest.raises(ValueError):
        api.recovery_nudge(REQUEST)
    assert not [event for event in bus.events if event[0] != "read"]


def test_l4_sweep_stall_ends_at_six_seconds_and_restores_saved_lower_limit(rig):
    api, bus, clock = rig
    home = valid_raw_start(bus)
    bus.limit[16] = 350
    bus.stalled.add(16)
    start = clock.now
    result = api.recovery_nudge(REQUEST)
    assert not result["ok"] and result["torque_off"]
    assert 6 <= clock.now - start < 6.1
    assert result["joints"]["14"]["applied_torque_limit"] == 350
    assert bus.limit[16] == 350
    assert bus.groups == [{16: (home + expected_target(14, -30) - 2000, 90, 4)}]
    assert not bus.on


@pytest.mark.parametrize("sid,address,value,votes", [
    (16, 69, 116, 3), (16, 60, 530, 3), (16, 69, 154, 1),
    (12, 69, 39, 3), (12, 60, 230, 3),
])
def test_l4_sweep_keeps_knee_and_support_fault_guards(rig, sid, address, value, votes):
    api, bus, clock = rig
    valid_raw_start(bus)
    samples = active_fault(bus, sid, address, [value] * 20)
    start = clock.now
    result = api.recovery_nudge(REQUEST)
    assert not result["ok"] and result["torque_off"]
    assert len(samples) == votes
    assert clock.now - start < 6
    assert not bus.on


def test_l4_sweep_abort_before_target_disables_all_participants(rig):
    api, bus, _clock = rig
    valid_raw_start(bus)
    bus.after_enable = lambda sid: api.require_setup_for("/cmd", "X")
    result = api.recovery_nudge(REQUEST)
    assert not result["ok"] and result["torque_off"]
    assert not bus.groups
    assert {event[1] for event in bus.events if event[0] == "torque" and not event[2]} == set(IDS)
    assert not bus.on


def test_l4_sweep_unverified_preload_never_enables(rig):
    api, bus, _clock = rig
    valid_raw_start(bus)
    bus.faults[(16, 42)] = lambda b: 1234
    result = api.recovery_nudge(REQUEST)
    assert not result["ok"] and result["torque_off"]
    assert not [event for event in bus.events if event[0] == "torque" and event[2]]
    assert not bus.groups


def test_l4_sweep_missing_feedback_stops_after_three_attempts_and_cleans_up(rig):
    api, bus, _clock = rig
    valid_raw_start(bus)
    attempts = active_fault(bus, 16, 69, [(0, -1, 0)] * 10)
    result = api.recovery_nudge(REQUEST)
    assert not result["ok"] and result["torque_off"]
    assert len(attempts) == 3
    assert all(bus.limit[sid] == 700 for sid in IDS)
    assert not bus.on


def test_l4_sweep_cleanup_failure_attempts_every_motor_without_high_limit_restore(rig):
    api, bus, _clock = rig
    valid_raw_start(bus)
    bus.disable_fail.add(16)
    result = api.recovery_nudge(REQUEST)
    assert not result["ok"] and not result["torque_off"]
    assert {event[1] for event in bus.events if event[0] == "torque" and not event[2]} == set(IDS)
    assert all(bus.limit[j + 2] == (500 if j == 14 else 200) for j in JOINTS)
    assert bus.on == {16}
