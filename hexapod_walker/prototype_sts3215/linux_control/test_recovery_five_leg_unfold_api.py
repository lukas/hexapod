"""Off-robot guards for the exact five-leg support then L4 unfold sequence."""
from __future__ import annotations

import pytest

from feetech_bus import JOINT_SIGN
from test_recovery_effort_api import active_fault
from test_recovery_five_leg_support_api import IDS, JOINTS, assert_no_writes, raw_pose
from test_recovery_nudge_api import expected_target, rig  # noqa: F401


HOLDS = [1, 4, 8, 11, 13, 17]


def request(magnitude=10, unfold=30):
    return {"effort_profile": "five_leg_unfold", "hold_joints": list(HOLDS),
            "phases": [{"deltas_deg": {"2": -magnitude, "5": magnitude,
                                        "7": magnitude, "10": magnitude, "16": magnitude}},
                       {"deltas_deg": {"14": -unfold}}]}


def start_pose(bus):
    # Independent RAW knee hinges, irrespective of hip angles or the fake's trims.
    raw_pose(bus, 5, -36)
    raw_pose(bus, 14, 40)
    return {j: bus.position[j + 2] for j in JOINTS}


@pytest.mark.parametrize("magnitude,unfold", [(5, 5), (10, 30)])
def test_exact_bounds_preload_all_twelve_once_and_retain_raw_support_goals(rig, magnitude, unfold):
    api, bus, _clock = rig
    homes = start_pose(bus)
    bus.limit[9] = 120
    payload = request(magnitude, unfold)
    result = api.recovery_nudge(payload)
    assert result["ok"] and result["torque_off"]
    assert result["joint_frame"] == "servo_relative"
    assert result["effort_profile"] == "five_leg_unfold"
    assert result["active_time_limit_s"] == 10
    assert result["phase_settle_tolerance_deg"] == 3
    assert [phase["time_limit_s"] for phase in result["phases"]] == [4, 6]
    assert result["raw_limit_recovery_joints"] == [5]
    assert result["joints"]["5"]["raw_start_outside_soft_limits"]
    expected_groups = [{int(j) + 2: (homes[int(j)] + expected_target(int(j), delta) - 2000, 90, 4)
                        for j, delta in phase["deltas_deg"].items()} for phase in payload["phases"]]
    assert bus.groups == expected_groups
    first_on = next(i for i, e in enumerate(bus.events) if e[0] == "torque" and e[2])
    before = bus.events[:first_on]
    assert all(("read", sid, 40) in before for sid in range(2, 20))
    for j in JOINTS:
        sid = j + 2
        cap = 120 if j == 7 else 500 if j == 14 else 300
        preload = ("position", sid, homes[j], 90, 4)
        limit = ("limit", sid, cap)
        assert preload in before and limit in before
        assert ("read", sid, 42) in before[before.index(preload) + 1:]
        assert ("read", sid, 48) in before[before.index(limit) + 1:]
        row = result["joints"][str(j)]
        assert row["applied_torque_limit"] == cap
        assert row["current_soft_limit_a"] == (.75 if j == 14 else .5)
        assert row["load_soft_limit_pct"] == (53 if j == 14 else 33)
        assert row["before_counts"] == homes[j]
    assert [e for e in bus.events if e[0] == "torque" and e[2]] == [
        ("torque", sid, True) for sid in IDS]
    assert [e for e in bus.events if e[0] == "torque" and not e[2]] == [
        ("torque", sid, False) for sid in IDS]
    group_indices = [i for i, e in enumerate(bus.events) if e[0] == "group"]
    assert not [e for e in bus.events[group_indices[0]:group_indices[1]]
                if e[0] in ("position", "torque")]
    for phase in result["phases"]:
        assert phase["settled"]
        assert len(phase["settle_scans"]) == 3
        assert all(set(scan["counts"]) == set(JOINTS) for scan in phase["settle_scans"])
    assert all(bus.goal[sid] == command[0] for sid, command in expected_groups[0].items())
    assert result["joints"]["5"]["target_deg"] == pytest.approx(-36 + magnitude, abs=.2)
    last_off = max(i for i, e in enumerate(bus.events) if e[0] == "torque" and not e[2])
    assert not [e for e in bus.events[:last_off] if e[0] == "limit" and e[2] == 700]
    assert all(bus.limit[sid] == (120 if sid == 9 else 700) for sid in IDS)
    assert not bus.on


