"""Off-robot regression tests for the walk-only hardware session wrapper."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from rl_move.scripts import run_rl_walk_trial as walk_trial


def _robot_sample(stamp: float, *, live: int = 18,
                  missing: list[int] | None = None) -> dict:
    return {
        "armed": True,
        "activity": "holding",
        "servo": {
            "ts": stamp,
            "live": live,
            "missing": missing or [],
            "max_temp_c": 35.0,
            "tripped": [],
        },
    }


def _trial_with(samples, monkeypatch):
    trial = walk_trial.Trial.__new__(walk_trial.Trial)
    trial.args = SimpleNamespace(temp_trip_c=55.0)
    replies = iter(samples)
    trial.request = lambda _path: next(replies)
    trial.event = lambda *_args, **_kwargs: None
    monkeypatch.setattr(walk_trial.time, "sleep", lambda _seconds: None)
    return trial


def test_one_missing_scan_remains_telemetry_noise(monkeypatch):
    trial = _trial_with([
        _robot_sample(1.0, live=17, missing=[3]),
        _robot_sample(2.0),
        _robot_sample(3.0),
    ], monkeypatch)

    samples = trial.three_fresh_health_samples(require_armed=True)

    assert len(samples) == 3


def test_three_missing_scans_raise_confirmed_health_trip(monkeypatch):
    trial = _trial_with([
        _robot_sample(float(index), live=16, missing=[3, 4])
        for index in range(1, 4)
    ], monkeypatch)

    with pytest.raises(walk_trial.ConfirmedHealthTrip, match="not clear"):
        trial.three_fresh_health_samples(require_armed=True)


class _Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def _drive_trial(monkeypatch, live_times: list[float | None]):
    trial = walk_trial.Trial.__new__(walk_trial.Trial)
    trial.args = SimpleNamespace(
        speed_m_s=0.08,
        duration_s=3.0,
        course_segment_s=1.0,
    )
    trial.results = []
    trial.recorder = SimpleNamespace(assert_live=lambda: None)
    trial.event = lambda *_args, **_kwargs: None
    trial.wait_job = lambda *_args, **_kwargs: {"ok": True}
    trial.pull_policy_logs = lambda *_args, **_kwargs: []
    trial.snapshot = lambda *_args, **_kwargs: None
    trial.three_fresh_health_samples = lambda **_kwargs: []

    clock = _Clock()
    command_times = iter(live_times)
    calls: list[str] = []

    def request(path, _body=None):
        calls.append(path)
        if path == "/api/rl/drive/start":
            return {"ok": True}
        if path == "/api/rl/drive/stop":
            return {"ok": True}
        if path == "/api/rl/drive/cmd":
            clock.now += 0.7
            t_s = next(command_times)
            return {"ok": True, "live": {"t_s": t_s}}
        raise AssertionError(path)

    trial.request = request
    monkeypatch.setattr(walk_trial.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(walk_trial.time, "sleep", clock.sleep)
    return trial, calls


def test_drive_leg_waits_for_requested_active_time(monkeypatch):
    trial, calls = _drive_trial(
        monkeypatch,
        [None, 0.0, 0.9, 1.9, 2.9, 3.0],
    )

    trial.drive_leg("forward")

    assert calls.count("/api/rl/drive/cmd") == 6
    assert calls[-1] == "/api/rl/drive/stop"
    assert trial.results[0]["command_active_s"] == pytest.approx(3.0)


def test_drive_leg_stops_and_fails_after_bounded_startup_allowance(monkeypatch):
    trial, calls = _drive_trial(monkeypatch, [1.0] * 20)

    with pytest.raises(RuntimeError, match="did not reach 3.0s active"):
        trial.drive_leg("forward")

    assert calls[-1] == "/api/rl/drive/stop"
    assert calls.count("/api/rl/drive/stop") == 1


def test_direction_course_uses_active_time_delta_for_each_segment(monkeypatch):
    trial, calls = _drive_trial(
        monkeypatch,
        [
            0.0, 0.5, 1.0,
            1.0, 1.5, 2.0,
            2.0, 2.5, 3.0,
            3.0, 3.5, 4.0,
        ],
    )

    trial.direction_course()

    assert calls.count("/api/rl/drive/cmd") == 12
    assert calls[-1] == "/api/rl/drive/stop"
    assert [segment["active_s"] for segment in trial.results[0]["segments"]] == [
        pytest.approx(1.0),
        pytest.approx(1.0),
        pytest.approx(1.0),
        pytest.approx(1.0),
    ]
