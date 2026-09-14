"""Off-robot mechanics of the absolute-pose / relative-servo boundary."""
import csv
import struct
from types import SimpleNamespace

import pytest

from feetech_bus import (
    FeetechBus, count_to_deg, deg_to_count, robot_pose_to_raw_degrees,
    raw_positions_to_robot_degrees, raw_feedback_to_robot_feedback,
)
from mcu_feetech_bus import McuFeetechBus
from drive_controller import DriveController
from inplace_demos import PoseStreamer, _write_pose, _read_pose, _glide_speed_acc
from api.zero import ZeroApi
from motion_telemetry import MotionLog
from test_mcu_stream import _mk_bus, _fw_snapshot_frame, _fw_snapshot_payload


@pytest.fixture(autouse=True)
def model_family(monkeypatch):
    monkeypatch.setenv('HEXAPOD_MODEL_SOURCE', 'sts3215')


def pose(hip=19., knee=28.):
    return [0., hip, knee] * 6


class PacketRecorder:
    def __init__(self):
        self.writes = []
        self.sent = 0
        self.groupSyncWrite = self

    def SyncWritePosEx(self, sid, count, speed, acc):
        self.writes.append((sid, count, speed, acc))

    def WritePosEx(self, sid, count, speed, acc):
        self.writes.append((sid, count, speed, acc))
        return 0

    def txPacket(self):
        self.sent += 1

    def clearParam(self):
        pass


def recorded_bus(cls=FeetechBus):
    bus = object.__new__(cls)
    bus.trims = [0.] * 18
    bus.pkt = PacketRecorder()
    return bus


def test_pose_roundtrip_including_raw_trims_and_negative_hip():
    q = pose(-10., 30.)
    trims = [1., -2., 3.] * 6
    raw = robot_pose_to_raw_degrees(q, trims)
    assert raw[:3] == [1., -12., 43.]
    logical = raw_positions_to_robot_degrees(dict(enumerate(raw)), trims)
    assert [logical[j] for j in range(18)] == q
    assert count_to_deg(2, deg_to_count(2, 30., 0.)) == pytest.approx(30., abs=.05)


@pytest.mark.parametrize('writer', ['legacy', 'mcu', 'drive', 'demo'])
def test_full_pose_writers_command_relative_knee(writer):
    bus = recorded_bus(McuFeetechBus if writer == 'mcu' else FeetechBus)
    q = pose()
    if writer == 'drive':
        drive = DriveController(dry_run=True)
        drive.bus, drive.armed = bus, True
        drive._live_ids = lambda **kw: set(range(2, 20))
        drive._write_pose(q)
    elif writer == 'demo':
        _write_pose(bus, q, set(range(2, 20)))
    else:
        bus.write_all(q)
    assert bus.pkt.sent == 1
    assert len(bus.pkt.writes) == 18
    assert bus.pkt.writes[1][1] == deg_to_count(1, 19., 0.)
    assert bus.pkt.writes[2][1] == deg_to_count(2, 9., 0.)


@pytest.mark.parametrize('q', [pose(-78., 148.), [0.] * 17,
                              [float('nan')] + [0.] * 17])
def test_invalid_converted_pose_writes_nothing(q):
    bus = recorded_bus()
    with pytest.raises(ValueError):
        _write_pose(bus, q, set(range(2, 20)))
    assert not bus.pkt.writes and not bus.pkt.sent


def test_streamer_compensates_knee_when_absolute_tibia_stays_fixed(monkeypatch):
    monkeypatch.setattr('inplace_demos.STREAM_DENSE', False)
    bus, streamer = recorded_bus(), PoseStreamer()
    streamer.write(bus, pose(10., 30.), set(range(2, 20)))
    bus.pkt.writes.clear()
    wrote = streamer.write(bus, pose(15., 30.), set(range(2, 20)), dt=.1)
    assert 1 in wrote and 2 in wrote
    goals = {sid: count_to_deg(sid - 2, count) for sid, count, *_ in bus.pkt.writes}
    assert goals[3] == pytest.approx(15., abs=.05)
    assert goals[4] == pytest.approx(15., abs=.05)
    assert wrote[1] == wrote[2]


