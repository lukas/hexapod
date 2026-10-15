"""Off-robot regression tests for async-reader bus quarantine."""
from __future__ import annotations

import threading
import json
import types
from io import BytesIO
from pathlib import Path

import pytest


import mcu_feetech_bus as mcu_bus_module
import rl_policy
import web_drive as web_drive_module
from async_bus_guard import (
    AsyncSamplerCleanupError,
    bus_quarantine_status,
    quarantine_bus,
    recover_bus_quarantine,
)
from bench_api import BenchAPI
from drive_controller import DriveController
from feetech_bus import FeetechBus
from mcu_feetech_bus import McuFeetechBus


class _ReaderThread:
    def __init__(self, *, alive: bool = True):
        self.alive = alive
        self.join_timeouts: list[float | None] = []

    def is_alive(self) -> bool:
        return self.alive

    def join(self, timeout=None) -> None:
        self.join_timeouts.append(timeout)


class _Reader:
    def __init__(self, thread):
        self._thread = thread


class _CountingBus:
    def __init__(self):
        self.calls: list[tuple] = []

    def scan(self, ids):
        self.calls.append(("scan", tuple(ids)))
        return []

    def read_position_deg(self, joint: int):
        self.calls.append(("read_position_deg", joint))
        return 0.0

    def read_all_feedback(self):
        self.calls.append(("read_all_feedback",))
        return {}

    def read_imu(self, **kwargs):
        self.calls.append(("read_imu", kwargs))
        return None

    def enable_all_torque(self, on: bool):
        self.calls.append(("enable_all_torque", on))


class _FailingTorqueBus(_CountingBus):
    def enable_all_torque(self, on: bool):
        self.calls.append(("enable_all_torque", on))
        raise RuntimeError("torque write failed")


class _Gait:
    def stop(self) -> None:
        pass


class _Drive:
    def __init__(self, bus):
        self.bus = bus
        self.dry_run = False
        self.port = "fake"
        self.armed = True
        self.mode = "demo"
        self.status = "test"
        self.gait = _Gait()
        self._lock = threading.RLock()

    def scripted_contract_state(self) -> dict:
        return {"supported": False}

    def _torque_all(self, on: bool) -> None:
        self.bus.enable_all_torque(on)


class _FakeSerial:
    def __init__(self):
        self.calls: list[tuple] = []

    def reset_input_buffer(self) -> None:
        self.calls.append(("reset",))

    def write(self, data) -> None:
        self.calls.append(("write", bytes(data)))

    def flush(self) -> None:
        self.calls.append(("flush",))

    def read(self, _n: int = 1) -> bytes:
        self.calls.append(("read",))
        return b""


class _RecordingLink:
    def __init__(self):
        self.calls: list[str] = []

    def send(self, command: str):
        self.calls.append(command)
        return True, "ok"


class _GuardOnlyBench:
    def __init__(self):
        self.delegated: list[str] = []

    def bus_access_state(self, *, recover: bool):
        return {
            "bus_quarantined": True,
            "bus_available": False,
            "reader_alive": True,
            "cleanup_details": ["join timeout"],
            "torque_state": "unverified",
            "error": "async reader cleanup incomplete; serial bus unavailable",
        }

    def __getattr__(self, name: str):
        self.delegated.append(name)
        raise AssertionError(f"quarantined request delegated to {name}")


def _mcu_bus() -> McuFeetechBus:
    bus = McuFeetechBus.__new__(McuFeetechBus)
    bus._lock = threading.Lock()
    bus._ser = _FakeSerial()
    bus._telemetry_sink = None
    bus.streaming = True
    bus._bin_trace_events = []
    bus._bin_trace_seq = 0
    bus._bin_trace_slow_ms = 30.0
    bus._bin_trace_keep = 16
    bus._pending = []
    return bus


def _release_quarantine(bus, reader: _Reader) -> None:
    if reader._thread is None:
        reader._thread = _ReaderThread(alive=False)
    reader._thread.alive = False
    state = recover_bus_quarantine(bus)
    assert state["bus_quarantined"] is False


def _http_request(path: str, *, method: str = "GET", body=None):
    handler_cls = web_drive_module.Handler
    handler = handler_cls.__new__(handler_cls)
    if isinstance(body, bytes):
        data = body
    elif isinstance(body, str):
        data = body.encode()
    elif body is None:
        data = b""
    else:
        data = json.dumps(body).encode()
    handler.path = path
    handler.command = method
    handler.headers = {"Content-Length": str(len(data))}
    handler.rfile = BytesIO(data)
    handler.wfile = BytesIO()
    handler._headers = {}
    handler.send_response = lambda code: setattr(handler, "_code", code)
    handler.send_header = (
        lambda key, value: handler._headers.__setitem__(key, value))
    handler.end_headers = lambda: None
    if method == "POST":
        handler_cls.do_POST(handler)
    else:
        handler_cls.do_GET(handler)
    return handler._code, handler._headers, handler.wfile.getvalue()


