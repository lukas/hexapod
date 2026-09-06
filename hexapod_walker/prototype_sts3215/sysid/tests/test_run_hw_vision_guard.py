from __future__ import annotations

import time

import pytest

import sysid.run_hw as run_hw
from sysid.run_hw import VisionGuard, _wait_idle_guarded


def test_vision_guard_requires_three_advancing_frames() -> None:
    guard = VisionGuard(required_frames=3, stale_after_s=1.0)

    assert guard.observe(10)
    assert not guard.observe(10)
    assert guard.observe(11)
    assert not guard.ready.is_set()
    assert guard.observe(12)
    assert guard.ready.is_set()
    assert guard.snapshot()["advancing_frames"] == 3


def test_vision_guard_faults_when_stream_stops_advancing() -> None:
    guard = VisionGuard(required_frames=1, stale_after_s=0.001)
    guard.observe(1)
    time.sleep(0.003)
    guard.check_stale()

    assert guard.fault.is_set()
    assert "did not advance" in str(guard.snapshot()["reason"])


class _Client:
    def __init__(self) -> None:
        self.stops = 0
        self.states = 0

    def stop(self) -> dict:
        self.stops += 1
        return {"ok": True}

    def state(self) -> dict:
        self.states += 1
        return {
            "ok": True,
            "calibrate": {
                "running": self.states == 1,
                "result": {"ok": False, "aborted": True},
            },
        }


def test_guard_fault_binds_to_one_remote_stop_and_seals_result() -> None:
    guard = VisionGuard(required_frames=1, stale_after_s=1.0)
    guard.fail("camera disconnected")
    client = _Client()

    result = _wait_idle_guarded(
        client, timeout_s=1.0, poll_s=0.001, guard=guard
    )

    assert client.stops == 1
    assert result["ok"] is False
    assert result["guard_stop"]["reason"] == "camera disconnected"
    assert result["result"]["aborted"] is True


def test_go_without_camera_guard_fails_before_robot_client(monkeypatch) -> None:
    def unexpected_client(*_args, **_kwargs):
        raise AssertionError("robot client must not be constructed")

    monkeypatch.setattr(run_hw, "HexapodClient", unexpected_client)
    protocol = (
        run_hw.PROTO_DIR / "sysid" / "protocols" / "steps_air_v1.json"
    )
    with pytest.raises(SystemExit, match="requires --capture-vision"):
        run_hw.main(["--protocol", str(protocol), "--go"])
