"""Off-robot bounds for equal outward movement of the L0/L4 knees."""
from __future__ import annotations

import pytest

from feetech_bus import COUNTS_PER_DEG, JOINT_SIGN, STS_CENTRE_COUNT
from test_recovery_effort_api import active_fault
from test_recovery_nudge_api import expected_target, rig  # noqa: F401


HOLDS = [1, 13, 16, 17]
JOINTS = (1, 2, 13, 14, 16, 17)
IDS = tuple(j + 2 for j in JOINTS)
PROFILE = {"effort_profile": "two_knees_50pct", "hold_joints": HOLDS,
           "deltas_deg": {"2": -5, "14": -5}}
PHASES = {"effort_profile": "two_knees_50pct", "hold_joints": HOLDS,
          "phases": [{"deltas_deg": {"2": -10, "14": -10}},
                     {"deltas_deg": {"2": -5, "14": -5}}]}


@pytest.mark.parametrize("delta", [-5, -10])
def test_exact_two_knee_request_raises_only_knee_caps_and_restores_after_all_off(rig, delta):
    api, bus, _clock = rig
    result = api.recovery_nudge({**PROFILE, "hold_joints": list(reversed(HOLDS)),
                                 "deltas_deg": {"2": delta, "14": delta}})
    assert result["ok"] and result["torque_off"]
    assert result["effort_profile"] == "two_knees_50pct"
    assert result["joint_frame"] == "servo_relative"
    assert bus.groups == [{4: (expected_target(2, delta), 90, 4),
                           16: (expected_target(14, delta), 90, 4)}]
    for joint in JOINTS:
        row = result["joints"][str(joint)]
        knee = joint in (2, 14)
        assert row["applied_torque_limit"] == (500 if knee else 200)
        assert row["current_soft_limit_a"] == (.75 if knee else .25)
        assert row["load_soft_limit_pct"] == (53 if knee else 23)
    last_disable = max(i for i, event in enumerate(bus.events)
                       if event[0] == "torque" and not event[2])
    assert not [event for event in bus.events[:last_disable]
                if event[0] == "limit" and event[2] == 700]
    assert all(bus.limit[sid] == 700 for sid in IDS)
    assert not bus.on


@pytest.mark.parametrize("payload", [
    {**PROFILE, "deltas_deg": {"2": -4.9, "14": -4.9}},
    {**PROFILE, "deltas_deg": {"2": -10.1, "14": -10.1}},
    {**PROFILE, "deltas_deg": {"2": 5, "14": 5}},
    {**PROFILE, "deltas_deg": {"2": -5, "14": 5}},
    {**PROFILE, "deltas_deg": {"2": -5, "14": -6}},
    {**PROFILE, "deltas_deg": {"2": -5}},
    {**PROFILE, "deltas_deg": {"2": -5, "11": -5}},
    {**PROFILE, "deltas_deg": {"2": -5, "14": float("nan")}},
    {**PROFILE, "hold_joints": [1, 13, 16]},
    {**PROFILE, "hold_joints": [1, 10, 13, 16]},
    {**PHASES, "deltas_deg": {"2": -5, "14": -5}},
    {**PHASES, "phases": [{"deltas_deg": {"2": -5, "14": -5}}]},
    {**PHASES, "phases": [{"deltas_deg": {"2": -5, "14": -5}},
                           {"deltas_deg": {"2": -5, "14": -6}}]},
])
def test_profile_rejects_nonexact_shapes_before_any_write(rig, payload):
    api, bus, _clock = rig
    with pytest.raises(ValueError):
        api.recovery_nudge(payload)
    assert not [event for event in bus.events if event[0] != "read"]


@pytest.mark.parametrize("delta,hard", [(-5, False), (-10, True)])
@pytest.mark.parametrize("stalled_sid", [4, 16])
def test_one_knee_stuck_trips_measured_progress_mismatch(rig, delta, hard, stalled_sid):
    api, bus, clock = rig
    bus.stalled.add(stalled_sid)
    start = clock.now
    result = api.recovery_nudge({**PROFILE, "deltas_deg": {"2": delta, "14": delta}})
    assert not result["ok"] and result["torque_off"]
    assert result["max_knee_progress_mismatch_deg"] > (5 if hard else 3)
    assert result["knee_progress_fault_reads"] == (1 if hard else 3)
    assert clock.now - start < 3
    assert not bus.on


@pytest.mark.parametrize("sid", [4, 16])
@pytest.mark.parametrize("address,value", [(69, 116), (60, 530)])
def test_each_knee_soft_effort_guard_still_needs_three_fresh_votes(rig, sid, address, value):
    api, bus, _clock = rig
    samples = active_fault(bus, sid, address, [value] * 20)
    result = api.recovery_nudge(PROFILE)
    assert not result["ok"] and result["torque_off"]
    assert len(samples) == 3
    assert not bus.on


@pytest.mark.parametrize("sid", [4, 16])
def test_each_knee_hard_current_guard_stops_immediately(rig, sid):
    api, bus, _clock = rig
    samples = active_fault(bus, sid, 69, [154] * 20)
    result = api.recovery_nudge(PROFILE)
    assert not result["ok"] and result["torque_off"]
    assert samples == [154]
    assert not bus.on


