"""Offline fault-injection tests for deterministic sysid admission guards."""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _path in (_HERE, _HERE.parent / "motor_setup"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from sysid_runner import _telemetry_admission


def _sample(*, count: int = 18, voltage: float = 12.0) -> dict[int, dict]:
    return {joint: {"volt": voltage} for joint in range(count)}


class _Bus:
    def __init__(self, samples):
        self.samples = iter(samples)

    def read_all_feedback(self):
        return next(self.samples)


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
