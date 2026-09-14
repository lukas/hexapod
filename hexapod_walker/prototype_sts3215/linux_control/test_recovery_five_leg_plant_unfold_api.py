"""Off-robot planting sequence and sustained-current guards for its explicit profile."""
from __future__ import annotations

import pytest

from feetech_bus import COUNTS_PER_DEG, JOINT_SIGN, count_to_deg
from test_recovery_effort_api import active_fault
from test_recovery_five_leg_support_api import IDS, JOINTS, assert_no_writes, raw_pose
from test_recovery_five_leg_unfold_api import request as old_unfold_request, start_pose
from test_recovery_nudge_api import REQUEST as DEFAULT_REQUEST, expected_target, rig  # noqa: F401


HOLDS = [2, 5, 8, 11, 13, 16]
MOVERS = (1, 4, 7, 10, 17)


def request(magnitude=10, unfold=30):
    return {"effort_profile": "five_leg_plant_unfold", "hold_joints": list(HOLDS),
            "phases": [{"deltas_deg": {"1": magnitude, "4": magnitude, "7": magnitude,
                                       "10": magnitude, "17": -magnitude}},
                       {"deltas_deg": {"14": -unfold}}]}


@pytest.mark.parametrize("magnitude,unfold", [(5, 5), (10, 30)])
def test_exact_sequence_preloads_all_raw_pitch_goals_once_with_isolated_effort_caps(rig, magnitude, unfold):
    api, bus, _clock = rig
    homes = start_pose(bus)
    bus.limit.update({sid: 900 for sid in IDS})
    bus.limit[6] = 120
    payload = request(magnitude, unfold)
    result = api.recovery_nudge(payload)
    assert result["ok"] and result["torque_off"]
    assert result["effort_profile"] == "five_leg_plant_unfold"
    assert result["single_sample_current_limit_a"] is None
    assert result["joint_frame"] == "servo_relative"
    assert result["active_time_limit_s"] == 10
    assert [phase["time_limit_s"] for phase in result["phases"]] == [4, 6]
    assert result["phases"][0]["min_progress_fraction"] == .5
    assert result["phases"][0]["max_goal_error_deg"] == 5
    assert result["phase_settle_tolerance_deg"] == 3
    assert result["raw_limit_recovery_joints"] == [5]
    assert result["joints"]["5"]["raw_start_outside_soft_limits"]
    expected_groups = [{int(j) + 2: (homes[int(j)] + expected_target(int(j), delta) - 2000, 90, 4)
                        for j, delta in phase["deltas_deg"].items()} for phase in payload["phases"]]
    assert bus.groups == expected_groups
    first_on = next(i for i, e in enumerate(bus.events) if e[0] == "torque" and e[2])
    before = bus.events[:first_on]
    assert all(("read", sid, 40) in before for sid in range(2, 20))
    for j in JOINTS:
        sid, row = j + 2, result["joints"][str(j)]
        cap = 120 if j == 4 else 700 if j == 14 else 500
        preload, limit = ("position", sid, homes[j], 90, 4), ("limit", sid, cap)
        assert preload in before and limit in before
        assert ("read", sid, 42) in before[before.index(preload) + 1:]
        assert ("read", sid, 48) in before[before.index(limit) + 1:]
        assert row["saved_torque_limit"] == (120 if j == 4 else 900)
        assert row["applied_torque_limit"] == cap
        assert row["current_soft_limit_a"] == (2 if j == 14 else 1)
        assert row["load_soft_limit_pct"] == (73 if j == 14 else 53)
    assert [e for e in bus.events if e[0] == "torque" and e[2]] == [
        ("torque", sid, True) for sid in IDS]
    assert [e for e in bus.events if e[0] == "torque" and not e[2]] == [
        ("torque", sid, False) for sid in IDS]
    indices = [i for i, e in enumerate(bus.events) if e[0] == "group"]
    assert not [e for e in bus.events[indices[0]:indices[1]] if e[0] in ("position", "torque")]
    assert all(bus.goal[sid] == target[0] for sid, target in expected_groups[0].items())
    assert bus.goal[7] == homes[5]  # Calibrated raw knee is held, without hip coupling or trims.
    assert set(result["achieved_support_anchors_counts"]) == {str(j) for j in MOVERS}
    for phase in result["phases"]:
        assert phase["settled"] and len(phase["settle_scans"]) == 3
        assert all(set(scan["counts"]) == set(JOINTS) for scan in phase["settle_scans"])
    last_off = max(i for i, e in enumerate(bus.events) if e[0] == "torque" and not e[2])
    assert not [e for e in bus.events[:last_off] if e[0] == "limit" and e[2] == 900]
    assert all(bus.limit[sid] == (120 if sid == 6 else 900) for sid in IDS)
    assert not bus.on


