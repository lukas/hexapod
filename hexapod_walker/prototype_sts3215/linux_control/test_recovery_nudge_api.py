"""Off-robot tests for bounded recovery with selectively held support."""
from __future__ import annotations

import json
import math
import threading
from io import BytesIO
from types import SimpleNamespace

import pytest

import motor_setup_api
from feetech_bus import COUNTS_PER_DEG, JOINT_SIGN, STS_CENTRE_COUNT, count_to_deg
from motor_setup_api import MotorSetup


REQUEST = {"deltas_deg": {"1": -3, "2": 3}, "hold_joints": [4, 5]}
NEIGHBOR_REQUEST = {"deltas_deg": {"1": -3, "2": 3}, "hold_joints": [4, 5, 16, 17]}


class Clock:
    def __init__(self):
        self.now = 100.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class Event:
    def __init__(self, clock):
        self.clock, self.flag = clock, False

    def clear(self):
        self.flag = False

    def set(self):
        self.flag = True

    def is_set(self):
        return self.flag

    def wait(self, seconds):
        self.clock.sleep(seconds)
        return self.flag


class RawBus:
    def __init__(self):
        self.pkt = self
        self.scs = SimpleNamespace(COMM_SUCCESS=0)
        self.groupSyncWrite = self
        self.trims = [10.0] * 18  # Recovery uses raw hinges, not pose trims.
        self.position = {sid: 2000 for sid in range(2, 20)}
        self.goal = {sid: 1800 for sid in range(2, 20)}  # stale goals
        self.limit = {sid: 700 for sid in range(2, 20)}
        self.on, self.stalled = set(), set()
        self.pending, self.events, self.faults = {}, [], {}
        self.disable_fail = set()
        self.after_enable = lambda sid: None
        self.after_preload = lambda sid: None
        self.groups = []

    def scan(self, ids):
        return [sid for sid in ids if sid in self.position]

    def _read(self, sid, address):
        self.events.append(("read", sid, address))
        fault = self.faults.get((sid, address))
        if fault is not None:
            value = fault(self)
            if value is not None:
                return value if isinstance(value, tuple) else (value, 0, 0)
        value = {40: int(sid in self.on), 42: self.goal[sid],
                 48: self.limit[sid], 56: self.position[sid],
                 19: 44, 28: 500, 33: 0, 34: 20, 35: 50, 36: 80,
                 60: 0, 69: 0, 62: 114, 63: 30, 65: 0, 66: 0}[address]
        return value, 0, 0

    read1ByteTxRx = read2ByteTxRx = _read

    def write2ByteTxRx(self, sid, address, value):
        assert address == 48
        self.events.append(("limit", sid, value))
        self.limit[sid] = value
        return 0, 0, 0

    def WritePosEx(self, sid, target, speed, acc):
        self.events.append(("position", sid, target, speed, acc))
        self.goal[sid] = target
        if sid in self.on and sid not in self.stalled:
            self.position[sid] = target
        self.after_preload(sid)
        return 0

    def SyncWritePosEx(self, sid, target, speed, acc):
        self.pending[sid] = (target, speed, acc)
        self.events.append(("queue", sid, target, speed, acc))

    def txPacket(self):
        self.groups.append(dict(self.pending))
        self.events.append(("group", dict(self.pending)))
        for sid, (target, _speed, _acc) in self.pending.items():
            self.goal[sid] = target
            if sid in self.on and sid not in self.stalled:
                self.position[sid] = target
        return 0

    def clearParam(self):
        self.pending.clear()

    def torque(self, sid, on):
        self.events.append(("torque", sid, on))
        if on:
            self.on.add(sid)
            self.after_enable(sid)
        elif sid in self.disable_fail:
            raise RuntimeError(f"servo {sid} torque-off write failed")
        else:
            self.on.discard(sid)


@pytest.fixture
def rig(tmp_path, monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "sts3215")
    clock, bus = Clock(), RawBus()
    monkeypatch.setattr(motor_setup_api, "time", clock)
    drive = SimpleNamespace(bus=bus, dry_run=False, armed=False,
                            _lock=threading.RLock())
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"servos": {
        str(j + 2): {"id": j + 2, "joint": j} for j in range(18)}}))
    api = MotorSetup(drive, SimpleNamespace(_demo_thread=None), registry)
    api.abort = Event(clock)
    return api, bus, clock


def expected_target(joint, delta):
    return 2000 + math.trunc(delta * COUNTS_PER_DEG * JOINT_SIGN[joint])