@pytest.fixture
def gamepad_web(monkeypatch):
    monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", "sts3215")
    drive = DriveController(dry_run=True)
    drive.armed = True
    monkeypatch.setattr(web_drive_module, "DRIVE", drive)
    monkeypatch.setattr(web_drive_module, "BENCH", None)
    monkeypatch.setattr(web_drive_module, "SETUP", None)
    monkeypatch.setattr(web_drive_module, "LINK", web_drive_module.Link(drive))
    monkeypatch.setattr(web_drive_module, "POST_STATE", {"active": 0, "setup": False})
    return drive


def test_gamepad_api_advertises_lease_and_preserves_estop(gamepad_web):
    code, _, raw = _http_request("/api/ping")
    assert code == 200
    assert json.loads(raw)["scripted_gamepad_lease"] == {"version": 1, "timeout_s": 0.75}
    code, _, raw = _http_request("/cmd", method="POST", body="JLEASE BEGIN api-gamepad-token-0001")
    assert code == 200 and raw == b"JLEASE"
    code, _, raw = _http_request("/cmd", method="POST", body="JLEASE api-gamepad-token-0001 nan 0 0")
    assert code == 409 and raw.startswith(b"bad JLEASE")
    code, _, _ = _http_request("/api/standup", method="POST", body={"direction": "up"})
    assert code == 409
    code, _, raw = _http_request("/cmd", method="POST", body="X")
    assert code == 200 and raw == b"limp"
    assert not gamepad_web.armed and not gamepad_web.gamepad_lease_busy()


def test_gamepad_begin_cannot_race_inflight_post(gamepad_web):
    web_drive_module.POST_STATE["active"] = 1
    code, _, raw = _http_request("/cmd", method="POST", body="JLEASE BEGIN api-gamepad-token-0001")
    assert code == 409 and b"another operation is busy" in raw
    assert not gamepad_web.gamepad_lease_busy()
    assert web_drive_module.POST_STATE["active"] == 1


def test_gamepad_begin_refuses_running_worker(gamepad_web, monkeypatch):
    bench = types.SimpleNamespace(robot_state=lambda: {"demo": {"running": True, "name": "standup"}})
    monkeypatch.setattr(web_drive_module, "BENCH", bench)
    code, _, raw = _http_request("/cmd", method="POST", body="JLEASE BEGIN api-gamepad-token-0001")
    assert code == 409 and b"robot busy with standup" in raw
    assert not gamepad_web.gamepad_lease_busy()


@pytest.fixture
def pose_web(gamepad_web, monkeypatch):
    from api.gamepad_pose import GamepadPose
    drive = gamepad_web
    drive.dry_run = False
    drive.bus = _CountingBus()
    drive.bus.read_snapshot = lambda: {"pos_deg": dict.fromkeys(range(18), 12.0), "pos_age_ms": 0}
    bench = BenchAPI(drive)
    monkeypatch.setattr(bench, "robot_state", lambda: {"demo": {"running": False}})
    monkeypatch.setattr(bench, "demo_state", lambda: {})
    drive.gamepad_pose = GamepadPose(bench)
    monkeypatch.setattr(web_drive_module, "BENCH", bench)
    return drive, bench


def _prepare_pose():
    code, _, body = _http_request("/api/gamepad/pose", method="POST",
                                body={"action": "prepare", "pose": "stand"})
    assert code == 200
    result = json.loads(body)
    assert result["state"] == "prepared"
    return result["token"]


def test_pose_api_prepare_is_motion_free_and_excludes_motion(pose_web):
    drive, _ = pose_web
    token = _prepare_pose()
    assert not drive.bus.calls
    assert drive.gamepad_lease_busy()
    for path in ("/api/zero", "/api/standup", "/api/setup/scan"):
        code, _, _ = _http_request(path, method="POST", body={})
        assert code == 409
    code, _, body = _http_request("/cmd", method="POST", body="JLEASE BEGIN another-owner-1234")
    assert code == 409 and b"gamepad pose" in body
    code, _, body = _http_request("/api/gamepad/pose", method="POST",
                                body={"action": "stop", "token": token})
    assert code == 200 and json.loads(body)["state"] == "stopping"
    assert not drive.gamepad_lease_busy()


