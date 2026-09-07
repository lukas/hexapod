from types import SimpleNamespace
from pathlib import Path
import os
import subprocess
import sys
import threading
import time
import csv

import numpy as np
import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT / "linux_control") not in sys.path:
    sys.path.insert(0, str(_ROOT / "linux_control"))

import rl_policy  # noqa: E402
from rl_move.robot_state import RobotState, RobotStateEstimator  # noqa: E402


def _policy(meta):
    return SimpleNamespace(meta=dict(meta))


def _state(*, bus_ok=True, timestamp=0.0, health=False, timing=None,
           load=12.0, current=0.4, temperature=31.0):
    z = np.zeros(rl_policy.N_JOINTS, dtype=float)
    return RobotState(
        timestamp=float(timestamp),
        joint_position=z.copy(),
        joint_velocity=z.copy(),
        imu_roll=0.0,
        imu_pitch=0.0,
        imu_yaw=0.0,
        imu_gyro=np.zeros(3, dtype=float),
        imu_accel=np.zeros(3, dtype=float),
        commanded_position=z.copy(),
        servo_load=(np.full(rl_policy.N_JOINTS, float(load))
                    if health else None),
        servo_current=(np.full(rl_policy.N_JOINTS, float(current))
                       if health else None),
        servo_temperature=(np.full(rl_policy.N_JOINTS, float(temperature))
                           if health else None),
        bus_ok=bus_ok,
        imu_ok=True,
        timing=(dict(timing) if timing is not None else
                {"source": "fake_state"}),
    )


def _complete_health_timing(*, source="fake_async", **extra):
    timing = {
        "source": source,
        "full_feedback": True,
        "full_feedback_complete": True,
        "full_feedback_count": rl_policy.N_JOINTS,
        "full_feedback_ids": list(range(rl_policy.N_JOINTS)),
        "feedback_sample_fresh": True,
        "feedback_complete": True,
        "feedback_valid_count": rl_policy.N_JOINTS,
        "feedback_valid_ids": list(range(rl_policy.N_JOINTS)),
        "feedback_missing_ids": [],
    }
    timing.update(extra)
    return timing


class _FakeBus:
    def __init__(self):
        self.writes = 0

    def write_all(self, _deg, *, speed, acc):
        self.writes += 1


def _snapshot(seq, *, gx_dps=0.0, pos_age_ms=1.0, imu_age_ms=1.0):
    return {
        "seq": seq,
        "pos_age_ms": pos_age_ms,
        "imu_age_ms": imu_age_ms,
        "pos_deg": {j: 0.0 for j in range(rl_policy.N_JOINTS)},
        "speed_deg_s": {j: 0.0 for j in range(rl_policy.N_JOINTS)},
        "imu": {
            "ax_g": 0.0, "ay_g": 0.0, "az_g": 1.0,
            "gx_dps": gx_dps, "gy_dps": 0.0, "gz_dps": 0.0,
        },
    }


class _AsyncHealthBus(_FakeBus):
    has_stream = True

    def __init__(self, seqs=None, *, current=0.4):
        super().__init__()
        self.seqs = list(seqs or range(1, 1000))
        self.last_seq = 0
        self.current = current
        self.feedback_reads = 0

    def read_snapshot(self):
        if self.seqs:
            self.last_seq = self.seqs.pop(0)
        return _snapshot(self.last_seq)

    def read_all_feedback(self):
        self.feedback_reads += 1
        return {
            j: {"load_pct": 12.0, "current_a": self.current,
                "temp_c": 31.0}
            for j in range(rl_policy.N_JOINTS)
        }


class _FakeStepBus(_FakeBus):
    has_stream = True

    def __init__(self, snaps=None):
        super().__init__()
        self.steps = 0
        self.snaps = list(snaps or [])
        self.commands = []

    def step_all(self, deg, *, speed, acc):
        self.steps += 1
        self.commands.append(np.asarray(deg, dtype=float).copy())
        if self.snaps:
            return self.snaps.pop(0)
        return {
            "seq": self.steps,
            "pos_age_ms": 1,
            "imu_age_ms": 1,
            "pos_deg": {j: 0.0 for j in range(rl_policy.N_JOINTS)},
            "imu": {
                "ax_g": 0.0, "ay_g": 0.0, "az_g": 1.0,
                "gx_dps": 0.0, "gy_dps": 0.0, "gz_dps": 0.0,
            },
        }


class _PreflightBus:
    def __init__(self, q_deg):
        self.q_deg = list(q_deg)

    def read_all_positions(self):
        return {j: float(v) for j, v in enumerate(self.q_deg)}

    def read_imu(self, *, apply_calib=True):
        return {
            "ax_g": 0.0, "ay_g": 0.0, "az_g": 1.0,
            "gx_dps": 0.0, "gy_dps": 0.0, "gz_dps": 0.0,
        }


class _FakeEstimator:
    def __init__(self, states):
        self._states = list(states)
        self.commanded = []
        self.snapshots = []

    def set_commanded(self, q):
        self.commanded.append(np.asarray(q, dtype=float).copy())

    def update(self):
        return self._states.pop(0) if self._states else _state()

    def update_from_snapshot(self, snap):
        self.snapshots.append(dict(snap))
        return self.update()


class _FakeSampler:
    def __init__(self, states=None, *, age_s=0.01,
                 max_age_s=rl_policy.DRIVE_ASYNC_STATE_MAX_AGE_S):
        self.states = list(states or [_state()])
        self.age_s = age_s
        self.max_age_s = max_age_s
        self.commanded = []

    def set_commanded(self, q):
        self.commanded.append(np.asarray(q, dtype=float).copy())

    def latest(self):
        state = self.states[-1] if self.states else None
        return state, self.age_s, {
            "samples": len(self.states),
            "good_samples": len([s for s in self.states if s.bus_ok]),
        }


def test_policy_bus_profile_prefers_metadata():
    cfg = {"bus": {"write_speed": 400, "write_acc": 20}}

    assert rl_policy._policy_bus_profile(  # noqa: SLF001
        _policy({"bus_write_speed": 1500, "bus_write_acc": 80}), cfg
    ) == (1500, 80)


def test_policy_bus_profile_falls_back_to_config():
    cfg = {"bus": {"write_speed": 500, "write_acc": 30}}

    assert rl_policy._policy_bus_profile(_policy({}), cfg) == (500, 30)  # noqa: SLF001


def test_inner_stream_plan_noops_at_100hz_default():
    cfg = {"control": {"inner_hz": 100}}

    steps, actual_hz, inner_dt = rl_policy._inner_stream_plan(  # noqa: SLF001
        _policy({"control_hz": 100}), cfg, policy_hz=100
    )

    assert steps == 1
    assert actual_hz == pytest.approx(100.0)
    assert inner_dt == pytest.approx(0.01)


def test_legacy_policy_streams_25hz_decisions_at_100hz_inner_rate():
    cfg = {"control": {"inner_hz": 100}}

    steps, actual_hz, inner_dt = rl_policy._inner_stream_plan(  # noqa: SLF001
        _policy({}), cfg, policy_hz=25
    )

    assert steps == 4
    assert actual_hz == pytest.approx(100.0)
    assert inner_dt == pytest.approx(0.01)


def test_inner_stream_plan_can_be_disabled():
    cfg = {"control": {"inner_hz": 25}}

    steps, actual_hz, inner_dt = rl_policy._inner_stream_plan(  # noqa: SLF001
        _policy({"inner_hz": 25}), cfg, policy_hz=25
    )

    assert steps == 1
    assert actual_hz == pytest.approx(25.0)
    assert inner_dt == pytest.approx(0.04)


def test_policy_timing_requires_declared_training_rate():
    with pytest.raises(ValueError, match="missing meta.training_hz"):
        rl_policy._policy_timing(_policy({}))  # noqa: SLF001

    explicit = rl_policy._policy_timing(  # noqa: SLF001
        _policy({"training_hz": 100})
    )

    assert explicit.policy_hz == pytest.approx(100.0)
    assert explicit.adapted is False
    assert rl_policy._check_policy_control_hz(  # noqa: SLF001
        _policy({"training_hz": 25}), "walk"
    ) is None


def test_policy_safety_slew_preserves_deg_per_second_for_legacy():
    cfg = {"control": {"hz": 100}, "safety": {"max_delta_q_deg": 0.375}}

    dq, explicit = rl_policy._policy_safety_max_delta_q_deg(  # noqa: SLF001
        _policy({}), cfg, policy_hz=25
    )

    assert explicit is False
    assert dq == pytest.approx(1.5)


def test_policy_safety_slew_prefers_trained_metadata():
    cfg = {"control": {"hz": 100}, "safety": {"max_delta_q_deg": 0.375}}

    dq, explicit = rl_policy._policy_safety_max_delta_q_deg(  # noqa: SLF001
        _policy({"max_delta_q_deg": 5.0}), cfg, policy_hz=25
    )

    assert explicit is True
    assert dq == pytest.approx(5.0)


def test_walk_start_options_use_sim_start_only():
    options, err = rl_policy._expected_start_options_deg("walk")  # noqa: SLF001

    assert err == ""
    assert options is not None
    names = [name for name, _pose, _tol in options]
    assert "sim_walk_start" in names
    assert names == ["sim_walk_start"]
    pose = dict((name, pose) for name, pose, _tol in options)["sim_walk_start"]
    assert pose.tolist() == pytest.approx([0.0, 20.0, 80.0] * 6)


def test_walk_preflight_reports_sim_walk_start():
    ok, reason, details = rl_policy.preflight(
        _PreflightBus([0.0, 20.0, 80.0] * 6), "walk")

    assert ok, reason
    assert details["start_pose"] == "sim_walk_start"
    assert details["max_pose_delta_deg"] == pytest.approx(0.0)


def test_neutral_drive_command_stays_in_hold():
    assert not rl_policy._drive_command_is_moving(  # noqa: SLF001
        0.0, 0.0, 0.0
    )