@pytest.mark.parametrize('payload', [REQUEST, NEIGHBOR_REQUEST])
def test_recovery_preloads_all_before_enabling_and_only_groups_deltas(rig, payload):
    api, bus, _clock = rig
    bus.limit[6] = 90
    joints = (1, 2, *payload['hold_joints'])
    ids = tuple(j + 2 for j in joints)
    result = api.recovery_nudge(payload)
    assert result["ok"] and result["torque_off"]
    assert result["joint_frame"] == "servo_relative"
    assert set(result["joints"]) == {str(j) for j in joints}
    first_enable = next(i for i, event in enumerate(bus.events)
                        if event[0] == "torque" and event[2])
    before = bus.events[:first_enable]
    assert all(("read", sid, 40) in before for sid in range(2, 20))
    for sid in ids:
        assert all(('read', sid, address) in before for address in (19, 28, 33, 34, 35, 36))
        assert ("position", sid, 2000, 90, 4) in before
        assert ("limit", sid, 90 if sid == 6 else 200) in before
        preload = before.index(("position", sid, 2000, 90, 4))
        assert ("read", sid, 42) in before[preload + 1:]
        limit = before.index(("limit", sid, 90 if sid == 6 else 200))
        assert ("read", sid, 48) in before[limit + 1:]
    assert bus.groups == [{3: (expected_target(1, -3), 90, 4),
                           4: (expected_target(2, 3), 90, 4)}]
    assert [event for event in bus.events if event[0] == "position"] == [
        ("position", sid, 2000, 90, 4) for sid in ids]
    assert {event[1] for event in bus.events if event[0] == "torque"} == set(ids)
    assert all(bus.position[j + 2] == 2000 for j in payload['hold_joints'])
    assert result["joints"]["2"]["target_deg"] == pytest.approx(
        count_to_deg(2, expected_target(2, 3)))
    assert not bus.on
    last_disable = max(i for i, event in enumerate(bus.events)
                       if event[0] == "torque" and not event[2])
    assert all(event[2] <= 200 for event in bus.events[:last_disable]
               if event[0] == "limit")
    assert all(bus.limit[sid] == 700 for sid in ids if sid != 6)
    assert bus.limit[6] == 90
    for joint in joints:
        row = result["joints"][str(joint)]
        assert row["saved_torque_limit"] == (90 if joint == 4 else 700)
        assert row["applied_torque_limit"] == (90 if joint == 4 else 200)
        assert row['protection_config'] == dict(
            unload_mask=44, current_protection_raw=500, mode=0,
            protection_torque_raw=20, protection_time_raw=50, overload_torque_raw=80)


@pytest.mark.parametrize('holds', [[4, 5], [4, 5, 16, 17]])
def test_support_only_is_bounded_and_does_not_send_movement(rig, holds):
    api, bus, clock = rig
    start = clock.now
    result = api.recovery_nudge({"deltas_deg": {}, "hold_joints": holds})
    assert result["ok"] and result["torque_off"]
    assert 1.0 <= clock.now - start < 2.0
    assert not bus.groups
    assert set(result["joints"]) == {str(j) for j in holds}
    assert not bus.on


def test_l5_bounded_placement_uses_raw_pitch_targets_only(rig):
    api, bus, _clock = rig
    result = api.recovery_nudge({'deltas_deg': {'16': -2, '17': 2}, 'hold_joints': [4, 5]})
    assert result['ok'] and result['torque_off']
    assert bus.groups == [{18: (expected_target(16, -2), 90, 4),
                           19: (expected_target(17, 2), 90, 4)}]
    assert bus.position[6] == bus.position[7] == 2000
    assert not bus.on


def add_active_read_latency(bus, clock, *, bad_register=None):
    """24ms reads; an injected bad read expires the next partial scan."""
    original = bus._read
    active_start = []
    active_reads = []
    bad_register_reads = 0
    bus.after_enable = lambda sid: active_start.append(clock.now) if not active_start else None

    def read(sid, address):
        nonlocal bad_register_reads
        if bus.on:
            clock.sleep(.024)
            elapsed = clock.now - active_start[0]
            if sid == 6 and address == bad_register:
                bad_register_reads += 1
                if bad_register_reads == 2:
                    # One complete healthy active scan precedes this fault.
                    clock.now = max(clock.now, active_start[0] + .999)
                    elapsed = clock.now - active_start[0]
            active_reads.append((sid, address, elapsed))
            if sid == 6 and address == bad_register and bad_register_reads == 2:
                return (39 if address == 69 else 80), 0, 0
        return original(sid, address)

    bus.read1ByteTxRx = bus.read2ByteTxRx = read
    return active_reads