@pytest.mark.parametrize("path,body", [("/cmd", "X"), ("/api/demo/stop", {})])
def test_pose_prepared_token_dies_on_canonical_stop(pose_web, path, body):
    drive, _ = pose_web
    token = _prepare_pose()
    code, _, _ = _http_request(path, method="POST", body=body)
    assert code == 200
    code, _, body = _http_request("/api/gamepad/pose", method="POST",
                                body={"action": "renew", "token": token})
    assert code == 200 and json.loads(body)["state"] == "error"
    assert drive.gamepad_pose.job["thread"] is None
    assert not drive.gamepad_lease_busy()
    assert not any(call == ("enable_all_torque", True) for call in drive.bus.calls)


def test_pose_stop_bypasses_setup_and_quarantine(pose_web, monkeypatch):
    drive, bench = pose_web
    token = _prepare_pose()
    monkeypatch.setattr(bench, "bus_access_state", lambda **kw: {"bus_quarantined": True})
    web_drive_module.POST_STATE["setup"] = True
    code, _, _ = _http_request("/api/gamepad/pose", method="POST",
                              body={"action": "stop", "token": token})
    assert code == 200
    assert drive.gamepad_pose.job["abort"].is_set()
    assert not drive.bus.calls


def test_pose_prepare_cannot_race_inflight_post(pose_web):
    drive, _ = pose_web
    web_drive_module.POST_STATE["active"] = 1
    code, _, body = _http_request("/api/gamepad/pose", method="POST",
                                body={"action": "prepare", "pose": "stand"})
    assert code == 409 and b"busy" in body
    assert drive.gamepad_pose.job is None


def test_pose_ping_advertises_protocol(pose_web):
    code, _, body = _http_request("/api/ping")
    assert code == 200
    assert json.loads(body)["scripted_gamepad_pose"] == {"version": 1, "timeout_s": 0.75}


def test_pose_endpoint_renews_and_stops_its_own_busy_worker(pose_web, monkeypatch):
    from api import gamepad_pose
    class ParkedThread:
        def __init__(self, **kw):
            self.alive = False
        def start(self):
            self.alive = True
        def is_alive(self):
            return self.alive
    monkeypatch.setattr(gamepad_pose, "threading", types.SimpleNamespace(Thread=ParkedThread))
    drive, _ = pose_web
    token = _prepare_pose()
    for _ in range(2):
        code, _, body = _http_request("/api/gamepad/pose", method="POST",
                                    body={"action": "renew", "token": token})
        assert code == 200 and json.loads(body)["state"] == "running"
        assert drive.gamepad_lease_busy()
    code, _, body = _http_request("/api/gamepad/pose", method="POST",
                                body={"action": "stop", "token": token})
    assert code == 200 and json.loads(body)["state"] == "stopping"
    assert drive.gamepad_lease_busy()


def test_telemetry_get_forwards_decoded_marker_id(monkeypatch) -> None:
    requested: list[str | None] = []

    class _TelemetryBench:
        def telemetry_state(self, marker_id=None):
            requested.append(marker_id)
            return {
                "ok": True,
                "active": True,
                "marker_ack": ({"marker_id": marker_id}
                               if marker_id is not None else None),
            }

    monkeypatch.setattr(web_drive_module, "BENCH", _TelemetryBench())
    code, headers, body = _http_request(
        "/api/telemetry?ignored=1&marker_id=marker%2Bexact")

    assert code == 200
    assert headers["Cache-Control"] == web_drive_module.NO_STORE
    assert requested == ["marker+exact"]
    assert json.loads(body)["marker_ack"] == {"marker_id": "marker+exact"}


def test_live_quarantine_blocks_api_reads_and_motion_without_bus_touch() -> None:
    bus = _CountingBus()
    reader = _Reader(_ReaderThread(alive=True))
    quarantine_bus(bus, reader, "reader did not stop")
    api = BenchAPI(_Drive(bus))
    try:
        calls = (
            api.status,
            api.pose,
            api.check_near_zero,
            lambda: api.command_pose([0.0] * 18),
            api.rl_preflight,
            api.rl_feedback,
            api.rl_timing_probe,
            api.rl_drive_start,
            lambda: api.rl_policy_move(mode="stand"),
            lambda: api.rl_find_plant(force=True),
        )
        for call in calls:
            result = call()
            assert result["ok"] is False
            assert result["bus_quarantined"] is True
            assert result["bus_available"] is False
            assert result["torque_state"] == "unverified"
        assert bus.calls == []

        # The non-bus state endpoint stays useful but never claims ARMED/HOLD.
        robot = api.robot_state()
        assert robot["bus_quarantined"] is True
        assert robot["armed"] is False
        assert robot["activity"] == "error"
        assert bus.calls == []
    finally:
        _release_quarantine(bus, reader)


