"""Off-robot regression tests for the walk-only hardware session wrapper."""
from __future__ import annotations

from types import SimpleNamespace
import csv
import io
import json
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
    trial.args = SimpleNamespace(speed_m_s=0.08, duration_s=3.0,
                                 velocity_filter_alpha=alpha)
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
    if course:
        assert "active_duration_s" not in body
    else:
        assert body["active_duration_s"] == 3.0
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


def _course_trial(monkeypatch, live_times: list[float | None]):
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


def test_direction_course_uses_active_time_delta_for_each_segment(monkeypatch):
    trial, calls = _course_trial(
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
    trial.args = SimpleNamespace(joystick_start_phase=None)
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


def test_joystick_response_can_resume_at_exact_saved_phase(tmp_path, monkeypatch):
    trial = walk_trial.Trial.__new__(walk_trial.Trial)
    trial.output_dir = tmp_path
    trial.args = SimpleNamespace(joystick_start_phase="reverse")
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

    assert [item["name"] for item in trial.results[0]["segments"]] == [
        item[0] for item in walk_trial.JOYSTICK_RESPONSE_SEQUENCE[2:]
    ]
    assert [path for path, _ in calls].count("/api/rl/drive/start") == 1
    assert [path for path, _ in calls].count("/api/rl/drive/stop") == 1


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
    assert summary["execution"] == {
        "ok": False,
        "scope": "guarded_runner",
        "meaning": (
            "ok is true only when the bounded runner completed its requested "
            "control and safety sequence without a retained runner error."
        ),
    }
    assert summary["locomotion_assessment"]["status"] == (
        "not_assessed_after_runner_error"
    )
    assert summary["locomotion_assessment"]["success"] is None
    assert summary["policy"] is None
    assert summary["policy_read_error"] == "network unavailable"


def _communication_trial(tmp_path):
    trial = walk_trial.Trial.__new__(walk_trial.Trial)
    trial.output_dir = tmp_path
    trial.base = "http://fake-robot"
    trial.phase = "preflight"
    trial.communication_capture = {"artifacts": [], "errors": [], "markers": {}}
    trial.event = lambda *_args, **_kwargs: None
    return trial


def test_communication_capture_reuses_session_and_collects_run_rotation_parts(
        tmp_path, monkeypatch):
    trial = _communication_trial(tmp_path)
    calls = []
    start = {
        "ok": True, "active": True, "already_active": True,
        "communication_capture": True,
        "path": "/logs/current.jsonl",
        "paths": ["/logs/earlier.jsonl", "/logs/current.jsonl"],
    }
    end = {
        **start, "path": "/logs/next.jsonl",
        "paths": [*start["paths"], "/logs/next.jsonl"],
        "flushed_marker": "end-1", "queue_dropped": 3, "write_error": None,
    }
    statuses = iter([start, {**end, "flushed_marker": None}, end])

    def request(path, body=None):
        calls.append((path, body))
        assert path == "/api/telemetry"
        if body is None:
            return next(statuses)
        if body["action"] == "start":
            return start
        assert body["action"] == "mark"
        return {"ok": True, "marker_id": "end-1"}

    trial.request = request
    opened = []
    payload = b'{"record_type":"bus_tx","bytes_hex":"53"}\n'

    def open_log(url, timeout):
        opened.append(url)
        return io.BytesIO(payload)

    monkeypatch.setattr(walk_trial.urllib.request, "build_opener", lambda *_: (
        SimpleNamespace(open=open_log)))
    monkeypatch.setattr(walk_trial.time, "sleep", lambda _: None)

    trial.start_communication_capture()
    trial.collect_communication_capture()

    assert opened == [
        "http://fake-robot/api/logs/current.jsonl",
        "http://fake-robot/api/logs/next.jsonl",
    ]
    capture = trial.communication_capture
    assert capture["artifacts"] == ["robot_current.jsonl", "robot_next.jsonl"]
    assert all((tmp_path / name).read_bytes() == payload
               for name in capture["artifacts"])
    assert capture["end_marker_flushed"] is True
    assert capture["end"]["queue_dropped"] == 3
    assert capture["errors"] == []
    assert all(body is None or body["action"] != "stop" for _, body in calls)
    assert all(body is None or body["action"] != "start" for _, body in calls)


def test_old_recorder_is_not_enabled_by_communication_capture(tmp_path):
    trial = _communication_trial(tmp_path)
    calls = []

    def request(path, body=None):
        calls.append((path, body))
        return {"ok": True, "active": False, "piggyback_snapshots": True}

    trial.request = request

    trial.start_communication_capture()

    assert calls == [("/api/telemetry", None)]
    assert "does not capture raw communication" in trial.communication_capture["errors"][0]


def test_communication_failure_is_reported_without_failing_trial(tmp_path):
    trial = _communication_trial(tmp_path)
    trial.request = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        RuntimeError("recorder unavailable"))

    trial.start_communication_capture()
    trial.communication_mark("recovery_begin")
    trial.collect_communication_capture()

    assert trial.communication_capture["artifacts"] == []
    assert "recorder unavailable" in str(trial.communication_capture["errors"])


