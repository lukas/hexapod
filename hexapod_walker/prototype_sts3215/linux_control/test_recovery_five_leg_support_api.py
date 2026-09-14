"""Off-robot mechanics for retained support on all twelve raw pitch motors."""
from __future__ import annotations

import pytest

from feetech_bus import COUNTS_PER_DEG, JOINT_SIGN, STS_CENTRE_COUNT, count_to_deg
from test_recovery_effort_api import active_fault
from test_recovery_nudge_api import expected_target, rig  # noqa: F401


JOINTS = (1, 2, 4, 5, 7, 8, 10, 11, 13, 14, 16, 17)
IDS = tuple(j + 2 for j in JOINTS)


def request(deltas=None, *, phases=None):
    changes = phases if phases is not None else [deltas or {}]
    movers = {int(j) for phase in changes for j in phase}
    data = {"effort_profile": "five_leg_support",
            "hold_joints": [j for j in JOINTS if j not in movers]}
    if phases is not None:
        data["phases"] = [{"deltas_deg": phase} for phase in phases]
    else:
        data["deltas_deg"] = changes[0]
    return data


def raw_pose(bus, joint, degrees):
    count = round(STS_CENTRE_COUNT + degrees * COUNTS_PER_DEG * JOINT_SIGN[joint])
    bus.position[joint + 2] = count
    return count


def assert_no_writes(bus):
    assert not [event for event in bus.events if event[0] != "read"]


def test_all_twelve_preloaded_and_verified_before_single_enable_then_retained_across_phases(rig):
    api, bus, _clock = rig
    knee_home = raw_pose(bus, 5, -36)
    bus.limit[9] = 120  # Preserve a lower saved L2 hip cap.
    result = api.recovery_nudge(request(phases=[{"7": 3, "8": 3}, {"14": -5}]))
    assert result["ok"] and result["torque_off"]
    assert result["joint_frame"] == "servo_relative"
    assert result["raw_limit_recovery_joints"] == [5]
    assert result["active_time_limit_s"] == 6
    assert set(result["joints"]) == {str(j) for j in JOINTS}
    assert bus.groups == [{9: (expected_target(7, 3), 90, 4),
                           10: (expected_target(8, 3), 90, 4)},
                          {16: (expected_target(14, -5), 90, 4)}]
    first_enable = next(i for i, event in enumerate(bus.events)
                        if event[0] == "torque" and event[2])
    before = bus.events[:first_enable]
    assert all(("read", sid, 40) in before for sid in range(2, 20))
    for joint in JOINTS:
        sid = joint + 2
        row = result["joints"][str(joint)]
        cap = 120 if joint == 7 else 500 if joint == 14 else 300
        home = knee_home if joint == 5 else 2000
        preload = ("position", sid, home, 90, 4)
        assert preload in before
        assert ("read", sid, 42) in before[before.index(preload) + 1:]
        limit = ("limit", sid, cap)
        assert limit in before
        assert ("read", sid, 48) in before[before.index(limit) + 1:]
        assert row["applied_torque_limit"] == cap
        assert row["current_soft_limit_a"] == (.75 if joint == 14 else .5)
        assert row["load_soft_limit_pct"] == (53 if joint == 14 else 33)
    assert [e for e in bus.events if e[0] == "torque" and e[2]] == [
        ("torque", sid, True) for sid in IDS]
    group_indices = [i for i, event in enumerate(bus.events) if event[0] == "group"]
    assert not [e for e in bus.events[group_indices[0]:group_indices[1]]
                if e[0] in ("position", "torque")]
    for phase in result["phases"]:
        assert phase["settled"]
        assert len(phase["settle_scans"]) == 3
        assert all(set(scan["counts"]) == set(JOINTS) for scan in phase["settle_scans"])
    assert bus.goal[7] == knee_home
    assert bus.goal[9] == expected_target(7, 3)
    assert not bus.on
    last_off = max(i for i, event in enumerate(bus.events)
                   if event[0] == "torque" and not event[2])
    assert not [e for e in bus.events[:last_off] if e[0] == "limit" and e[2] == 700]
    assert all(bus.limit[sid] == (120 if sid == 9 else 700) for sid in IDS)


