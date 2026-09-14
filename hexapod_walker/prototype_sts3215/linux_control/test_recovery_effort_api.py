"""Off-robot limits for the narrowly scoped L4 knee effort profile."""
from __future__ import annotations

import pytest

from test_recovery_nudge_api import expected_target, rig  # noqa: F401


HOLDS = [10, 11, 13, 16, 17]
PROFILE = {"deltas_deg": {"14": -3}, "hold_joints": HOLDS,
           "effort_profile": "l4_30pct"}
PARTICIPANTS = (10, 11, 13, 14, 16, 17)
IDS = tuple(j + 2 for j in PARTICIPANTS)


def active_fault(bus, sid, address, values):
    """Inject fresh register readings only while that servo is enabled."""
    sequence, samples = iter(values), []

    def fault(b):
        if sid in b.on:
            value = next(sequence, 0)
            samples.append(value)
            return value
        return None

    bus.faults[(sid, address)] = fault
    return samples


@pytest.mark.parametrize("payload", [
    {**PROFILE, "effort_profile": "unbounded"},
    {**PROFILE, "effort_profile": True},
    {**PROFILE, "deltas_deg": {"14": 3}},
    {**PROFILE, "deltas_deg": {"14": -5.1}},
    {**PROFILE, "deltas_deg": {"14": float("nan")}},
    {**PROFILE, "deltas_deg": {"13": -3}},
    {**PROFILE, "deltas_deg": {"14": -3, "13": 3}},
    {**PROFILE, "deltas_deg": {}},
    {**PROFILE, "hold_joints": [10, 11, 13, 16]},
    {**PROFILE, "hold_joints": [1, 11, 13, 16, 17]},
    {**PROFILE, "hold_joints": [10, 11, 13, 16, 17, 2]},
    {"phases": [{"deltas_deg": {"14": -3}}, {"deltas_deg": {"14": -2}}],
     "hold_joints": HOLDS, "effort_profile": "l4_30pct"},
])
def test_profile_rejects_unauthorized_shapes_before_writes(rig, payload):
    api, bus, _clock = rig
    with pytest.raises(ValueError):
        api.recovery_nudge(payload)
    assert not [event for event in bus.events if event[0] != "read"]


def test_only_l4_knee_gets_higher_cap_and_all_off_precedes_restore(rig):
    api, bus, _clock = rig
    result = api.recovery_nudge({**PROFILE, "hold_joints": list(reversed(HOLDS))})
    assert result["ok"] and result["torque_off"]
    assert result["effort_profile"] == "l4_30pct"
    assert bus.groups == [{16: (expected_target(14, -3), 90, 4)}]
    first_enable = next(i for i, event in enumerate(bus.events)
                        if event[0] == "torque" and event[2])
    before = bus.events[:first_enable]
    for joint in PARTICIPANTS:
        row = result["joints"][str(joint)]
        cap = 300 if joint == 14 else 200
        assert row["saved_torque_limit"] == 700
        assert row["applied_torque_limit"] == cap
        assert row["current_soft_limit_a"] == (.5 if joint == 14 else .25)
        assert row["load_soft_limit_pct"] == (33 if joint == 14 else 23)
        assert ("limit", joint + 2, cap) in before
        assert ("position", joint + 2, 2000, 90, 4) in before
        assert ("read", joint + 2, 42) in before
    last_disable = max(i for i, event in enumerate(bus.events)
                       if event[0] == "torque" and not event[2])
    assert not [event for event in bus.events[:last_disable]
                if event[0] == "limit" and event[2] == 700]
    assert all(bus.limit[sid] == 700 for sid in IDS)
    assert not bus.on


def test_saved_lower_caps_are_never_raised_by_profile(rig):
    api, bus, _clock = rig
    bus.limit[16] = 150
    bus.limit[12] = 90
    result = api.recovery_nudge(PROFILE)
    assert result["ok"] and result["torque_off"]
    assert result["joints"]["14"]["applied_torque_limit"] == 150
    assert result["joints"]["10"]["applied_torque_limit"] == 90
    assert all(event[2] <= 150 for event in bus.events if event[:2] == ("limit", 16))
    assert all(event[2] <= 90 for event in bus.events if event[:2] == ("limit", 12))
    assert bus.limit[16] == 150 and bus.limit[12] == 90