def test_api_admission_nonblockingly_reaps_a_confirmed_dead_reader() -> None:
    bus = _CountingBus()
    thread = _ReaderThread(alive=True)
    reader = _Reader(thread)
    quarantine_bus(bus, reader, "reader did not stop")
    thread.alive = False

    result = BenchAPI(_Drive(bus)).pose()

    assert result["ok"] is True
    assert result["live"] == 18
    assert [c[0] for c in bus.calls] == ["read_position_deg"] * 18
    assert thread.join_timeouts == [0]
    assert bus_quarantine_status(bus)["bus_quarantined"] is False


def test_recovery_does_not_clear_reader_without_dead_thread_proof() -> None:
    bus = _CountingBus()
    reader = _Reader(None)
    quarantine_bus(bus, reader, "lost reader handle")
    try:
        state = recover_bus_quarantine(bus)
        assert state["bus_quarantined"] is True
        assert bus.calls == []
    finally:
        _release_quarantine(bus, reader)


def test_mcu_transaction_fence_checks_under_lock_before_serial_io(
        monkeypatch) -> None:
    bus = _mcu_bus()
    reader = _Reader(_ReaderThread(alive=True))
    quarantine_bus(bus, reader, "reader did not stop")
    real_require = mcu_bus_module.require_bus_available

    def require_under_lock(candidate) -> None:
        # The fast pre-lock check is an additional protection. Let that
        # check pass here so this test proves the fence is repeated while
        # holding the UART lock, before any serial I/O.
        if candidate._lock.locked():
            real_require(candidate)

    monkeypatch.setattr(
        mcu_bus_module, "require_bus_available", require_under_lock)
    try:
        operations = (
            lambda: bus._transact("PING 2"),
            lambda: bus._transact_try("PING 2"),
            lambda: bus._bin_txn(
                bytes([0xA5, 0x5A, ord("F"), 0, ord("F")]),
                ord("f"), 13),
        )
        for operation in operations:
            with pytest.raises(AsyncSamplerCleanupError):
                operation()
            assert bus._ser.calls == []
            assert not bus._lock.locked()

        bus._pending = [(2, 2048, 400, 20)]
        with pytest.raises(AsyncSamplerCleanupError):
            bus._flush_sync()
        assert bus._ser.calls == []
        assert not bus._lock.locked()
    finally:
        _release_quarantine(bus, reader)


def test_mcu_transaction_fence_reaps_dead_reader_and_allows_write(
        monkeypatch) -> None:
    bus = _mcu_bus()
    thread = _ReaderThread(alive=True)
    reader = _Reader(thread)
    quarantine_bus(bus, reader, "reader did not stop")
    thread.alive = False
    monkeypatch.setattr(bus, "_readline", lambda _timeout: "OK")

    assert bus._transact("PING") == "OK"
    assert ("write", b"PING\n") in bus._ser.calls
    assert thread.join_timeouts == [0]
    assert bus_quarantine_status(bus)["bus_quarantined"] is False


@pytest.mark.parametrize("reply", [None, "ERR torque failed"])
def test_mcu_torque_disable_requires_positive_acknowledgement(
        monkeypatch, reply) -> None:
    bus = _mcu_bus()
    monkeypatch.setattr(bus, "_readline", lambda _timeout: reply)

    with pytest.raises((TimeoutError, RuntimeError), match="TA 0"):
        bus.enable_all_torque(False)

    assert ("write", b"TA 0\n") in bus._ser.calls


def test_usb_torque_disable_requires_servo_acknowledgement() -> None:
    class _Pkt:
        def write1ByteTxRx(self, *_args):
            return 7, 0

    bus = FeetechBus.__new__(FeetechBus)
    bus.scs = types.SimpleNamespace(COMM_SUCCESS=0)
    bus.pkt = _Pkt()

    with pytest.raises(RuntimeError, match="not acknowledged"):
        bus.torque(2, False)


