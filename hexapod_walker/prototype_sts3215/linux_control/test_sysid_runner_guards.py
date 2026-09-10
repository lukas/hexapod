"""Offline fault-injection tests for deterministic sysid admission guards."""
from __future__ import annotations

import sys
import types


from sysid_runner import _telemetry_admission, run_sysid_protocol


def _sample(*, count: int = 18, voltage: float = 12.0) -> dict[int, dict]:
    return {joint: {"volt": voltage} for joint in range(count)}


class _Bus:
    def __init__(self, samples):
        self.samples = iter(samples)
        self.writes = []

    def read_all_feedback(self):
        return next(self.samples)

    def write_all(self, pose, **kwargs):
        self.writes.append(("all", list(pose)))

    def write_joint(self, joint, value, **kwargs):
        self.writes.append(("joint", joint, value))


def _admit(samples, *, clock=None):
    values = iter(clock or [0.0, 0.01, 0.1, 0.11, 0.2, 0.21])
    return _telemetry_admission(
        _Bus(samples),
        expected_live_motors=18,
        healthy_motor_samples=3,
        max_state_age_ms=100.0,
        voltage_bounds_v=(10.8, 13.0),
        clock=lambda: next(values),
        sleep=lambda _seconds: None,
    )


def test_telemetry_admission_accepts_three_fresh_full_samples():
    ok, error, evidence = _admit([_sample(), _sample(), _sample()])

    assert ok is True
    assert error == "ok"
    assert evidence["samples"] == 3
    assert evidence["servos_per_sample"] == 18
    assert evidence["min_voltage_v"] == 12.0


def test_telemetry_admission_rejects_incomplete_sample():
    ok, error, _ = _admit([_sample(), _sample(count=17), _sample()])

    assert ok is False
    assert "17/18 servos" in error


def test_telemetry_admission_rejects_wrong_servo_identity_set():
    wrong = _sample()
    wrong[18] = wrong.pop(17)
    ok, error, _ = _admit([_sample(), wrong, _sample()])

    assert ok is False
    assert "incomplete" in error


def test_telemetry_admission_rejects_stale_sample():
    ok, error, _ = _admit(
        [_sample(), _sample(), _sample()],
        clock=[0.0, 0.01, 0.1, 0.25, 0.3, 0.31],
    )

    assert ok is False
    assert "stale" in error


def test_telemetry_admission_rejects_nonadvancing_timestamp():
    ok, error, _ = _admit(
        [_sample(), _sample(), _sample()],
        clock=[0.0, 0.01, 0.01, 0.01, 0.2, 0.21],
    )

    assert ok is False
    assert "did not advance" in error


def test_telemetry_admission_rejects_voltage_out_of_bounds():
    ok, error, _ = _admit([_sample(), _sample(voltage=10.7), _sample()])

    assert ok is False
    assert "voltage out of bounds" in error


def test_relative_multi_joint_trajectory_retains_force_guard():
    row = [0.0] * 18
    result = run_sysid_protocol(
        None,
        {
            "sysid_protocol": 1,
            "name": "guard_test",
            "hz": 10,
            "segments": [{
                "kind": "rel_traj",
                "t_s": [0.0],
                "active": [7, 16],
                "q_deg": [row],
            }],
        },
    )

    assert result["ok"] is False
    assert "require force=true" in result["error"]


def test_remote_abort_reaches_final_limp(monkeypatch, tmp_path):
    import sysid_runner

    calls = []
    fake_demos = types.SimpleNamespace(
        _enable_torque=lambda bus, ids: calls.append("enable"),
        _live_robot_ids=lambda bus: {
            sysid_runner.joint_to_servo_id(joint) for joint in range(18)
        },
        _limp_all=lambda bus, ids: calls.append("limp"),
        _set_torque_limit=lambda bus, ids, value: calls.append(("limit", value)),
        _write_pose=lambda *args, **kwargs: calls.append("hold"),
    )
    monkeypatch.setitem(sys.modules, "inplace_demos", fake_demos)
    monkeypatch.setattr(sysid_runner, "validate", lambda protocol: [])
    monkeypatch.setattr(sysid_runner, "start_pose", lambda protocol: None)
    monkeypatch.setattr(
        sysid_runner,
        "materialize",
        lambda protocol: {
            "hz": 10.0,
            "ticks": [{"active": [0], "cmd": [0.0] * 18,
                       "mode": "rel", "seg": 0, "phase": "test"}],
            "seg_labels": ["test"],
        },
    )
    bus = _Bus([_sample(), _sample(), _sample()])
    bus.read_all_positions = lambda: {joint: 0.0 for joint in range(18)}

    result = run_sysid_protocol(
        bus,
        {"name": "abort_guard", "segments": [{"kind": "step"}]},
        abort_check=lambda: True,
        log_dir=tmp_path,
    )

    assert result["ok"] is False
    assert result["aborted"] is True
    assert "limp" in calls