def test_hold_deadline_mid_healthy_scan_releases_without_extending_hold(rig):
    api, bus, clock = rig
    active_reads = add_active_read_latency(bus, clock)
    result = api.recovery_nudge({"deltas_deg": {}, "hold_joints": [4, 5]})
    assert result["ok"] and result["torque_off"]
    assert 1.0 <= result["active_seconds"] <= 1.0241
    assert active_reads[-1][1] != 56  # The final scan was incomplete.
    assert sum(sid == 7 and address == 56 for sid, address, _ in active_reads) >= 1
    assert not bus.on and not bus.groups


@pytest.mark.parametrize("bad_register,field,value", [(69, "current_a", .2535),
                                                       (62, "voltage_v", 8.0)])
def test_hold_deadline_after_partial_bad_health_cannot_claim_success(rig, bad_register, field, value):
    api, bus, clock = rig
    active_reads = add_active_read_latency(bus, clock, bad_register=bad_register)
    result = api.recovery_nudge({"deltas_deg": {}, "hold_joints": [4, 5]})
    assert not result["ok"] and result["torque_off"]
    assert 1.0 <= result["active_seconds"] <= 1.0241
    assert result["joints"]["4"][field] == pytest.approx(value)
    assert active_reads[-1][1] != 56
    assert not bus.on and not bus.groups


@pytest.mark.parametrize("data", [
    {"deltas_deg": {}, "hold_joints": []},
    {"deltas_deg": {"0": 1}, "hold_joints": []},
    {"deltas_deg": {"15": 1}, "hold_joints": []},
    {"deltas_deg": {"7": 1}, "hold_joints": []},
    {"deltas_deg": {}, "hold_joints": [1, 2, 4, 5, 16, 17, 15]},
    {"deltas_deg": {"1": 5.1}, "hold_joints": []},
    {"deltas_deg": {"1": True}, "hold_joints": []},
    {"deltas_deg": {"1": float("nan")}, "hold_joints": []},
    {"deltas_deg": {"1": 1, "2": 1, "4": 1}, "hold_joints": []},
    {"deltas_deg": {"1": 1}, "hold_joints": [1]},
    {"deltas_deg": {}, "hold_joints": [4, 4]},
    {"deltas_deg": {}, "hold_joints": [True]},
    {"deltas_deg": {"1": 1}, "hold_joints": [], "torque": 1000},
])
def test_invalid_request_never_writes(rig, data):
    api, bus, _clock = rig
    with pytest.raises(ValueError):
        api.recovery_nudge(data)
    assert not [event for event in bus.events if event[0] != "read"]


def test_unrelated_motor_on_refuses_before_any_write(rig):
    api, bus, _clock = rig
    bus.on.add(19)
    with pytest.raises(ValueError):
        api.recovery_nudge(REQUEST)
    assert not [event for event in bus.events if event[0] != "read"]


def test_raw_start_or_target_outside_physical_limits_never_writes(rig):
    api, bus, _clock = rig
    bus.position[3] = round(STS_CENTRE_COUNT + 39 * COUNTS_PER_DEG * JOINT_SIGN[1])
    with pytest.raises(ValueError):
        api.recovery_nudge({"deltas_deg": {"1": 5}, "hold_joints": [4, 5]})
    assert not [event for event in bus.events if event[0] != "read"]


@pytest.mark.parametrize("bad_register", [42, 48])
def test_unverified_preload_or_limit_never_enables(rig, bad_register):
    api, bus, _clock = rig
    bus.faults[(7, bad_register)] = lambda b: 999
    result = api.recovery_nudge(REQUEST)
    assert not result["ok"]
    assert not [event for event in bus.events if event[0] == "torque" and event[2]]
    assert not bus.groups


def test_sync_target_must_be_read_back_from_moving_servo(rig):
    api, bus, _clock = rig
    original = bus.txPacket
    def drop_target():
        original()
        bus.goal[3] = 2000
        return 0  # Bridge ACK alone does not establish servo acceptance.
    bus.txPacket = drop_target
    result = api.recovery_nudge(REQUEST)
    assert not result['ok'] and result['torque_off']
    assert 'target not accepted' in result['error']
    assert result['joints']['1']['accepted_goal_counts'] == 2000
    assert len(bus.groups) == 1 and not bus.on


