"""Off-robot regression: a sysid job owns the shared result slot.

2026-09-10: ``l3_air_radial_shear_hysteresis_control_v1`` returned
``ok=True`` with no ticks and no CSV. The runner had failed before it
opened its trace, but ``calibrate_state()`` did not count ``sysid_run``
as an owned job, so the stale ``calibration_report_latest.json`` replaced
the real error on the way back to the client.
"""
from __future__ import annotations

import threading

from bench_api import BenchAPI


class _Gait:
    def stop(self) -> None:
        pass


class _Drive:
    def __init__(self):
        self.bus = None
        self.dry_run = True
        self.port = "fake"
        self.armed = False
        self.mode = "idle"
        self.status = "test"
        self.gait = _Gait()
        self._lock = threading.RLock()

    def scripted_contract_state(self) -> dict:
        return {"supported": False}


_STALE_REPORT = {"ok": True, "mode": "calibrate_checkup"}


def _api(monkeypatch) -> BenchAPI:
    api = BenchAPI(_Drive())
    monkeypatch.setattr(api, "_latest_calibration_report",
                        lambda: dict(_STALE_REPORT))
    return api


def test_finished_sysid_result_is_not_replaced_by_the_latest_report(
        monkeypatch) -> None:
    api = _api(monkeypatch)
    api._demo_name = "sysid_run"
    api._cal_result = {"ok": False, "mode": "sysid",
                       "error": "servo IDs not answering: joints [9]"}

    state = api.calibrate_state()

    assert state["running"] is False
    assert state["result"]["ok"] is False
    assert state["result"]["error"] == "servo IDs not answering: joints [9]"
    assert state["latest_report"] == _STALE_REPORT


def test_running_sysid_job_reports_running(monkeypatch) -> None:
    api = _api(monkeypatch)
    api._demo_name = "sysid_run"
    api._cal_result = None
    done = threading.Event()
    api._demo_thread = threading.Thread(target=done.wait, daemon=True)
    api._demo_thread.start()
    try:
        state = api.calibrate_state()
    finally:
        done.set()
        api._demo_thread.join(timeout=2.0)

    assert state["running"] is True
    # A mid-run poll must not read the previous checkup as this job's result.
    assert state["result"] is None


def test_idle_slot_still_falls_back_to_the_latest_report(monkeypatch) -> None:
    api = _api(monkeypatch)
    api._demo_name = None
    api._cal_result = None

    assert api.calibrate_state()["result"] == _STALE_REPORT
