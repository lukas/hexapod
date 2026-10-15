"""Leased pose ownership mechanics; no physical IO, sleeps, or worker races."""
from contextlib import contextmanager, nullcontext
import threading
from types import SimpleNamespace

import pytest

from api import gamepad_pose as pose_api
from hexapod_core.joint_frame import N_JOINTS, SERVO_IDS
import inplace_demos as demos


def snapshot(positions=None, *, age=1):
    positions = [float(i + 1) for i in range(N_JOINTS)] if positions is None else positions
    return {"pos_deg": dict(enumerate(positions)), "pos_age_ms": age}


class ParkedThread:
    def __init__(self, *, target, args, daemon):
        self.target, self.args = target, args
        self.alive = False

    def start(self):
        self.alive = True

    def is_alive(self):
        return self.alive

    def run(self):
        try:
            self.target(*self.args)
        finally:
            self.alive = False


@pytest.fixture(autouse=True)
def robot_model(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "sts3215")


@pytest.fixture
def rig(monkeypatch):
    monkeypatch.setattr(pose_api.threading, "Thread", ParkedThread)
    now = [100.0]
    calls = []
    drive = SimpleNamespace(
        _lock=threading.Lock(), _gamepad_token=None, _gamepad_settle_until=None,
        mode="idle", dry_run=False,
        bus=SimpleNamespace(read_snapshot=lambda: snapshot(),
                            enable_all_torque=lambda enabled: calls.append(("torque", enabled))), armed=False,
        gait=SimpleNamespace(stop=lambda: calls.append(("gait_stop",))),
        _torque_all=lambda enabled: calls.append(("torque", enabled)),
        _write_pose=lambda positions, **kwargs: calls.append(("write", list(positions), kwargs)),
    )
    def command(line):
        calls.append(("command", line))
        drive.armed = False
        drive.mode = "idle"
    drive._handle_locked = command
    bench = SimpleNamespace(
        drive=drive, _demo_thread=None, _demo_gen=0, _demo_abort=threading.Event(),
        _drive_active=lambda: False,
        _bus_hot_begin=lambda: None, _bus_hot_end=lambda: None,
        _acquire_start=lambda *args, **kwargs: {"ok": True},
        standup=lambda **kwargs: {"ok": True},
    )
    manager = pose_api.GamepadPose(bench, clock=lambda: now[0])
    return SimpleNamespace(manager=manager, bench=bench, drive=drive, now=now, calls=calls)


def prepare(rig, pose="stand"):
    response = rig.manager.request({"action": "prepare", "pose": pose})
    assert response["ok"] and response["state"] == "prepared"
    return response["token"]


def request(rig, action, token):
    return rig.manager.request({"action": action, "token": token})


def start(rig, pose="stand"):
    """Reserve and launch a parked worker; each test decides when it runs."""
    token = prepare(rig, pose)
    assert request(rig, "renew", token)["state"] == "running"
    return token


def test_prepare_is_motion_free_and_token_exclusive(rig):
    token = prepare(rig)
    assert rig.calls == [] and not rig.drive.armed
    assert rig.bench._demo_thread is None
    assert not rig.manager.request({"action": "prepare", "pose": "stand"})["ok"]
    assert not request(rig, "renew", "someone-else")["ok"]
    assert rig.manager.job["token"] == token


@pytest.mark.parametrize("state", ["walk", "demo"])
def test_prepare_rejects_active_drive_mode(rig, state):
    rig.drive.mode = state
    assert not rig.manager.request({"action": "prepare", "pose": "stand"})["ok"]
    assert rig.calls == []


@pytest.mark.parametrize("blocked", ["lease", "settling", "worker", "rl", "no_bus", "dry_run"])
def test_prepare_rejects_existing_owner_or_unavailable_bus(rig, blocked):
    target, attribute, value = {
        "lease": (rig.drive, "_gamepad_token", "other"),
        "settling": (rig.drive, "_gamepad_settle_until", 101),
        "worker": (rig.bench, "_demo_thread", SimpleNamespace(is_alive=lambda: True)),
        "rl": (rig.bench, "_drive_active", lambda: True),
        "no_bus": (rig.drive, "bus", None),
        "dry_run": (rig.drive, "dry_run", True),
    }[blocked]
    setattr(target, attribute, value)
    assert not rig.manager.request({"action": "prepare", "pose": "stand"})["ok"]
    assert rig.calls == []


def test_sit_never_arms_an_unarmed_robot(rig):
    assert not rig.manager.request({"action": "prepare", "pose": "sit"})["ok"]
    assert rig.calls == []


