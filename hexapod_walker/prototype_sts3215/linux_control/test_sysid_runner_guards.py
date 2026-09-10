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


def _admit(samples, *, clock=None, max_consecutive_incomplete=3):
    """Run admission over ``samples``.

    The default clock advances 10 ms per call forever, so a test that needs a
    RESAMPLE is not accidentally failed by running out of clock values. Tests
    that care about freshness pass their own explicit sequence.
    """
    if clock is None:
        def tick(counter=iter(range(10_000))):
            return next(counter) * 0.01
    else:
        values = iter(clock)

        def tick():
            return next(values)
    return _telemetry_admission(
        _Bus(samples),
        expected_live_motors=18,
        healthy_motor_samples=3,
        max_state_age_ms=100.0,
        voltage_bounds_v=(10.8, 13.0),
        max_consecutive_incomplete=max_consecutive_incomplete,
        clock=tick,
        sleep=lambda _seconds: None,
    )


def test_telemetry_admission_accepts_three_fresh_full_samples():
    ok, error, evidence = _admit([_sample(), _sample(), _sample()])

    assert ok is True
    assert error == "ok"
    assert evidence["samples"] == 3
    assert evidence["servos_per_sample"] == 18
    assert evidence["min_voltage_v"] == 12.0
    assert evidence["resampled_reads"] == 0


def test_telemetry_admission_resamples_one_dropped_servo_reply():
    """One dropped reply is telemetry noise, not a refusal.

    Regression for experiment 881677a0, 2026-09-10: two 156 s guarded runs
    were refused before any motion because a single read came back 17/18,
    while three fresh 18/18 samples taken seconds either side were clean.
    The command loop's own MAX_MISSED_READS trip and _read_pose_debounced
    already required three consecutive misses; this guard did not.
    """
    ok, error, evidence = _admit(
        [_sample(count=17), _sample(), _sample(), _sample()])

    assert ok is True, error
    assert evidence["samples"] == 3
    assert evidence["resampled_reads"] == 1


def test_telemetry_admission_still_needs_three_CONSECUTIVE_good_samples():
    """A dropped reply mid-run resets the consecutive count; it never counts.

    Two good samples, a bad one, then only two more good ones is NOT three
    in a row, so admission is still refused. This is the property that makes
    the resample above a debounce rather than a weakening.
    """
    # Two good then one dropped, repeated: never three in a row, and the
    # read budget is exhausted without admission.
    ok, error, _ = _admit([_sample(), _sample(), _sample(count=17)] * 3)

    assert ok is False
    assert "consecutive healthy samples" in error


def test_telemetry_admission_rejects_persistently_incomplete_stream():
    """A genuinely absent servo still refuses, after three consecutive reads."""
    ok, error, _ = _admit([_sample(count=17)] * 6)

    assert ok is False
    assert "17/18 servos" in error
    assert "3 consecutive reads" in error


def test_telemetry_admission_rejects_wrong_servo_identity_set():
    wrong = _sample()
    wrong[18] = wrong.pop(17)
    ok, error, _ = _admit([wrong] * 6)

    assert ok is False
    assert "incomplete" in error


def test_telemetry_admission_rejects_persistently_stale_samples():
    ok, error, _ = _admit(
        [_sample()] * 6,
        clock=[0.0, 0.25, 0.3, 0.55, 0.6, 0.85, 0.9, 1.15, 1.2, 1.45],
    )

    assert ok is False
    assert "stale" in error


def test_telemetry_admission_rejects_nonadvancing_timestamp():
    ok, error, _ = _admit(
        [_sample()] * 8,
        clock=[0.0, 0.01] + [0.01] * 40,
    )

    assert ok is False


def test_telemetry_admission_rejects_voltage_out_of_bounds_immediately():
    """A rail outside bounds is an electrical fault, never resampled away."""
    ok, error, _ = _admit(
        [_sample(), _sample(voltage=10.7), _sample(), _sample(), _sample()])

    assert ok is False
    assert "voltage out of bounds" in error


def test_telemetry_admission_rejects_a_bus_that_keeps_raising():
    class _Dead:
        def read_all_feedback(self):
            raise OSError("bus gone")

    ok, error, _ = _telemetry_admission(
        _Dead(), expected_live_motors=18, healthy_motor_samples=3,
        max_state_age_ms=100.0, voltage_bounds_v=(10.8, 13.0),
        clock=lambda: 0.0, sleep=lambda _s: None)

    assert ok is False
    assert "bus gone" in error


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