@pytest.mark.parametrize('address,value,message,field', [
    (40, 0, 'torque unexpectedly off', 'torque_enabled'),
    (42, 2001, 'goal changed', 'observed_goal_counts'),
    (48, 201, 'torque limit changed', 'observed_torque_limit'),
])
@pytest.mark.parametrize('joint', [1, 4])
def test_active_command_mutation_stops_without_reenable_or_rewrite(rig, address, value, message, field, joint):
    api, bus, _clock = rig
    sid = joint + 2
    reads = []
    def fault(b):
        if b.groups:
            reads.append(True)
            # Goal's first read verifies the synchronized target. Corrupt
            # the following ACTIVE observation to model a later rewrite.
            if address != 42 or joint == 4 or len(reads) >= 2:
                if address == 40:
                    b.on.discard(sid)
                return value
        return None
    bus.faults[(sid, address)] = fault
    bus.faults[(sid, 65)] = lambda b: 32 if b.groups else None
    result = api.recovery_nudge(REQUEST)
    row = result['joints'][str(joint)]
    assert not result['ok'] and result['torque_off']
    assert message in result['error']
    assert row[field] == value
    assert row['servo_status'] == 32 and row['seen_statuses'] == [32]
    assert row['last_sample_monotonic_s'] is not None and row['active_sample_s'] >= 0
    assert len(bus.groups) == 1 and not bus.on
    assert [e for e in bus.events if e[0] == 'torque' and e[2]] == [
        ('torque', sid, True) for sid in (3, 4, 6, 7)]
    assert len([e for e in bus.events if e[0] == 'position']) == 4


def test_active_status_history_and_accepted_goals_are_retained(rig):
    api, bus, _clock = rig
    statuses, forces = iter([0, 8]), iter([39, 0])
    bus.faults[(3, 65)] = lambda b: next(statuses, 8) if b.groups else None
    bus.faults[(3, 69)] = lambda b: next(forces, 0) if b.groups else None
    bus.faults[(3, 66)] = lambda b: 1 if b.groups else None
    result = api.recovery_nudge(REQUEST)
    row = result['joints']['1']
    assert result['ok'] and result['torque_off']
    assert row['seen_statuses'] == [0, 8] and row['servo_status'] == 8
    assert row['moving'] == row['torque_enabled'] == 1
    assert row['active_sample_s'] == pytest.approx(.05)
    assert row['accepted_goal_counts'] == row['observed_goal_counts'] == expected_target(1, -3)
    assert row['observed_torque_limit'] == row['applied_torque_limit'] == 200


def test_abort_during_enable_prevents_movement_and_cleans_every_participant(rig):
    api, bus, _clock = rig
    bus.after_enable = lambda sid: api.require_setup_for("/cmd", "X")
    result = api.recovery_nudge(REQUEST)
    assert not result["ok"] and result["torque_off"]
    assert not bus.groups
    assert not bus.on
    assert {event[1] for event in bus.events
            if event[0] == "torque" and not event[2]} == {3, 4, 6, 7}


@pytest.mark.parametrize("address,value", [(69, 39), (60, 230), (62, 80), (63, 60)])
def test_three_consecutive_faults_on_support_limp_all(rig, address, value):
    api, bus, _clock = rig
    samples = []

    def fault(b):
        if 6 in b.on:
            samples.append(value)
            return value
        return None

    bus.faults[(6, address)] = fault
    result = api.recovery_nudge(REQUEST)
    assert not result["ok"] and result["torque_off"]
    assert len(samples) >= 3
    assert not bus.on


def test_hard_current_aborts_on_first_sample(rig):
    api, bus, _clock = rig
    samples = []

    def fault(b):
        if 6 in b.on:
            samples.append(154)
            return 154
        return None

    bus.faults[(6, 69)] = fault
    result = api.recovery_nudge(REQUEST)
    assert not result["ok"] and result["torque_off"]
    assert len(samples) == 1
    assert not bus.on


def test_three_missing_feedback_attempts_stop_and_clean_all_participants(rig):
    api, bus, _clock = rig
    attempts = []

    def fault(b):
        if 6 in b.on:
            attempts.append(True)
            return (0, -1, 0)
        return None

    bus.faults[(6, 69)] = fault
    result = api.recovery_nudge(REQUEST)
    assert not result["ok"] and result["torque_off"]
    assert len(attempts) == 3
    assert not bus.on