@pytest.mark.parametrize("stop", ["stop", "expire"])
def test_reservation_cannot_launch_after_stop_or_expiry(rig, stop):
    token = prepare(rig)
    if stop == "stop":
        request(rig, "stop", token)
    else:
        rig.now[0] += pose_api.GAMEPAD_LEASE_TIMEOUT_S
    result = request(rig, "renew", token)
    assert result["state"] == "error"
    assert rig.manager.job["thread"] is None
    assert rig.calls == []


def test_deadline_expiration_is_sticky_even_if_clock_or_late_renew_changes(rig):
    abort = pose_api.DeadlineAbort(lambda: rig.now[0])
    rig.now[0] += pose_api.GAMEPAD_LEASE_TIMEOUT_S
    assert abort.wait(0)
    rig.now[0] -= 0.5
    assert not abort.renew() and abort.is_set()


def test_renew_during_wait_preserves_the_full_requested_dwell(monkeypatch):
    now, waits = [0.0], []
    abort = pose_api.DeadlineAbort(lambda: now[0])
    def wait(event, timeout):
        waits.append(timeout)
        if len(waits) == 1:
            now[0] = 0.5
            assert abort.renew()
            now[0] = 0.75
        else:
            now[0] += timeout
        return False
    monkeypatch.setattr(threading.Event, "wait", wait)
    assert not abort.wait(1.2)
    assert waits == pytest.approx([0.75, 0.45])
    assert now[0] == pytest.approx(1.2)


@pytest.mark.parametrize("reason", ["stop", "estop"])
def test_cancel_before_delayed_worker_launch_prevents_torque_enable(rig, reason):
    token = start(rig)
    if reason == "stop":
        request(rig, "stop", token)
        assert request(rig, "renew", token)["state"] == "stopping"
    else:
        rig.bench._demo_gen += 1
        rig.drive.armed = False
    assert not rig.manager.request({"action": "prepare", "pose": "stand"})["ok"]
    rig.manager.job["thread"].run()
    assert rig.calls == [] and not rig.drive.armed
    assert rig.manager.job["state"] == "error"


def test_failed_initial_bulk_arm_issues_limp_without_per_joint_enable_retry(rig):
    start(rig)
    def failed_arm(enabled):
        assert enabled
        rig.calls.append(("failed_bulk_arm",))
        raise TimeoutError("TA enable ACK lost")
    rig.drive.bus.enable_all_torque = failed_arm
    rig.manager.job["thread"].run()
    assert rig.calls == [("failed_bulk_arm",), ("command", "X")]
    assert not rig.drive.armed
    assert rig.manager.job["state"] == "error"


@pytest.mark.parametrize("reason", ["stop", "expire"])
def test_cancel_during_worker_keeps_exclusion_until_measured_hold_finishes(rig, reason):
    token = start(rig)
    def move(*args, **kwargs):
        if reason == "stop":
            request(rig, "stop", token)
        else:
            rig.now[0] += pose_api.GAMEPAD_LEASE_TIMEOUT_S
        assert request(rig, "renew", token)["state"] == "stopping"
        assert not rig.manager.request({"action": "prepare", "pose": "stand"})["ok"]
        return {"ok": True}  # Cancellation must override a late success result.
    def read_pose():
        # Position reads run without holding the plain drive lock.
        assert rig.drive._lock.acquire(blocking=False)
        rig.drive._lock.release()
        assert rig.manager.busy_locked()
        assert not rig.manager.request({"action": "prepare", "pose": "stand"})["ok"]
        return snapshot()
    rig.bench._acquire_start = move
    rig.drive.bus.read_snapshot = read_pose
    rig.manager.job["thread"].run()
    writes = [call for call in rig.calls if call[0] == "write"]
    assert writes == [("write", [float(i + 1) for i in range(N_JOINTS)], {"speed": 250, "acc": 30})]
    assert rig.drive.mode == "idle"
    assert rig.manager.job["result"]["aborted"]
    assert not rig.manager.job["result"]["ok"]