def invalid_requests():
    cases = [request(4.9), request(10.1), request(unfold=4.9), request(unfold=30.1),
             request(unfold=-5)]
    for joint, delta in [("1", -10), ("17", 10), ("7", 9), ("10", 0),
                         ("4", float("nan")), ("4", True)]:
        payload = request()
        payload["phases"][0]["deltas_deg"][joint] = delta
        cases.append(payload)
    for movers in ({"13": -5}, {"14": -5, "2": -5}, {}):
        payload = request()
        payload["phases"][1]["deltas_deg"] = movers
        cases.append(payload)
    for holds in (HOLDS[:-1], [0, *HOLDS[1:]], [*HOLDS, 1]):
        cases.append({**request(), "hold_joints": holds})
    wrong_first = old_unfold_request()
    wrong_first["effort_profile"] = "five_leg_plant_unfold"
    cases.extend([wrong_first, {**request(), "phases": request()["phases"][:1]},
                  {**request(), "deltas_deg": {"14": -5}},
                  {"effort_profile": "five_leg_plant_unfold", "hold_joints": list(JOINTS)}])
    return cases


@pytest.mark.parametrize("payload", invalid_requests())
def test_exact_shape_and_bounds_refuse_before_writes(rig, payload):
    api, bus, _clock = rig
    start_pose(bus)
    with pytest.raises(ValueError):
        api.recovery_nudge(payload)
    assert_no_writes(bus)


@pytest.mark.parametrize("joint,degrees", [(1, 35), (17, -15), (14, 0)])
def test_current_and_later_raw_endpoint_limits_are_prevalidated_before_any_enable(rig, joint, degrees):
    api, bus, _clock = rig
    start_pose(bus)
    raw_pose(bus, joint, degrees)
    with pytest.raises(ValueError):
        api.recovery_nudge(request())
    assert_no_writes(bus)


@pytest.mark.parametrize("count", [-1, 4096])
def test_raw_knee_exception_never_admits_invalid_encoder_counts(rig, count):
    api, bus, _clock = rig
    start_pose(bus)
    bus.position[7] = count
    with pytest.raises(ValueError):
        api.recovery_nudge(request())
    assert_no_writes(bus)


@pytest.mark.parametrize("sid,high", [(3, 154), (7, 154), (16, 308)])
def test_isolated_high_current_votes_reset_and_require_three_new_healthy_handoff_scans(rig, sid, high):
    api, bus, _clock = rig
    start_pose(bus)
    samples = active_fault(bus, sid, 69, [high, high, 0, high, 0, 0, 0])
    original = bus.txPacket
    handoff_reads = []

    def write():
        if len(bus.groups) == 1:
            handoff_reads.append(len(samples))
        return original()

    bus.txPacket = write
    result = api.recovery_nudge(request())
    assert result["ok"] and result["torque_off"]
    assert samples[:7] == [high, high, 0, high, 0, 0, 0]
    assert handoff_reads == [7]
    assert result["joints"][str(sid - 2)]["force_fault_reads"] == 0
    assert not bus.on


@pytest.mark.parametrize("sid,address,high", [(3, 69, 154), (7, 69, 154), (16, 69, 308),
                                              (3, 60, 530), (16, 60, 730)])