@pytest.mark.parametrize("address,value", [(69, 62), (60, 290)])
def test_moderate_knee_effort_is_allowed_but_same_support_effort_trips(rig, address, value):
    api, bus, _clock = rig
    knee_samples = active_fault(bus, 16, address, [value] * 20)
    knee_result = api.recovery_nudge(PROFILE)
    assert knee_result["ok"] and knee_result["torque_off"]
    assert knee_samples

    support_samples = active_fault(bus, 12, address, [value] * 20)
    support_result = api.recovery_nudge(PROFILE)
    assert not support_result["ok"] and support_result["torque_off"]
    assert len(support_samples) == 3
    assert not bus.on


@pytest.mark.parametrize("address,value", [(69, 77), (60, 330)])
def test_knee_soft_effort_limit_still_requires_three_consecutive_reads(rig, address, value):
    api, bus, _clock = rig
    samples = active_fault(bus, 16, address, [value] * 20)
    result = api.recovery_nudge(PROFILE)
    assert not result["ok"] and result["torque_off"]
    assert len(samples) == 3
    assert all(bus.limit[sid] == 700 for sid in IDS)
    assert not bus.on


def test_transient_knee_force_votes_clear_before_success(rig):
    api, bus, _clock = rig
    samples = active_fault(bus, 16, 69, [77, 77, 0])
    result = api.recovery_nudge(PROFILE)
    assert result["ok"] and result["torque_off"]
    assert samples[:3] == [77, 77, 0]
    assert not bus.on


def test_profile_hard_current_remains_immediate(rig):
    api, bus, _clock = rig
    samples = active_fault(bus, 16, 69, [154] * 20)
    result = api.recovery_nudge(PROFILE)
    assert not result["ok"] and result["torque_off"]
    assert samples == [154]
    assert not bus.on


@pytest.mark.parametrize("sid", [12, 16])
def test_nonzero_status_on_knee_or_support_stops_profile(rig, sid):
    api, bus, _clock = rig
    samples = active_fault(bus, sid, 65, [1] * 20)
    result = api.recovery_nudge(PROFILE)
    assert not result["ok"] and result["torque_off"]
    assert samples == [1]
    assert not bus.on


def test_profile_keeps_three_second_deadline_and_never_returns_home(rig):
    api, bus, clock = rig
    bus.stalled.add(16)
    start = clock.now
    result = api.recovery_nudge(PROFILE)
    assert not result["ok"] and result["torque_off"]
    assert 3.0 <= clock.now - start < 3.1
    assert bus.groups == [{16: (expected_target(14, -3), 90, 4)}]
    assert bus.goal[16] == expected_target(14, -3)
    assert not bus.on


def test_profile_cleanup_failure_does_not_skip_supports_or_raise_any_limits(rig):
    api, bus, _clock = rig
    bus.disable_fail.add(16)
    result = api.recovery_nudge(PROFILE)
    assert not result["ok"] and not result["torque_off"]
    assert {event[1] for event in bus.events if event[0] == "torque" and not event[2]} == set(IDS)
    assert all(bus.limit[j + 2] == (300 if j == 14 else 200) for j in PARTICIPANTS)
    assert bus.on == {16}


def test_same_shape_without_profile_retains_default_caps_and_guards(rig):
    api, bus, _clock = rig
    samples = active_fault(bus, 16, 69, [62] * 20)
    result = api.recovery_nudge({"deltas_deg": {"14": -3}, "hold_joints": HOLDS})
    assert not result["ok"] and result["torque_off"]
    assert result["effort_profile"] == "default"
    assert len(samples) == 3
    assert all(row["applied_torque_limit"] == 200 for row in result["joints"].values())
    assert not bus.on


@pytest.mark.parametrize("delta", [-6, -10])
def test_50pct_profile_alone_allows_larger_step_and_caps_only_knee(rig, delta):
    api, bus, _clock = rig
    result = api.recovery_nudge({**PROFILE, "effort_profile": "l4_50pct",
                                 "deltas_deg": {"14": delta}})
    assert result["ok"] and result["torque_off"]
    assert result["effort_profile"] == "l4_50pct"
    assert bus.groups == [{16: (expected_target(14, delta), 90, 4)}]
    for joint in PARTICIPANTS:
        row = result["joints"][str(joint)]
        assert row["applied_torque_limit"] == (500 if joint == 14 else 200)
        assert row["current_soft_limit_a"] == (.75 if joint == 14 else .25)
        assert row["load_soft_limit_pct"] == (53 if joint == 14 else 23)
    assert all(bus.limit[sid] == 700 for sid in IDS)
    assert not bus.on


