from pathlib import Path
from types import SimpleNamespace
import sys
import threading

import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT / "linux_control") not in sys.path:
    sys.path.insert(0, str(_ROOT / "linux_control"))

import rl_policy  # noqa: E402
from rl_move.robot_state import RobotState  # noqa: E402


class _Debug:
    def __init__(self, order):
        self.order = order
        self.events = []

    def event(self, name, **fields):
        self.order.append(f"event:{name}")
        self.events.append((name, fields))


class _Bus:
    def __init__(self, order, *, fail_write=False):
        self.order = order
        self.fail_write = fail_write
        self.commands = []

    def write_all(self, command, *, speed, acc):
        self.order.append("write")
        if self.fail_write:
            raise RuntimeError("injected write failure")
        self.commands.append((command, speed, acc))


class _Estimator:
    def __init__(self, order, states):
        self.order = order
        self.states = list(states)
        self.commanded = []

    def set_commanded(self, command):
        self.order.append("set_commanded")
        self.commanded.append(np.asarray(command).copy())

    def update(self, *, want_full_feedback):
        assert want_full_feedback is True
        self.order.append("sample")
        return self.states.pop(0) if self.states else None


class _Drive:
    def __init__(self, order):
        self.order = order
        self._lock = threading.Lock()
        self.armed = False
        self.status = ""

    def _torque_all(self, enabled):
        self.order.append(f"torque:{enabled}")


def _state(*, roll_deg=0.0, bus_ok=True):
    return SimpleNamespace(
        joint_position=np.full(rl_policy.N_JOINTS, 0.4),
        imu_roll=roll_deg / rl_policy.RAD2DEG,
        imu_pitch=0.0,
        imu_gyro=np.zeros(3),
        bus_ok=bus_ok,
        imu_ok=True,
        timing={},
    )


def _robot_state(*, bus_ok=True):
    zeros = np.zeros(rl_policy.N_JOINTS)
    return RobotState(
        timestamp=0.0,
        joint_position=zeros.copy(),
        joint_velocity=zeros.copy(),
        imu_roll=0.0,
        imu_pitch=0.0,
        imu_yaw=0.0,
        imu_gyro=np.zeros(3),
        imu_accel=np.zeros(3),
        commanded_position=zeros.copy(),
        bus_ok=bus_ok,
        imu_ok=True,
        timing={"source": "stop_ordering_fault_matrix"},
    )


def _run(monkeypatch, states, *, fail_write=False):
    order = []
    bus = _Bus(order, fail_write=fail_write)
    drive = _Drive(order)
    est = _Estimator(order, states)
    debug = _Debug(order)
    monkeypatch.setattr(
        rl_policy, "_set_weight_bearing_torque",
        lambda _bus: order.append("weight_bearing_torque"),
    )
    fallback = np.linspace(-0.2, 0.2, rl_policy.N_JOINTS)
    held = rl_policy._hold_after_stream_loss(  # noqa: SLF001
        bus, drive, est, fallback,
        write_speed=800, write_acc=40, policy_dt=0.0,
        debug=debug, max_tilt_deg=25.0,
    )
    return SimpleNamespace(
        held=held, order=order, bus=bus, drive=drive, est=est,
        debug=debug, fallback=fallback,
    )


def test_fallback_hold_write_precedes_foreground_resample(monkeypatch):
    run = _run(monkeypatch, [None, _state()])

    assert run.held is True
    assert run.order.index("write") < run.order.index("sample")
    np.testing.assert_allclose(run.est.commanded[0], run.fallback)
    np.testing.assert_allclose(
        run.bus.commands[0][0], run.fallback * rl_policy.RAD2DEG,
    )
    assert len(run.bus.commands) == 1
    assert "weight_bearing_torque" not in run.order[:run.order.index("write")]
    assert "torque:True" not in run.order[:run.order.index("write")]


