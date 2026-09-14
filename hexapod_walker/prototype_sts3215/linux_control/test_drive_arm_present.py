"""Motor-free ordering tests for re-arming a limp robot with stale goals."""
import threading

import pytest

from drive_controller import DriveController


class ArmBus:
    def __init__(self):
        self.pkt = self
        self.trims = [25.0] * 18  # must never affect a raw present hold
        self.positions = {sid: 1100 + 23 * sid for sid in range(2, 20)}
        self.goals = {sid: 3900 for sid in self.positions}  # stale targets
        self.limits = {sid: 1000 for sid in self.positions}
        self.on = set()
        self.writes = []
        self.fail_position = None
        self.fail_preload = None
        self.bad_limit = None
        self.abort_after_enable = None
        self.abort = threading.Event()

    def read1ByteTxRx(self, sid, address):
        assert address == 40
        return int(sid in self.on), 0, 0

    def read2ByteTxRx(self, sid, address):
        if address == 56 and sid == self.fail_position:
            return 0, -1, 0
        return {56: self.positions, 42: self.goals, 48: self.limits}[address][sid], 0, 0

    def write2ByteTxRx(self, sid, address, value):
        assert address == 48
        self.writes.append(('limit', sid, value))
        if sid != self.bad_limit:
            self.limits[sid] = value
        return 0, 0, 0

    def WritePosEx(self, sid, value, speed, acc):
        self.writes.append(('goal', sid, value))
        assert (speed, acc) == (90, 4)
        if sid == self.fail_preload:
            return -1
        self.goals[sid] = value
        return 0

    def torque(self, sid, on):
        self.writes.append(('torque', sid, on))
        if on:
            # No servo may energize before every old goal was replaced.
            assert self.goals == self.positions
            assert all(limit < 1000 for limit in self.limits.values())
            self.on.add(sid)
            if sid == self.abort_after_enable:
                self.abort.set()
        else:
            self.on.discard(sid)


@pytest.fixture
def drive(monkeypatch):
    monkeypatch.setenv('HEXAPOD_MODEL_SOURCE', 'sts3215')
    result = DriveController(dry_run=False)
    result.bus = ArmBus()
    return result


def test_arm_preloads_every_raw_count_and_limit_before_first_enable(drive):
    drive.arm_at_present(450)
    writes = drive.bus.writes
    assert [w[0] for w in writes] == ['limit'] * 18 + ['goal'] * 18 + ['torque'] * 18
    assert drive.bus.goals == drive.bus.positions
    assert drive.bus.on == set(range(2, 20))
    assert drive.armed


def test_arm_command_uses_present_hold_and_is_idempotent_when_armed(drive):
    assert drive.handle('ARM') == 'armed'  # nested control lock must not deadlock
    assert set(drive.bus.limits.values()) == {450}
    before = list(drive.bus.writes)
    assert drive.handle('ARM') == 'armed'
    assert drive.bus.writes == before


def test_dry_run_arm_keeps_its_existing_no_bus_behavior(monkeypatch):
    monkeypatch.setenv('HEXAPOD_MODEL_SOURCE', 'sts3215')
    drive = DriveController(dry_run=True)
    assert drive.bus is None
    assert drive.handle('ARM') == 'armed'
    assert drive.armed


@pytest.mark.parametrize('fault', ['fail_position', 'fail_preload', 'bad_limit'])
def test_partial_preparation_failure_never_enables_any_servo(drive, fault):
    setattr(drive.bus, fault, 8)
    with pytest.raises(RuntimeError):
        drive.arm_at_present(450)
    assert not any(w[0] == 'torque' and w[2] for w in drive.bus.writes)
    assert drive.bus.writes[-18:] == [('torque', sid, False) for sid in range(2, 20)]
    assert not drive.bus.on
    assert not drive.armed
    assert 'torque off verified' in drive.status


def test_abort_during_enable_disables_even_partially_armed_bus(drive):
    drive.bus.abort_after_enable = 2
    with pytest.raises(RuntimeError, match='aborted'):
        drive.arm_at_present(450, abort_check=drive.bus.abort.is_set)
    assert [w for w in drive.bus.writes if w[0] == 'torque' and w[2]] == [('torque', 2, True)]
    assert not drive.bus.on
    assert not drive.armed


def test_abort_before_preload_never_enables(drive):
    drive.bus.abort.set()
    with pytest.raises(RuntimeError, match='aborted'):
        drive.arm_at_present(450, abort_check=drive.bus.abort.is_set)
    assert drive.bus.writes == [('torque', sid, False) for sid in range(2, 20)]


def test_disarmed_flag_does_not_override_a_servo_still_enabled(drive):
    drive.bus.on.add(19)
    with pytest.raises(RuntimeError, match='not off'):
        drive.arm_at_present(450)
    assert not drive.bus.on
    assert not any(w[0] == 'goal' for w in drive.bus.writes)


def test_failed_cleanup_reports_unverified_torque(drive):
    drive.bus.abort_after_enable = 2
    original = drive.bus.torque
    drive.bus.torque = lambda sid, on: original(sid, on) if on else None
    with pytest.raises(RuntimeError, match='torque-off unverified'):
        drive.arm_at_present(450, abort_check=drive.bus.abort.is_set)
    assert not drive.armed
    assert drive.bus.on == {2}
    assert 'torque state unverified' in drive.status


def test_standup_arm_failure_does_not_restore_full_torque(drive, monkeypatch):
    import inplace_demos
    from bench_api import BenchAPI

    drive.bus.fail_preload = 8
    api = BenchAPI(drive)
    monkeypatch.setattr(api, '_load_standup', lambda: {'modes': {'step': {
        'keyframes': [{'q_deg': [0.0] * 18, 's': 1.0}]}}})
    monkeypatch.setattr(inplace_demos, '_live_robot_ids', lambda _bus: set(range(2, 20)))
    limit_restores = []
    monkeypatch.setattr(inplace_demos, '_set_torque_limit',
                        lambda _bus, _ids, value: limit_restores.append(value))
    result = api.standup(force=True, torque=450, sync_gen=api._demo_gen)
    assert not result['ok']
    assert 'preload failed' in api._cal_result['error']
    assert limit_restores == []
    assert not drive.bus.on
    assert not drive.armed