def test_communication_capture_reports_unflushed_tail_and_keeps_partial_evidence(
        tmp_path, monkeypatch):
    trial = _communication_trial(tmp_path)
    trial.communication_capture["start"] = {"path": "/logs/current.jsonl"}
    state = {
        "ok": True, "active": False, "path": "/logs/current.jsonl",
        "paths": ["/logs/current.jsonl"], "flushed_marker": None,
        "queue_dropped": 7, "write_error": "disk full",
    }
    trial.request = lambda _path, body=None: (
        {"ok": True, "marker_id": "never-flushed"} if body else state)
    clock = _Clock()
    monkeypatch.setattr(walk_trial.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(walk_trial.time, "sleep", clock.sleep)
    monkeypatch.setattr(walk_trial.urllib.request, "build_opener", lambda *_: (
        SimpleNamespace(open=lambda *_args, **_kwargs: io.BytesIO(b"partial\n"))))

    trial.collect_communication_capture()

    capture = trial.communication_capture
    assert clock.now <= 102.1
    assert capture["end_marker_flushed"] is False
    assert "may be incomplete" in capture["errors"][0]
    assert capture["end"]["write_error"] == "disk full"
    assert capture["artifacts"] == ["robot_current.jsonl"]


def test_communication_capture_files_and_loss_status_appear_in_summary(tmp_path):
    trial = _communication_trial(tmp_path)
    trial.completed = True
    trial.results = []
    trial.args = SimpleNamespace(
        phases=["forward"], speed_m_s=0.08, duration_s=3.0,
        course_segment_s=2.0, joystick_response=False,
    )
    trial.request = lambda *_args, **_kwargs: {"ok": True}
    trial.communication_capture.update({
        "artifacts": ["robot_bus.jsonl"],
        "end": {"queue_dropped": 2, "write_error": None},
    })

    trial.write_summary()

    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["ok"] is True
    assert summary["execution"]["ok"] is True
    assert summary["execution"]["scope"] == "guarded_runner"
    assert summary["locomotion_assessment"] == {
        "status": "requires_evidence_review",
        "success": None,
        "metric_displacement_available": False,
        "reason": (
            "Runner completion verifies command delivery and safety handling "
            "only. Review synchronized video or a calibrated phase-bound "
            "chassis trajectory to decide whether the requested translation "
            "or turn was achieved."
        ),
    }
    assert summary["artifacts"]["communication"] == ["robot_bus.jsonl"]
    assert summary["communication_capture"]["end"]["queue_dropped"] == 2


class _TrialClock:
    now = 0.0
    def monotonic(self):
        return self.now
    def time(self):
        return 1000.0 + self.now
    def sleep(self, duration):
        self.now += duration


def _drive_trial(monkeypatch, response_at):
    clock = _TrialClock()
    monkeypatch.setattr(walk_trial.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(walk_trial.time, "time", clock.time)
    monkeypatch.setattr(walk_trial.time, "sleep", clock.sleep)
    trial = walk_trial.Trial.__new__(walk_trial.Trial)
    trial.args = SimpleNamespace(speed_m_s=0.08, duration_s=3.0,
                                 velocity_filter_alpha=0.3)
    requests, events = [], []
    def request(path, body):
        requests.append((path, dict(body), clock.now))
        if path == "/api/rl/drive/cmd":
            return response_at(clock.now)
        return {"ok": True}
    trial.request = request
    trial.event = lambda name, detail="": events.append((name, detail))
    trial.recorder = SimpleNamespace(assert_live=lambda: None)
    trial.sample = lambda: None
    trial.wait_job = lambda *args: {
        "ok": True,
        "ended": "stopped",
        "active_duration_limit_s": trial.args.duration_s,
        "active_wall_time_s": trial.args.duration_s,
    }
    trial.pull_policy_logs = lambda *args: []
    trial.snapshot = lambda *args: None
    trial.three_fresh_health_samples = lambda **kwargs: []
    trial.results = []
    return trial, clock, requests, events


def _drive_live(t, *, arming=False, vx=0.08, stopping=None):
    return {"ok": True, "active": True, "live": {
        "t_s": round(t, 1), "model": "arming" if arming else "walk",
        "walk_has_engaged": True, "walk_arming": arming,
        "learned_policy_active": True, "stopping": stopping,
        "vx_cmd": vx, "vy_cmd": 0.0, "wz_cmd": 0.0,
    }}


def test_drive_duration_starts_after_confirmed_walk_and_excludes_initialization(monkeypatch):
    trial, clock, requests, events = _drive_trial(
        monkeypatch, lambda t: _drive_live(t, arming=t < 2.7))
    trial.drive_leg("forward")
    result = trial.results[0]
    assert 2.7 <= result["startup_duration_s"] <= 2.81
    assert 3.0 <= result["confirmed_active_window_s"] <= 3.051
    assert result["command_duration_s"] >= 5.7
    assert result["activation_unix_s"] == pytest.approx(
        1000.0 + result["activation_monotonic_s"])
    assert any(name == "drive_walk_activated" for name, _ in events)
    owner = requests[0][1]["command_owner"]
    assert len(owner) == 32
    commands = [body for path, body, _ in requests if path.endswith("/cmd")]
    assert commands and all(body["command_owner"] == owner for body in commands)
    assert all(body["vx"] == 0.08 and body["wz"] == 0.0 for body in commands)
    assert requests[-1][0].endswith("/stop")
    assert "command_owner" not in requests[-1][1]


def test_board_duration_completion_is_not_misclassified_as_transport_loss(monkeypatch):
    def response(t):
        if t < 2.9:
            return _drive_live(t)
        return {"ok": False, "active": False, "error": "no drive session"}

    trial, clock, requests, events = _drive_trial(monkeypatch, response)
    trial.wait_job = lambda *args: {
        "ok": True,
        "ended": "active walk cap 3s reached",
        "active_duration_limit_s": 3.0,
        "active_wall_time_s": 3.0,
    }
    trial.drive_leg("forward")

    assert trial.results[0]["trial_error"] is None
    assert any(name == "drive_server_duration_limit_observed"
               for name, _ in events)


def test_late_independent_stop_is_not_accepted_as_board_duration_cap(monkeypatch):
    # The controller keeps its three-second read-only tail inside the worker,
    # so /drive/cmd can still report active after learned motion has stopped.
    # The terminal wall time must prove the full requested window happened.
    trial, clock, requests, events = _drive_trial(monkeypatch, _drive_live)
    trial.wait_job = lambda *args: {
        "ok": True,
        "ended": "stopped",
        "active_duration_limit_s": 3.0,
        "active_wall_time_s": 2.9,
    }

    with pytest.raises(RuntimeError, match="active-duration evidence"):
        trial.drive_leg("forward")

    assert "active-duration evidence" in trial.results[0]["trial_error"]
    assert any(name == "drive_server_duration_limit_mismatch"
               for name, _ in events)
    assert not any(name == "drive_server_duration_limit_observed"
                   for name, _ in events)


@pytest.mark.parametrize("active_wall_time_s", [3.1001, 3.369])
def test_drive_rejects_controller_active_window_overrun(
        monkeypatch, active_wall_time_s):
    trial, _clock, _requests, events = _drive_trial(monkeypatch, _drive_live)
    trial.wait_job = lambda *args: {
        "ok": True,
        "ended": "active walk cap 3s reached",
        "active_duration_limit_s": 3.0,
        "active_wall_time_s": active_wall_time_s,
    }

    with pytest.raises(RuntimeError, match=r"\[3, 3.1\] seconds"):
        trial.drive_leg("forward")

    assert str(active_wall_time_s) in trial.results[0]["trial_error"]
    mismatches = [detail for name, detail in events
                  if name == "drive_server_duration_limit_mismatch"]
    assert mismatches[0]["accepted_active_duration_range_s"] == [3.0, 3.1]
    assert not any(name == "drive_server_duration_limit_observed"
                   for name, _ in events)


def test_drive_accepts_controller_active_window_at_upper_bound(monkeypatch):
    trial, _clock, _requests, events = _drive_trial(monkeypatch, _drive_live)
    trial.wait_job = lambda *args: {
        "ok": True,
        "ended": "active walk cap 3s reached",
        "active_duration_limit_s": 3.0,
        "active_wall_time_s": 3.1,
    }

    trial.drive_leg("forward")

    assert trial.results[0]["trial_error"] is None
    assert any(name == "drive_server_duration_limit_observed"
               for name, _ in events)


def test_each_drive_session_gets_a_distinct_command_owner():
    trial = walk_trial.Trial.__new__(walk_trial.Trial)
    trial.args = SimpleNamespace(velocity_filter_alpha=None)
    a = trial.drive_start_payload()
    b = trial.drive_start_payload()
    assert a["command_owner"] != b["command_owner"]
    assert trial._drive_command_owner == b["command_owner"]


@pytest.mark.parametrize("failure", ["inactive", "stopping", "countercommand", "stalled"])
def test_drive_stops_early_when_live_control_ends_or_changes(monkeypatch, failure):
    def response(t):
        if t < 0.3:
            return _drive_live(t)
        if failure == "inactive":
            return {"ok": True, "active": False}
        if failure == "stopping":
            return _drive_live(t, stopping="heartbeat_timeout")
        if failure == "countercommand":
            return _drive_live(t, vx=0.0)
        return _drive_live(0.3)
    trial, clock, requests, events = _drive_trial(monkeypatch, response)
    with pytest.raises(RuntimeError, match="ended|stopped|changed|advancing"):
        trial.drive_leg("forward")
    assert clock.now < 1.1
    assert requests[-1][0].endswith("/stop")
    assert any(name == "drive_duration" for name, _ in events)
    assert trial.results[0]["trial_error"]


def test_drive_startup_has_a_separate_bound_and_stops(monkeypatch):
    trial, clock, requests, events = _drive_trial(
        monkeypatch, lambda t: _drive_live(t, arming=True))
    with pytest.raises(RuntimeError, match="engage within 8 seconds"):
        trial.drive_leg("forward")
    assert 8.0 <= clock.now <= 8.051
    assert requests[-1][0].endswith("/stop")
    duration = next(detail for name, detail in events if name == "drive_duration")
    assert duration["activation_unix_s"] is None
    assert duration["confirmed_active_window_s"] == 0.0


def test_drive_camera_must_remain_live_before_another_command(monkeypatch):
    trial, clock, requests, events = _drive_trial(monkeypatch, _drive_live)
    checks = 0
    def assert_live():
        nonlocal checks
        checks += 1
        if checks > 1:
            raise RuntimeError("camera became stale")
    trial.recorder.assert_live = assert_live
    with pytest.raises(RuntimeError, match="camera became stale"):
        trial.drive_leg("forward")
    assert len([r for r in requests if r[0].endswith("/cmd")]) == 1
    assert requests[-1][0].endswith("/stop")


@pytest.mark.parametrize("course", [False, True])
def test_active_drive_reuses_command_live_without_extra_feedback(monkeypatch, course):
    trial, clock, requests, events = _drive_trial(monkeypatch, _drive_live)
    trial.args.course_segment_s = 0.1
    trial.args.duration_s = 0.1
    camera_checks, health_checks = [], []
    trial.recorder.assert_live = lambda: camera_checks.append(clock.now)
    trial.three_fresh_health_samples = lambda **kw: health_checks.append(kw)
    def no_feedback():
        pytest.fail("active drive must not add a separate feedback transaction")
    trial.sample = no_feedback

    if course:
        trial.direction_course()
    else:
        trial.drive_leg("forward")

    commands = [row for row in requests if row[0].endswith("/cmd")]
    live_events = [detail for name, detail in events if name == "drive_live"]
    assert len(camera_checks) == len(commands) == len(live_events)
    assert live_events == [_drive_live(stamp)["live"] for _, _, stamp in commands]
    assert health_checks == [{"require_armed": True}]
    assert all(path != "/api/feedback" for path, _, _ in requests)
    if course:
        assert sum(segment["command_samples"]
                   for segment in trial.results[0]["segments"]) == len(commands)
    else:
        assert trial.results[0]["command_samples"] == len(commands)
        assert trial.results[0]["transport"] == "drive_100hz_combined_snapshot"


def test_course_camera_must_remain_live_before_another_command(monkeypatch):
    trial, clock, requests, events = _drive_trial(monkeypatch, _drive_live)
    trial.args.course_segment_s = 0.1
    checks = 0
    def assert_live():
        nonlocal checks
        checks += 1
        if checks > 1:
            raise RuntimeError("camera became stale")
    trial.recorder.assert_live = assert_live
    with pytest.raises(RuntimeError, match="camera became stale"):
        trial.direction_course()
    assert len([r for r in requests if r[0].endswith("/cmd")]) == 1
    assert requests[-1][0].endswith("/stop")



def test_early_terminal_result_and_logs_preserved_before_original_error(monkeypatch):
    trial, clock, requests, events = _drive_trial(
        monkeypatch, lambda t: {"ok": False, "active": False, "error": "owner refused"})
    request = trial.request
    def terminal_request(path, body):
        reply = request(path, body)
        if path.endswith("/stop"):
            return {"ok": True, "active": False,
                    "result": {"ok": False, "error": "controller fault", "log": "rl_drive_x.csv"}}
        return reply
    trial.request = terminal_request
    def no_wait(*args):
        pytest.fail("terminal stop receipt should avoid another wait")
    trial.wait_job = no_wait
    trial.pull_policy_logs = lambda *args: ["robot_rl_drive_x.csv"]
    with pytest.raises(RuntimeError, match="owner refused"):
        trial.drive_leg("forward")
    assert trial.results[0]["result"]["error"] == "controller fault"
    assert trial.results[0]["robot_logs"] == ["robot_rl_drive_x.csv"]
    assert "owner refused" in trial.results[0]["trial_error"]


def test_original_drive_error_survives_missing_stop_terminal_and_logs(monkeypatch):
    trial, clock, requests, events = _drive_trial(
        monkeypatch, lambda t: {"ok": False, "active": False, "error": "original refusal"})
    request = trial.request
    def disconnected_stop(path, body):
        if path.endswith("/stop"):
            raise RuntimeError("stop unavailable")
        return request(path, body)
    def fail(*args):
        raise RuntimeError("artifacts unavailable")
    trial.request = disconnected_stop
    trial.wait_job = fail
    trial.pull_policy_logs = fail
    with pytest.raises(RuntimeError, match="original refusal"):
        trial.drive_leg("forward")
    assert "original refusal" in trial.results[0]["trial_error"]
    assert trial.results[0]["robot_logs"] == []
    assert trial.results[0]["result"]["ok"] is False