def test_three_consecutive_fresh_force_votes_stop_and_cleanup(rig, sid, address, high):
    api, bus, _clock = rig
    start_pose(bus)
    samples = active_fault(bus, sid, address, [high, 0, high, high, high])
    result = api.recovery_nudge(request())
    assert not result["ok"] and result["torque_off"]
    assert len(samples) == 5
    assert result["joints"][str(sid - 2)]["force_fault_reads"] == 3
    assert "force fault on 3 consecutive" in result["error"]
    assert len(bus.groups) == 1
    assert all(bus.limit[sid] == 700 for sid in IDS)
    assert not bus.on


def test_l4_current_between_one_and_two_amps_is_admitted_only_with_its_larger_limit(rig):
    api, bus, _clock = rig
    start_pose(bus)
    samples = active_fault(bus, 16, 69, [230] * 20)  # 1.495 A, below this knee's 2 A threshold.
    result = api.recovery_nudge(request())
    assert result["ok"] and result["torque_off"]
    assert len(samples) >= 6
    assert result["joints"]["14"]["peak_current_a"] == pytest.approx(1.495)


def test_phase_two_isolated_current_above_two_amps_waits_for_recovery_instead_of_single_sample_stop(rig):
    api, bus, _clock = rig
    start_pose(bus)
    samples = []

    def current(b):
        if len(b.groups) == 2 and 16 in b.on:
            value = 462 if not samples else 0  # 3.003 A: one force vote, then healthy.
            samples.append(value)
            return value
        return None

    bus.faults[(16, 69)] = current
    result = api.recovery_nudge(request())
    assert result["ok"] and result["torque_off"]
    assert samples == [462, 0, 0, 0]
    assert result["joints"]["14"]["force_fault_reads"] == 0


def test_pending_alternating_force_votes_cannot_admit_handoff(rig):
    api, bus, clock = rig
    start_pose(bus)
    active_fault(bus, 3, 69, [154, 0] * 100)
    start = clock.now
    result = api.recovery_nudge(request())
    assert not result["ok"] and result["torque_off"]
    assert len(bus.groups) == 1
    assert "time limit" in result["error"]
    assert 4 <= clock.now - start < 4.1


@pytest.mark.parametrize("payload", [DEFAULT_REQUEST, old_unfold_request()])
def test_existing_profiles_keep_their_single_sample_one_amp_cutoff(rig, payload):
    api, bus, _clock = rig
    if payload is not DEFAULT_REQUEST:
        start_pose(bus)
    samples = active_fault(bus, 3, 69, [154] * 10)
    result = api.recovery_nudge(payload)
    assert not result["ok"] and result["torque_off"]
    assert len(samples) == 1
    assert result["single_sample_current_limit_a"] == 1.0
    assert "hard current" in result["error"]


@pytest.mark.parametrize("joint,progress", [(1, 0), (4, 27), (17, -1)])
def test_first_phase_cannot_admit_no_insufficient_or_backward_progress(rig, joint, progress):
    api, bus, clock = rig
    homes = start_pose(bus)
    original = bus.txPacket

    def write():
        value = original()
        if len(bus.groups) == 1:
            bus.position[joint + 2] = homes[joint] + progress * JOINT_SIGN[joint] * (-1 if joint == 17 else 1)
        return value

    bus.txPacket = write
    start = clock.now
    result = api.recovery_nudge(request(magnitude=5))
    assert not result["ok"] and result["torque_off"]
    assert result["phases"][0]["progress_fractions"][str(joint)] < .5
    assert len(bus.groups) == 1
    assert 4 <= clock.now - start < 4.1