@pytest.mark.parametrize("profile", [None, "l4_30pct"])
def test_existing_profiles_still_reject_steps_over_five_degrees(rig, profile):
    api, bus, _clock = rig
    payload = {"deltas_deg": {"14": -6}, "hold_joints": HOLDS}
    if profile:
        payload["effort_profile"] = profile
    with pytest.raises(ValueError):
        api.recovery_nudge(payload)
    assert not [event for event in bus.events if event[0] != "read"]


@pytest.mark.parametrize("payload", [
    {**PROFILE, "effort_profile": "l4_60pct", "deltas_deg": {"14": -6}},
    {**PROFILE, "effort_profile": "l4_50pct", "deltas_deg": {"14": -10.1}},
    {**PROFILE, "effort_profile": "l4_50pct", "deltas_deg": {"14": 6}},
    {**PROFILE, "effort_profile": "l4_50pct", "deltas_deg": {"13": -6}},
    {**PROFILE, "effort_profile": "l4_50pct", "deltas_deg": {"14": -3, "13": 3}},
    {**PROFILE, "effort_profile": "l4_50pct", "hold_joints": [1, 11, 13, 16, 17]},
    {"effort_profile": "l4_50pct", "hold_joints": HOLDS,
     "phases": [{"deltas_deg": {"14": -3}}, {"deltas_deg": {"14": -3}}]},
    {"effort_profile": "l4_50pct", "hold_joints": HOLDS, "deltas_deg": {"14": -3},
     "phases": [{"deltas_deg": {"14": -3}}, {"deltas_deg": {"14": -3}}]},
])
def test_50pct_profile_rejects_other_shapes_before_writes(rig, payload):
    api, bus, _clock = rig
    with pytest.raises(ValueError):
        api.recovery_nudge(payload)
    assert not [event for event in bus.events if event[0] != "read"]


@pytest.mark.parametrize("address,value", [(69, 116), (60, 530)])
def test_50pct_knee_soft_limits_require_three_consecutive_reads(rig, address, value):
    api, bus, _clock = rig
    samples = active_fault(bus, 16, address, [value] * 20)
    result = api.recovery_nudge({**PROFILE, "effort_profile": "l4_50pct"})
    assert not result["ok"] and result["torque_off"]
    assert len(samples) == 3
    assert not bus.on


def test_50pct_does_not_raise_support_current_threshold(rig):
    api, bus, _clock = rig
    samples = active_fault(bus, 12, 69, [39] * 20)
    result = api.recovery_nudge({**PROFILE, "effort_profile": "l4_50pct"})
    assert not result["ok"] and result["torque_off"]
    assert len(samples) == 3
    assert result["joints"]["10"]["applied_torque_limit"] == 200
    assert not bus.on


def test_50pct_hard_current_remains_immediate(rig):
    api, bus, _clock = rig
    samples = active_fault(bus, 16, 69, [154] * 20)
    result = api.recovery_nudge({**PROFILE, "effort_profile": "l4_50pct"})
    assert not result["ok"] and result["torque_off"]
    assert samples == [154]
    assert not bus.on


def test_50pct_retains_saved_lower_cap_and_three_second_bound(rig):
    api, bus, clock = rig
    bus.limit[16] = 350
    bus.stalled.add(16)
    start = clock.now
    result = api.recovery_nudge({**PROFILE, "effort_profile": "l4_50pct",
                                 "deltas_deg": {"14": -10}})
    assert not result["ok"] and result["torque_off"]
    assert result["joints"]["14"]["applied_torque_limit"] == 350
    assert 3.0 <= clock.now - start < 3.1
    assert all(event[2] <= 350 for event in bus.events if event[:2] == ("limit", 16))
    assert bus.limit[16] == 350
    assert bus.groups == [{16: (expected_target(14, -10), 90, 4)}]
    assert not bus.on