def test_drive_command_engages_walk_on_translation_or_yaw():
    assert rl_policy._drive_command_is_moving(  # noqa: SLF001
        0.001, 0.0, 0.0
    )
    for obs_dim in (75, 81, 93):
        assert rl_policy._drive_command_is_moving(  # noqa: SLF001
            0.0, 0.0, 0.01, walk_obs=obs_dim
        )
    assert not rl_policy._drive_command_is_moving(  # noqa: SLF001
        0.0, 0.0, 0.01, walk_obs=72
    )


def test_obs75_tail_matches_phase_plus_yaw_training_contract():
    tail = rl_policy._walk_obs_tail(  # noqa: SLF001
        75, 0.075, -0.0375, np.pi / 2.0, 0.25
    )

    assert tail.tolist() == pytest.approx([
        0.5, -0.25, 0.5, -0.25, 1.0, 0.0, 0.5,
    ])


def test_drive_walk_engages_on_first_real_command():
    assert rl_policy.DRIVE_WALK_ENGAGE_S == pytest.approx(0.0)


def test_drive_timing_trip_applies_to_policy_ticks_only():
    timing = SimpleNamespace(policy_hz=100.0, policy_dt=0.01)

    assert rl_policy._drive_timing_trip_reason(  # noqa: SLF001
        "hold", None, 0, timing, 0.025, 1
    ) is None
    assert rl_policy._drive_timing_trip_reason(  # noqa: SLF001
        "walk", None, 0, timing, 0.025, 1
    ) is None
    assert rl_policy._drive_timing_trip_reason(  # noqa: SLF001
        "walk", None, rl_policy.DRIVE_TIMING_STARTUP_GRACE_TICKS,
        timing, 0.025, 1
    ) is None
    assert "consecutive" in rl_policy._drive_timing_trip_reason(  # noqa: SLF001
        "walk", None, rl_policy.DRIVE_TIMING_STARTUP_GRACE_TICKS + 20,
        timing, 0.025, rl_policy.DRIVE_TIMING_MAX_CONSECUTIVE_LATE
    )
    assert rl_policy._drive_timing_trip_reason(  # noqa: SLF001
        "walk", None, rl_policy.DRIVE_TIMING_STARTUP_GRACE_TICKS + 20,
        timing, rl_policy.DRIVE_TIMING_HARD_LAG_S + 0.001, 1
    ) is None
    assert "hard misses" in rl_policy._drive_timing_trip_reason(  # noqa: SLF001
        "walk", None, rl_policy.DRIVE_TIMING_STARTUP_GRACE_TICKS + 21,
        timing, rl_policy.DRIVE_TIMING_HARD_LAG_S + 0.001,
        rl_policy.DRIVE_TIMING_HARD_LAG_CONSECUTIVE,
    )
    assert "missed the 100 Hz deadline" in rl_policy._drive_timing_trip_reason(  # noqa: SLF001
        "walk", None, rl_policy.DRIVE_TIMING_STARTUP_GRACE_TICKS + 22,
        timing, rl_policy.DRIVE_TIMING_CRITICAL_LAG_S + 0.001, 1,
    )


def test_async_snapshot_sampler_is_lower_rate_than_policy_loop():
    assert rl_policy.DRIVE_ASYNC_SNAPSHOT_HZ == pytest.approx(10.0)
    assert rl_policy.DRIVE_ASYNC_STATE_MAX_AGE_S == pytest.approx(0.15)


def test_async_transport_probe_reports_sequence_and_source_ages():
    probe = rl_policy._probe_async_transport(  # noqa: SLF001
        _AsyncHealthBus(seqs=[0xFFFF, 0, 1]), samples=3,
        sample_gap_s=0.0)

    assert probe["source"] == "read_snapshot"
    assert probe["seq_first"] == 0xFFFF
    assert probe["seq_last"] == 1
    assert probe["seq_advance_count"] == 2
    assert probe["max_pos_age_ms"] == pytest.approx(1.0)
    assert probe["max_imu_age_ms"] == pytest.approx(1.0)
    assert probe["async_capable"] is True


def test_async_transport_probe_rejects_unsupported_before_motion():
    bus = _FakeBus()

    probe = rl_policy._probe_async_transport(  # noqa: SLF001
        bus, sample_gap_s=0.0)

    assert probe["async_capable"] is False
    assert probe["source"] == "unsupported"
    assert "unavailable" in probe["error"]
    assert bus.writes == 0


def test_only_high_rate_stance_moves_use_async_transport():
    assert rl_policy._policy_move_uses_async("stand", 100.0)  # noqa: SLF001
    assert rl_policy._policy_move_uses_async("lower", 100.0)  # noqa: SLF001
    assert not rl_policy._policy_move_uses_async("stand", 50.0)  # noqa: SLF001
    assert not rl_policy._policy_move_uses_async("lower", 25.0)  # noqa: SLF001
    assert not rl_policy._policy_move_uses_async("walk", 100.0)  # noqa: SLF001


@pytest.mark.parametrize("mode", ["stand", "lower", "walk"])
@pytest.mark.parametrize("training_hz", [25.0, 50.0, 100.0])
def test_every_learned_move_requires_sequenced_transport_before_arm(
        monkeypatch, mode, training_hz):
    class _Policy:
        meta = {
            "name": "probe-test",
            "obs_dim": 72 if mode == "walk" else 68,
            "training_hz": training_hz,
            "joint_frame": rl_policy.FRAME_ROBOT_ABS,
            "joint_contract": rl_policy.JOINT_CONTRACT,
            "profile": {
                "stand": {"hold_s": 0.0, "ramp_s": 1.0,
                          "target_m": 0.1, "total_s": 1.0},
                "lower": {"hold_s": 0.0, "ramp_s": 1.0,
                          "target_m": -0.05, "total_s": 1.0},
            },
        }

    class _Debug:
        def __init__(self, *_args, **_kwargs):
            pass

        def event(self, *_args, **_kwargs):
            pass

        def attach(self, result):
            return result

        def close(self, _result=None):
            pass

    class _NoMotionBus:
        def __init__(self):
            self.writes = 0
            self.torque_enables = 0

        def write_all(self, *_args, **_kwargs):
            self.writes += 1

        def enable_all_torque(self, *_args, **_kwargs):
            self.torque_enables += 1

    bus = _NoMotionBus()
    drive = SimpleNamespace(bus=bus, dry_run=False)
    probe_calls = []
    monkeypatch.setattr(rl_policy, "NumpyPolicy", lambda _path: _Policy())
    monkeypatch.setattr(rl_policy, "_RunDebug", _Debug)
    monkeypatch.setattr(
        rl_policy, "preflight",
        lambda *_args, **_kwargs: (
            True, "", {"q_deg": [0.0] * rl_policy.N_JOINTS,
                       "start_pose": "sim_walk_start"}),
    )
    monkeypatch.setattr(
        rl_policy, "_preflight_start_target_deg",
        lambda *_args, **_kwargs: (
            np.zeros(rl_policy.N_JOINTS), ""),
    )

    def reject_probe(_bus):
        probe_calls.append(_bus)
        return {"async_capable": False, "error": "no fresh sequence"}

    monkeypatch.setattr(rl_policy, "_probe_async_transport", reject_probe)

    result = rl_policy._run_policy_move_impl(  # noqa: SLF001
        drive, mode, rot60=False)

    assert result["ok"] is False
    assert "sequenced transport unavailable before arm" in result["error"]
    assert probe_calls == [bus]
    assert bus.writes == 0
    assert bus.torque_enables == 0


def test_async_sampler_caps_age_and_delivers_health_freshness_once():
    bus = _AsyncHealthBus()
    sampler = rl_policy._AsyncSnapshotSampler(  # noqa: SLF001
        bus, {},
        initial_state=_state(timestamp=time.monotonic(), health=True),
        hz=200.0, max_age_s=9.0)
    assert sampler.max_age_s == pytest.approx(
        rl_policy.DRIVE_ASYNC_STATE_MAX_AGE_S)
    sampler.start()
    deadline = time.monotonic() + 0.5
    while sampler.stats()["samples"] < 1 and time.monotonic() < deadline:
        time.sleep(0.001)
    sampler.stop()

    first, age_first, _ = sampler.latest()
    second, age_second, _ = sampler.latest()

    assert bus.feedback_reads == sampler.stats()["good_samples"]
    assert bus.feedback_reads >= 1
    assert age_first is not None and age_first <= sampler.max_age_s
    assert age_second is not None and age_second <= sampler.max_age_s
    assert first.timing["async_sample_seq"] > 0
    assert first.timing["async_sample_fresh"] is True
    assert first.timing["async_health_fresh"] is True
    assert first.timing["full_feedback"] is True
    assert second.timing["async_sample_seq"] == first.timing["async_sample_seq"]
    assert second.timing["async_sample_fresh"] is False
    assert second.timing["async_health_fresh"] is False
    assert second.timing["full_feedback"] is False
    # Cached values remain available for diagnostics/logging...
    assert second.servo_current is not None
    assert second.servo_temperature is not None
    assert rl_policy._state_for_async_safety(first).servo_current is not None  # noqa: SLF001
    # ...but cannot advance a safety debounce twice.
    safety_state = rl_policy._state_for_async_safety(second)  # noqa: SLF001
    assert safety_state.servo_load is None
    assert safety_state.servo_current is None
    assert safety_state.servo_temperature is None


def test_async_ready_requires_advancing_samples_and_fresh_health():
    sampler = rl_policy._AsyncSnapshotSampler(  # noqa: SLF001
        _AsyncHealthBus(), {}, hz=200.0, max_age_s=0.1)
    sampler.start()
    state, details, err = rl_policy._await_async_sampler_ready(  # noqa: SLF001
        sampler, lambda: False, min_good_samples=3, timeout_s=0.5)
    sampler.stop()

    assert err == ""
    assert state is not None
    assert details["good_sequences"] >= 3
    assert details["fresh_health"] is True
    assert details["sampler"]["motion_ready"] is True