def test_streamer_priming_does_not_create_a_knee_step(monkeypatch):
    monkeypatch.setattr('inplace_demos.STREAM_DENSE', True)
    bus, streamer = recorded_bus(), PoseStreamer()
    streamer.prime(bus, pose(-10., 30.))
    assert streamer.write(bus, pose(-10., 30.), set(range(2, 20)), dt=.01) == {}
    assert not bus.pkt.writes


def test_glide_timing_uses_actual_hinge_displacement():
    # Hip rises 10 while tibia lowers 10: the knee servo travels 20, not 10.
    coupled = _glide_speed_acc(pose(0., 10.), pose(-10., 20.), set(range(2, 20)), 3.)
    knee_only = _glide_speed_acc(pose(0., 0.), pose(0., 20.), set(range(2, 20)), 3.)
    assert coupled == knee_only


def test_missing_hip_keeps_raw_knee_health_but_not_logical_angle():
    row = dict(deg=30., speed_deg_s=5., current_a=.2, temp_c=31, pos_counts=2389)
    got = raw_feedback_to_robot_feedback({2: row})[2]
    assert got['deg'] is None and got['speed_deg_s'] is None
    assert got['raw_deg'] == 30. and got['raw_speed_deg_s'] == 5.
    assert got['current_a'] == .2 and got['temp_c'] == 31
    complete = raw_feedback_to_robot_feedback({1: dict(deg=10., speed_deg_s=-5.), 2: row})
    assert complete[2]['deg'] == 40. and complete[2]['speed_deg_s'] == 0.
    assert row['deg'] == 30.  # The parsed raw record is not mutated.


def test_bulk_positions_replace_stale_cache_without_single_joint_fallback():
    bus = _mk_bus(b'')
    bus._pos_cache = {1: 90., 2: 120.}
    bus._bin_req = lambda *a, **k: (1, struct.pack('<BBh', 4, 1, 2389))
    bus._read_pos_counts = lambda *a: pytest.fail('must not fill a missing hip')
    assert bus.read_all_positions() == {}
    assert bus._pos_cache == {}
    assert bus.read_position_deg(2) is None


def test_snapshot_converts_position_and_velocity_and_keeps_raw():
    counts = [(3, 1, 2162, 114), (4, 1, 2276, -114)]
    bus = _mk_bus(_fw_snapshot_frame(_fw_snapshot_payload(8, 1, 1, (0,)*7, counts), 2))
    snap = bus.read_snapshot()
    assert snap['pos_deg'][2] == pytest.approx(30., abs=.1)
    assert snap['raw_pos_deg'][2] == pytest.approx(20., abs=.1)
    assert snap['speed_deg_s'][2] == 0.
    assert snap['raw_speed_deg_s'][2] < 0.


def test_bulk_feedback_keeps_present_knee_health_when_hip_drops():
    bus = _mk_bus(b'')
    bus._fb_cache = {3: dict(deg=90.)}
    bus._pos_cache = {1: 90., 2: 100.}
    # Present knee: position20deg, velocity10counts/s, load4%, 12V, 31C.
    record = struct.pack('<BBhhHBBBh', 4, 1, 2276, 10, 40, 120, 31, 1, 2)
    bus._bin_req = lambda *a, **k: (1, record)
    out = bus.read_all_feedback()
    assert out[2]['deg'] is None
    assert out[2]['raw_deg'] == pytest.approx(20., abs=.1)
    assert out[2]['current_a'] == .013 and out[2]['temp_c'] == 31
    assert bus._pos_cache == {} and set(bus._fb_cache) == {4}


def test_partial_snapshot_reports_physical_ids_separately_from_unknown_coordinates():
    bus = _mk_bus(_fw_snapshot_frame(_fw_snapshot_payload(
        8, 1, 1, (0,)*7, [(4, 1, 2276, 0)]), 1))
    snapshot = bus.read_snapshot()
    assert snapshot['pos_deg'] == {} and 2 in snapshot['raw_pos_deg']
    payload = bus._snapshot_payload(snapshot)
    assert 4 not in payload['missing_servo_ids']
    assert 2 in payload['missing_joint_coordinates']


def test_raw_packet_telemetry_does_not_mislabel_isolated_knee_as_absolute():
    bus = _mk_bus(b'')
    events = []
    bus._telemetry_sink = object()
    bus._emit_telemetry = lambda kind, payload: events.append(payload)
    bus._emit_goal_items([(4, 2276, 90, 4)], kind='joint_write', ok=True)
    assert events[0]['command_deg'][2] is None
    assert events[0]['raw_command_deg'][2] == pytest.approx(20., abs=.1)
    assert events[0]['raw_joint_frame'] == 'servo_relative'