def test_support_effort_limit_does_not_inherit_knee_profile(rig):
    api, bus, _clock = rig
    samples = active_fault(bus, 15, 69, [39] * 20)
    result = api.recovery_nudge(PROFILE)
    assert not result["ok"] and result["torque_off"]
    assert len(samples) == 3
    assert not bus.on


def test_two_phase_reference_resets_and_original_targets_remain_immutable(rig):
    api, bus, _clock = rig
    original = bus.txPacket

    def write():
        result = original()
        # L0 keeps a stable2.46deg residual, permitted only by the new
        # three-degree phase tolerance. Phase2 adds a1.05deg L4 overshoot.
        bus.position[4] += 28 * JOINT_SIGN[2]
        if len(bus.groups) == 2:
            bus.position[16] -= 12 * JOINT_SIGN[14]
        return result

    bus.txPacket = write
    result = api.recovery_nudge(PHASES)
    assert result["ok"] and result["torque_off"]
    assert result["phase_settle_tolerance_deg"] == 3
    assert result["knee_progress_soft_limit_deg"] == 3
    assert result["knee_progress_hard_limit_deg"] == 5
    first = {j: expected_target(j, -10) for j in (2, 14)}
    final = {j: first[j] + expected_target(j, -5) - 2000 for j in (2, 14)}
    assert bus.groups == [
        {j + 2: (first[j], 90, 4) for j in (2, 14)},
        {j + 2: (final[j], 90, 4) for j in (2, 14)}]
    assert result["phases"][1]["start_counts"][2] == first[2] + 28 * JOINT_SIGN[2]
    assert result["phases"][1]["target_counts"][2] == final[2]
    assert result["knee_progress_mismatch_deg"] == pytest.approx(12 / COUNTS_PER_DEG)
    assert result["max_knee_progress_mismatch_deg"] == pytest.approx(28 / COUNTS_PER_DEG)
    assert [event for event in bus.events if event[0] == "torque" and event[2]] == [
        ("torque", sid, True) for sid in IDS]
    assert [event for event in bus.events if event[0] == "position"] == [
        ("position", sid, 2000, 90, 4) for sid in IDS]
    assert not bus.on


def test_next_phase_actual_travel_over_ten_degrees_refuses_even_with_valid_raw_targets(rig):
    api, bus, _clock = rig
    bus.position[4] = bus.position[16] = STS_CENTRE_COUNT
    original = bus.txPacket

    def write():
        result = original()
        if len(bus.groups) == 1:
            for joint in (2, 14):
                bus.position[joint + 2] += 28 * JOINT_SIGN[joint]
        return result

    bus.txPacket = write
    result = api.recovery_nudge({**PHASES, "phases": [
        {"deltas_deg": {"2": -10, "14": -10}},
        {"deltas_deg": {"2": -10, "14": -10}}]})
    assert not result["ok"] and result["torque_off"]
    assert len(bus.groups) == 1
    assert not bus.on


def test_later_cumulative_raw_limit_violation_refuses_before_arming(rig):
    api, bus, _clock = rig
    # Starting at the fixture's -4.2 degrees, two -10-degree phases would
    # exceed the physical knee's -20-degree limit even though each step fits.
    with pytest.raises(ValueError):
        api.recovery_nudge({**PHASES, "phases": [
            {"deltas_deg": {"2": -10, "14": -10}},
            {"deltas_deg": {"2": -10, "14": -10}}]})
    assert not [event for event in bus.events if event[0] != "read"]


def test_default_phased_recovery_keeps_its_two_degree_settle_tolerance(rig):
    api, bus, _clock = rig
    original = bus.txPacket

    def write():
        result = original()
        for joint in (2, 14):
            bus.position[joint + 2] += 28 * JOINT_SIGN[joint]
        return result

    bus.txPacket = write
    result = api.recovery_nudge({"hold_joints": HOLDS, "phases": [
        {"deltas_deg": {"2": -5, "14": -5}},
        {"deltas_deg": {"2": -5, "14": -5}}]})
    assert not result["ok"] and result["torque_off"]
    assert result["phase_settle_tolerance_deg"] == 2
    assert len(bus.groups) == 1
    assert not bus.on


def test_second_phase_stall_obeys_three_second_window_and_six_second_total(rig):
    api, bus, clock = rig
    original = bus.txPacket

    def write():
        if bus.groups:
            bus.stalled.update((4, 16))
        return original()

    bus.txPacket = write
    start = clock.now
    result = api.recovery_nudge(PHASES)
    assert not result["ok"] and result["torque_off"]
    assert len(bus.groups) == 2
    assert result["phases"][1]["elapsed_s"] == pytest.approx(3, abs=.001)
    assert 3 <= clock.now - start <= 6
    assert not bus.on


def test_lower_saved_knee_limit_and_failed_cleanup_preserve_low_limits(rig):
    api, bus, _clock = rig
    bus.limit[4] = 300
    bus.disable_fail.add(16)
    result = api.recovery_nudge(PROFILE)
    assert not result["ok"] and not result["torque_off"]
    assert result["joints"]["2"]["applied_torque_limit"] == 300
    assert bus.limit[4] == 300 and bus.limit[16] == 500
    assert {event[1] for event in bus.events if event[0] == "torque" and not event[2]} == set(IDS)
    assert all(bus.limit[j + 2] == 200 for j in HOLDS)
    assert bus.on == {16}
