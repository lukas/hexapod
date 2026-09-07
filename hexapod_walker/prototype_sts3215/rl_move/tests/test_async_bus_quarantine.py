from pathlib import Path
from types import SimpleNamespace
import sys
import threading

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "linux_control"))
sys.path.insert(0, str(_ROOT / "motor_setup"))
from async_bus_guard import (AsyncSamplerCleanupError, quarantine_bus,
    bus_quarantine_status, clear_bus_quarantine, recover_bus_quarantine,
    require_bus_available)
from api.rl import RlApi
from api.core import CoreApi
from mcu_feetech_bus import McuFeetechBus
from rl_policy import validate_velocity_filter_alpha


class ReaderThread:
    alive = True
    joins = 0
    def is_alive(self):
        return self.alive
    def join(self, timeout=None):
        assert not self.alive
        self.joins += 1


@pytest.fixture
def quarantined():
    bus = SimpleNamespace()
    reader = SimpleNamespace(_thread=ReaderThread())
    quarantine_bus(bus, reader, "reader did not stop")
    yield bus, reader
    reader._thread.alive = False
    clear_bus_quarantine(bus, reader)


def test_quarantine_visible_across_worker_threads_and_cannot_clear_live(quarantined):
    bus, reader = quarantined
    errors = []
    def worker():
        try:
            require_bus_available(bus)
        except AsyncSamplerCleanupError as exc:
            errors.append(str(exc))
    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert errors
    with pytest.raises(AsyncSamplerCleanupError):
        clear_bus_quarantine(bus, reader)
    assert recover_bus_quarantine(bus)["bus_quarantined"]
    reader._thread.alive = False
    assert bus_quarantine_status(bus)["bus_quarantined"]
    assert recover_bus_quarantine(bus)["bus_available"]
    assert reader._thread.joins >= 1


@pytest.mark.parametrize("operation", [
    lambda b: b._transact("TA 0"),
    lambda b: b._transact_try("TA 0"),
    lambda b: b._bin_txn(bytes([0xA5, 0x5A, ord("F"), 0]), ord("F"), 13),
    lambda b: b.write_all([0.0] * 18),
    lambda b: b._flush_sync(),
])
def test_quarantine_blocks_every_serial_transaction_boundary(operation):
    bus = object.__new__(McuFeetechBus)
    bus._pending = [(2, 2000, 100, 20)]
    reader = SimpleNamespace(_thread=ReaderThread())
    quarantine_bus(bus, reader, "timeout")
    try:
        # No serial object or lock is present: any I/O would fail this test.
        with pytest.raises(AsyncSamplerCleanupError):
            operation(bus)
    finally:
        reader._thread.alive = False
        clear_bus_quarantine(bus, reader)


class Api(RlApi, CoreApi):
    def __init__(self, bus):
        self.drive = SimpleNamespace(bus=bus, dry_run=False, armed=True,
            _lock=threading.RLock(), mode="idle", status="ready")
        self._lock = threading.RLock()
        self._demo_thread = None
        self._demo_gen = 0
        self._demo_abort = threading.Event()
        self._drive_cmd = None
        self._bus_hot = 0
        self._demo_name = ""
        self._cal_result = None
    def _role_weights(self, mode):
        return Path("weights.json")
    def _roles(self):
        return {"stand": "test", "hold": "test"}
    def _bus_hot_begin(self):
        self._bus_hot += 1
    def _bus_hot_end(self):
        self._bus_hot -= 1
    def _set_activity(self, activity, detail=""):
        self.activity = activity
    def _drive_active(self):
        return bool(self._demo_thread and self._demo_thread.is_alive())
    def calibrate_state(self):
        return {}


@pytest.mark.parametrize("alpha", [float("nan"), float("inf"), -0.1, 1.1, "invalid"])
def test_drive_api_rejects_invalid_filter_before_preflight(monkeypatch, alpha):
    import rl_policy
    monkeypatch.setattr(rl_policy, "preflight",
                        lambda *a, **k: pytest.fail("preflight called"))
    api = Api(object())
    result = api.rl_drive_start(velocity_filter_alpha=alpha)
    assert not result["ok"]
    assert "velocity_filter_alpha" in result["error"]
    assert api._demo_thread is None