def test_async_sampler_requires_advancing_wrap_aware_mcu_sequence_and_age():
    sampler = rl_policy._AsyncSnapshotSampler(  # noqa: SLF001
        _FakeBus(), {}, hz=10.0, max_age_s=0.15)

    def stream_state(seq, *, pos_age_ms=1.0, imu_age_ms=1.0):
        return _state(
            timestamp=time.monotonic(),
            timing={
                "source": "read_snapshot",
                "snapshot_seq": seq,
                "pos_age_ms": pos_age_ms,
                "imu_age_ms": imu_age_ms,
            },
        )

    assert sampler._physical_state_error_locked(  # noqa: SLF001
        stream_state(0xFFFF)) == ""
    assert sampler._physical_state_error_locked(  # noqa: SLF001
        stream_state(0)) == ""
    assert "did not advance" in sampler._physical_state_error_locked(  # noqa: SLF001
        stream_state(0))
    assert "did not advance" in sampler._physical_state_error_locked(  # noqa: SLF001
        stream_state(0xFFFF))
    assert "exceeds" in sampler._physical_state_error_locked(  # noqa: SLF001
        stream_state(1, pos_age_ms=151.0))
    assert "missing/invalid imu_age_ms" in (  # noqa: SLF001
        sampler._physical_state_error_locked(
            _state(timing={
                "source": "read_snapshot",
                "snapshot_seq": 1,
                "pos_age_ms": 1.0,
            })))
    # ASCII legacy IMUR has no sensor sequence/age; a host request alone
    # cannot prove that its physical cache advanced.
    assert "no physical freshness proof" in (  # noqa: SLF001
        sampler._physical_state_error_locked(
            _state(timing={"source": "legacy_read"})))
    # Simulation/fake estimators may still use host-side acquisitions.
    assert sampler._physical_state_error_locked(  # noqa: SLF001
        _state(timing={"source": "fake_async"})) == ""


def test_async_sampler_first_background_stream_sample_must_advance_preflight():
    initial = _state(
        timestamp=time.monotonic(),
        timing={
            "source": "read_snapshot",
            "snapshot_seq": 7,
            "pos_age_ms": 1.0,
            "imu_age_ms": 1.0,
        },
    )
    sampler = rl_policy._AsyncSnapshotSampler(  # noqa: SLF001
        _FakeBus(), {}, initial_state=initial)

    assert "did not advance" in sampler._physical_state_error_locked(  # noqa: SLF001
        initial)


def test_frozen_mcu_sequence_never_completes_async_readiness():
    sampler = rl_policy._AsyncSnapshotSampler(  # noqa: SLF001
        _AsyncHealthBus(seqs=[23]), {}, hz=100.0, max_age_s=0.15)
    sampler.start()
    _state_out, details, err = rl_policy._await_async_sampler_ready(  # noqa: SLF001
        sampler, lambda: False, min_good_samples=3, timeout_s=0.08)
    stats = sampler.stats()
    sampler.stop()

    assert "snapshot_seq did not advance" in err
    assert details["consecutive_healthy"] < 3
    assert stats["physical_rejects"] >= 1
    assert stats["good_samples"] == 1
    assert sampler.motion_ready is False


def test_frozen_gyro_snapshot_is_rejected_before_stateful_recovery_update(
        monkeypatch):
    class _SequenceBus(_FakeBus):
        has_stream = True

        def __init__(self):
            super().__init__()
            self.snaps = [
                _snapshot(1, gx_dps=100.0),
                _snapshot(1, gx_dps=100.0),
                _snapshot(2, gx_dps=0.0),
            ]

        def read_snapshot(self):
            return self.snaps.pop(0) if self.snaps else _snapshot(2)

    updates = []

    class _RecordingEstimator:
        def __init__(self, _bus, _cfg):
            pass

        def set_commanded(self, _q):
            pass

        def update_from_snapshot(self, snap, *, want_full_feedback, source):
            updates.append((snap["seq"], snap["imu"]["gx_dps"]))
            return _state(
                timestamp=time.monotonic(),
                timing={
                    "source": source,
                    "snapshot_seq": snap["seq"],
                    "pos_age_ms": snap["pos_age_ms"],
                    "imu_age_ms": snap["imu_age_ms"],
                })

        def update_feedback(self, state):
            return _state(
                timestamp=state.timestamp, health=True,
                timing={**state.timing, **_complete_health_timing(
                    source=state.timing["source"])})

    monkeypatch.setattr(
        rl_policy, "RobotStateEstimator", _RecordingEstimator)
    sampler = rl_policy._AsyncSnapshotSampler(  # noqa: SLF001
        _SequenceBus(), {}, hz=200.0)
    sampler.start()
    deadline = time.monotonic() + 0.5
    while sampler.stats()["samples"] < 3 and time.monotonic() < deadline:
        time.sleep(0.001)
    sampler.stop()

    # The repeated nonzero-gyro snapshot never reaches the estimator; only
    # the first physical sample and the advancing recovery mutate its state.
    assert updates == [(1, 100.0), (2, 0.0)]


def test_partial_feedback_is_not_published_as_complete_servo_health():
    def frame(ids, *, current_base):
        return {
            j: {
                "load_pct": 10.0 + j,
                "current_a": current_base + j / 100.0,
                "temp_c": 30.0 + j,
            }
            for j in ids
        }

    class _FeedbackBus:
        def __init__(self):
            self.frames = [
                frame(range(17), current_base=0.1),
                frame(range(18), current_base=0.2),
                frame(range(17), current_base=9.0),
            ]

        def read_all_positions(self):
            return {j: 0.0 for j in range(rl_policy.N_JOINTS)}

        def read_imu(self, *, apply_calib=True):
            return {
                "ax_g": 0.0, "ay_g": 0.0, "az_g": 1.0,
                "gx_dps": 0.0, "gy_dps": 0.0, "gz_dps": 0.0,
            }

        def read_all_feedback(self):
            return self.frames.pop(0)

    estimator = RobotStateEstimator(_FeedbackBus(), {})

    partial_first = estimator.update(want_full_feedback=True)
    assert partial_first.servo_current is not None
    assert partial_first.servo_current[16] == pytest.approx(0.26)
    assert partial_first.timing["full_feedback_attempted"] is True
    assert partial_first.timing["full_feedback_complete"] is False
    assert partial_first.timing["full_feedback_count"] == 17
    assert partial_first.timing["full_feedback_ids"] == list(range(17))

    complete = estimator.update(want_full_feedback=True)
    assert complete.timing["full_feedback_complete"] is True
    assert complete.timing["full_feedback_count"] == 18
    assert complete.timing["full_feedback_ids"] == list(range(18))
    complete_current = complete.servo_current.copy()

    partial_after_cache = estimator.update(want_full_feedback=True)
    assert partial_after_cache.timing["full_feedback"] is False
    assert partial_after_cache.timing["full_feedback_complete"] is False
    assert partial_after_cache.timing["full_feedback_count"] == 17
    # Valid partial values update immediately, while missing ID 17 retains
    # the prior complete value and remains explicitly invalid this frame.
    assert partial_after_cache.servo_current[:17] == pytest.approx(
        [9.0 + j / 100.0 for j in range(17)])
    assert partial_after_cache.servo_current[17] == pytest.approx(
        complete_current[17])
    assert partial_after_cache.timing["feedback_valid_ids"] == list(range(17))
    assert partial_after_cache.timing["feedback_missing_ids"] == [17]

    # A later position-only inner substep retains the physical acquisition
    # identity, so the direct runner cannot skip this partial high current.
    after_position_substep = estimator.update(want_full_feedback=False)
    assert (after_position_substep.timing["feedback_sample_seq"]
            == partial_after_cache.timing["feedback_sample_seq"])
    safety = rl_policy.SafetyLayer({})
    safety._over_current_trip_ticks = 1  # noqa: SLF001
    safety.set_nominal(np.zeros(rl_policy.N_JOINTS))
    _q, status = safety.filter(
        np.zeros(rl_policy.N_JOINTS), after_position_substep)
    assert status.terminate is True
    assert status.reason == "over_current"
    assert "L5 hip" in status.detail


def test_servo_current_debounce_consumes_each_feedback_sequence_once():
    safety = rl_policy.SafetyLayer({})
    safety._over_current_trip_ticks = 3  # noqa: SLF001
    safety.set_nominal(np.zeros(rl_policy.N_JOINTS))

    def high_current(seq):
        return _state(
            timestamp=time.monotonic(), health=True, current=4.0,
            timing=_complete_health_timing(feedback_sample_seq=seq))

    repeated = high_current(7)
    for _ in range(3):
        _q, status = safety.filter(
            np.zeros(rl_policy.N_JOINTS), repeated)
        assert status.terminate is False
    assert safety._over_current_ticks == 1  # noqa: SLF001

    _q, status = safety.filter(
        np.zeros(rl_policy.N_JOINTS), high_current(8))
    assert status.terminate is False
    _q, status = safety.filter(
        np.zeros(rl_policy.N_JOINTS), high_current(9))
    assert status.terminate is True
    assert status.reason == "over_current"


def test_direct_safety_stops_after_three_distinct_incomplete_frames():
    safety = rl_policy.SafetyLayer({})
    safety.set_nominal(np.zeros(rl_policy.N_JOINTS))
    valid_ids = list(range(17))
    statuses = []
    for seq in (1, 2, 3):
        state = _state(
            timestamp=time.monotonic(), health=True,
            timing={
                "feedback_sample_seq": seq,
                "feedback_sample_fresh": True,
                "feedback_complete": False,
                "feedback_valid_count": 17,
                "feedback_valid_ids": valid_ids,
                "feedback_missing_ids": [17],
                "full_feedback": False,
                "full_feedback_attempted": True,
                "full_feedback_complete": False,
                "full_feedback_count": 17,
                "full_feedback_ids": valid_ids,
            })
        _q, status = safety.filter(
            np.zeros(rl_policy.N_JOINTS), state)
        statuses.append(status)

    assert statuses[0].terminate is False
    assert statuses[1].terminate is False
    assert statuses[2].terminate is True
    assert statuses[2].reason == "incomplete_feedback"
    assert "17/18 valid" in statuses[2].detail