def test_snapshot_bus_not_ok_is_skipped_after_fallback_write(monkeypatch):
    run = _run(monkeypatch, [_state(bus_ok=False), _state()])

    assert run.held is True
    assert run.order.index("write") < run.order.index("sample")
    assert run.order.count("sample") == 2
    assert len(run.bus.commands) == 1
    np.testing.assert_allclose(
        run.bus.commands[0][0], run.fallback * rl_policy.RAD2DEG,
    )


def test_fresh_tilted_pose_is_diagnostic_only(monkeypatch):
    run = _run(monkeypatch, [_state(roll_deg=29.0)])

    assert run.held is False
    assert len(run.bus.commands) == 1
    np.testing.assert_allclose(
        run.bus.commands[0][0], run.fallback * rl_policy.RAD2DEG,
    )
    sampled = next(fields for name, fields in run.debug.events
                   if name == "hold_after_stream_loss_sampled")
    assert sampled["tilt_within_envelope"] is False
    assert sampled["reanchored"] is False
    assert any(name == "hold_after_stream_loss_unconfirmed"
               for name, _fields in run.debug.events)


def test_missing_fresh_diagnostic_sample_does_not_report_hold(monkeypatch):
    run = _run(monkeypatch, [None] * 5)

    assert run.held is False
    assert len(run.bus.commands) == 1
    assert run.order.index("write") < run.order.index("sample")
    assert any(name == "hold_after_stream_loss_unconfirmed"
               for name, _fields in run.debug.events)


def test_write_failure_does_not_resample_or_limp(monkeypatch):
    run = _run(monkeypatch, [_state()], fail_write=True)

    assert run.held is False
    assert "sample" not in run.order
    assert "torque:False" not in run.order
    assert run.order.count("weight_bearing_torque") == 1
    assert run.order.index("write") < run.order.index("weight_bearing_torque")
    assert ("hold_after_stream_loss_write_failed", {}) in run.debug.events


def test_interlock_triggers_at_eleven_consecutive_stale_ticks():
    class _StaleSampler:
        max_age_s = 0.15
        motion_ready = True

        def __init__(self):
            self.calls = 0

        def latest(self):
            self.calls += 1
            return _robot_state(bus_ok=False), 0.02, {"samples": self.calls}

    bus = _Bus([])
    sampler = _StaleSampler()
    good = _robot_state()
    out = rl_policy._stream_target_async(  # noqa: SLF001
        bus, sampler,
        np.zeros(rl_policy.N_JOINTS),
        np.ones(rl_policy.N_JOINTS) * 0.1,
        t_next=0.0, inner_steps=1, inner_dt=0.0,
        write_speed=800, write_acc=40,
        abort_check=lambda: False,
        last_good_state=good,
        stale_ticks=0,
        max_stale_ticks=rl_policy.DRIVE_STREAM_STALE_TICKS,
    )

    _state_out, _next, _overruns, err, stale_ticks, stale_samples, _timing = out
    assert rl_policy.DRIVE_STREAM_STALE_TICKS == 10
    assert err == "feedback stale during stream"
    assert stale_ticks == 11
    assert stale_samples == 11
    assert sampler.calls == 11
    assert bus.commands == []


def test_success_callback_tracks_only_targets_written_to_bus():
    class _FreshSampler:
        max_age_s = 0.15
        motion_ready = True

        def latest(self):
            return _robot_state(), 0.02, {"samples": 1}

        def set_commanded(self, _command):
            pass

    bus = _Bus([])
    written = []
    target = np.ones(rl_policy.N_JOINTS) * 0.1
    out = rl_policy._stream_target_async(  # noqa: SLF001
        bus, _FreshSampler(), np.zeros(rl_policy.N_JOINTS), target,
        t_next=0.0, inner_steps=1, inner_dt=0.0,
        write_speed=800, write_acc=40, abort_check=lambda: False,
        last_good_state=_robot_state(), on_write_success=written.append,
    )

    assert out[3] == ""
    assert len(written) == 1
    np.testing.assert_allclose(written[0], target)
    np.testing.assert_allclose(bus.commands[0][0], target * rl_policy.RAD2DEG)