def test_drive_disarm_failure_is_logically_disarmed_but_not_limp() -> None:
    class _NoAckBus:
        scs = types.SimpleNamespace(COMM_SUCCESS=0)

        def enable_all_torque(self, _on):
            raise TimeoutError("no bulk acknowledgement")

        def scan(self, _ids):
            return []

        def torque(self, sid, _on):
            raise TimeoutError(f"no acknowledgement from {sid}")

    drive = DriveController(dry_run=True)
    drive.bus = _NoAckBus()
    drive.armed = True

    with pytest.raises(RuntimeError, match="not acknowledged"):
        drive.handle("X")

    assert drive.armed is False
    assert drive.status == "disarm requested; torque unverified"


def test_learned_safety_limp_propagates_unacknowledged_disable() -> None:
    calls: list[str] = []

    class _Bus:
        def enable_all_torque(self, _on):
            calls.append("bulk")
            raise TimeoutError("no MCU acknowledgement")

    class _AckDrive:
        bus = _Bus()

        def _torque_all(self, _on):
            calls.append("fallback")
            raise RuntimeError("per-servo disable not acknowledged")

    with pytest.raises(RuntimeError, match="not acknowledged"):
        rl_policy._confirmed_limp(_AckDrive())

    assert calls == ["bulk", "fallback"]


def test_learned_worker_cleanup_error_never_touches_bus_or_reports_hold(
        monkeypatch) -> None:
    monkeypatch.setattr(rl_policy, "preflight", lambda *_a, **_k: (True, "", {}))
    current: dict = {}

    def fail_cleanup(*_args, **_kwargs):
        quarantine_bus(current["bus"], current["reader"], "join timeout")
        raise AsyncSamplerCleanupError("join timeout")

    monkeypatch.setattr(rl_policy, "run_drive_session", fail_cleanup)
    monkeypatch.setattr(rl_policy, "run_policy_move", fail_cleanup)

    for kind in ("drive", "walk"):
        bus = _CountingBus()
        drive = _Drive(bus)
        api = BenchAPI(drive)
        reader = _Reader(_ReaderThread(alive=True))
        current.update(bus=bus, reader=reader)
        monkeypatch.setattr(
            api, "_role_weights", lambda role: Path(f"/tmp/{role}.json"))
        try:
            started = (api.rl_drive_start() if kind == "drive" else
                       api.rl_policy_move(mode="walk"))
            assert started["ok"] is True
            api._demo_thread.join(timeout=2.0)
            assert not api._demo_thread.is_alive()

            result = api._cal_result
            assert result["ok"] is False
            assert result["bus_quarantined"] is True
            assert result["bus_available"] is False
            assert result["torque_state"] == "unverified"
            assert drive.armed is False
            assert "quarantined" in drive.status
            assert api._activity == "error"
            assert bus.calls == []
        finally:
            _release_quarantine(bus, reader)