@pytest.mark.parametrize("payload", [
    {**request({"14": -5}), "hold_joints": [j for j in JOINTS if j not in (8, 14)]},
    {**request({"14": -5}), "hold_joints": list(JOINTS)},
    {**request({"14": -5}), "hold_joints": [0, *[j for j in JOINTS if j != 14]]},
    request({"1": 1, "4": 1, "7": 1}),
    request({"7": 5.1}),
    request(phases=[{"7": 1}, {"8": 0}]),
    request(phases=[{"7": 1}, {"8": -5.1}]),
    request(phases=[{"7": 1}]),
])
def test_profile_shape_and_five_degree_bounds_reject_before_writes(rig, payload):
    api, bus, _clock = rig
    with pytest.raises(ValueError):
        api.recovery_nudge(payload)
    assert_no_writes(bus)


@pytest.mark.parametrize("joint", [7, 8])
def test_l2_admission_is_exclusive_to_explicit_support_profile(rig, joint):
    api, bus, _clock = rig
    with pytest.raises(ValueError):
        api.recovery_nudge({"deltas_deg": {str(joint): 3}, "hold_joints": [1]})
    assert_no_writes(bus)


def test_calibrated_knee_hold_uses_fresh_raw_count_and_ignores_logical_knee_and_trims(rig):
    api, bus, clock = rig
    raw_pose(bus, 4, 20)
    old = raw_pose(bus, 5, -36)
    fresh = old - 10 * JOINT_SIGN[5]
    reads = []

    def position(b):
        reads.append(True)
        if len(reads) >= 3:
            b.position[7] = fresh
            return fresh
        return old

    bus.faults[(7, 56)] = position
    start = clock.now
    result = api.recovery_nudge(request())
    row = result["joints"]["5"]
    assert result["ok"] and result["torque_off"]
    assert row["raw_start_outside_soft_limits"]
    assert row["before_counts"] == row["target_counts"] == fresh
    assert row["before_deg"] == pytest.approx(count_to_deg(5, fresh))
    assert row["before_deg"] < -36  # Not logical hip + knee (~-17) or trim-adjusted.
    assert ("position", 7, fresh, 90, 4) in bus.events
    assert not bus.groups
    assert 1 <= clock.now - start < 1.1
    assert not bus.on


@pytest.mark.parametrize("start,phases", [
    (-36, [{"5": 5}, {"5": 5}]),
    (-23, [{"5": 5}, {"5": 1}]),
    (153, [{"5": -5}, {"5": -1}]),
])
def test_raw_exception_accepts_monotonic_immutable_endpoints_toward_or_into_range(rig, start, phases):
    api, bus, _clock = rig
    home = raw_pose(bus, 5, start)
    original = bus.txPacket

    def write():
        result = original()
        if len(bus.groups) == 1:
            # Closer to the next goal by <1 degree, so the next actual step remains bounded.
            bus.position[7] += 5 * JOINT_SIGN[5] * (1 if start < 0 else -1)
        return result

    bus.txPacket = write
    result = api.recovery_nudge(request(phases=phases))
    first = home + expected_target(5, phases[0]["5"]) - 2000
    second = first + expected_target(5, phases[1]["5"]) - 2000
    assert result["ok"] and result["torque_off"]
    assert bus.groups == [{7: (first, 90, 4)}, {7: (second, 90, 4)}]
    assert result["joints"]["5"]["raw_start_outside_soft_limits"]
    assert result["phases"][1]["target_counts"][5] == second


@pytest.mark.parametrize("start,phases", [
    (-36, [{"5": -1}, {"5": 5}]),
    (-36, [{"5": 5}, {"5": -1}]),
    (-23, [{"5": 4}, {"5": -3}]),
    (153, [{"5": -5}, {"5": 5}]),
])
def test_any_phase_that_worsens_or_reenters_violation_refuses_entire_plan_before_writes(rig, start, phases):
    api, bus, _clock = rig
    raw_pose(bus, 5, start)
    with pytest.raises(ValueError):
        api.recovery_nudge(request(phases=phases))
    assert_no_writes(bus)


