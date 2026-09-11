"""Offline camera-failure ordering and terminal-result regressions."""
import json
import threading
from types import SimpleNamespace

import pytest

from sysid.camera_guard import CameraGuard
from sysid import run_hw


def test_failed_admission_neither_starts_nor_stops_another_job():
    calls = []
    client = SimpleNamespace(
        _req=lambda *args: calls.append("start"),
        stop=lambda: calls.append("stop"),
    )
    guard = CameraGuard(frozenset({18}))
    launch = run_hw._CameraGuardedLaunch(client, guard, {})
    guard.reject("camera lost before launch")
    launch.camera_failed(guard.failure)

    with pytest.raises(RuntimeError, match="before motion"):
        launch.run({}, force=False)
    assert calls == []


def test_camera_failure_during_start_cannot_send_stop_before_start_finishes():
    entered = threading.Event()
    release = threading.Event()
    abort_entered = threading.Event()
    stopped = threading.Event()
    calls, errors = [], []

    def request(*args):
        calls.append("start_entered")
        entered.set()
        assert release.wait(2)
        calls.append("start_finished")
        return {"ok": True}

    def stop():
        calls.append("stop")
        stopped.set()

    guard = CameraGuard(frozenset({18}))
    launch = run_hw._CameraGuardedLaunch(
        SimpleNamespace(_req=request, stop=stop), guard, {})

    def start():
        try:
            launch.run({}, force=False)
        except BaseException as error:
            errors.append(error)

    def fail():
        guard.reject("camera lost during launch")
        abort_entered.set()
        launch.camera_failed(guard.failure)

    starter, aborter = threading.Thread(target=start), threading.Thread(target=fail)
    starter.start()
    try:
        assert entered.wait(2)
        aborter.start()
        assert abort_entered.wait(2)
        assert not stopped.wait(0.05)
    finally:
        release.set()
        starter.join(2)
        if aborter.ident is not None:
            aborter.join(2)
    assert not errors
    assert not starter.is_alive() and not aborter.is_alive()
    assert calls == ["start_entered", "start_finished", "stop"]


def test_camera_failure_overrides_hardware_success_without_rewriting_evidence():
    hardware = {"ok": True, "ticks_done": 10}
    guard = CameraGuard(frozenset({18}))
    guard.reject("coverage lost")
    result = run_hw._guarded_result(hardware, guard)
    assert result["ok"] is False
    assert result["camera_guard_failed"] == "coverage lost"
    assert result["hardware_result"] == hardware
    assert hardware == {"ok": True, "ticks_done": 10}


def test_main_cannot_report_success_after_camera_abort(monkeypatch, tmp_path):
    captured, calls = {}, []

    def capture(*args, guard, camera_guard, on_guard_failure, **kwargs):
        captured.update(guard=camera_guard, abort=on_guard_failure)
        guard.ready.set()

    class ImmediateThread:
        def __init__(self, *, target, args, kwargs, **ignored):
            self.target, self.args, self.kwargs = target, args, kwargs
        def start(self):
            self.target(*self.args, **self.kwargs)
        def join(self, **kwargs):
            pass
        def is_alive(self):
            return False

    class Client:
        def __init__(self, url):
            pass
        def feedback(self):
            return {"ok": True, "live": 18}
        def _req(self, *args):
            calls.append("start")
            return {"ok": True}
        def stop(self):
            calls.append("stop")
            return {"ok": True}
        def state(self):
            captured["guard"].reject("camera coverage lost")
            captured["abort"](captured["guard"].failure)
            return {"calibrate": {
                "running": False,
                "result": {"ok": True, "csv": "sysid_mock.csv"},
            }}

    def pull(client, name, out_dir):
        path = out_dir / name
        path.write_text(json.dumps({"ok": True}) if name.endswith(".json") else "t\n")
        return path

    protocol = tmp_path / "protocol.json"
    protocol.write_text(json.dumps({"name": "mock", "segments": []}))
    monkeypatch.setattr(run_hw, "DATASET_DIR", tmp_path / "datasets")
    monkeypatch.setattr(run_hw, "HexapodClient", Client)
    monkeypatch.setattr(run_hw, "validate", lambda doc: [])
    monkeypatch.setattr(run_hw, "duration_s", lambda doc: 1)
    monkeypatch.setattr(run_hw, "protocol_hash", lambda doc: "mock")
    monkeypatch.setattr(run_hw, "_capture_vision_sidecar", capture)
    monkeypatch.setattr(run_hw.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(run_hw.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(run_hw, "_pull", pull)

    code = run_hw.main(["--protocol", str(protocol), "--go", "--capture-vision",
                        "--required-target-tag", "18"])

    assert code == 1
    assert calls == ["start", "stop"]
    summary_path, = (tmp_path / "datasets").glob("*/runner_summary.json")
    summary = json.loads(summary_path.read_text())
    assert summary["ok"] is False
    assert summary["hardware_result"]["ok"] is True
    assert summary["camera_guard_failed"] == "camera coverage lost"


def test_ok_result_without_ticks_is_a_named_failure():
    # 2026-09-10 17:02: the L1 ladder's result was the stale calibration
    # checkup (ok=True, no ticks). Only the pulled summary distinguishes it
    # from a real run, so a missing pull must not read back as success.
    failed = run_hw._ticked_result({"ok": True, "mode": "calibrate_checkup"})

    assert failed["ok"] is False
    assert "ticks_done=None" in failed["error"]
    assert failed["hardware_result"]["ok"] is True


def test_zero_ticks_is_a_failure_and_keeps_the_planned_count():
    failed = run_hw._ticked_result(
        {"ok": True, "ticks_done": 0, "ticks_planned": 1740})

    assert failed["ok"] is False
    assert "ticks_done=0/1740" in failed["error"]


def test_a_run_that_ticked_is_left_alone():
    ran = {"ok": True, "ticks_done": 1740, "ticks_planned": 1740}

    assert run_hw._ticked_result(ran) == ran


def test_an_existing_failure_keeps_its_own_error():
    tripped = {"ok": False, "ticks_done": 0,
               "error": "joint 4 tracking error 31 deg"}

    assert run_hw._ticked_result(tripped) == tripped