def malformed_requests():
    cases = []
    for joint, delta in [("2", 10), ("5", -10), ("7", 9), ("10", 0),
                         ("16", 10.1), ("5", float("nan")), ("5", True)]:
        payload = request()
        payload["phases"][0]["deltas_deg"][joint] = delta
        cases.append(payload)
    cases.extend([request(4.9), request(10.1), request(unfold=4.9), request(unfold=30.1),
                  request(unfold=-5)])
    for movers in ({"13": -5}, {"14": -5, "2": -5}, {}):
        payload = request()
        payload["phases"][1]["deltas_deg"] = movers
        cases.append(payload)
    payload = request()
    payload["phases"][0]["deltas_deg"].pop("7")
    cases.append(payload)
    for holds in (HOLDS[:-1], [0, *HOLDS[1:]], [*HOLDS, 14]):
        cases.append({**request(), "hold_joints": holds})
    cases.extend([{**request(), "phases": request()["phases"][:1]},
                  {**request(), "phases": request()["phases"] * 2},
                  {**request(), "deltas_deg": {"14": -5}},
                  {"effort_profile": "five_leg_unfold", "deltas_deg": {}, "hold_joints": list(JOINTS)}])
    return cases


@pytest.mark.parametrize("payload", malformed_requests())
def test_exact_signed_sequence_and_bounds_are_required_before_writes(rig, payload):
    api, bus, _clock = rig
    start_pose(bus)
    with pytest.raises(ValueError):
        api.recovery_nudge(payload)
    assert_no_writes(bus)


@pytest.mark.parametrize("joint,degrees", [(14, 0), (7, 35), (5, 153)])
def test_all_raw_endpoints_are_prevalidated_including_later_phase_and_knee_exception(rig, joint, degrees):
    api, bus, _clock = rig
    start_pose(bus)
    raw_pose(bus, joint, degrees)
    with pytest.raises(ValueError):
        api.recovery_nudge(request())
    assert_no_writes(bus)


@pytest.mark.parametrize("count", [-1, 4096])
def test_calibrated_raw_knee_exception_never_admits_invalid_encoder_counts(rig, count):
    api, bus, _clock = rig
    start_pose(bus)
    bus.position[7] = count
    with pytest.raises(ValueError):
        api.recovery_nudge(request())
    assert_no_writes(bus)


@pytest.mark.parametrize("profile", [None, "five_leg_support", "l4_sweep50"])
def test_new_sequence_does_not_expand_other_profile_admission(rig, profile):
    api, bus, _clock = rig
    start_pose(bus)
    payload = request()
    if profile is None:
        payload.pop("effort_profile")
    else:
        payload["effort_profile"] = profile
    with pytest.raises(ValueError):
        api.recovery_nudge(payload)
    assert_no_writes(bus)


def test_phase_one_admits_three_degree_residual_only_after_three_stable_healthy_scans(rig):
    api, bus, _clock = rig
    start_pose(bus)
    original = bus.txPacket

    def write():
        value = original()
        if len(bus.groups) == 1:
            # ~2.46 degrees short, admissible under this profile's 3-degree gate.
            bus.position[4] += 28 * JOINT_SIGN[2]
        return value

    bus.txPacket = write
    result = api.recovery_nudge(request())
    assert result["ok"] and result["torque_off"]
    phase = result["phases"][0]
    assert phase["settled"] and len(phase["settle_scans"]) == 3
    assert abs(phase["reached_counts"][2] - phase["target_counts"][2]) == 28
    assert all(scan["counts"][2] == phase["reached_counts"][2] for scan in phase["settle_scans"])


def test_support_instability_blocks_phase_transition(rig):
    api, bus, clock = rig
    start_pose(bus)
    samples = []

    def position(b):
        if b.groups and 3 in b.on:
            samples.append(True)
            return b.goal[3] + (0 if len(samples) % 2 else 8)
        return None

    bus.faults[(3, 56)] = position
    start = clock.now
    result = api.recovery_nudge(request())
    assert not result["ok"] and result["torque_off"]
    assert len(bus.groups) == 1 and len(samples) >= 3
    assert 4 <= clock.now - start < 4.1
    assert not bus.on