def test_pose_readers_never_mix_bulk_sample_with_per_joint_retry():
    bus = SimpleNamespace(read_all_positions=lambda: {1: 10.},
        read_position_deg=lambda j: pytest.fail('per-joint retry mixed samples'))
    api = SimpleNamespace(drive=SimpleNamespace(bus=bus))
    values, missing = ZeroApi._present_pose18(api)
    assert values[1] == 10. and 2 in missing
    with pytest.raises(ValueError, match='missing coherent'):
        _read_pose(bus, {3, 4})


def test_hold_refuses_missing_logical_pose_without_writing():
    drive = DriveController(dry_run=True)
    drive.bus, drive.armed = recorded_bus(), True
    drive._read_present_pose = lambda: [None] * 18
    with pytest.raises(ValueError, match='coherent'):
        drive._hold_here()
    assert not drive.bus.pkt.writes


@pytest.mark.parametrize('single', [False, True])
@pytest.mark.parametrize('bad_goal', [False, True])
def test_bench_hold_preloads_and_verifies_before_enabling(monkeypatch, single, bad_goal):
    import feetech_bus

    bus = recorded_bus()
    bus.trims = [1., 2., 3.] * 6
    bus.scs = SimpleNamespace(COMM_SUCCESS=0)
    raw = pose(-30., 60.)
    logical = raw_positions_to_robot_degrees(dict(enumerate(raw)), bus.trims)
    bus.read_all_positions = lambda: logical
    bus.read_raw_position_deg = lambda j: raw[j]
    expected = {j + 2: deg_to_count(j, angle, 0.) for j, angle in enumerate(raw)}
    verified = []
    enabled = []

    def read_goal(sid, address):
        assert address == 42
        assert dict((s, count) for s, count, *_ in bus.pkt.writes)[sid] == expected[sid]
        verified.append(sid)
        return expected[sid] + int(bad_goal), 0, 0

    def torque(sid, on):
        assert on
        assert verified == ([4] if single else list(range(2, 20)))
        enabled.append(sid)

    bus.pkt.read2ByteTxRx, bus.torque = read_goal, torque
    bus.close = lambda: None
    monkeypatch.setattr(feetech_bus, 'FeetechBus', lambda *args: bus)
    action = (lambda: feetech_bus.cmd_hold(SimpleNamespace(port='', baud=0, joint=2))) if single else bus.hold_current_pose
    if bad_goal:
        with pytest.raises(RuntimeError, match='preload unverified'):
            action()
        assert not enabled
    else:
        action()
        assert enabled == ([4] if single else list(range(2, 20)))


@pytest.mark.parametrize('cls', [FeetechBus, McuFeetechBus])
def test_raw_sysid_writers_do_not_compensate_hip_or_apply_trims_twice(cls):
    bus = recorded_bus(cls)
    bus.trims = [3.] * 18
    raw = pose(-30., 60.)
    bus.write_raw_all(raw)
    assert bus.pkt.writes[2][1] == deg_to_count(2, 60., 0.)
    bus.pkt.writes.clear()
    bus.write_raw_joint(2, 60.)
    assert bus.pkt.writes == [(4, deg_to_count(2, 60., 0.), 1500, 30)]


def test_motion_log_keeps_unknown_knee_blank_and_raw_health(tmp_path):
    path = tmp_path / 'motion.csv'
    row = dict(deg=None, speed_deg_s=None, raw_deg=60., raw_speed_deg_s=1.,
               current_a=.02, load_pct=3., volt=12., temp_c=31, moving=0)
    bus = SimpleNamespace(read_all_feedback=lambda ids: {2: row})
    with MotionLog(path, {4}, names={}) as log:
        log.sample(bus, pose(-30., 30.), wrote={})
    data = list(csv.DictReader(path.open()))
    assert len(data) == 1
    assert data[0]['present_deg'] == data[0]['err_deg'] == data[0]['speed_deg_s'] == ''
    assert data[0]['raw_deg'] == '60.0' and data[0]['current_a'] == '0.020'


