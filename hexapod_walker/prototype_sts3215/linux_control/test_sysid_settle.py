"""After a sysid run the runner holds the present pose; the API decides:
belly → limp as before, standing → STEP down then limp, standing but the
step-down failed or the operator aborted → keep holding (never drop it).
2026-09-11: every stand protocol had been ending by limping a standing robot."""
from __future__ import annotations

import threading

import pytest

from bench_api import BenchAPI

STAND = [0.0, 21.0, 82.0] * 6
BELLY = [0.0] * 18


class _Gait:
    def stop(self) -> None:
        pass


class _PoseBus:
    def __init__(self, pose):
        self.pose = list(pose)
        self.calls: list[tuple] = []

    def read_all_positions(self):
        return {j: v for j, v in enumerate(self.pose)}

    def read_position_deg(self, joint: int):
        return self.pose[joint]

    def read_all_feedback(self):
        return {}

    def enable_all_torque(self, on: bool):
        self.calls.append(("enable_all_torque", on))


class _Drive:
    def __init__(self, bus):
        self.bus = bus
        self.dry_run = False
        self.port = "fake"
        self.armed = False
        self.mode = "idle"
        self.status = "test"
        self.gait = _Gait()
        self._lock = threading.RLock()

    def scripted_contract_state(self) -> dict:
        return {"supported": False}

    def _torque_all(self, on: bool) -> None:
        self.bus.enable_all_torque(on)


def _run(monkeypatch, pose, *, runner_result, standup=None, abort=False):
    import sysid_protocol
    import sysid_runner

    bus = _PoseBus(pose)
    api = BenchAPI(_Drive(bus))
    monkeypatch.setattr(sysid_protocol, "validate", lambda _p: [])
    monkeypatch.setattr(sysid_protocol, "duration_s", lambda _p: 1.0)

    def runner(*_a, **_k):
        if abort:
            api._demo_abort.set()
        return dict(runner_result)

    monkeypatch.setattr(sysid_runner, "run_sysid_protocol", runner)
    downs: list[dict] = []
    if standup is not None:
        def fake_standup(**kw):
            downs.append(kw)
            return standup
        monkeypatch.setattr(api, "standup", fake_standup)
    assert api.sysid_run({"name": "t", "segments": []})["ok"] is True
    api._demo_thread.join(timeout=3.0)
    assert not api._demo_thread.is_alive()
    return api, bus, downs


def test_belly_pose_still_limps(monkeypatch):
    api, bus, downs = _run(monkeypatch, BELLY, runner_result={"ok": True, "torque_left_on": True},
                           standup={"ok": True})
    assert downs == []
    assert bus.calls == [("enable_all_torque", False)]
    assert api._cal_result["settle"]["standing"] is False
    assert api._cal_result["torque_state"] == "off" and api._activity == "limp"


def test_standing_robot_steps_down_then_limps(monkeypatch):
    api, bus, downs = _run(monkeypatch, STAND, runner_result={"ok": True, "torque_left_on": True},
                           standup={"ok": True})
    assert downs == [{"mode": "step", "direction": "down", "sync_gen": api._demo_gen}]
    assert bus.calls == [("enable_all_torque", False)]
    s = api._cal_result["settle"]
    assert s["standing"] is True and s["lowered"] is True
    assert api._cal_result["torque_state"] == "off"


def test_standing_robot_whose_step_down_fails_keeps_torque(monkeypatch):
    api, bus, downs = _run(monkeypatch, STAND, runner_result={"ok": False, "error": "joint 8 tracking error",
                                                              "torque_left_on": True},
                           standup={"ok": False, "error": "stall"})
    assert len(downs) == 1
    assert bus.calls == []                       # never limped
    assert api._cal_result["torque_state"] == "on"
    assert api._cal_result["limped"] is False
    assert api.drive.armed is True and api._activity == "armed"
    assert "standing" in api.drive.status


def test_operator_abort_leaves_a_standing_robot_holding(monkeypatch):
    api, bus, downs = _run(monkeypatch, STAND, runner_result={"ok": False, "aborted": True, "torque_left_on": True},
                           standup={"ok": True}, abort=True)
    assert downs == []
    assert bus.calls == []
    assert api._cal_result["settle"]["route"] == "hold_after_abort"
    assert api._cal_result["torque_state"] == "on"


def test_runner_that_limped_itself_is_left_alone(monkeypatch):
    api, bus, downs = _run(monkeypatch, STAND, runner_result={"ok": True, "torque_left_on": False},
                           standup={"ok": True})
    assert downs == [] and bus.calls == [("enable_all_torque", False)]
    assert "settle" not in api._cal_result