@pytest.mark.parametrize("alpha", [None, 0.0, 0.8, 1.0])
def test_drive_api_forwards_velocity_alpha_to_worker(monkeypatch, alpha):
    import rl_policy
    calls = []
    monkeypatch.setattr(rl_policy, "preflight", lambda *a, **k: (True, "", {}))
    def run(*args, **kwargs):
        calls.append(kwargs)
        return {"ok": True, "velocity_filter_alpha": kwargs["velocity_filter_alpha"]}
    monkeypatch.setattr(rl_policy, "run_drive_session", run)
    api = Api(object())
    result = api.rl_drive_start(velocity_filter_alpha=alpha)
    assert result["ok"]
    api._demo_thread.join(timeout=1)
    assert not api._demo_thread.is_alive()
    assert len(calls) == 1
    assert calls[0]["velocity_filter_alpha"] == alpha
    assert api._cal_result["velocity_filter_alpha"] == alpha


def test_drive_api_forwards_active_duration_to_worker(monkeypatch):
    import rl_policy
    calls = []
    monkeypatch.setattr(rl_policy, "preflight", lambda *a, **k: (True, "", {}))
    def run(*args, **kwargs):
        calls.append(kwargs)
        return {"ok": True, "active_duration_s": kwargs["active_duration_s"]}
    monkeypatch.setattr(rl_policy, "run_drive_session", run)
    api = Api(object())
    result = api.rl_drive_start(active_duration_s=3.0)
    assert result["ok"]
    api._demo_thread.join(timeout=1)
    assert calls[0]["active_duration_s"] == 3.0


@pytest.mark.parametrize("mode", ["drive", "stand"])
def test_api_cleanup_failure_never_torques_or_advertises_bus_available(monkeypatch, mode):
    torque = []
    bus = SimpleNamespace(enable_all_torque=lambda value: torque.append(value))
    api = Api(bus)
    reader = SimpleNamespace(_thread=ReaderThread())
    class Command:
        live = {}
        def set(self, *args): pass
    def run(*args, **kwargs):
        quarantine_bus(bus, reader, "reader did not join")
        raise AsyncSamplerCleanupError("reader did not join")
    monkeypatch.setitem(sys.modules, "rl_policy", SimpleNamespace(
        DriveCommand=Command, preflight=lambda *a, **k: (True, "", {}),
        run_drive_session=run, run_policy_move=run,
        validate_drive_active_duration=lambda value: value,
        validate_velocity_filter_alpha=validate_velocity_filter_alpha))
    try:
        if mode == "drive":
            api.rl_drive_start()
        else:
            api.rl_policy_move(mode="stand", learned=True)
        api._demo_thread.join(timeout=1)
        assert not api._demo_thread.is_alive()
        assert torque == []
        assert api.drive.mode == "idle"
        assert not api.drive.armed
        assert api._bus_hot == 0
        assert api.activity == "error"
        assert api._cal_result["torque_state"] == "unverified"
        assert api.rl_drive_start()["bus_quarantined"]
        # Also blocks scripted stand/lower before their early dispatch.
        assert api.rl_policy_move(mode="lower")["bus_quarantined"]
        assert api.bus_status()["bus_available"] is False
        reader._thread.alive = False
        api.bus_access_state()
        assert api._bus_hot == 0
        assert api.drive.mode == "idle"
        assert not api.drive.armed
        assert api.activity == "error"
        assert torque == []
    finally:
        reader._thread.alive = False
        clear_bus_quarantine(bus, reader)


@pytest.mark.parametrize("method,args", [
    ("_transact", ("TA 0",)),
    ("_transact_try", ("TA 0",)),
    ("_bin_txn", (bytes([0xA5, 0x5A, ord("F"), 0]), ord("F"), 13)),
])
def test_quarantine_rechecked_after_waiting_for_serial_lock(method, args):
    bus = object.__new__(McuFeetechBus)
    reader = SimpleNamespace(_thread=ReaderThread())
    class LockThatQuarantines:
        def __enter__(self):
            quarantine_bus(bus, reader, "reader timed out while caller waited")
        def __exit__(self, *args): pass
        def acquire(self, **kwargs):
            self.__enter__()
            return True
        def release(self): pass
    bus._lock = LockThatQuarantines()
    try:
        with pytest.raises(AsyncSamplerCleanupError):
            getattr(bus, method)(*args)
    finally:
        reader._thread.alive = False
        clear_bus_quarantine(bus, reader)


def test_central_admission_joins_dead_reader_without_rearming_active_worker(quarantined):
    bus, reader = quarantined
    api = Api(bus)
    api._demo_thread = ReaderThread()
    reader._thread.alive = False
    assert api.bus_status()["bus_quarantined"]
    assert reader._thread.joins == 0
    assert not api.bus_access_state()["bus_quarantined"]
    assert reader._thread.joins >= 1
    assert not api.drive.armed
    assert api._demo_thread.is_alive()
