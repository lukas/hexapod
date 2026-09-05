"""Off-robot regression tests for the walk-only hardware session wrapper."""
from __future__ import annotations

from types import SimpleNamespace
import csv
import json

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


def _policy_trial(walk: dict):
    trial = walk_trial.Trial.__new__(walk_trial.Trial)
    trial.args = SimpleNamespace(speed_m_s=0.08)
    trial.request = lambda _path: {"ok": True, "walk": walk}
    trial.event = lambda *_args, **_kwargs: None
    return trial


def _walk_meta(obs_dim: int) -> dict:
    return {
        "obs_dim": obs_dim,
        "joint_frame": "robot_abs",
        "joint_contract": "robot_abs_tibia_v2",
        "training_hz": 100.0,
        "walk_speed_min_m_s": 0.08,
        "walk_speed_max_m_s": 0.08,
        "phase_hz": 1.333333,
        "walk_yaw_cmd": True,
        "walk_phase_run_on_yaw": True,
    }


def test_trial_accepts_phase_yaw_mlp_contract():
    assert _policy_trial(_walk_meta(75)).validate_walk_policy()["obs_dim"] == 75


def test_trial_accepts_frozen_dual_gru_contract():
    walk = _walk_meta(81)
    walk.update(
        architecture="dual_gru",
        mode_onehot_order=["hold", "rise", "lower", "walk", "turn", "quad"],
    )
    assert _policy_trial(walk).validate_walk_policy()["obs_dim"] == 81


def test_trial_rejects_obs81_without_recurrent_architecture():
    walk = _walk_meta(81)
    walk.update(architecture="mlp", mode_onehot_order=[])
    with pytest.raises(RuntimeError, match="dual_gru|mode-onehot"):
        _policy_trial(walk).validate_walk_policy()


def test_trial_rejects_phase_yaw_policy_without_explicit_clock_contract():
    walk = _walk_meta(75)
    del walk["walk_phase_run_on_yaw"]
    with pytest.raises(RuntimeError, match="yaw-clock"):
        _policy_trial(walk).validate_walk_policy()


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


