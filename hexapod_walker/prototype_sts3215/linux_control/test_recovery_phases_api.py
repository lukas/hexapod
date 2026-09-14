"""Off-robot guards for a bounded two-phase raw recovery sequence."""
from __future__ import annotations

import math

import pytest

from feetech_bus import COUNTS_PER_DEG, JOINT_SIGN, STS_CENTRE_COUNT
from test_recovery_nudge_api import REQUEST, expected_target, rig  # noqa: F401


PHASES = {"phases": [{"deltas_deg": {"4": 3, "5": 3}},
                      {"deltas_deg": {"2": -5}}], "hold_joints": [1, 16, 17]}


def group_indices(bus):
    return [i for i, event in enumerate(bus.events) if event[0] == "group"]


def test_two_phases_enable_union_once_and_preserve_prior_goals(rig):
    api, bus, _clock = rig
    result = api.recovery_nudge(PHASES)
    assert result["ok"] and result["torque_off"]
    assert result["joint_frame"] == "servo_relative"
    assert set(result["joints"]) == {"1", "2", "4", "5", "16", "17"}
    assert bus.groups == [
        {6: (expected_target(4, 3), 90, 4), 7: (expected_target(5, 3), 90, 4)},
        {4: (expected_target(2, -5), 90, 4)}]
    ids = (3, 4, 6, 7, 18, 19)
    assert [e for e in bus.events if e[0] == "torque" and e[2]] == [
        ("torque", sid, True) for sid in ids]
    assert [e for e in bus.events if e[0] == "torque" and not e[2]] == [
        ("torque", sid, False) for sid in ids]
    first, second = group_indices(bus)
    cleanup = next(i for i, event in enumerate(bus.events)
                   if event[0] == "torque" and not event[2])
    assert not [e for e in bus.events[first:second] if e[0] in ("torque", "position")]
    for sid in ids:
        assert bus.events[first + 1:second].count(("read", sid, 56)) >= 3
        assert bus.events[second + 1:cleanup].count(("read", sid, 56)) >= 3
    assert result["phase_index"] == 2
    assert [phase["settled"] for phase in result["phases"]] == [True, True]
    assert bus.goal[6] == expected_target(4, 3)
    assert bus.goal[7] == expected_target(5, 3)
    assert not bus.on


def test_previous_phase_movers_hold_their_commanded_goal_not_initial_pose(rig):
    api, bus, _clock = rig
    payload = {"phases": [{"deltas_deg": {"4": 5, "5": 5}},
                           {"deltas_deg": {"2": -5}}], "hold_joints": [1, 16, 17]}
    result = api.recovery_nudge(payload)
    assert result["ok"] and result["torque_off"]
    assert len(bus.groups) == 2
    assert bus.goal[6] == expected_target(4, 5)
    assert bus.goal[7] == expected_target(5, 5)


def test_repeated_joint_goal_is_cumulative_from_initial_snapshot_not_actual_sag(rig):
    api, bus, _clock = rig
    original = bus.txPacket

    def write():
        result = original()
        if len(bus.groups) == 1:
            bus.position[4] -= 10  # Stable <1 degree tracking residual.
        return result

    bus.txPacket = write
    result = api.recovery_nudge({"phases": [{"deltas_deg": {"2": 3}},
                                            {"deltas_deg": {"2": 3}}], "hold_joints": [4, 5]})
    offset = math.trunc(3 * COUNTS_PER_DEG * JOINT_SIGN[2])
    assert result["ok"] and result["torque_off"]
    assert bus.groups == [{4: (2000 + offset, 90, 4)},
                           {4: (2000 + 2 * offset, 90, 4)}]
    assert result["phases"][1]["start_counts"][2] == 2000 + offset - 10
    assert result["phases"][1]["target_counts"][2] == 2000 + 2 * offset


@pytest.mark.parametrize("payload", [
    {"phases": [], "hold_joints": [4]},
    {"phases": [{"deltas_deg": {"2": 1}}], "hold_joints": [4]},
    {"phases": [{"deltas_deg": {"2": 1}}] * 3, "hold_joints": [4]},
    {"phases": [{"deltas_deg": {}}, {"deltas_deg": {"2": 1}}]},
    {"phases": [{"deltas_deg": {"1": 1, "2": 1, "4": 1}}, {"deltas_deg": {"2": 1}}]},
    {"phases": [{"deltas_deg": {"2": 1}}, {"deltas_deg": {"0": 1}}]},
    {"phases": [{"deltas_deg": {"2": 1}}, {"deltas_deg": {"2": 0}}]},
    {"phases": [{"deltas_deg": {"2": 1}}, {"deltas_deg": {"2": 5.1}}]},
    {"phases": [{"deltas_deg": {"2": 1}}, {"deltas_deg": {"2": float("nan")}}]},
    {"phases": [{"deltas_deg": {"2": 1}}, {"deltas_deg": {"2": True}}]},
    {"phases": [{"deltas_deg": {"2": 1}}, {"deltas_deg": {"2": 1}, "torque": 700}]},
    {"phases": [{"deltas_deg": {"2": 1}}, {"deltas_deg": {"2": 1}}], "deltas_deg": {"2": 1}},
    {"phases": [{"deltas_deg": {"2": 1}}, {"deltas_deg": {"2": 1}}], "hold_joints": [2]},
])
def test_invalid_phase_request_is_rejected_without_any_writes(rig, payload):
    api, bus, _clock = rig
    with pytest.raises(ValueError):
        api.recovery_nudge(payload)
    assert not [e for e in bus.events if e[0] != "read"]