def test_phase_two_target_remains_immutable_when_actual_knee_drift_is_within_bound(rig):
    api, bus, _clock = rig
    homes = start_pose(bus)
    original = bus.txPacket

    def write():
        value = original()
        if len(bus.groups) == 1:
            bus.position[16] -= 10 * JOINT_SIGN[14]  # ~0.9 degree closer to its next goal.
        return value

    bus.txPacket = write
    result = api.recovery_nudge(request())
    goal = homes[14] + expected_target(14, -30) - 2000
    assert result["ok"] and result["torque_off"]
    assert bus.groups[1] == {16: (goal, 90, 4)}
    assert result["phases"][1]["start_counts"][14] == homes[14] - 10 * JOINT_SIGN[14]
    assert result["phases"][1]["target_counts"][14] == goal


def test_phase_two_refuses_if_actual_sag_makes_immutable_goal_more_than_thirty_degrees_away(rig):
    api, bus, _clock = rig
    start_pose(bus)
    original = bus.txPacket

    def write():
        value = original()
        if len(bus.groups) == 1:
            bus.position[16] += 10 * JOINT_SIGN[14]  # Safe support drift, excessive next step.
        return value

    bus.txPacket = write
    result = api.recovery_nudge(request())
    assert not result["ok"] and result["torque_off"]
    assert result["phases"][0]["settled"]
    assert len(bus.groups) == 1
    assert "30" in result["error"] and "actual" in result["error"]
    assert not bus.on


def test_first_phase_stall_stops_at_four_seconds_without_starting_second(rig):
    api, bus, clock = rig
    start_pose(bus)
    bus.stalled.add(4)
    start = clock.now
    result = api.recovery_nudge(request())
    assert not result["ok"] and result["torque_off"]
    assert len(bus.groups) == 1
    assert 4 <= clock.now - start < 4.1
    assert not bus.on


def test_late_first_phase_then_stalled_second_gets_six_seconds_and_total_under_ten(rig):
    api, bus, clock = rig
    homes = start_pose(bus)
    bus.stalled.add(16)
    start = clock.now

    def position(b):
        if len(b.groups) == 1 and 4 in b.on and clock.now - start < 3.75:
            return homes[2]
        return None

    bus.faults[(4, 56)] = position
    result = api.recovery_nudge(request())
    assert not result["ok"] and result["torque_off"]
    assert len(bus.groups) == 2
    assert 3.75 <= result["phases"][1]["started_active_s"] < 4
    assert 6 <= result["phases"][1]["elapsed_s"] < 6.1
    assert 9.75 <= clock.now - start <= 10
    assert not bus.on


@pytest.mark.parametrize("sid,address,value,votes", [
    (9, 69, 77, 3), (9, 60, 330, 3), (16, 69, 116, 3),
    (16, 69, 154, 1), (3, 65, 4, 1),
])
def test_force_and_status_faults_stop_without_advancing(rig, sid, address, value, votes):
    api, bus, _clock = rig
    start_pose(bus)
    samples = active_fault(bus, sid, address, [value] * 20)
    result = api.recovery_nudge(request())
    assert not result["ok"] and result["torque_off"]
    assert len(samples) == votes and len(bus.groups) == 1
    assert not bus.on
    assert all(bus.limit[sid] == 700 for sid in IDS)


def test_bad_preload_never_enables(rig):
    api, bus, _clock = rig
    start_pose(bus)
    bus.faults[(19, 42)] = lambda b: 1234
    result = api.recovery_nudge(request())
    assert not result["ok"] and result["torque_off"]
    assert not [e for e in bus.events if e[0] == "torque" and e[2]]
    assert not bus.groups
    assert not bus.on


def test_abort_with_one_failed_off_still_disables_every_other_motor_before_any_restore(rig):
    api, bus, _clock = rig
    start_pose(bus)
    bus.after_enable = lambda sid: api.require_setup_for("/cmd", "X")
    bus.disable_fail.add(3)
    result = api.recovery_nudge(request())
    assert not result["ok"] and not result["torque_off"]
    assert not bus.groups
    assert {e[1] for e in bus.events if e[0] == "torque" and not e[2]} == set(IDS)
    assert all(bus.limit[j + 2] == (500 if j == 14 else 300) for j in JOINTS)
    assert bus.on == {3}
