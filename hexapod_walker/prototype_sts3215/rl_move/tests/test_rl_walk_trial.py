"""Off-robot regression tests for the walk-only hardware session wrapper."""
from __future__ import annotations

from types import SimpleNamespace
import sys

import pytest

from rl_move.scripts import run_rl_walk_trial as walk_trial


@pytest.mark.parametrize("alpha", ["nan", "inf", "-0.1", "1.1"])
def test_bad_velocity_alpha_refused_before_trial_setup(tmp_path, monkeypatch, alpha):
    monkeypatch.setattr(sys, "argv", ["trial", "--output-dir", str(tmp_path),
        "--walk-transport", "drive", "--velocity-filter-alpha", alpha])
    with pytest.raises(SystemExit) as error:
        walk_trial.main()
    assert error.value.code == 2
    assert list(tmp_path.iterdir()) == []


def test_velocity_alpha_cannot_silently_apply_to_timed_walk(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["trial", "--output-dir", str(tmp_path),
        "--velocity-filter-alpha", "0.8"])
    with pytest.raises(SystemExit) as error:
        walk_trial.main()
    assert error.value.code == 2
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("alpha", [None, 0.0, 0.8, 1.0])
@pytest.mark.parametrize("course", [False, True])
def test_trial_drive_start_forwards_optional_filter(alpha, course):
    trial = walk_trial.Trial.__new__(walk_trial.Trial)
    trial.args = SimpleNamespace(speed_m_s=0.08, velocity_filter_alpha=alpha)
    requests = []
    trial.request = lambda path, body: requests.append((path, body)) or {"ok": False}
    trial.event = lambda *a: None
    with pytest.raises(RuntimeError, match="drive start refused"):
        if course:
            trial.direction_course()
        else:
            trial.drive_leg("forward")
    assert len(requests) == 1
    path, body = requests[0]
    assert path == "/api/rl/drive/start"
    if alpha is None:
        assert "velocity_filter_alpha" not in body
    else:
        assert body["velocity_filter_alpha"] == alpha


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