@pytest.mark.parametrize("feedback", [
    pytest.param(snapshot([1.0] * (N_JOINTS - 1)), id="missing-joint"),
    pytest.param(snapshot([None] + [1.0] * (N_JOINTS - 1)), id="missing-value"),
    pytest.param(snapshot([float("nan")] + [1.0] * (N_JOINTS - 1)), id="nonfinite"),
    pytest.param(snapshot(age=501), id="stale"),
    pytest.param(snapshot(age=float("nan")), id="nonfinite-age"),
    pytest.param({"seq": 123, "pos_age_ms": 0, "pos_deg": {}}, id="repeated-sweep"),
])
def test_three_unusable_snapshots_never_substitute_zero_and_limp(rig, feedback):
    start(rig)
    reads = []
    def read():
        reads.append(True)
        return feedback
    rig.drive.bus.read_snapshot = read
    rig.manager.job["thread"].run()
    assert not any(call[0] == "write" for call in rig.calls)
    assert rig.manager.job["result"]["hold_unverified"]
    assert len(reads) == 3
    assert ("command", "X") in rig.calls
    assert not rig.drive.armed
    assert not rig.manager.busy_locked()


def test_estop_during_final_feedback_read_suppresses_late_hold_write(rig):
    start(rig)
    def read_pose():
        rig.bench._demo_gen += 1
        rig.drive.armed = False
        return snapshot([2.0] * N_JOINTS)
    rig.drive.bus.read_snapshot = read_pose
    rig.manager.job["thread"].run()
    assert not any(call[0] == "write" for call in rig.calls)
    assert not rig.drive.armed


def test_pose_streamer_nested_write_acquires_plain_guard_once_and_restores_scope():
    calls = []
    lock = threading.Lock()
    @contextmanager
    def guard():
        assert lock.acquire(blocking=False), "nested motor helper reacquired the plain lock"
        calls.append("guard")
        try:
            yield
        finally:
            lock.release()
    bus = SimpleNamespace(trims=[0.0] * N_JOINTS, pkt=SimpleNamespace(
        SyncWritePosEx=lambda *args: calls.append("write"),
        groupSyncWrite=SimpleNamespace(txPacket=lambda: None, clearParam=lambda: None)))
    with demos.scripted_motion_scope(guard):
        demos.PoseStreamer().write(bus, [1.0] * N_JOINTS, set(SERVO_IDS))
    assert calls.count("guard") == 1 and calls.count("write") == N_JOINTS
    demos._write_pose(bus, [1.0] * N_JOINTS, set(SERVO_IDS))
    assert calls.count("guard") == 1  # Other workers do not inherit the scope.


def test_one_incomplete_snapshot_recovers_without_limp(rig):
    start(rig)
    responses = iter([snapshot([None] * N_JOINTS), snapshot([3.0] * N_JOINTS)])
    rig.drive.bus.read_snapshot = lambda: next(responses)
    rig.manager.job["thread"].run()
    assert not any(call[0] == "command" for call in rig.calls)
    assert [call[1] for call in rig.calls if call[0] == "write"] == [[3.0] * N_JOINTS]
    assert rig.manager.job["state"] == "done"


def test_failed_limp_after_three_bad_reads_keeps_unverified_stop_exclusive(rig):
    start(rig)
    rig.drive.bus.read_snapshot = lambda: snapshot([None] * N_JOINTS)
    def failed_limp(line):
        raise OSError("torque transaction failed")
    rig.drive._handle_locked = failed_limp
    rig.manager.job["thread"].run()
    assert rig.manager.job["result"]["hold_unverified"]
    assert rig.manager.busy_locked()
    assert not rig.manager.request({"action": "prepare", "pose": "stand"})["ok"]


def test_ownership_lasts_through_actual_worker_exit(rig):
    start(rig)
    def finish_hot_bus():
        assert rig.manager.job["state"] == "done"
        assert rig.manager.busy_locked()  # Result ready does not mean thread exited.
        assert not rig.manager.request({"action": "prepare", "pose": "stand"})["ok"]
    rig.bench._bus_hot_end = finish_hot_bus
    rig.manager.job["thread"].run()
    assert not rig.manager.busy_locked()


def test_sit_uses_existing_step_lower_without_arming_or_zeroing(rig):
    rig.drive.armed = True
    start(rig, "sit")
    calls = []
    rig.bench.standup = lambda **kwargs: calls.append(kwargs) or {"ok": True}
    rig.manager.job["thread"].run()
    assert calls == [{"mode": "step", "speed": 10.0, "direction": "down", "sync_gen": rig.bench._demo_gen}]
    assert not any(call[0] == "torque" for call in rig.calls)