def test_velocity_sign_matches_raw_position_before_knee_sum(monkeypatch):
    signs = [1] * 18
    signs[1] = -1
    monkeypatch.setattr('feetech_bus.JOINT_SIGN', signs)
    monkeypatch.setattr('mcu_feetech_bus.JOINT_SIGN', signs)
    rec = struct.pack('<BBhhHBBBh', 3, 1, 2162, 114, 0, 120, 31, 1, 0)
    decoded = _mk_bus(b'')._fb_dict_from_rec(rec)
    assert decoded['deg'] < 0 and decoded['speed_deg_s'] < 0
    bus = _mk_bus(_fw_snapshot_frame(_fw_snapshot_payload(
        8, 1, 1, (0,)*7, [(3, 1, 2162, 114), (4, 1, 2276, 0)]), 2))
    snap = bus.read_snapshot()
    assert snap['pos_deg'][2] == pytest.approx(10., abs=.1)
    assert snap['speed_deg_s'][2] == pytest.approx(-10., abs=.1)
    legacy = recorded_bus()
    legacy.scs = SimpleNamespace(COMM_SUCCESS=0)
    legacy.pkt = SimpleNamespace(ReadPos=lambda sid: (2162, 0, 0),
        read2ByteTxRx=lambda sid, addr: (114 if addr == 58 else 0, 0, 0),
        read1ByteTxRx=lambda sid, addr: (120 if addr == 62 else 31, 0, 0))
    assert legacy.read_raw_feedback(1)['speed_deg_s'] == pytest.approx(-10., abs=.1)


def test_sysid_single_and_multi_joint_ticks_keep_the_same_raw_knee(monkeypatch, tmp_path):
    import sysid_runner
    import inplace_demos
    q = pose(-10., 60.)
    sent = []
    def write_all(values, *, ids=None, **kw):
        if ids is None:
            sent.append(('all', list(values)))
        q[:] = values
    def write_one(j, value, **kw):
        sent.append(('one', j, value))
        q[j] = value
    bus = SimpleNamespace(
        read_all_raw_positions=lambda: dict(enumerate(q)),
        read_all_raw_feedback=lambda: {j: dict(deg=v, current_a=0., volt=12., temp_c=31)
                                       for j, v in enumerate(q)},
        write_raw_all=write_all, write_raw_joint=write_one)
    monkeypatch.setattr(sysid_runner, 'validate', lambda p: [])
    monkeypatch.setattr(sysid_runner, 'start_pose', lambda p: None)
    monkeypatch.setattr(sysid_runner, '_telemetry_admission',
        lambda *a, **kw: (True, '', dict(samples=3, servos_per_sample=18)))
    monkeypatch.setattr(inplace_demos, '_live_robot_ids', lambda b: set(range(2, 20)))
    monkeypatch.setattr(inplace_demos, '_set_torque_limit', lambda *a: None)
    monkeypatch.setattr(inplace_demos, '_enable_torque', lambda *a: None)
    monkeypatch.setattr(sysid_runner.time, 'sleep', lambda s: None)
    delta = [0.] * 18
    delta[2] = 3.
    ticks = [dict(active=active, cmd=delta, mode='rel', seg=0, phase='test')
             for active in ([2], [1, 2])]
    monkeypatch.setattr(sysid_runner, 'materialize', lambda p:
        dict(hz=100., ticks=ticks, seg_labels=['test']))
    result = sysid_runner.run_sysid_protocol(bus,
        dict(name='raw_boundary', segments=[dict(kind='step')]), log_dir=tmp_path)
    assert result['ok'], result
    assert result['joint_frame'] == 'servo_relative'
    assert sent[0] == ('one', 2, 63.)
    assert sent[1][0] == 'all' and sent[1][1][2] == 63.
def test_http_feedback_keeps_knee_health_when_hip_angle_is_missing():
    from types import SimpleNamespace
    from api.rl import RlApi

    api = RlApi()
    api.drive = SimpleNamespace(dry_run=False, bus=SimpleNamespace(
        read_all_feedback=lambda: {2: dict(deg=None, raw_deg=35.25,
            current_a=.026, temp_c=30, load_pct=1.2, volt=12.)},
        read_imu=lambda **kwargs: None))
    api._bus_admission_error = lambda: None
    result = api.rl_feedback()
    assert result['ok'] and result['live'] == 1
    assert result['joints'][1] is None
    knee = result['joints'][2]
    assert knee['deg'] is None and knee['raw_deg'] == 35.25
    assert knee['cur_a'] == .026 and knee['temp_c'] == 30