def test_phase_two_refuses_fixed_goal_that_would_worsen_fresh_actual_raw_violation(rig):
    api, bus, _clock = rig
    home = raw_pose(bus, 5, -36)
    original = bus.txPacket

    def write():
        result = original()
        if len(bus.groups) == 1:
            # Phase one overshoots toward the safe range by 1.75 degrees.
            # Its stable actual -29.3 is inside settling tolerance, but the
            # next immutable -30.1 target would move back outside again.
            bus.position[7] += 20 * JOINT_SIGN[5]
        return result

    bus.txPacket = write
    result = api.recovery_nudge(request(phases=[{"5": 5}, {"5": 1}]))
    first = home + expected_target(5, 5) - 2000
    assert not result["ok"] and result["torque_off"]
    assert len(bus.groups) == 1
    assert bus.groups[0] == {7: (first, 90, 4)}
    assert result["phases"][0]["settled"]
    assert not result["phases"][1]["settled"]
    assert "raw" in result["error"].lower()
    assert not bus.on


@pytest.mark.parametrize("joint,count", [(5, -1), (5, 4096), (8, 1638), (14, 1638)])
def test_exception_never_allows_invalid_counts_or_other_outside_raw_knees(rig, joint, count):
    api, bus, _clock = rig
    bus.position[joint + 2] = count
    with pytest.raises(ValueError):
        api.recovery_nudge(request())
    assert_no_writes(bus)


def test_other_profiles_still_reject_calibrated_raw_knee_even_when_logical_sum_is_in_range(rig):
    api, bus, _clock = rig
    raw_pose(bus, 4, 20)
    raw_pose(bus, 5, -36)  # Logical absolute knee ~-16 does not repair raw -36.
    with pytest.raises(ValueError):
        api.recovery_nudge({"deltas_deg": {"1": 1}, "hold_joints": [4, 5]})
    assert_no_writes(bus)


def test_valid_raw_pitch_pair_is_not_rejected_for_its_logical_absolute_knee(rig):
    api, bus, _clock = rig
    raw_pose(bus, 4, -40)
    raw_pose(bus, 5, 10)  # Logical absolute knee ~-30; both raw motors are in range.
    result = api.recovery_nudge(request({"5": 3}))
    assert result["ok"] and result["torque_off"]
    assert not result["joints"]["5"]["raw_start_outside_soft_limits"]
    assert result["joints"]["5"]["target_deg"] == pytest.approx(13, abs=.15)


@pytest.mark.parametrize("sid,address,value,votes", [
    (9, 69, 77, 3), (10, 60, 330, 3),
    (16, 69, 116, 3), (16, 60, 530, 3), (9, 69, 154, 1),
])
def test_support_and_l4_effort_guards_keep_three_votes_and_hard_stop(rig, sid, address, value, votes):
    api, bus, _clock = rig
    samples = active_fault(bus, sid, address, [value] * 20)
    result = api.recovery_nudge(request({"14": -5}))
    assert not result["ok"] and result["torque_off"]
    assert len(samples) == votes
    assert not bus.on
    assert all(bus.limit[sid] == 700 for sid in IDS)


def test_l2_opposite_pair_stops_if_only_one_motor_moves(rig):
    api, bus, _clock = rig
    bus.stalled.add(10)
    result = api.recovery_nudge(request({"7": -3, "8": 3}))
    assert not result["ok"] and result["torque_off"]
    assert "L2 hip/knee actual pair mismatch" in result["error"]
    assert result["max_pair_error_deg"] > 2.5
    assert not bus.on


def test_phase_timeout_does_not_advance_or_extend_three_second_window(rig):
    api, bus, clock = rig
    bus.stalled.add(9)
    start = clock.now
    result = api.recovery_nudge(request(phases=[{"7": 5}, {"14": -5}]))
    assert not result["ok"] and result["torque_off"]
    assert len(bus.groups) == 1
    assert 3 <= clock.now - start < 3.1
    assert not bus.on


def test_abort_and_failed_off_attempt_every_participant_without_restoring_high_limits(rig):
    api, bus, _clock = rig
    bus.after_enable = lambda sid: api.require_setup_for("/cmd", "X")
    bus.disable_fail.add(3)
    result = api.recovery_nudge(request({"14": -5}))
    assert not result["ok"] and not result["torque_off"]
    assert not bus.groups
    assert {e[1] for e in bus.events if e[0] == "torque" and not e[2]} == set(IDS)
    assert all(bus.limit[j + 2] == (500 if j == 14 else 300) for j in JOINTS)
    assert bus.on == {3}