def _drive_trial(monkeypatch, live_samples: list[float | None | dict]):
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
    command_samples = iter(live_samples)
    calls: list[str] = []

    def request(path, _body=None):
        calls.append(path)
        if path == "/api/rl/drive/start":
            return {"ok": True}
        if path == "/api/rl/drive/stop":
            return {"ok": True}
        if path == "/api/rl/drive/cmd":
            clock.now += 0.7
            sample = next(command_samples)
            if not isinstance(sample, dict):
                sample = {
                    "t_s": sample,
                    "model": "walk",
                    "learned_policy_active": True,
                    "walk_has_engaged": True,
                }
            return {"ok": True, "live": sample}
        raise AssertionError(path)

    trial.request = request
    monkeypatch.setattr(walk_trial.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(walk_trial.time, "sleep", clock.sleep)
    return trial, calls


def test_drive_leg_waits_for_requested_active_time(monkeypatch):
    trial, calls = _drive_trial(
        monkeypatch,
        [None, 0.0, 0.9, 1.9, 2.9, 3.0, 3.1],
    )

    trial.drive_leg("forward")

    assert calls.count("/api/rl/drive/cmd") == 6
    assert calls[-1] == "/api/rl/drive/stop"
    assert trial.results[0]["actual_engaged_duration_s"] == pytest.approx(3.0)


def test_drive_leg_excludes_arming_time_from_engaged_duration(monkeypatch):
    arming = {
        "t_s": 2.0,
        "model": "arming",
        "learned_policy_active": False,
        "walk_has_engaged": False,
    }
    engaged = [
        {
            "t_s": t_s,
            "model": "walk",
            "learned_policy_active": True,
            "walk_has_engaged": True,
        }
        for t_s in (2.1, 3.1, 4.1, 5.1)
    ]
    trial, calls = _drive_trial(monkeypatch, [arming, *engaged])

    trial.drive_leg("forward")

    assert calls.count("/api/rl/drive/cmd") == 5
    assert trial.results[0]["last_live_t_s"] == pytest.approx(5.1)
    assert trial.results[0]["actual_engaged_duration_s"] == pytest.approx(3.0)


def test_drive_leg_stops_and_fails_after_bounded_startup_allowance(monkeypatch):
    trial, calls = _drive_trial(monkeypatch, [1.0] * 20)

    with pytest.raises(RuntimeError, match="3.0s of learned-walk engagement"):
        trial.drive_leg("forward")

    assert calls[-1] == "/api/rl/drive/stop"
    assert calls.count("/api/rl/drive/stop") == 1


def test_summary_exposes_actual_engaged_duration(tmp_path):
    trial = walk_trial.Trial.__new__(walk_trial.Trial)
    trial.output_dir = tmp_path
    trial.completed = True
    trial.results = [{"actual_engaged_duration_s": 3.05}]
    trial.args = SimpleNamespace(
        phases=["forward"], speed_m_s=0.08, duration_s=3.0,
        course_segment_s=2.0, joystick_response=False,
    )
    trial.request = lambda _path: {"ok": True, "walk": _walk_meta(74)}

    trial.write_summary()

    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["actual_engaged_duration_s"] == pytest.approx(3.05)


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


def test_joystick_response_keeps_one_session_and_records_neutral_hold(
        tmp_path, monkeypatch):
    trial = walk_trial.Trial.__new__(walk_trial.Trial)
    trial.output_dir = tmp_path
    trial.started = 100.0
    trial.results = []
    trial.recorder = SimpleNamespace(assert_live=lambda: None)
    trial.event = lambda *_args, **_kwargs: None
    trial.wait_job = lambda *_args, **_kwargs: {"ok": True}
    trial.pull_policy_logs = lambda *_args, **_kwargs: []
    trial.snapshot = lambda *_args, **_kwargs: None
    trial.three_fresh_health_samples = lambda **_kwargs: []

    clock = _Clock()
    session_t = 0.0
    calls: list[tuple[str, dict | None]] = []

    def request(path, body=None):
        nonlocal session_t
        calls.append((path, body))
        if path in ("/api/rl/drive/start", "/api/rl/drive/stop"):
            return {"ok": True}
        if path == "/api/rl/drive/cmd":
            session_t += 1.0
            zero = all(float(body[key]) == 0.0 for key in ("vx", "vy", "wz"))
            return {
                "ok": True,
                "live": {
                    "t_s": session_t,
                    "model": "hold" if zero else "walk",
                    "vx_ref": body["vx"], "vy_ref": body["vy"],
                    "wz_ref": body["wz"],
                },
            }
        raise AssertionError(path)

    trial.request = request
    monkeypatch.setattr(walk_trial.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(walk_trial.time, "sleep", clock.sleep)
    monkeypatch.setattr(walk_trial.time, "time", clock.monotonic)

    trial.joystick_response()

    assert [path for path, _ in calls].count("/api/rl/drive/start") == 1
    assert [path for path, _ in calls].count("/api/rl/drive/stop") == 1
    assert [item["name"] for item in trial.results[0]["segments"]] == [
        item[0] for item in walk_trial.JOYSTICK_RESPONSE_SEQUENCE
    ]
    neutral = [
        item for item in trial.results[0]["segments"]
        if item["name"].startswith("release_after_")
    ]
    assert all(item["neutral_to_hold_observed_s"] == pytest.approx(0.0)
               for item in neutral)
    with (tmp_path / "joystick_commands.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert {row["model"] for row in rows} == {"walk", "hold"}


def test_failure_summary_survives_unreachable_policy_endpoint(tmp_path):
    trial = walk_trial.Trial.__new__(walk_trial.Trial)
    trial.output_dir = tmp_path
    trial.completed = False
    trial.args = SimpleNamespace(
        phases=["forward"], speed_m_s=0.08, duration_s=3.0,
        course_segment_s=2.0, joystick_response=False,
    )
    trial.results = []
    trial.request = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        RuntimeError("network unavailable")
    )

    trial.write_summary(error="preflight failed")

    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["error"] == "preflight failed"
    assert summary["policy"] is None
    assert summary["policy_read_error"] == "network unavailable"