@pytest.mark.parametrize("cancelled", [False, True])
def test_real_inline_standup_cannot_rearm_or_launch_after_cancel(rig, cancelled):
    from api.standup import StandupApi
    bench = rig.bench
    bench._lock = threading.Lock()
    bench._load_standup = lambda: {"modes": {"step": {"keyframes": [{"q_deg": [0.0] * N_JOINTS, "s": 1.0}]}}}
    rig.drive.armed = cancelled
    if cancelled:
        bench._demo_abort.set()
    result = StandupApi.standup(bench, direction="down", force=True, sync_gen=bench._demo_gen)
    assert not result["ok"] and result["aborted"]
    assert rig.calls == []


def test_real_inline_upright_stand_stays_synchronous(rig):
    from api.standup import StandupApi
    bench = rig.bench
    bench._load_standup = lambda: {"modes": {"step": {"keyframes": []}}}
    bench._present_pose18 = lambda: ([1.0] * N_JOINTS, [])
    bench._normal_standing_pose = lambda present: {"standing": True}
    bench._step_to_rl_walk_ready_start_sync = lambda **kw: {"ok": True, "inline": True}
    def async_forbidden(**kw):
        pytest.fail("inline stand escaped to an asynchronous job")
    bench.go_zero = async_forbidden
    result = StandupApi.standup(bench, sync_gen=bench._demo_gen)
    assert result["ok"] and result["inline"]


@pytest.mark.parametrize("helper", ["enable", "limit", "pose", "stream"])
def test_scripted_scope_denies_each_write_boundary_before_bus_io(helper):
    @contextmanager
    def cancelled():
        raise pose_api.PoseCancelled("expired")
        yield  # pragma: no cover
    # No bus members: any attempted bus access would fail this test.
    bus = object()
    with demos.scripted_motion_scope(cancelled), pytest.raises(pose_api.PoseCancelled):
        if helper == "enable":
            demos._enable_torque(bus, {2})
        elif helper == "limit":
            demos._set_torque_limit(bus, {2}, 300)
        elif helper == "pose":
            demos._write_pose(bus, [1.0] * N_JOINTS, {2})
        else:
            demos.PoseStreamer().write(bus, [1.0] * N_JOINTS, {2})


@pytest.mark.parametrize("kind", ["enable", "limit"])
def test_torque_scope_rechecks_between_individual_packets(rig, kind):
    start(rig)
    rig.drive.armed = True
    job = rig.manager.job
    packets = []
    def first_packet(*args):
        packets.append(args)
        job["abort"].set()
    bus = SimpleNamespace(pkt=SimpleNamespace(write1ByteTxRx=first_packet,
                                             write2ByteTxRx=first_packet))
    with demos.scripted_motion_scope(lambda: rig.manager._write_guard(job)):
        with pytest.raises(pose_api.PoseCancelled):
            if kind == "enable":
                demos._enable_torque(bus, set(SERVO_IDS))
            else:
                demos._set_torque_limit(bus, set(SERVO_IDS), 300)
    assert len(packets) == 1


@pytest.mark.parametrize("feedback", [snapshot([None] + [1.0] * (N_JOINTS - 1)),
                                      snapshot([float("nan")] + [1.0] * (N_JOINTS - 1)),
                                      snapshot(age=65535), snapshot(age=float("nan"))])
def test_scoped_legacy_guard_hold_refuses_incomplete_or_stale_pose(feedback):
    bus = SimpleNamespace(read_snapshot=lambda: feedback)
    with demos.scripted_motion_scope(nullcontext):
        with pytest.raises(RuntimeError, match="complete fresh encoder"):
            demos._read_pose(bus, set(SERVO_IDS))


def test_scoped_guard_hold_reads_complete_pose_without_substituting_zero():
    positions = [float(i + 2) for i in range(N_JOINTS)]
    bus = SimpleNamespace(read_snapshot=lambda: snapshot(positions))
    with demos.scripted_motion_scope(nullcontext):
        assert demos._read_pose(bus, set(SERVO_IDS)) == positions


def test_running_renew_and_stop_do_not_wait_for_telemetry_drive_lock(rig):
    token = start(rig)
    actual_lock = rig.drive._lock
    class FailIfReacquired:
        def __enter__(self):
            pytest.fail("heartbeat/stop attempted the drive lock held by telemetry")
        def __exit__(self, *args):
            pass
    with actual_lock:
        rig.drive._lock = FailIfReacquired()
        rig.now[0] += 0.1
        assert request(rig, "renew", token)["state"] == "running"
        assert request(rig, "stop", token)["state"] == "stopping"
        assert rig.manager.job["abort"].is_set()
        assert request(rig, "renew", token)["state"] == "stopping"
    rig.drive._lock = actual_lock