def test_pending_fault_votes_delay_success_then_reset(rig):
    api, bus, _clock = rig
    sequence, samples = iter([39, 39, 0]), []

    def fault(b):
        if 6 in b.on:
            value = next(sequence, 0)
            samples.append(value)
            return value
        return None

    bus.faults[(6, 69)] = fault
    result = api.recovery_nudge(REQUEST)
    assert result["ok"] and result["torque_off"]
    assert samples[:3] == [39, 39, 0]
    assert not bus.on


def test_support_drift_is_guarded_even_when_moving_joint_reaches_goal(rig):
    api, bus, _clock = rig
    samples = []

    def fault(b):
        if 6 in b.on:
            samples.append(2048)
            return 2048  # 4.2 degrees from held current position.
        return None

    bus.faults[(6, 56)] = fault
    result = api.recovery_nudge(REQUEST)
    assert not result["ok"] and result["torque_off"]
    assert len(samples) >= 3
    assert not bus.on


def test_nontracking_motor_times_out_without_returning_home(rig):
    api, bus, clock = rig
    bus.stalled.add(3)
    start = clock.now
    result = api.recovery_nudge({"deltas_deg": {"1": -3}, "hold_joints": [4, 5]})
    assert not result["ok"] and result["torque_off"]
    assert 3.0 <= clock.now - start < 4.0
    assert len(bus.groups) == 1
    assert bus.goal[3] == expected_target(1, -3)
    assert not bus.on


@pytest.mark.parametrize("delta,hard", [(2, False), (3, True)])
@pytest.mark.parametrize("hip", [1, 4, 16])
def test_pair_guard_detects_one_joint_stuck_despite_compensating_targets(rig, delta, hard, hip):
    api, bus, clock = rig
    bus.stalled.add(hip + 2)
    start = clock.now
    supports = [4, 5] if hip != 4 else [16, 17]
    result = api.recovery_nudge({"deltas_deg": {str(hip): -delta, str(hip + 1): delta},
                                 "hold_joints": supports})
    assert not result["ok"] and result["torque_off"]
    assert result["max_pair_error_deg"] > (2.5 if hard else 1.5)
    if not hard:
        assert result["pair_fault_reads"] >= 3
    assert clock.now - start < 3.0
    assert not bus.on


@pytest.mark.parametrize('payload', [REQUEST, NEIGHBOR_REQUEST])
def test_one_failed_disable_does_not_skip_others_or_restore_high_limits(rig, payload):
    api, bus, _clock = rig
    bus.disable_fail.add(3)
    ids = {3, 4, *(j + 2 for j in payload['hold_joints'])}
    result = api.recovery_nudge(payload)
    assert not result["ok"] and not result["torque_off"]
    assert {event[1] for event in bus.events
            if event[0] == "torque" and not event[2]} == ids
    assert bus.on == {3}
    assert all(bus.limit[sid] <= 200 for sid in ids)


def test_unverified_torque_off_keeps_every_limit_low(rig):
    api, bus, _clock = rig

    def fault(b):
        if any(event == ("torque", 3, False) for event in b.events):
            return 1  # Even an acknowledged OFF command needs readback.
        return None

    bus.faults[(3, 40)] = fault
    result = api.recovery_nudge(REQUEST)
    assert not result["ok"] and not result["torque_off"]
    assert all(bus.limit[sid] <= 200 for sid in (3, 4, 6, 7))


def test_route_dispatch_and_quarantine(monkeypatch):
    import web_drive

    calls = []
    setup = SimpleNamespace(require_setup_for=lambda *args: None,
                            recovery_nudge=lambda data: calls.append(data) or {"ok": True})
    monkeypatch.setattr(web_drive, "SETUP", setup)

    def request(quarantined):
        handler = web_drive.Handler.__new__(web_drive.Handler)
        data = json.dumps(REQUEST).encode()
        handler.path = "/api/setup/recovery_nudge"
        handler.command = "POST"
        handler.headers = {"Content-Length": str(len(data))}
        handler.rfile, handler._peer = BytesIO(data), lambda: "test"
        responses = []
        handler._json = lambda code, obj, **kw: responses.append((code, obj))
        monkeypatch.setattr(web_drive, "BENCH", SimpleNamespace(
            bus_access_state=lambda **kw: {"bus_quarantined": True} if quarantined else None))
        handler.do_POST()
        return responses

    assert request(False) == [(200, {"ok": True})]
    assert calls == [REQUEST]
    assert request(True)[0][0] == 503
    assert calls == [REQUEST]