def test_achieved_plant_anchors_freeze_without_rewriting_goals_and_detect_new_collapse(rig):
    api, bus, _clock = rig
    homes = start_pose(bus)
    bus.stalled.add(16)
    original = bus.txPacket
    anchor, observations = {}, []

    def write():
        value = original()
        if len(bus.groups) == 1:
            bus.position[3] -= 36 * JOINT_SIGN[1]
            anchor["count"] = bus.position[3]
        return value

    def position(b):
        if len(b.groups) == 2 and 3 in b.on:
            observations.append(True)
            b.position[3] = anchor["count"] - len(observations) * 8 * JOINT_SIGN[1]
            return b.position[3]
        return None

    bus.txPacket = write
    bus.faults[(3, 56)] = position
    result = api.recovery_nudge(request())
    assert not result["ok"] and result["torque_off"]
    assert result["phases"][0]["settled"]
    assert len(observations) == 7
    assert "Joint 1 support_drift fault" in result["error"]
    assert set(result["achieved_support_anchors_counts"]) == {str(j) for j in MOVERS}
    assert result["achieved_support_anchors_counts"]["1"] == anchor["count"]
    assert result["joints"]["1"]["support_anchor_deg"] == count_to_deg(1, anchor["count"])
    assert result["joints"]["1"]["max_support_drift_deg"] == pytest.approx(56 / COUNTS_PER_DEG)
    assert result["joints"]["2"]["support_anchor_deg"] == count_to_deg(2, homes[2])
    assert bus.goal[3] == result["phases"][0]["target_counts"][1]
    assert not bus.on


def test_phase_two_actual_distance_must_not_exceed_thirty_from_immutable_target(rig):
    api, bus, _clock = rig
    start_pose(bus)
    original = bus.txPacket

    def write():
        value = original()
        if len(bus.groups) == 1:
            bus.position[16] += 10 * JOINT_SIGN[14]
        return value

    bus.txPacket = write
    result = api.recovery_nudge(request())
    assert not result["ok"] and result["torque_off"]
    assert result["phases"][0]["settled"] and len(bus.groups) == 1
    assert "30" in result["error"] and "actual" in result["error"]


def test_late_first_phase_and_stalled_second_respect_four_six_ten_second_bounds(rig):
    api, bus, clock = rig
    homes = start_pose(bus)
    bus.stalled.add(16)
    start = clock.now

    def position(b):
        if len(b.groups) == 1 and 3 in b.on and clock.now - start < 3.75:
            return homes[1]
        return None

    bus.faults[(3, 56)] = position
    result = api.recovery_nudge(request())
    assert not result["ok"] and result["torque_off"]
    assert len(bus.groups) == 2
    assert 3.75 <= result["phases"][1]["started_active_s"] < 4
    assert 6 <= result["phases"][1]["elapsed_s"] < 6.1
    assert 9.75 <= clock.now - start <= 10
    assert not bus.on


def test_phase_two_three_degree_settle_tolerance_is_unchanged(rig):
    api, bus, _clock = rig
    start_pose(bus)
    original = bus.txPacket

    def write():
        value = original()
        if len(bus.groups) == 2:
            bus.position[16] += 36 * JOINT_SIGN[14]
        return value

    bus.txPacket = write
    result = api.recovery_nudge(request())
    assert not result["ok"] and result["torque_off"]
    assert result["phases"][0]["settled"] and not result["phases"][1]["settled"]
    assert result["phases"][1]["elapsed_s"] >= 6


def test_preload_readback_failure_never_enables(rig):
    api, bus, _clock = rig
    start_pose(bus)
    bus.faults[(19, 42)] = lambda b: 1234
    result = api.recovery_nudge(request())
    assert not result["ok"] and result["torque_off"]
    assert not [e for e in bus.events if e[0] == "torque" and e[2]]
    assert not bus.groups and not bus.on


def test_abort_attempts_every_off_before_restore_even_when_one_off_fails(rig):
    api, bus, _clock = rig
    start_pose(bus)
    bus.after_enable = lambda sid: api.require_setup_for("/cmd", "X")
    bus.disable_fail.add(3)
    result = api.recovery_nudge(request())
    assert not result["ok"] and not result["torque_off"]
    assert not bus.groups
    assert {e[1] for e in bus.events if e[0] == "torque" and not e[2]} == set(IDS)
    assert all(bus.limit[j + 2] == (700 if j == 14 else 500) for j in JOINTS)
    assert bus.on == {3}