def test_generic_learned_worker_error_records_the_torque_off_limp(
        monkeypatch) -> None:
    bus = _CountingBus()
    drive = _Drive(bus)
    api = BenchAPI(drive)
    monkeypatch.setattr(rl_policy, "preflight", lambda *_a, **_k: (True, "", {}))
    monkeypatch.setattr(
        rl_policy, "run_drive_session",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(
        api, "_role_weights", lambda role: Path(f"/tmp/{role}.json"))

    assert api.rl_drive_start()["ok"] is True
    api._demo_thread.join(timeout=2.0)

    assert api._cal_result["limped"] is True
    assert api._cal_result["torque_state"] == "off"
    assert drive.armed is False
    assert api._activity == "limp"
    assert bus.calls == [("enable_all_torque", False)]


def test_failed_generic_torque_off_never_claims_limp_for_learned_workers(
        monkeypatch) -> None:
    monkeypatch.setattr(rl_policy, "preflight", lambda *_a, **_k: (True, "", {}))

    def fail_run(*_args, **_kwargs):
        raise RuntimeError("runner failed")

    monkeypatch.setattr(rl_policy, "run_drive_session", fail_run)
    monkeypatch.setattr(rl_policy, "run_policy_move", fail_run)

    for kind in ("drive", "walk"):
        bus = _FailingTorqueBus()
        drive = _Drive(bus)
        api = BenchAPI(drive)
        monkeypatch.setattr(
            api, "_role_weights", lambda role: Path(f"/tmp/{role}.json"))

        started = (api.rl_drive_start() if kind == "drive" else
                   api.rl_policy_move(mode="walk"))
        assert started["ok"] is True
        api._demo_thread.join(timeout=2.0)
        assert not api._demo_thread.is_alive()

        assert api._cal_result["limped"] is False
        assert api._cal_result["torque_state"] == "unverified"
        assert drive.armed is False
        assert "torque unverified" in drive.status
        assert api._activity == "error"
        assert bus.calls == [("enable_all_torque", False)]


@pytest.mark.parametrize("kind", ["dynamics", "sysid"])
def test_probe_wrappers_do_not_pre_enable_and_track_runner_armed_state(
        monkeypatch, kind) -> None:
    import motor_dynamics
    import sysid_protocol
    import sysid_runner

    bus = _CountingBus()
    drive = _Drive(bus)
    drive.armed = False
    api = BenchAPI(drive)

    def runner(*_args, **_kwargs):
        assert drive.armed is True
        assert ("enable_all_torque", True) not in bus.calls
        return {"ok": True, "mode": kind}

    if kind == "dynamics":
        monkeypatch.setattr(motor_dynamics, "run_motor_dynamics", runner)
        started = api.rl_probe_dynamics()
    else:
        monkeypatch.setattr(sysid_protocol, "validate", lambda _p: [])
        monkeypatch.setattr(sysid_protocol, "duration_s", lambda _p: 1.0)
        monkeypatch.setattr(sysid_runner, "run_sysid_protocol", runner)
        started = api.sysid_run({"name": "test", "segments": []})

    assert started["ok"] is True
    api._demo_thread.join(timeout=2.0)
    assert not api._demo_thread.is_alive()
    assert bus.calls == [("enable_all_torque", False)]
    assert drive.armed is False
    assert api._cal_result["limped"] is True
    assert api._cal_result["torque_state"] == "off"
    assert api._activity == "limp"


@pytest.mark.parametrize("kind", ["dynamics", "sysid"])
def test_probe_wrapper_exception_and_failed_disable_are_unverified(
        monkeypatch, kind) -> None:
    import motor_dynamics
    import sysid_protocol
    import sysid_runner

    bus = _FailingTorqueBus()
    drive = _Drive(bus)
    drive.armed = False
    api = BenchAPI(drive)

    def fail_runner(*_args, **_kwargs):
        assert drive.armed is True
        assert ("enable_all_torque", True) not in bus.calls
        raise RuntimeError("runner failed")

    if kind == "dynamics":
        monkeypatch.setattr(motor_dynamics, "run_motor_dynamics", fail_runner)
        started = api.rl_probe_dynamics()
    else:
        monkeypatch.setattr(sysid_protocol, "validate", lambda _p: [])
        monkeypatch.setattr(sysid_protocol, "duration_s", lambda _p: 1.0)
        monkeypatch.setattr(sysid_runner, "run_sysid_protocol", fail_runner)
        started = api.sysid_run({"name": "test", "segments": []})

    assert started["ok"] is True
    api._demo_thread.join(timeout=2.0)
    assert not api._demo_thread.is_alive()
    assert bus.calls == [("enable_all_torque", False)]
    assert drive.armed is False
    assert api._cal_result["ok"] is False
    assert api._cal_result["limped"] is False
    assert api._cal_result["torque_state"] == "unverified"
    assert "runner failed" in api._cal_result["error"]
    assert "torque disable unverified" in api._cal_result["error"]
    assert api._activity == "error"


def test_http_maps_quarantine_errors_to_503_without_bus_io(
        monkeypatch) -> None:
    bus = _CountingBus()
    reader = _Reader(_ReaderThread(alive=True))
    quarantine_bus(bus, reader, "reader did not stop")
    api = BenchAPI(_Drive(bus))
    link = _RecordingLink()
    monkeypatch.setattr(web_drive_module, "BENCH", api)
    monkeypatch.setattr(web_drive_module, "LINK", link)
    try:
        requests = (
            ("/api/status", "GET", None),
            ("/api/pose", "POST", {"q_deg": [0.0] * 18}),
        )
        for path, method, body in requests:
            code, headers, raw = _http_request(
                path, method=method, body=body)
            payload = json.loads(raw)
            assert code == 503
            assert payload["ok"] is False
            assert payload["code"] == "bus_quarantined"
            assert payload["bus_quarantined"] is True
            assert payload["bus_available"] is False
            assert payload["reader_alive"] is True
            assert payload["torque_state"] == "unverified"
            assert headers["Content-Type"] == "application/json"
            assert "no-store" in headers["Cache-Control"]
        assert bus.calls == []
        assert link.calls == []
    finally:
        _release_quarantine(bus, reader)


def test_http_centrally_rejects_all_bus_route_families_before_delegate(
        monkeypatch) -> None:
    bench = _GuardOnlyBench()
    monkeypatch.setattr(web_drive_module, "BENCH", bench)
    monkeypatch.setattr(web_drive_module, "LINK", _RecordingLink())

    get_paths = sorted(web_drive_module.BUS_REQUIRED_GET) + [
        "/api/robot?zero=true",
    ]
    post_paths = sorted(web_drive_module.BUS_REQUIRED_POST) + [
        "/api/measure/walk",
        "/api/measure/hold",
        "/api/measure/quad_pitch",
        "/api/measure/slip",
        "/api/measure/axis_geometry",
        "/api/measure/touchdown_zero",
    ]
    for path in get_paths:
        code, headers, raw = _http_request(path)
        payload = json.loads(raw)
        assert code == 503, path
        assert payload["code"] == "bus_quarantined"
        assert "no-store" in headers["Cache-Control"]
    for path in post_paths:
        code, headers, raw = _http_request(path, method="POST", body={})
        payload = json.loads(raw)
        assert code == 503, path
        assert payload["code"] == "bus_quarantined"
        assert "no-store" in headers["Cache-Control"]
    assert bench.delegated == []


def test_http_cmd_refuses_false_limp_while_bus_is_quarantined(
        monkeypatch) -> None:
    bus = _CountingBus()
    reader = _Reader(_ReaderThread(alive=True))
    quarantine_bus(bus, reader, "reader did not stop")
    api = BenchAPI(_Drive(bus))
    estop_calls: list[bool] = []
    monkeypatch.setattr(api, "estop", lambda: estop_calls.append(True))
    link = _RecordingLink()
    monkeypatch.setattr(web_drive_module, "BENCH", api)
    monkeypatch.setattr(web_drive_module, "LINK", link)
    try:
        code, headers, raw = _http_request(
            "/cmd", method="POST", body="X")
        text = raw.decode()
        assert code == 503
        assert "quarantined" in text
        assert "torque state unverified" in text
        assert "no-store" in headers["Cache-Control"]
        assert estop_calls == []
        assert link.calls == []
        assert bus.calls == []
    finally:
        _release_quarantine(bus, reader)


@pytest.mark.parametrize(
    "command",
    ["ARM", "P", "HOLD", "J 1 0 0", "# 0 1", "Q 0 1", "GAIT 1",
     "SETTLE"],
)
def test_http_cmd_fails_closed_for_every_command_during_quarantine(
        monkeypatch, command) -> None:
    bench = _GuardOnlyBench()
    link = _RecordingLink()
    monkeypatch.setattr(web_drive_module, "BENCH", bench)
    monkeypatch.setattr(web_drive_module, "LINK", link)

    code, headers, raw = _http_request(
        "/cmd", method="POST", body=command)

    assert code == 503
    assert "quarantined" in raw.decode()
    assert "torque state unverified" in raw.decode()
    assert "no-store" in headers["Cache-Control"]
    assert link.calls == []
    assert bench.delegated == []


def test_http_cmd_x_reports_unverified_torque_as_503(monkeypatch) -> None:
    class _Bench:
        def bus_access_state(self, *, recover: bool):
            return {"bus_quarantined": False, "bus_available": True}

        def estop(self):
            return {
                "ok": False,
                "limped": False,
                "torque_state": "unverified",
                "error": "TA 0: no MCU acknowledgement",
            }

    monkeypatch.setattr(web_drive_module, "BENCH", _Bench())
    monkeypatch.setattr(web_drive_module, "LINK", _RecordingLink())

    code, headers, raw = _http_request("/cmd", method="POST", body="X")

    assert code == 503
    assert raw.decode() == "stop requested; torque state unverified"
    assert "no-store" in headers["Cache-Control"]


def test_http_cmd_rechecks_quarantine_after_dispatch(monkeypatch) -> None:
    class _RaceBench:
        def __init__(self):
            self.calls = 0

        def bus_access_state(self, *, recover: bool):
            self.calls += 1
            if self.calls == 1:
                return {"bus_quarantined": False, "bus_available": True}
            return {
                "bus_quarantined": True,
                "bus_available": False,
                "torque_state": "unverified",
            }

    bench = _RaceBench()
    link = _RecordingLink()
    monkeypatch.setattr(web_drive_module, "BENCH", bench)
    monkeypatch.setattr(web_drive_module, "LINK", link)

    code, headers, raw = _http_request("/cmd", method="POST", body="ARM")

    assert link.calls == ["ARM"]
    assert bench.calls == 2
    assert code == 503
    assert raw.decode() == "bus quarantined; torque state unverified"
    assert "no-store" in headers["Cache-Control"]


def test_estop_never_claims_limp_when_torque_disable_raises() -> None:
    class _EstopDrive(_Drive):
        def handle(self, command: str):
            assert command == "X"
            self.armed = False
            raise TimeoutError("TA 0: no MCU acknowledgement")

    drive = _EstopDrive(_CountingBus())
    api = BenchAPI(drive)

    result = api.estop()

    assert result["ok"] is False
    assert result["limped"] is False
    assert result["torque_state"] == "unverified"
    assert "no MCU acknowledgement" in result["error"]
    assert drive.armed is False
    assert "torque unverified" in drive.status
    assert api._activity == "error"


def test_http_bus_status_and_nonblocking_recovery_never_touch_bus(
        monkeypatch) -> None:
    bus = _CountingBus()
    thread = _ReaderThread(alive=True)
    reader = _Reader(thread)
    quarantine_bus(bus, reader, "reader did not stop")
    api = BenchAPI(_Drive(bus))
    monkeypatch.setattr(web_drive_module, "BENCH", api)
    monkeypatch.setattr(web_drive_module, "LINK", _RecordingLink())
    try:
        code, headers, raw = _http_request("/api/bus/status")
        status = json.loads(raw)
        assert code == 200
        assert status["ok"] is True
        assert status["code"] == "bus_quarantined"
        assert status["bus_quarantined"] is True
        assert status["reader_alive"] is True
        assert "no-store" in headers["Cache-Control"]

        code, headers, raw = _http_request(
            "/api/bus/recover", method="POST")
        blocked = json.loads(raw)
        assert code == 409
        assert blocked["ok"] is False
        assert blocked["code"] == "bus_quarantined"
        assert blocked["reader_alive"] is True
        assert thread.join_timeouts == []
        assert "no-store" in headers["Cache-Control"]

        thread.alive = False
        code, headers, raw = _http_request(
            "/api/bus/recover", method="POST")
        recovered = json.loads(raw)
        assert code == 200
        assert recovered["ok"] is True
        assert recovered["recovered"] is True
        assert recovered["bus_quarantined"] is False
        assert recovered["bus_available"] is True
        assert recovered["armed"] is False
        assert recovered["torque_state"] == "unverified"
        assert thread.join_timeouts == [0]
        assert "no-store" in headers["Cache-Control"]
        assert bus.calls == []
    finally:
        if bus_quarantine_status(bus)["bus_quarantined"]:
            _release_quarantine(bus, reader)


def test_http_rechecks_quarantine_after_route_to_close_admission_race(
        monkeypatch) -> None:
    class _RaceBench:
        def __init__(self):
            self.status_calls = 0

        def bus_access_state(self, *, recover: bool):
            self.status_calls += 1
            if recover:
                return {"bus_quarantined": False, "bus_available": True}
            return {
                "bus_quarantined": True,
                "bus_available": False,
                "reader_alive": True,
                "cleanup_details": ["late quarantine"],
                "torque_state": "unverified",
                "error": "serial bus unavailable",
            }

        def pose(self):
            return {"ok": True, "degrees": [0.0] * 18}

    bench = _RaceBench()
    monkeypatch.setattr(web_drive_module, "BENCH", bench)
    code, headers, raw = _http_request("/api/pose")
    payload = json.loads(raw)

    assert code == 503
    assert payload["ok"] is False
    assert payload["code"] == "bus_quarantined"
    assert payload["torque_state"] == "unverified"
    assert "no-store" in headers["Cache-Control"]
    assert bench.status_calls == 2


def test_http_nonbus_status_and_stop_routes_remain_available(
        monkeypatch) -> None:
    class _SafeBench(_GuardOnlyBench):
        def robot_state(self, **_kwargs):
            return {"ok": True, **self.bus_access_state(recover=False)}

        def stop_demo(self):
            return {"ok": True}

        def stop_calibrate(self):
            return {"ok": True}

        def rl_stop(self):
            return {"ok": True}

        def rl_drive_stop(self):
            return {"ok": True}

    bench = _SafeBench()
    monkeypatch.setattr(web_drive_module, "BENCH", bench)

    code, headers, raw = _http_request("/api/robot")
    payload = json.loads(raw)
    assert code == 200
    assert payload["degraded"] is True
    assert payload["code"] == "bus_quarantined"
    assert "no-store" in headers["Cache-Control"]

    for path in ("/api/demo/stop", "/api/calibrate/stop", "/api/rl/stop",
                 "/api/standup/stop", "/api/rl/drive/stop"):
        code, _headers, raw = _http_request(path, method="POST")
        assert code == 200, path
        assert json.loads(raw)["ok"] is True