def _runtime_stream_run(monkeypatch, tmp_path, *, glide: bool):
    import sysid_runner

    calls = []
    fake_demos = types.SimpleNamespace(
        _enable_torque=lambda bus, ids: calls.append("enable"),
        _live_robot_ids=lambda bus: {
            sysid_runner.joint_to_servo_id(joint) for joint in range(18)
        },
        _limp_all=lambda bus, ids: calls.append("limp"),
        _set_torque_limit=lambda bus, ids, value: calls.append(("limit", value)),
        _write_pose=lambda *args, **kwargs: calls.append("hold"),
    )
    monkeypatch.setitem(sys.modules, "inplace_demos", fake_demos)
    monkeypatch.setattr(sysid_runner, "validate", lambda protocol: [])
    monkeypatch.setattr(
        sysid_runner, "start_pose",
        lambda protocol: [10.0] * 18 if glide else None,
    )
    monkeypatch.setattr(
        sysid_runner,
        "materialize",
        lambda protocol: {
            "hz": 10.0,
            "ticks": [{"active": [0], "cmd": [0.0] * 18,
                       "mode": "rel", "seg": 0, "phase": "test"}],
            "seg_labels": ["test"],
        },
    )
    monkeypatch.setattr(sysid_runner.time, "sleep", lambda _seconds: None)
    bus = _Bus([_sample(), _sample(), _sample()])
    bus.read_all_positions = lambda: {joint: 0.0 for joint in range(18)}
    # Baseline advances.  In trajectory mode the segment-start sample also
    # advances.  The first post-command sample then repeats its predecessor.
    timestamps = iter(
        [0.0, 0.01, 0.02, 0.03, 0.04, 0.03]
        if not glide else [0.0, 0.01, 0.02, 0.01]
    )
    result = run_sysid_protocol(
        bus,
        {"name": "runtime_stream_guard", "segments": [{"kind": "step"}]},
        log_dir=tmp_path,
        runtime_state_clock=lambda: next(timestamps),
    )
    return result, bus, calls


def test_nonadvancing_state_timestamp_during_glide_aborts_before_further_motion(
        monkeypatch, tmp_path):
    result, bus, calls = _runtime_stream_run(
        monkeypatch, tmp_path, glide=True)

    assert result["ok"] is False
    assert "runtime state timestamp did not advance" in result["error"]
    assert len(bus.writes) == 1
    assert "limp" in calls


def test_nonadvancing_state_timestamp_during_trajectory_aborts_before_further_motion(
        monkeypatch, tmp_path):
    result, bus, calls = _runtime_stream_run(
        monkeypatch, tmp_path, glide=False)

    assert result["ok"] is False
    assert "runtime state timestamp did not advance" in result["error"]
    assert len(bus.writes) == 1
    assert "limp" in calls


def _glide_current_run(monkeypatch, tmp_path, *, hot_joint: int,
                       amps: float = 1.4):
    """Glide + one segment tick on joint 0, with ``hot_joint`` at ``amps``."""
    import sysid_runner

    calls = []
    fake_demos = types.SimpleNamespace(
        _enable_torque=lambda bus, ids: calls.append("enable"),
        _live_robot_ids=lambda bus: {
            sysid_runner.joint_to_servo_id(joint) for joint in range(18)
        },
        _limp_all=lambda bus, ids: calls.append("limp"),
        _set_torque_limit=lambda bus, ids, value: calls.append(("limit", value)),
        _write_pose=lambda *args, **kwargs: calls.append("hold"),
    )
    monkeypatch.setitem(sys.modules, "inplace_demos", fake_demos)
    monkeypatch.setattr(sysid_runner, "validate", lambda protocol: [])
    monkeypatch.setattr(sysid_runner, "start_pose", lambda protocol: [10.0] * 18)
    monkeypatch.setattr(
        sysid_runner,
        "materialize",
        lambda protocol: {
            "hz": 10.0,
            "ticks": [{"active": [0], "cmd": [0.0] * 18,
                       "mode": "rel", "seg": 0, "phase": "test"}],
            "seg_labels": ["test"],
        },
    )
    monkeypatch.setattr(sysid_runner.time, "sleep", lambda _seconds: None)
    # Every poll counts as fresh so the trip counters advance in wall-clock
    # time the test does not spend.
    monkeypatch.setattr(sysid_runner, "FEEDBACK_HZ", 1e6)

    def _feedback():
        return {joint: {"volt": 12.0, "temp_c": 33.0,
                        "current_a": amps if joint == hot_joint else 0.0}
                for joint in range(18)}

    bus = _Bus([])
    bus.read_all_feedback = _feedback
    pose = {joint: 0.0 for joint in range(18)}
    bus.read_all_positions = lambda: dict(pose)

    def _write_all(target, **kwargs):
        bus.writes.append(("all", list(target)))
        pose.update({joint: float(v) for joint, v in enumerate(target)})

    bus.write_all = _write_all
    return run_sysid_protocol(
        bus,
        {"name": "glide_current_guard", "max_current_a": 0.75,
         "current_trip_polls": 1, "hard_current_a": 3.0,
         "segments": [{"kind": "step"}]},
        log_dir=tmp_path,
    )


def test_loaded_knee_current_during_glide_does_not_trip_the_protocol_budget(
        monkeypatch, tmp_path):
    # 2026-09-10: the L4 ladder limped 2.2 s into its glide because joint 14
    # drew 1.38 A unfolding a weight-loaded knee off the floor, over the
    # protocol's 0.75 A MEASUREMENT budget.  The glide runs on GLIDE_CURRENT_A.
    result = _glide_current_run(monkeypatch, tmp_path, hot_joint=14)

    assert result["error"] is None, result["error"]
    assert result["ok"] is True


def test_protocol_current_budget_still_trips_once_the_segments_run(
        monkeypatch, tmp_path):
    # The wider budget is scoped to the glide: the measured motion keeps the
    # protocol's own limit, and glide polls do not carry into segment 0.
    result = _glide_current_run(monkeypatch, tmp_path, hot_joint=0)

    assert result["ok"] is False
    assert "overcurrent 1.40 A (limit 0.75" in result["error"]