def test_safety_rejects_false_complete_flag_without_all_valid_ids():
    safety = rl_policy.SafetyLayer({})
    safety.set_nominal(np.zeros(rl_policy.N_JOINTS))
    valid_ids = list(range(17))
    status = None
    for seq in (1, 2, 3):
        state = _state(
            timestamp=time.monotonic(), health=True,
            timing={
                "feedback_sample_seq": seq,
                "feedback_sample_fresh": True,
                # A contradictory producer must fail closed: explicit IDs
                # are the authority, not a stale/corrupt completeness bit.
                "feedback_complete": True,
                "feedback_valid_count": 17,
                "feedback_valid_ids": valid_ids,
                "feedback_missing_ids": [17],
            })
        _q, status = safety.filter(
            np.zeros(rl_policy.N_JOINTS), state)

    assert status is not None
    assert status.terminate is True
    assert status.reason == "incomplete_feedback"


class _ReadinessSequenceSampler:
    def __init__(self, samples):
        self.cfg = {}
        self.interval_s = 0.001
        self.max_age_s = 0.15
        self.samples = list(samples)
        self.calls = 0
        self.motion_ready = False

    def latest(self):
        idx = min(self.calls, len(self.samples) - 1)
        self.calls += 1
        value = self.samples[idx]
        health_kwargs = (dict(value) if isinstance(value, dict)
                         else {"current": value})
        timing_overrides = health_kwargs.pop("timing", {})
        timing = _complete_health_timing(
            async_sample_seq=self.calls,
            async_sample_fresh=True,
            async_health_fresh=True,
            async_health_ok=True,
            async_feedback_fresh=True,
            feedback_sample_seq=self.calls,
        )
        timing.update(timing_overrides)
        state = _state(
            timestamp=time.monotonic(), health=True,
            timing=timing,
            **health_kwargs,
        )
        return state, 0.001, self.stats()

    def stats(self):
        return {"errors": 0, "motion_ready": self.motion_ready}

    def mark_motion_ready(self):
        self.motion_ready = True


@pytest.mark.parametrize(("health_kwargs", "reason"), [
    ({"temperature": 66.0}, "over_temp"),
    ({"current": 2.6}, "over_current"),
    ({"load": 91.0}, "over_load"),
])
def test_async_health_gate_checks_each_safety_limit(health_kwargs, reason):
    state = _state(
        timestamp=time.monotonic(), health=True,
        timing=_complete_health_timing(
            async_sample_seq=1,
            async_sample_fresh=True,
            async_health_fresh=True,
            async_health_ok=True,
        ),
        **health_kwargs,
    )

    assert rl_policy._async_health_safety_error(  # noqa: SLF001
        rl_policy.SafetyLayer({}), state).startswith(reason)


def test_async_ready_resets_probation_on_unsafe_health_sample():
    sampler = _ReadinessSequenceSampler([0.4, 4.0, 0.4, 0.4, 0.4])
    safety = rl_policy.SafetyLayer({})

    _state_out, details, err = rl_policy._await_async_sampler_ready(  # noqa: SLF001
        sampler, lambda: False, min_good_samples=3, timeout_s=0.1,
        health_safety=safety)

    assert err == ""
    assert sampler.calls == 5
    assert details["consecutive_healthy"] == 3
    assert sampler.motion_ready is True


def test_async_ready_returns_exact_health_failure_and_stays_not_ready():
    sampler = _ReadinessSequenceSampler([4.0])
    safety = rl_policy.SafetyLayer({})
    safety._over_current_trip_ticks = 3  # noqa: SLF001

    _state_out, details, err = rl_policy._await_async_sampler_ready(  # noqa: SLF001
        sampler, lambda: False, min_good_samples=3, timeout_s=0.05,
        health_safety=safety)

    assert isinstance(err, rl_policy.AsyncReadinessFailure)
    assert err.startswith("async physical health trip: over_current")
    assert err.confirmed_physical is True
    assert rl_policy._async_readiness_requires_limp(err) is True  # noqa: SLF001
    assert sampler.calls == 3
    assert details["consecutive_healthy"] == 0
    assert sampler.motion_ready is False


def test_async_ready_detects_confirmed_current_in_partial_frames():
    valid_ids = list(range(17))
    partial_timing = {
        "full_feedback": False,
        "full_feedback_complete": False,
        "full_feedback_count": 17,
        "full_feedback_ids": valid_ids,
        "feedback_complete": False,
        "feedback_valid_count": 17,
        "feedback_valid_ids": valid_ids,
        "feedback_missing_ids": [17],
        "async_health_ok": False,
    }
    sampler = _ReadinessSequenceSampler([
        {"current": 4.0, "timing": partial_timing},
    ])
    safety = rl_policy.SafetyLayer({})
    safety._over_current_trip_ticks = 3  # noqa: SLF001

    _state_out, details, err = rl_policy._await_async_sampler_ready(  # noqa: SLF001
        sampler, lambda: False, min_good_samples=3, timeout_s=0.05,
        health_safety=safety)

    assert isinstance(err, rl_policy.AsyncReadinessFailure)
    assert err.confirmed_physical is True
    assert err.reason == "over_current"
    assert sampler.calls == 3
    assert details["consecutive_healthy"] == 0


@pytest.mark.parametrize(("samples", "expected_calls", "reason"), [
    ([{"temperature": 66.0}] * 3, 3, "over_temp"),
    ([{"load": 91.0}], 1, "over_load"),
])
def test_async_ready_uses_safety_debounce_for_physical_trip(
        samples, expected_calls, reason):
    sampler = _ReadinessSequenceSampler(samples)
    safety = rl_policy.SafetyLayer({})

    _state_out, _details, err = rl_policy._await_async_sampler_ready(  # noqa: SLF001
        sampler, lambda: False, min_good_samples=3, timeout_s=0.05,
        health_safety=safety)

    assert isinstance(err, rl_policy.AsyncReadinessFailure)
    assert err.confirmed_physical is True
    assert err.reason == reason
    assert sampler.calls == expected_calls


def test_async_readiness_limp_on_three_fresh_missing_servo_frames():
    ids = list(range(17))
    sampler = _ReadinessSequenceSampler([{
        "current": 0.4,
        "timing": {
            "full_feedback": False, "full_feedback_complete": False,
            "full_feedback_count": 17, "full_feedback_ids": ids,
            "feedback_complete": False, "feedback_valid_ids": ids,
            "async_health_ok": False,
        },
    }])
    _state_out, _details, err = rl_policy._await_async_sampler_ready(
        sampler, lambda: False, timeout_s=0.1)
    assert sampler.calls == 3
    assert err.reason == "incomplete_feedback"
    assert rl_policy._async_readiness_requires_limp(err)
    assert not sampler.motion_ready


