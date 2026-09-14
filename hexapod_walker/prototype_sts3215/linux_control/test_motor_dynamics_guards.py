"""Offline raw-boundary and cleanup mechanics for the air diagnostic."""
from types import SimpleNamespace

import pytest

import inplace_demos
import motor_dynamics
from feetech_bus import raw_degree_to_count, raw_pose_to_counts


class RawBus:
    def __init__(self):
        self.positions = [0., 0., 30.] * 6
        self.events = []
        self.on = False
        self.fault = None
        self.reads = 0

    def read_all_raw_positions(self):
        return dict(enumerate(self.positions))

    def read_raw_position_deg(self, joint):
        self.reads += 1
        if self.fault == 'read':
            raise OSError('injected read failure')
        if self.fault == 'missing_step' and self.reads > 1:
            return None
        if self.fault == 'drift' and self.reads > 1:
            return 145.
        return self.positions[joint]

    def read_raw_feedback(self, joint):
        return dict(deg=self.positions[joint], current_a=.01, load_pct=1.,
                    volt=12., temp_c=30., speed_deg_s=0.)

    def write_raw_all(self, pose, **kwargs):
        raw_pose_to_counts(pose)
        self.events.append('preload')
        if self.fault == 'preload':
            raise OSError('injected preload failure')

    def write_raw_joint(self, joint, deg, **kwargs):
        raw_degree_to_count(joint, deg)
        self.events.append(('joint', joint, deg))
        if self.fault == 'write':
            raise OSError('injected write failure')
        self.positions[joint] = deg


@pytest.fixture
def fixture(monkeypatch, tmp_path):
    monkeypatch.setenv('HEXAPOD_MODEL_SOURCE', 'sts3215')
    monkeypatch.setattr(motor_dynamics, 'LOG_DIR', tmp_path)
    bus = RawBus()
    clock = [0.]

    def monotonic():
        clock[0] += .001
        return clock[0]

    def enable(_bus, _ids):
        assert bus.events[:2] == [('limit', 350), 'preload']
        bus.events.append('enable')
        bus.on = True
        if bus.fault == 'enable':
            raise OSError('injected partial enable failure')

    def limp(_bus, _ids):
        bus.events.append('limp')
        bus.on = False

    monkeypatch.setattr(motor_dynamics, 'time', SimpleNamespace(
        monotonic=monotonic, sleep=lambda seconds: clock.__setitem__(0, clock[0] + seconds),
        strftime=lambda _fmt: 'test'))
    monkeypatch.setattr(inplace_demos, '_live_robot_ids', lambda _bus: set(range(2, 20)))
    monkeypatch.setattr(inplace_demos, '_set_torque_limit',
                        lambda _bus, _ids, value: bus.events.append(('limit', value)))
    monkeypatch.setattr(inplace_demos, '_enable_torque', enable)
    monkeypatch.setattr(inplace_demos, '_limp_all', limp)

    def run(**kwargs):
        return motor_dynamics.run_motor_dynamics(
            bus, joints=[2], full_joints=[], amp_deg=10., log_dir=tmp_path, **kwargs)

    return bus, run


@pytest.mark.parametrize('joint,start', [(2, 145.), (2, -15.), (1, 35.)])
def test_complete_extent_refused_before_any_preload_or_enable(fixture, joint, start):
    bus, _run = fixture
    bus.positions[joint] = start
    # Validate every requested joint, not only the first probed one.
    result = motor_dynamics.run_motor_dynamics(
        bus, joints=[1, 2], full_joints=[2], amp_deg=10., log_dir=None)
    assert not result['ok'] and 'extent preflight' in result['error']
    assert not bus.events and not bus.on


@pytest.mark.parametrize('fault', ['preload', 'enable', 'write', 'read', 'drift'])
def test_runtime_fault_always_limps_and_keeps_soft_limit(fixture, fault):
    bus, run = fixture
    bus.fault = fault
    with pytest.raises((OSError, ValueError)):
        run()
    assert bus.events[-1] == 'limp'
    assert not bus.on
    assert ('limit', 1000) not in bus.events


def test_three_missing_step_reads_limp_without_a_target_or_return_move(fixture):
    bus, run = fixture
    bus.fault = 'missing_step'
    result = run()
    assert result['aborted'] and not result['ok']
    assert bus.reads == 4  # one home read, then three fresh step-start attempts
    assert not any(isinstance(event, tuple) and event[0] == 'joint' for event in bus.events)
    assert not bus.on


def test_successful_probe_limps_before_restoring_limit(fixture):
    bus, run = fixture
    result = run()
    assert not result['aborted']
    assert bus.events[-2:] == ['limp', ('limit', 1000)]
    assert not bus.on