def test_later_cumulative_out_of_limit_target_refuses_before_any_enable(rig):
    api, bus, _clock = rig
    bus.position[3] = round(STS_CENTRE_COUNT + 34 * COUNTS_PER_DEG * JOINT_SIGN[1])
    with pytest.raises(ValueError):
        api.recovery_nudge({"phases": [{"deltas_deg": {"1": 4}},
                                        {"deltas_deg": {"1": 4}}], "hold_joints": [4, 5]})
    assert not [e for e in bus.events if e[0] != "read"]


def test_phase_one_timeout_never_starts_phase_two(rig):
    api, bus, clock = rig
    bus.stalled.add(6)
    start = clock.now
    result = api.recovery_nudge(PHASES)
    assert not result["ok"] and result["torque_off"]
    assert len(bus.groups) == 1
    assert 3 <= clock.now - start < 3.1
    assert not bus.on


def test_second_phase_has_its_own_three_second_bound_and_total_under_six(rig):
    api, bus, clock = rig
    bus.stalled.add(4)
    start = clock.now
    result = api.recovery_nudge(PHASES)
    assert not result["ok"] and result["torque_off"]
    assert len(bus.groups) == 2
    assert 3 <= clock.now - start <= 6
    assert not bus.on


def test_targets_near_goal_but_not_stable_cannot_advance(rig):
    api, bus, _clock = rig
    samples = []

    def position(b):
        if b.groups and 6 in b.on:
            # Both readings are within two degrees, but their spread
            # exceeds three counts in every three-sample window.
            samples.append(True)
            return b.goal[6] + (0 if len(samples) % 2 else 8)
        return None

    bus.faults[(6, 56)] = position
    result = api.recovery_nudge(PHASES)
    assert not result["ok"] and result["torque_off"]
    assert len(bus.groups) == 1
    assert len(samples) >= 3
    assert not bus.on


def test_fault_votes_are_preserved_until_clear_and_not_hidden_by_phase_handoff(rig):
    api, bus, _clock = rig
    samples = []

    def current(b):
        if b.groups and 18 in b.on:
            samples.append(True)
            return 39
        return None

    bus.faults[(18, 69)] = current
    result = api.recovery_nudge(PHASES)
    assert not result["ok"] and result["torque_off"]
    assert len(samples) == 3
    assert len(bus.groups) == 1
    assert not bus.on


def test_phase_handoff_requires_three_healthy_scans_after_transient_fault_clears(rig):
    api, bus, _clock = rig
    samples = []

    def current(b):
        if len(b.groups) == 1 and 18 in b.on:
            value = 39 if len(samples) < 2 else 0
            samples.append(value)
            return value
        return None

    bus.faults[(18, 69)] = current
    result = api.recovery_nudge(PHASES)
    assert result["ok"] and result["torque_off"]
    assert samples[:5] == [39, 39, 0, 0, 0]
    assert len(bus.groups) == 2


def test_later_fixed_goal_is_refused_if_actual_phase_start_makes_move_over_five_degrees(rig):
    api, bus, _clock = rig
    original = bus.txPacket

    def write():
        result = original()
        if len(bus.groups) == 1:
            bus.position[4] -= 15  # Stable1.3degshort, withinphase1 settle tolerance.
        return result

    bus.txPacket = write
    result = api.recovery_nudge({"phases": [{"deltas_deg": {"2": 3}},
                                            {"deltas_deg": {"2": 5}}], "hold_joints": [4, 5]})
    assert not result["ok"] and result["torque_off"]
    assert len(bus.groups) == 1
    assert not bus.on


def test_nonzero_status_prevents_phase_handoff(rig):
    api, bus, _clock = rig
    bus.faults[(18, 65)] = lambda b: 1 if b.groups and 18 in b.on else None
    result = api.recovery_nudge(PHASES)
    assert not result["ok"] and result["torque_off"]
    assert len(bus.groups) == 1
    assert not bus.on


def test_abort_in_first_phase_does_not_start_second_and_disables_whole_union(rig):
    api, bus, _clock = rig
    original = bus.txPacket

    def write():
        result = original()
        api.require_setup_for("/cmd", "X")
        return result

    bus.txPacket = write
    result = api.recovery_nudge(PHASES)
    assert not result["ok"] and result["torque_off"]
    assert len(bus.groups) == 1
    assert {e[1] for e in bus.events if e[0] == "torque" and not e[2]} == {3, 4, 6, 7, 18, 19}
    assert not bus.on


def test_second_phase_cleanup_failure_does_not_skip_any_participant(rig):
    api, bus, _clock = rig
    bus.disable_fail.add(3)
    result = api.recovery_nudge(PHASES)
    assert not result["ok"] and not result["torque_off"]
    assert len(bus.groups) == 2
    assert {e[1] for e in bus.events if e[0] == "torque" and not e[2]} == {3, 4, 6, 7, 18, 19}
    assert all(bus.limit[sid] <= 200 for sid in (3, 4, 6, 7, 18, 19))
    assert bus.on == {3}


def test_legacy_single_phase_payload_still_produces_one_group(rig):
    api, bus, _clock = rig
    result = api.recovery_nudge(REQUEST)
    assert result["ok"] and result["torque_off"]
    assert bus.groups == [{3: (expected_target(1, -3), 90, 4),
                           4: (expected_target(2, 3), 90, 4)}]