def test_default_readiness_timeout_allows_real_current_confirmation(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(rl_policy.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(rl_policy.time, "sleep", lambda _s: None)

    class _TenHzSampler(_ReadinessSequenceSampler):
        def latest(self):
            now[0] += self.interval_s
            return super().latest()

    sampler = _TenHzSampler([4.0])
    sampler.interval_s = 0.1
    safety = rl_policy.SafetyLayer({"safety": {"over_current_trip_s": 2.0}})
    rl_policy._apply_async_safety_feedback_timing(safety, safety.cfg, 10.0)
    _state_out, _details, err = rl_policy._await_async_sampler_ready(
        sampler, lambda: False, health_safety=safety)
    assert err.reason == "over_current"
    assert err.confirmed_physical
    assert sampler.calls == 20
    assert now[0] == pytest.approx(2.0)


def test_episode_log_records_actual_time_activity_and_sensor_age(tmp_path, monkeypatch):
    now = [10.0]
    monkeypatch.setattr(rl_policy, "_HERE", tmp_path)
    monkeypatch.setattr(rl_policy.time, "monotonic", lambda: now[0])
    monkeypatch.setitem(sys.modules, "event_log", SimpleNamespace(emit=lambda *a, **k: None))
    log = rl_policy._EpisodeLog("drive", {})
    state = _state(timestamp=10.01, timing={
        "snapshot_seq": 42, "pos_age_ms": 4.0, "imu_age_ms": 7.0,
    })
    now[0] = 10.08
    log.tick(0.01, state, None, None, None, 0.08, 0.0, 0.4,
             phase="walk", walk_engaged=True, learned_policy_active=True,
             bus_write_due=True)
    now[0] = 10.18
    log.tick(0.02, state, None, None, None, 0.0, 0.0, 0.4, phase="tail")
    log.close({"ok": True})
    with log.csv_path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert list(rows[0])[:2] == ["t_s", "phase"]
    assert float(rows[0]["mono_s"]) == pytest.approx(10.08)
    assert float(rows[0]["wall_elapsed_s"]) == pytest.approx(0.08)
    assert rows[0]["walk_engaged"] == rows[0]["learned_policy_active"] == "1"
    assert rows[0]["bus_write_due"] == "1"
    assert float(rows[0]["position_age_ms"]) == pytest.approx(74.0)
    assert float(rows[0]["imu_age_ms"]) == pytest.approx(77.0)
    assert float(rows[0]["state_age_ms"]) == pytest.approx(77.0)
    assert rows[0]["snapshot_seq"] == "42"
    assert rows[1]["walk_engaged"] == rows[1]["learned_policy_active"] == "0"
    assert rows[1]["bus_write_due"] == "0"


@pytest.mark.parametrize("capture", [None, "nan", "97.0", "101.0"])
def test_http_camera_requires_fresh_source_capture_time(tmp_path, monkeypatch, capture):
    from rl_move.scripts import run_rl_walk_trial as trial

    class _Response:
        headers = {} if capture is None else {"X-Capture-Unix-S": capture}
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return None
        def read(self):
            return b"unused because timestamp is rejected first"

    monkeypatch.setattr(trial.time, "time", lambda: 100.0)
    monkeypatch.setattr(trial.urllib.request, "urlopen", lambda *a, **k: _Response())
    recorder = trial.HttpFrameRecorder(tmp_path / "out.mp4", tmp_path / "ts.csv", "http://fake/frame.jpg")
    with pytest.raises(RuntimeError, match="capture timestamp|lacks X-Capture"):
        recorder._read_frame()


def test_http_camera_preserves_capture_time_instead_of_receipt(tmp_path, monkeypatch):
    from rl_move.scripts import run_rl_walk_trial as trial

    class _Response:
        headers = {"X-Capture-Unix-S": "99.5"}
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return None
        def read(self):
            return b"jpeg"

    monkeypatch.setattr(trial.time, "time", lambda: 100.0)
    monkeypatch.setattr(trial.urllib.request, "urlopen", lambda *a, **k: _Response())
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    monkeypatch.setattr(trial.cv2, "imdecode", lambda *a: frame)
    recorder = trial.HttpFrameRecorder(tmp_path / "out.mp4", tmp_path / "ts.csv", "http://fake/frame.jpg")
    _, captured = recorder._read_frame()
    assert captured == 99.5


def test_async_freshness_failure_is_typed_but_does_not_require_limp():
    err = rl_policy.AsyncReadinessFailure(
        "async feedback not ready: legacy freshness unavailable",
        kind="freshness", reason="feedback_not_ready",
        detail="legacy freshness unavailable")

    assert err.confirmed_physical is False
    assert rl_policy._async_readiness_requires_limp(err) is False  # noqa: SLF001


def test_async_sampler_failed_stop_keeps_registry_and_blocks_motion_write(monkeypatch):
    class _StuckThread:
        def __init__(self):
            self.alive = True
            self.join_timeout = None

        def is_alive(self):
            return self.alive

        def join(self, timeout=None):
            assert timeout is not None
            self.join_timeout = timeout

    bus = _FakeBus()
    sampler = rl_policy._AsyncSnapshotSampler(  # noqa: SLF001
        bus, {}, initial_state=_state(timestamp=time.monotonic()))
    stuck = _StuckThread()
    sampler._thread = stuck  # noqa: SLF001
    sampler.mark_motion_ready()
    rl_policy._register_async_sampler(sampler)  # noqa: SLF001

    with pytest.raises(RuntimeError, match="failed to stop"):
        sampler.stop()

    assert sampler._thread is stuck  # noqa: SLF001
    assert stuck.join_timeout >= 2.5
    assert sampler in rl_policy._ASYNC_SAMPLER_GUARD.active  # noqa: SLF001
    assert sampler.motion_ready is False
    out = rl_policy._stream_target_async(  # noqa: SLF001
        bus, sampler,
        np.zeros(rl_policy.N_JOINTS), np.ones(rl_policy.N_JOINTS) * 0.1,
        t_next=time.monotonic(), inner_steps=1, inner_dt=0.0,
        write_speed=100, write_acc=20, abort_check=lambda: False)
    assert out[3] == "feedback stale during stream"
    assert bus.writes == 0

    # A new API worker has a different thread-local sampler registry. The
    # physical bus quarantine must still reject it before preflight/arming.
    reached_impl = []
    monkeypatch.setattr(rl_policy, "_run_policy_move_impl",
                        lambda *a, **k: reached_impl.append(True))
    monkeypatch.setattr(rl_policy, "_run_drive_session_impl",
                        lambda *a, **k: reached_impl.append(True))
    failures = []

    def new_worker():
        for runner, args in ((rl_policy.run_policy_move, ("stand",)),
                             (rl_policy.run_drive_session, (None,))):
            try:
                runner(SimpleNamespace(bus=bus), *args)
            except rl_policy.AsyncSamplerCleanupError as error:
                failures.append(str(error))

    worker = threading.Thread(target=new_worker)
    worker.start()
    worker.join(timeout=0.5)
    assert not worker.is_alive()
    assert len(failures) == 2
    assert reached_impl == []

    stuck.alive = False
    sampler.stop()
    rl_policy.require_bus_available(bus)
    assert sampler not in rl_policy._ASYNC_SAMPLER_GUARD.active  # noqa: SLF001


def test_async_stop_cancels_between_snapshot_and_full_feedback():
    class _BlockingSnapshotBus(_AsyncHealthBus):
        def __init__(self):
            super().__init__()
            self.entered = threading.Event()
            self.release = threading.Event()

        def read_snapshot(self):
            self.entered.set()
            assert self.release.wait(timeout=1.0)
            return _snapshot(1)

    bus = _BlockingSnapshotBus()
    sampler = rl_policy._AsyncSnapshotSampler(  # noqa: SLF001
        bus, {}, hz=10.0)
    sampler.start()
    assert bus.entered.wait(timeout=0.5)
    release = threading.Timer(0.02, bus.release.set)
    release.start()
    sampler.stop()
    release.join()

    assert bus.feedback_reads == 0
    assert sampler.stats()["thread_alive"] is False


def test_async_stream_refuses_first_write_until_background_ready():
    class _NotReadySampler(_FakeSampler):
        motion_ready = False

    bus = _FakeBus()
    sampler = _NotReadySampler([_state()], age_s=0.01)

    out = rl_policy._stream_target_async(  # noqa: SLF001
        bus, sampler,
        np.zeros(rl_policy.N_JOINTS),
        np.ones(rl_policy.N_JOINTS) * 0.1,
        t_next=time.monotonic(), inner_steps=1, inner_dt=0.0,
        write_speed=100, write_acc=20,
        abort_check=lambda: False,
        last_good_state=_state(), stale_ticks=0, max_stale_ticks=3)

    _state_out, _next, _overruns, err, _stale, _samples, _timing = out
    assert err == "feedback stale during stream"
    assert bus.writes == 0


@pytest.mark.parametrize("public_name, impl_name, args", [
    ("run_policy_move", "_run_policy_move_impl", (None, "stand")),
    ("run_drive_session", "_run_drive_session_impl", (None, None)),
])
def test_public_runner_stops_async_sampler_on_exception(
        monkeypatch, public_name, impl_name, args):
    stopped = []

    class _GuardedSampler:
        def stop(self):
            stopped.append(True)
            rl_policy._unregister_async_sampler(self)  # noqa: SLF001

    sampler = _GuardedSampler()

    def _boom(*_args, **_kwargs):
        rl_policy._register_async_sampler(sampler)  # noqa: SLF001
        raise RuntimeError("synthetic runner failure")

    monkeypatch.setattr(rl_policy, impl_name, _boom)
    with pytest.raises(RuntimeError, match="synthetic runner failure"):
        getattr(rl_policy, public_name)(*args)

    assert stopped == [True]


def test_async_health_debounce_uses_feedback_rate():
    cfg = {
        "control": {"hz": 100},
        "sensing": {"full_feedback_hz": 10},
        "safety": {"over_current_trip_s": 2.0},
    }
    safety = rl_policy.SafetyLayer(cfg)

    feedback_hz = rl_policy._apply_async_safety_feedback_timing(  # noqa: SLF001
        safety, cfg, snapshot_hz=10.0)

    assert feedback_hz == pytest.approx(10.0)
    assert safety._over_current_trip_ticks == 20  # noqa: SLF001


def test_drive_joint_hold_trips_current_at_fresh_feedback_cadence(monkeypatch):
    cfg = {
        "control": {"hz": 100, "inner_hz": 100},
        "sensing": {"full_feedback_hz": 10},
        "safety": {"over_current_trip_s": 2.0, "max_current_a": 2.5},
    }

    class _Policy:
        meta = {
            "name": "drive-cadence-test",
            "obs_dim": 74,
            "training_hz": 100,
            "phase_hz": 1.0,
            "joint_frame": rl_policy.FRAME_ROBOT_ABS,
            "joint_contract": rl_policy.JOINT_CONTRACT,
        }

        def act(self, _obs):
            return np.zeros(rl_policy.N_JOINTS, dtype=float)

        def reset(self):
            pass

    def hot_state(seq):
        return _state(
            timestamp=time.monotonic(), health=True, current=4.0,
            timing=_complete_health_timing(feedback_sample_seq=seq),
        )

    class _Estimator:
        def __init__(self):
            self.calls = 0

        def set_commanded(self, _q):
            pass

        def reset_episode_filters(self):
            pass

        def update(self, want_full_feedback=False):
            del want_full_feedback
            self.calls += 1
            if self.calls <= 22:
                return hot_state(self.calls)
            return _state(bus_ok=False, timestamp=time.monotonic())

    class _Bus(_FakeBus):
        def __init__(self):
            super().__init__()
            self.torque = []

        def enable_all_torque(self, enabled):
            self.torque.append(bool(enabled))

    class _NoopDebug:
        name = "drive_cadence_debug.jsonl"

        def __init__(self, *_args, **_kwargs):
            pass

        def event(self, *_args, **_kwargs):
            pass

        def attach(self, result):
            result.setdefault("debug_log", self.name)

        def close(self, _result=None):
            pass

    class _NoopLog:
        def __init__(self, _mode, params=None, obs_dim=0, debug=None):
            del params, debug
            self.obs_dim = int(obs_dim)

        def tick(self, *_args, **_kwargs):
            pass

        def close(self, _result):
            return "drive_cadence.csv"

    class _Command:
        def get(self):
            return 0.0, 0.0, 0.0, 0.0, 0.0, False

        def publish(self, _snapshot):
            pass

    real_safety = rl_policy.SafetyLayer
    safeties = []

    class _RecordingSafety(real_safety):
        def __init__(self, inner_cfg):
            super().__init__(inner_cfg)
            safeties.append(self)

    bus = _Bus()
    estimator = _Estimator()
    drive = SimpleNamespace(
        bus=bus, dry_run=False, _lock=threading.RLock(),
        gait=SimpleNamespace(stop=lambda: None),
        _torque_all=lambda _enabled: None,
        armed=False, mode="idle", status="idle",
    )
    monkeypatch.setattr(rl_policy, "load_config", lambda _path: cfg)
    monkeypatch.setattr(rl_policy, "NumpyPolicy", lambda _path: _Policy())
    monkeypatch.setattr(rl_policy, "RobotStateEstimator",
                        lambda _bus, _cfg: estimator)
    monkeypatch.setattr(rl_policy, "SafetyLayer", _RecordingSafety)
    monkeypatch.setattr(rl_policy, "_RunDebug", _NoopDebug)
    monkeypatch.setattr(rl_policy, "_EpisodeLog", _NoopLog)
    monkeypatch.setattr(rl_policy, "_set_weight_bearing_torque",
                        lambda _bus: None)
    monkeypatch.setattr(
        rl_policy, "preflight",
        lambda *_args, **_kwargs: (
            True, "", {"q_deg": [0.0] * rl_policy.N_JOINTS,
                       "start_pose": "sim_walk_start"}),
    )
    monkeypatch.setattr(
        rl_policy, "_preflight_start_target_deg",
        lambda *_args, **_kwargs: (
            np.zeros(rl_policy.N_JOINTS, dtype=float), ""),
    )
    monkeypatch.setattr(
        rl_policy, "_refresh_verified_start_pose",
        lambda *_args, **_kwargs: (hot_state(0), {}, ""),
    )
    monkeypatch.setattr(
        rl_policy, "_probe_async_transport",
        lambda _bus: {"async_capable": True},
    )
    monkeypatch.setattr(rl_policy.time, "sleep", lambda _seconds: None)

    result = rl_policy._run_drive_session_impl(  # noqa: SLF001
        drive, _Command(), rot60=False, hold_weights=None)

    primary = safeties[0]
    assert result["error"].startswith("safety trip: over_current")
    assert result["ticks"] == 19
    assert result["limped"] is True
    assert primary._health_sample_hz == pytest.approx(10.0)  # noqa: SLF001
    assert primary._over_current_trip_ticks == 20  # noqa: SLF001
    assert primary._over_current_ticks == 20  # noqa: SLF001
    assert estimator.calls == 23
    assert False in bus.torque


def test_deploy_manifest_stages_importable_async_bus_guard(tmp_path):
    manifest = _ROOT / "linux_control" / "deploy_manifest.sh"
    stage = tmp_path / "stage"
    subprocess.run(
        [
            "bash", "-c",
            'source "$1"; stage_deploy_tree "$2" "$3"',
            "deploy-manifest-test", str(manifest), str(stage),
            str(_ROOT / "linux_control"),
        ],
        check=True,
    )
    assert (stage / "linux_control" / "async_bus_guard.py").is_file()

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([
        str(stage / "linux_control" / "vendor"),
        str(stage / "motor_setup"),
        str(stage / "linux_control"),
        str(stage),
    ])
    subprocess.run(
        [sys.executable, "-c", "import rl_policy"],
        cwd=stage / "linux_control", env=env, check=True,
    )


def test_drive_write_plan_decimates_100hz_policy_to_50hz_bus():
    cadence = rl_policy._drive_write_plan(  # noqa: SLF001
        _policy({"training_hz": 100}), {"control": {}}, policy_hz=100
    )

    assert cadence.requested_hz == pytest.approx(50.0)
    assert cadence.write_hz == pytest.approx(50.0)
    assert cadence.write_every_ticks == 2
    assert cadence.write_dt == pytest.approx(0.02)


def test_drive_write_plan_preserves_legacy_25hz_policy_bus_writes():
    cadence = rl_policy._drive_write_plan(  # noqa: SLF001
        _policy({"training_hz": 25}), {"control": {}}, policy_hz=25
    )

    assert cadence.write_hz == pytest.approx(25.0)
    assert cadence.write_every_ticks == 1


def test_drive_write_plan_honors_policy_metadata_override():
    cadence = rl_policy._drive_write_plan(  # noqa: SLF001
        _policy({"training_hz": 100, "drive_write_hz": 25}),
        {"control": {"drive_write_hz": 50}},
        policy_hz=100,
    )

    assert cadence.requested_hz == pytest.approx(25.0)
    assert cadence.write_hz == pytest.approx(25.0)
    assert cadence.write_every_ticks == 4


def test_drive_translation_clamps_to_hardware_trained_band():
    vx, vy = rl_policy._drive_clamp_translation(0.002, 0.0)  # noqa: SLF001

    assert vx == pytest.approx(rl_policy.WALK_SPEED_MIN)
    assert vy == pytest.approx(0.0)

    vx, vy = rl_policy._drive_clamp_translation(0.2, 0.0)  # noqa: SLF001

    assert vx == pytest.approx(rl_policy.WALK_SPEED_MAX)
    assert vy == pytest.approx(0.0)


def test_drive_translation_uses_policy_metadata_band():
    speed_min, speed_max = rl_policy._policy_walk_speed_band(  # noqa: SLF001
        _policy({"walk_speed_min_m_s": 0.08, "walk_speed_max_m_s": 0.08})
    )

    assert speed_min == pytest.approx(0.08)
    assert speed_max == pytest.approx(0.08)

    vx, vy = rl_policy._drive_clamp_translation(  # noqa: SLF001
        0.05, 0.0, speed_min, speed_max)

    assert vx == pytest.approx(0.08)
    assert vy == pytest.approx(0.0)


def test_joint_hold_fallback_does_not_use_learned_policy():
    assert not rl_policy._drive_uses_learned_policy(  # noqa: SLF001
        "hold", None
    )
    assert rl_policy._drive_uses_learned_policy(  # noqa: SLF001
        "walk", None
    )
    assert rl_policy._drive_uses_learned_policy(  # noqa: SLF001
        "hold", _policy({"obs_dim": 68})
    )


def test_drive_waits_quietly_before_first_walk_command():
    hold_policy = _policy({"obs_dim": 68})

    assert not rl_policy._drive_should_run_learned_policy(  # noqa: SLF001
        "hold", hold_policy, walk_has_engaged=False
    )
    assert rl_policy._drive_should_run_learned_policy(  # noqa: SLF001
        "hold", hold_policy, walk_has_engaged=True
    )
    assert rl_policy._drive_should_run_learned_policy(  # noqa: SLF001
        "walk", None, walk_has_engaged=False
    )


def test_stream_target_tolerates_short_feedback_dropouts():
    bus = _FakeBus()
    good0 = _state()
    good1 = _state()
    est = _FakeEstimator([
        _state(bus_ok=False),
        _state(bus_ok=False),
        good1,
        _state(),
    ])

    out = rl_policy._stream_target(  # noqa: SLF001
        bus,
        est,
        np.zeros(rl_policy.N_JOINTS),
        np.ones(rl_policy.N_JOINTS) * 0.1,
        t_next=0.0,
        inner_steps=4,
        inner_dt=0.0,
        write_speed=100,
        write_acc=20,
        abort_check=lambda: False,
        last_good_state=good0,
        stale_ticks=0,
        max_stale_ticks=3,
    )

    state, _t_next, _overruns, err, stale_ticks, stale_samples, _timing = out
    assert err == ""
    assert state.bus_ok is True
    assert not rl_policy._stream_state_is_stale(state)  # noqa: SLF001
    assert stale_ticks == 0
    assert stale_samples == 2
    assert bus.writes == 4


def test_stream_target_prefers_combined_step_all_snapshot():
    bus = _FakeStepBus()
    est = _FakeEstimator([_state() for _ in range(4)])

    out = rl_policy._stream_target(  # noqa: SLF001
        bus,
        est,
        np.zeros(rl_policy.N_JOINTS),
        np.ones(rl_policy.N_JOINTS) * 0.1,
        t_next=0.0,
        inner_steps=4,
        inner_dt=0.0,
        write_speed=100,
        write_acc=20,
        abort_check=lambda: False,
        last_good_state=_state(),
        stale_ticks=0,
        max_stale_ticks=3,
    )

    state, _t_next, _overruns, err, stale_ticks, stale_samples, _timing = out
    assert err == ""
    assert state.bus_ok is True
    assert stale_ticks == 0
    assert stale_samples == 0
    assert bus.steps == 4
    assert bus.writes == 0
    assert len(est.snapshots) == 4


class _MetadataSnapshotEstimator:
    def __init__(self):
        self.snapshots = []
        self.commanded = []

    def set_commanded(self, q):
        self.commanded.append(np.asarray(q, dtype=float).copy())

    def update_from_snapshot(self, snap):
        self.snapshots.append(dict(snap))
        return _state(
            timestamp=time.monotonic(),
            timing={
                "source": "step_all",
                "snapshot_seq": snap["seq"],
                "pos_age_ms": snap["pos_age_ms"],
                "imu_age_ms": snap["imu_age_ms"],
            },
        )


def _run_direct_pending_policy_harness(monkeypatch, snapshots, *,
                                       abort_after_steps):
    """Run the real outer policy loop against a sequenced in-memory bus."""
    cfg = {
        "control": {"hz": 25, "inner_hz": 100},
        "sensing": {"full_feedback_hz": 10},
        "safety": {
            "max_delta_q_deg": 4.0,
            "over_current_trip_s": 2.0,
            "max_roll_deg": 30.0,
            "max_pitch_deg": 30.0,
        },
        "bus": {"write_speed": 100, "write_acc": 20},
    }

    class _RecordingPolicy:
        meta = {
            "name": "direct-pending-test",
            "obs_dim": 74,
            "training_hz": 25,
            "phase_hz": 1.0,
            "joint_frame": rl_policy.FRAME_ROBOT_ABS,
            "joint_contract": rl_policy.JOINT_CONTRACT,
        }

        def __init__(self):
            self.observations = []

        def act(self, obs):
            self.observations.append(np.asarray(obs).copy())
            # Make resumed inference visibly different at the bus while
            # staying inside validate_action's normalized envelope.
            return np.full(
                rl_policy.N_JOINTS,
                0.25 + 0.25 * (len(self.observations) - 1),
                dtype=float,
            )

    class _RunnerBus(_FakeStepBus):
        def __init__(self, snaps):
            super().__init__(snaps)
            self.torque = []

        def enable_all_torque(self, enabled):
            self.torque.append(bool(enabled))

    class _RunnerEstimator:
        def __init__(self):
            self.commanded = np.zeros(rl_policy.N_JOINTS, dtype=float)
            self.last_seq = 0xFFFF

        def set_commanded(self, q):
            self.commanded = np.asarray(q, dtype=float).copy()

        def reset_episode_filters(self):
            pass

        def _state(self):
            state = _state(
                timestamp=time.monotonic(),
                timing={
                    "source": "step_all",
                    "snapshot_seq": self.last_seq,
                    "pos_age_ms": 1.0,
                    "imu_age_ms": 1.0,
                },
            )
            state.commanded_position = self.commanded.copy()
            return state

        def update(self, want_full_feedback=False):
            del want_full_feedback
            return self._state()

        def update_from_snapshot(self, snap):
            self.last_seq = int(snap["seq"])
            return self._state()

    policy = _RecordingPolicy()
    bus = _RunnerBus(snapshots)
    est = _RunnerEstimator()
    debug_instances = []
    log_instances = []

    class _Debug:
        def __init__(self, *_args, **_kwargs):
            self.name = "direct_pending_debug.jsonl"
            self.events = []
            debug_instances.append(self)

        def event(self, name, **data):
            self.events.append({
                "name": name,
                "policy_calls": len(policy.observations),
                **data,
            })

        def attach(self, result):
            result.setdefault("debug_log", self.name)

        def close(self, _result=None):
            pass

    class _Log:
        def __init__(self, _mode, params=None, obs_dim=0, debug=None):
            del params, debug
            self.obs_dim = int(obs_dim)
            self.rows = []
            log_instances.append(self)

        def tick(self, *args, **kwargs):
            self.rows.append((args, kwargs))

        def close(self, _result):
            return "direct_pending.csv"

    drive = SimpleNamespace(
        bus=bus,
        dry_run=False,
        _lock=threading.RLock(),
        gait=SimpleNamespace(stop=lambda: None),
        _torque_all=lambda _enabled: None,
        armed=False,
        mode="idle",
        status="idle",
    )
    initial = est._state()
    monkeypatch.setattr(rl_policy, "load_config", lambda _path: cfg)
    monkeypatch.setattr(rl_policy, "NumpyPolicy", lambda _path: policy)
    monkeypatch.setattr(rl_policy, "RobotStateEstimator",
                        lambda _bus, _cfg: est)
    monkeypatch.setattr(rl_policy, "_RunDebug", _Debug)
    monkeypatch.setattr(rl_policy, "_EpisodeLog", _Log)
    monkeypatch.setattr(rl_policy, "_set_weight_bearing_torque",
                        lambda _bus: None)
    monkeypatch.setattr(
        rl_policy, "preflight",
        lambda *_args, **_kwargs: (
            True, "", {"q_deg": [0.0] * rl_policy.N_JOINTS,
                       "start_pose": "sim_walk_start"}),
    )
    monkeypatch.setattr(
        rl_policy, "_preflight_start_target_deg",
        lambda *_args, **_kwargs: (
            np.zeros(rl_policy.N_JOINTS, dtype=float), ""),
    )
    monkeypatch.setattr(
        rl_policy, "_refresh_verified_start_pose",
        lambda *_args, **_kwargs: (initial, {"test": True}, ""),
    )
    monkeypatch.setattr(
        rl_policy, "_probe_async_transport",
        lambda _bus: {"async_capable": True},
    )
    monkeypatch.setattr(
        rl_policy, "_walk_vel_ref",
        lambda *_args, **_kwargs: (0.03, 0.0),
    )
    monkeypatch.setattr(rl_policy.time, "sleep", lambda _seconds: None)

    result = rl_policy._run_policy_move_impl(  # noqa: SLF001
        drive, "walk", duration_s=3.0, rot60=False,
        abort_check=lambda: bus.steps >= abort_after_steps,
    )
    return SimpleNamespace(
        result=result,
        policy=policy,
        bus=bus,
        debug=debug_instances[0],
        log=log_instances[0],
    )


def test_direct_stream_returns_pending_at_first_repeated_snapshot():
    bus = _FakeStepBus(snaps=[_snapshot(7) for _ in range(4)])
    est = _MetadataSnapshotEstimator()
    initial = _state(
        timestamp=time.monotonic(),
        timing={"source": "step_all", "snapshot_seq": 6,
                "pos_age_ms": 1.0, "imu_age_ms": 1.0},
    )

    out = rl_policy._stream_target(  # noqa: SLF001
        bus, est, np.zeros(rl_policy.N_JOINTS),
        np.ones(rl_policy.N_JOINTS) * 0.1,
        t_next=0.0, inner_steps=4, inner_dt=0.0,
        write_speed=100, write_acc=20, abort_check=lambda: False,
        last_good_state=initial, stale_ticks=0, max_stale_ticks=2,
    )

    state, _next, _overruns, err, stale_ticks, stale_samples, _timing = out
    assert err == rl_policy.DIRECT_STREAM_STALE_PENDING
    assert stale_ticks == 1
    assert stale_samples == 1
    assert [snap["seq"] for snap in est.snapshots] == [7]
    assert bus.steps == 2
    assert state.timing["stale_diag"]["snapshot_rejected"] is True
    assert state.timing["stale_diag"]["stale_pending"] is True
    assert "did not advance" in state.timing["stale_diag"][
        "snapshot_freshness_error"]


@pytest.mark.parametrize("snapshot", [
    {**_snapshot(8), "pos_age_ms": 151.0},
    {**_snapshot(8), "imu_age_ms": float("nan")},
    {key: value for key, value in _snapshot(8).items()
     if key != "imu_age_ms"},
])
def test_direct_stream_rejects_invalid_snapshot_age_before_estimator(snapshot):
    bus = _FakeStepBus(snaps=[snapshot])
    est = _MetadataSnapshotEstimator()
    initial = _state(
        timestamp=time.monotonic(),
        timing={"source": "step_all", "snapshot_seq": 7,
                "pos_age_ms": 1.0, "imu_age_ms": 1.0},
    )

    out = rl_policy._stream_target(  # noqa: SLF001
        bus, est, np.zeros(rl_policy.N_JOINTS),
        np.ones(rl_policy.N_JOINTS) * 0.1,
        t_next=0.0, inner_steps=1, inner_dt=0.0,
        write_speed=100, write_acc=20, abort_check=lambda: False,
        last_good_state=initial, stale_ticks=0, max_stale_ticks=0,
    )

    state, _next, _overruns, err, stale_ticks, stale_samples, _timing = out
    assert err == "feedback stale during stream"
    assert stale_ticks == 1
    assert stale_samples == 1
    assert est.snapshots == []
    assert state.timing["stale_diag"]["snapshot_rejected"] is True


def test_direct_stream_accepts_uint16_snapshot_sequence_wrap():
    bus = _FakeStepBus(snaps=[_snapshot(0)])
    est = _MetadataSnapshotEstimator()
    initial = _state(
        timestamp=time.monotonic(),
        timing={"source": "step_all", "snapshot_seq": 65535,
                "pos_age_ms": 1.0, "imu_age_ms": 1.0},
    )

    out = rl_policy._stream_target(  # noqa: SLF001
        bus, est, np.zeros(rl_policy.N_JOINTS),
        np.ones(rl_policy.N_JOINTS) * 0.1,
        t_next=0.0, inner_steps=1, inner_dt=0.0,
        write_speed=100, write_acc=20, abort_check=lambda: False,
        last_good_state=initial, stale_ticks=0, max_stale_ticks=0,
    )

    state, _next, _overruns, err, stale_ticks, stale_samples, _timing = out
    assert err == ""
    assert stale_ticks == 0
    assert stale_samples == 0
    assert state.timing["snapshot_seq"] == 0
    assert [snap["seq"] for snap in est.snapshots] == [0]


def test_reconcile_safety_anchor_preserves_debounces_and_entry_ramp():
    safety = rl_policy.SafetyLayer({})
    safety._entry_ticks = 7  # noqa: SLF001
    safety._over_current_ticks = 5  # noqa: SLF001
    safety._over_temp_ticks = 2  # noqa: SLF001
    safety._incomplete_feedback_ticks = 1  # noqa: SLF001
    safety._last_feedback_sample_seq = 44  # noqa: SLF001
    held = np.linspace(-0.1, 0.1, rl_policy.N_JOINTS)

    rl_policy._reconcile_safety_command_anchor(safety, held)  # noqa: SLF001

    np.testing.assert_array_equal(safety._last_safe, held)  # noqa: SLF001
    assert safety._entry_ticks == 7  # noqa: SLF001
    assert safety._over_current_ticks == 5  # noqa: SLF001
    assert safety._over_temp_ticks == 2  # noqa: SLF001
    assert safety._incomplete_feedback_ticks == 1  # noqa: SLF001
    assert safety._last_feedback_sample_seq == 44  # noqa: SLF001


def test_direct_pending_wrap_recovery_holds_then_resumes_next_tick(monkeypatch):
    run = _run_direct_pending_policy_harness(
        monkeypatch,
        [_snapshot(0xFFFF), _snapshot(0),
         _snapshot(1), _snapshot(2), _snapshot(3), _snapshot(4)],
        abort_after_steps=6,
    )

    assert run.result["error"] == "aborted"
    assert run.result["held_pose"] is True
    assert len(run.policy.observations) == 2
    # The first rejected transaction and the wrap-recovery transaction both
    # carry the exact same already-sent target. Inference resumes only after
    # that recovery, so the next outer tick is the first command change.
    assert np.array_equal(run.bus.commands[0], run.bus.commands[1])
    assert not np.array_equal(run.bus.commands[1], run.bus.commands[2])
    recovered = [event for event in run.debug.events
                 if event["name"] == "stream_feedback_recovered_hold"]
    assert len(recovered) == 1
    assert recovered[0]["policy_calls"] == 1
    # prev_action (base obs 41:59) and the [sin, cos] phase clock are not
    # committed for the discarded partial action.
    first_obs, resumed_obs = run.policy.observations
    np.testing.assert_array_equal(first_obs[41:59], np.zeros(18))
    np.testing.assert_array_equal(resumed_obs[41:59], np.zeros(18))
    np.testing.assert_array_equal(first_obs[-2:], resumed_obs[-2:])
    run_rows = [row for row in run.log.rows if row[1].get("phase") != "tail"]
    assert len(run_rows) == 1


def test_direct_pending_abort_repeats_only_held_command(monkeypatch):
    run = _run_direct_pending_policy_harness(
        monkeypatch,
        [_snapshot(0xFFFF), _snapshot(0xFFFF)],
        abort_after_steps=2,
    )

    assert run.result["error"] == "aborted"
    assert run.result["held_pose"] is True
    assert run.result.get("limped") is not True
    assert len(run.policy.observations) == 1
    assert len(run.bus.commands) == 2
    assert np.array_equal(run.bus.commands[0], run.bus.commands[1])
    assert False not in run.bus.torque


def test_direct_pending_exhaustion_holds_without_new_targets(monkeypatch):
    run = _run_direct_pending_policy_harness(
        monkeypatch,
        [_snapshot(0xFFFF)] * (rl_policy.DRIVE_STREAM_STALE_TICKS + 1),
        abort_after_steps=10_000,
    )

    assert run.result["error"] == "feedback stale during stream"
    assert run.result["held_pose"] is True
    assert run.result["limped"] is False
    assert len(run.policy.observations) == 1
    assert len(run.bus.commands) == rl_policy.DRIVE_STREAM_STALE_TICKS + 1
    for command in run.bus.commands[1:]:
        np.testing.assert_array_equal(command, run.bus.commands[0])
    assert False not in run.bus.torque


def test_async_stream_target_writes_without_step_all_snapshot():
    bus = _FakeStepBus()
    sampler = _FakeSampler([_state()], age_s=0.02)

    out = rl_policy._stream_target_async(  # noqa: SLF001
        bus,
        sampler,
        np.zeros(rl_policy.N_JOINTS),
        np.ones(rl_policy.N_JOINTS) * 0.1,
        t_next=0.0,
        inner_steps=4,
        inner_dt=0.0,
        write_speed=100,
        write_acc=20,
        abort_check=lambda: False,
        last_good_state=_state(),
        stale_ticks=0,
        max_stale_ticks=3,
    )

    state, _t_next, _overruns, err, stale_ticks, stale_samples, timing = out
    assert err == ""
    assert state.bus_ok is True
    assert stale_ticks == 0
    assert stale_samples == 0
    assert bus.writes == 4
    assert bus.steps == 0
    assert len(sampler.commanded) == 4
    assert timing["read_s"] == pytest.approx(0.0)


def test_async_stream_target_marks_old_snapshot_stale():
    bus = _FakeStepBus()
    good0 = _state()
    sampler = _FakeSampler([good0], age_s=0.5, max_age_s=0.1)

    out = rl_policy._stream_target_async(  # noqa: SLF001
        bus,
        sampler,
        np.zeros(rl_policy.N_JOINTS),
        np.ones(rl_policy.N_JOINTS) * 0.1,
        t_next=0.0,
        inner_steps=1,
        inner_dt=0.0,
        write_speed=100,
        write_acc=20,
        abort_check=lambda: False,
        last_good_state=good0,
        stale_ticks=3,
        max_stale_ticks=3,
    )

    state, _t_next, _overruns, err, stale_ticks, stale_samples, _timing = out
    assert err == "feedback stale during stream"
    assert rl_policy._stream_state_is_stale(state)  # noqa: SLF001
    assert stale_ticks == 4
    assert stale_samples == 1
    # Age is checked before command dispatch: no extra learned target after
    # the hard freshness cap.
    assert bus.writes == 0
    assert bus.steps == 0


def test_async_stream_target_holds_through_isolated_old_snapshot():
    class _RecoveringSampler(_FakeSampler):
        def __init__(self, state):
            super().__init__([state], max_age_s=0.15)
            self.ages = [0.164, 0.02]
            self.calls = 0

        def latest(self):
            age_s = self.ages[min(self.calls, len(self.ages) - 1)]
            self.calls += 1
            return self.states[-1], age_s, {"samples": self.calls}

    bus = _FakeStepBus()
    good0 = _state()
    sampler = _RecoveringSampler(good0)

    out = rl_policy._stream_target_async(  # noqa: SLF001
        bus,
        sampler,
        np.zeros(rl_policy.N_JOINTS),
        np.ones(rl_policy.N_JOINTS) * 0.1,
        t_next=time.monotonic(),
        inner_steps=1,
        inner_dt=0.0,
        write_speed=100,
        write_acc=20,
        abort_check=lambda: False,
        last_good_state=good0,
        stale_ticks=0,
        max_stale_ticks=10,
    )

    state, _t_next, _overruns, err, stale_ticks, stale_samples, _timing = out
    assert err == ""
    assert not rl_policy._stream_state_is_stale(state)  # noqa: SLF001
    assert stale_ticks == 0
    assert stale_samples == 1
    assert sampler.calls == 2
    # The stale tick only holds; the new target is written after recovery.
    assert bus.writes == 1
    assert len(sampler.commanded) == 1


def test_async_stream_target_requires_consecutive_stale_limit():
    class _CountingStaleSampler(_FakeSampler):
        def __init__(self, state):
            super().__init__([state], age_s=0.164, max_age_s=0.15)
            self.calls = 0

        def latest(self):
            self.calls += 1
            return super().latest()

    bus = _FakeStepBus()
    good0 = _state()
    sampler = _CountingStaleSampler(good0)

    out = rl_policy._stream_target_async(  # noqa: SLF001
        bus,
        sampler,
        np.zeros(rl_policy.N_JOINTS),
        np.ones(rl_policy.N_JOINTS) * 0.1,
        t_next=time.monotonic(),
        inner_steps=1,
        inner_dt=0.0,
        write_speed=100,
        write_acc=20,
        abort_check=lambda: False,
        last_good_state=good0,
        stale_ticks=0,
        max_stale_ticks=3,
    )

    state, _t_next, _overruns, err, stale_ticks, stale_samples, _timing = out
    assert err == "feedback stale during stream"
    assert rl_policy._stream_state_is_stale(state)  # noqa: SLF001
    assert stale_ticks == 4
    assert stale_samples == 4
    assert sampler.calls == 4
    assert bus.writes == 0
    assert len(sampler.commanded) == 0


def test_async_tail_rejects_state_past_sampler_age_cap():
    state = _state(timestamp=time.monotonic())
    stale_sampler = _FakeSampler([state], age_s=0.151, max_age_s=0.15)
    fresh_sampler = _FakeSampler([state], age_s=0.149, max_age_s=0.15)

    stale_state, _ = rl_policy._latest_async_tail_state(  # noqa: SLF001
        stale_sampler)
    fresh_state, _ = rl_policy._latest_async_tail_state(  # noqa: SLF001
        fresh_sampler)

    assert stale_state is None
    assert fresh_state is state


def test_async_stream_target_can_skip_bus_write_on_decimated_tick():
    bus = _FakeStepBus()
    sampler = _FakeSampler([_state()], age_s=0.02)

    out = rl_policy._stream_target_async(  # noqa: SLF001
        bus,
        sampler,
        np.zeros(rl_policy.N_JOINTS),
        np.ones(rl_policy.N_JOINTS) * 0.1,
        t_next=0.0,
        inner_steps=1,
        inner_dt=0.0,
        write_speed=100,
        write_acc=20,
        abort_check=lambda: False,
        last_good_state=_state(),
        stale_ticks=0,
        max_stale_ticks=3,
        write_target=False,
    )

    state, _t_next, _overruns, err, stale_ticks, stale_samples, timing = out
    assert err == ""
    assert state.bus_ok is True
    assert stale_ticks == 0
    assert stale_samples == 0
    assert bus.writes == 0
    assert bus.steps == 0
    assert len(sampler.commanded) == 1
    assert timing["write_s"] == pytest.approx(0.0)


def test_stream_target_treats_stream_step_all_miss_as_stale_sample():
    bus = _FakeStepBus(snaps=[None, None, None, None])
    good0 = _state()
    est = _FakeEstimator([])

    out = rl_policy._stream_target(  # noqa: SLF001
        bus,
        est,
        np.zeros(rl_policy.N_JOINTS),
        np.ones(rl_policy.N_JOINTS) * 0.1,
        t_next=0.0,
        inner_steps=4,
        inner_dt=0.0,
        write_speed=100,
        write_acc=20,
        abort_check=lambda: False,
        last_good_state=good0,
        stale_ticks=0,
        max_stale_ticks=3,
    )

    state, _t_next, _overruns, err, stale_ticks, stale_samples, _timing = out
    assert err == rl_policy.DIRECT_STREAM_STALE_PENDING
    assert rl_policy._stream_state_is_stale(state)  # noqa: SLF001
    diag = state.timing["stale_diag"]
    assert diag["transport"] == "step_all"
    assert diag["step_all_none"] is True
    assert diag["fallback_suppressed"] == "stream_firmware"
    assert diag["stale_ticks_after"] == 1
    assert diag["max_stale_ticks"] == 3
    assert diag["last_good_source"] == "fake_state"
    assert diag["stale_pending"] is True
    assert stale_ticks == 1
    assert stale_samples == 1
    assert bus.steps == 1
    assert bus.writes == 0


def test_stream_target_stops_after_stale_feedback_limit():
    bus = _FakeBus()
    good0 = _state()
    est = _FakeEstimator([_state(bus_ok=False) for _ in range(4)])

    out = rl_policy._stream_target(  # noqa: SLF001
        bus,
        est,
        np.zeros(rl_policy.N_JOINTS),
        np.ones(rl_policy.N_JOINTS) * 0.1,
        t_next=0.0,
        inner_steps=4,
        inner_dt=0.0,
        write_speed=100,
        write_acc=20,
        abort_check=lambda: False,
        last_good_state=good0,
        stale_ticks=0,
        max_stale_ticks=3,
    )

    (_state_out, _t_next, _overruns, err, stale_ticks, stale_samples,
     _timing) = out
    assert err == "feedback stale during stream"
    assert stale_ticks == 4
    assert stale_samples == 4
    assert bus.writes == 4
