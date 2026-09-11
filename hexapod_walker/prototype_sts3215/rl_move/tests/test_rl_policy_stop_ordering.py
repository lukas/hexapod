from types import SimpleNamespace
import threading

import numpy as np


import rl_policy
from rl_move.robot_state import RobotState


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


def _fallback():
    return np.linspace(-0.2, 0.2, rl_policy.N_JOINTS)


def _full_timing(snapshot_seq, feedback_seq, *, complete=True,
                 pos_age_ms=1.0, imu_age_ms=1.0):
    ids = list(range(rl_policy.N_JOINTS)) if complete else [0]
    return {
        "source": "read_snapshot",
        "snapshot_seq": snapshot_seq,
        "pos_age_ms": pos_age_ms,
        "imu_age_ms": imu_age_ms,
        "full_feedback": complete,
        "full_feedback_attempted": True,
        "full_feedback_complete": complete,
        "full_feedback_count": len(ids),
        "full_feedback_ids": ids,
        "feedback_sample_fresh": True,
        "feedback_sample_seq": feedback_seq,
    }


def _state(*, sequence=1, feedback_sequence=None, timestamp=None,
           pose=None, roll_deg=0.0, pitch_deg=0.0, bus_ok=True,
           complete=True, pos_age_ms=1.0, imu_age_ms=1.0,
           current=0.4, temperature=31.0, load=12.0):
    if feedback_sequence is None:
        feedback_sequence = sequence
    if timestamp is None:
        timestamp = float(sequence)
    if pose is None:
        pose = _fallback()
    return SimpleNamespace(
        timestamp=float(timestamp),
        joint_position=np.asarray(pose, dtype=float).copy(),
        joint_velocity=np.zeros(rl_policy.N_JOINTS),
        imu_roll=roll_deg / rl_policy.RAD2DEG,
        imu_pitch=pitch_deg / rl_policy.RAD2DEG,
        imu_gyro=np.zeros(3),
        servo_current=np.full(rl_policy.N_JOINTS, current),
        servo_temperature=np.full(rl_policy.N_JOINTS, temperature),
        servo_load=np.full(rl_policy.N_JOINTS, load),
        bus_ok=bus_ok,
        imu_ok=True,
        timing=_full_timing(
            sequence, feedback_sequence, complete=complete,
            pos_age_ms=pos_age_ms, imu_age_ms=imu_age_ms,
        ),
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


def _run(monkeypatch, states, *, fail_write=False,
         tilt_reference_deg=(0.0, 0.0), baseline_state=None):
    order = []
    bus = _Bus(order, fail_write=fail_write)
    drive = _Drive(order)
    est = _Estimator(order, states)
    debug = _Debug(order)
    monkeypatch.setattr(
        rl_policy, "_set_weight_bearing_torque",
        lambda _bus: order.append("weight_bearing_torque"),
    )
    fallback = _fallback()
    held = rl_policy._hold_after_stream_loss(  # noqa: SLF001
        bus, drive, est, fallback,
        write_speed=800, write_acc=40, policy_dt=0.0,
        debug=debug,
        baseline_state=(baseline_state if baseline_state is not None else
                        _state(sequence=0, feedback_sequence=0,
                               timestamp=0.0)),
        tilt_reference=tuple(
            float(value) / rl_policy.RAD2DEG
            for value in tilt_reference_deg),
        max_tilt_deg=25.0,
        max_pose_delta_deg=8.0,
        max_state_age_s=0.15,
        max_current_a=2.5,
        max_temp_c=65.0,
        max_load_pct=90.0,
    )
    return SimpleNamespace(
        held=held, order=order, bus=bus, drive=drive, est=est,
        debug=debug, fallback=fallback,
    )


def test_fallback_hold_write_precedes_foreground_resample(monkeypatch):
    run = _run(monkeypatch, [
        None,
        _state(sequence=1),
        _state(sequence=2),
        _state(sequence=3),
    ])

    assert run.held is True
    assert run.order.index("write") < run.order.index("sample")
    np.testing.assert_allclose(run.est.commanded[0], run.fallback)
    np.testing.assert_allclose(
        run.bus.commands[0][0], run.fallback * rl_policy.RAD2DEG,
    )
    assert len(run.bus.commands) == 1
    assert "weight_bearing_torque" not in run.order[:run.order.index("write")]
    assert "torque:True" not in run.order[:run.order.index("write")]
    assert run.order.count("sample") == 4
    ok_event = next(fields for name, fields in run.debug.events
                    if name == "hold_after_stream_loss_ok")
    assert ok_event["confirmations"] == 3


def test_snapshot_bus_not_ok_is_skipped_after_fallback_write(monkeypatch):
    run = _run(monkeypatch, [
        _state(sequence=1, bus_ok=False),
        _state(sequence=2),
        _state(sequence=3),
        _state(sequence=4),
    ])

    assert run.held is True
    assert run.order.index("write") < run.order.index("sample")
    assert run.order.count("sample") == 4
    assert len(run.bus.commands) == 1
    np.testing.assert_allclose(
        run.bus.commands[0][0], run.fallback * rl_policy.RAD2DEG,
    )


def test_relative_tilt_reference_is_used_for_confirmation(monkeypatch):
    run = _run(monkeypatch, [
        _state(sequence=1, roll_deg=29.0),
        _state(sequence=2, roll_deg=29.0),
        _state(sequence=3, roll_deg=29.0),
    ], tilt_reference_deg=(10.0, 0.0))

    assert run.held is True
    assert len(run.bus.commands) == 1
    np.testing.assert_allclose(
        run.bus.commands[0][0], run.fallback * rl_policy.RAD2DEG,
    )
    sampled = next(fields for name, fields in run.debug.events
                   if name == "hold_after_stream_loss_sampled")
    assert sampled["tilt_relative_deg"] == 19.0
    assert sampled["tilt_within_envelope"] is True
    assert sampled["reanchored"] is False


def test_relative_tilt_outside_envelope_never_reports_hold(monkeypatch):
    run = _run(monkeypatch, [
        _state(sequence=i, roll_deg=36.0)
        for i in range(1, rl_policy.DRIVE_STREAM_HOLD_MAX_ATTEMPTS + 1)
    ], tilt_reference_deg=(10.0, 0.0))

    assert run.held is False
    assert any(name == "hold_after_stream_loss_unconfirmed"
               for name, _fields in run.debug.events)


def test_missing_fresh_diagnostic_sample_does_not_report_hold(monkeypatch):
    run = _run(
        monkeypatch, [None] * rl_policy.DRIVE_STREAM_HOLD_MAX_ATTEMPTS)

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
    assert "weight_bearing_torque" not in run.order
    assert ("hold_after_stream_loss_write_failed", {}) in run.debug.events


def test_replayed_snapshot_cannot_supply_three_confirmations(monkeypatch):
    run = _run(monkeypatch, [
        _state(sequence=7, timestamp=float(i), feedback_sequence=i)
        for i in range(1, rl_policy.DRIVE_STREAM_HOLD_MAX_ATTEMPTS + 1)
    ])

    assert run.held is False
    sampled = [fields for name, fields in run.debug.events
               if name == "hold_after_stream_loss_sampled"]
    assert sampled[0]["ok"] is True
    assert all(fields["reason"] == "snapshot_seq_not_advancing"
               for fields in sampled[1:])


def test_missing_pre_loss_identity_is_bootstrapped_not_counted(monkeypatch):
    run = _run(
        monkeypatch,
        [_state(sequence=i) for i in range(1, 5)],
        baseline_state=SimpleNamespace(timestamp=None, timing={}),
    )

    assert run.held is True
    sampled = [fields for name, fields in run.debug.events
               if name == "hold_after_stream_loss_sampled"]
    assert sampled[0]["reason"] == "identity_baseline_missing"
    assert sampled[0]["confirmation"] == 0
    assert sampled[-1]["confirmation"] == 3


def test_replayed_full_feedback_cannot_supply_three_confirmations(monkeypatch):
    run = _run(monkeypatch, [
        _state(sequence=i, feedback_sequence=7)
        for i in range(1, rl_policy.DRIVE_STREAM_HOLD_MAX_ATTEMPTS + 1)
    ])

    assert run.held is False
    sampled = [fields for name, fields in run.debug.events
               if name == "hold_after_stream_loss_sampled"]
    assert sampled[0]["ok"] is True
    assert all(fields["reason"] == "feedback_seq_not_advancing"
               for fields in sampled[1:])


def test_stale_position_source_never_reports_hold(monkeypatch):
    run = _run(monkeypatch, [
        _state(sequence=i, pos_age_ms=151.0)
        for i in range(1, rl_policy.DRIVE_STREAM_HOLD_MAX_ATTEMPTS + 1)
    ])

    assert run.held is False
    sampled = [fields for name, fields in run.debug.events
               if name == "hold_after_stream_loss_sampled"]
    assert all(fields["reason"] == "pos_age_ms_stale" for fields in sampled)


def test_pose_must_converge_inside_bounded_target_envelope(monkeypatch):
    poses = []
    for error_deg in (9.0, 7.0, 5.0, 3.0):
        pose = _fallback().copy()
        pose[5] += error_deg / rl_policy.RAD2DEG
        poses.append(pose)
    run = _run(monkeypatch, [
        _state(sequence=i, pose=pose)
        for i, pose in enumerate(poses, start=1)
    ])

    assert run.held is True
    sampled = [fields for name, fields in run.debug.events
               if name == "hold_after_stream_loss_sampled"]
    assert sampled[0]["reason"] == "pose_not_converged"
    assert [fields["max_pose_delta_deg"] for fields in sampled] == [
        9.0, 7.0, 5.0, 3.0]
    assert sampled[-1]["confirmation"] == 3


def test_full_healthy_feedback_is_required_for_every_confirmation(monkeypatch):
    run = _run(monkeypatch, [
        _state(sequence=1),
        _state(sequence=2, complete=False),
        _state(sequence=3),
        _state(sequence=4),
        _state(sequence=5),
    ])

    assert run.held is True
    sampled = [fields for name, fields in run.debug.events
               if name == "hold_after_stream_loss_sampled"]
    assert sampled[1]["reason"] == "full_feedback_incomplete"
    assert sampled[1]["confirmation"] == 0
    assert sampled[-1]["confirmation"] == 3


def test_unhealthy_current_never_reports_hold(monkeypatch):
    run = _run(monkeypatch, [
        _state(sequence=i, current=3.0)
        for i in range(1, rl_policy.DRIVE_STREAM_HOLD_MAX_ATTEMPTS + 1)
    ])

    assert run.held is False
    sampled = [fields for name, fields in run.debug.events
               if name == "hold_after_stream_loss_sampled"]
    assert all(fields["reason"] == "current_outside_envelope"
               for fields in sampled)


def _run_drive_stop_harness(monkeypatch, *, fault, hold_result):
    cfg = {
        "control": {"hz": 100, "inner_hz": 100},
        "sensing": {"full_feedback_hz": 10},
        "safety": {"max_delta_q_deg": 0.375},
    }

    class _Policy:
        meta = {
            "name": "stop-ordering-drive-policy",
            "obs_dim": 74,
            "training_hz": 100,
            "phase_hz": 1.0,
            "joint_frame": rl_policy.FRAME_ROBOT_ABS,
            "joint_contract": rl_policy.JOINT_CONTRACT,
            "walk_speed_min_m_s": 0.05,
            "walk_speed_max_m_s": 0.08,
        }

        def __init__(self):
            self.calls = 0

        def act(self, _obs):
            self.calls += 1
            return np.full(rl_policy.N_JOINTS,
                           min(0.8, self.calls * 0.1))

        def reset(self):
            self.calls = 0

    class _Estimator:
        def set_commanded(self, _command):
            pass

        def reset_episode_filters(self):
            pass

        def update(self, want_full_feedback=False):
            del want_full_feedback
            return _robot_state()

    class _SessionDebug:
        name = "stop_ordering_drive_debug.jsonl"

        def __init__(self, *_args, **_kwargs):
            pass

        def event(self, *_args, **_kwargs):
            pass

        def attach(self, result):
            result.setdefault("debug_log", self.name)

        def close(self, _result=None):
            pass

    class _SessionLog:
        def __init__(self, _mode, params=None, obs_dim=0, debug=None):
            del params, debug
            self.obs_dim = int(obs_dim)

        def tick(self, *_args, **_kwargs):
            pass

        def close(self, _result):
            return "stop_ordering_drive.csv"

    class _Command:
        def get(self):
            return 0.06, 0.0, 0.0, 0.0, 0.0, False

        def publish(self, _snapshot):
            pass

    order = []
    bus = _Bus(order)
    estimator = _Estimator()
    policy = _Policy()
    drive = SimpleNamespace(
        bus=bus, dry_run=False, _lock=threading.RLock(),
        gait=SimpleNamespace(stop=lambda: None),
        _torque_all=lambda enabled: order.append(f"torque:{enabled}"),
        armed=False, mode="idle", status="idle",
    )
    stream_targets = []
    recovery_targets = []

    def stream(_bus, _est, _q_from, q_to, *, t_next,
               stale_ticks, on_write_success, **_kwargs):
        target = np.asarray(q_to, dtype=float).copy()
        stream_targets.append(target)
        if fault == "stale" and len(stream_targets) > 1:
            return (_robot_state(bus_ok=False), t_next, 0,
                    "feedback stale during stream", stale_ticks + 1, 1,
                    {"stream_s": 0.0, "write_s": 0.0,
                     "read_s": 0.0, "lag_s": 0.0})
        _bus.write_all((target * rl_policy.RAD2DEG).tolist(),
                       speed=800, acc=40)
        on_write_success(target)
        return (_robot_state(), t_next, 0, "", 0, 0,
                {"stream_s": 0.0, "write_s": 0.0,
                 "read_s": 0.0, "lag_s": 0.0})

    def recover(_bus, _drive, _est, fallback, **_kwargs):
        recovery_targets.append(np.asarray(fallback, dtype=float).copy())
        return bool(hold_result)

    monkeypatch.setattr(rl_policy, "load_config", lambda _path: cfg)
    monkeypatch.setattr(rl_policy, "NumpyPolicy", lambda _path: policy)
    monkeypatch.setattr(rl_policy, "RobotStateEstimator",
                        lambda _bus, _cfg: estimator)
    monkeypatch.setattr(
        rl_policy, "_AsyncSnapshotSampler",
        lambda *_args, **_kwargs: pytest.fail(
            "persistent drive must use combined snapshots"),
    )
    monkeypatch.setattr(rl_policy, "_RunDebug", _SessionDebug)
    monkeypatch.setattr(rl_policy, "_EpisodeLog", _SessionLog)
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
        lambda *_args, **_kwargs: (_robot_state(), {}, ""),
    )
    monkeypatch.setattr(rl_policy, "_probe_async_transport",
                        lambda _bus: {"async_capable": True})
    monkeypatch.setattr(rl_policy, "_stream_target", stream)
    monkeypatch.setattr(rl_policy, "_hold_after_stream_loss", recover)
    monkeypatch.setattr(rl_policy, "DRIVE_WALK_ACTION_RAMP_S", 0.0)
    monkeypatch.setattr(rl_policy.time, "sleep", lambda _seconds: None)
    if fault == "timing":
        monkeypatch.setattr(
            rl_policy, "_drive_timing_trip_reason",
            lambda *_args, **_kwargs: "synthetic drive timing stop",
        )
    else:
        monkeypatch.setattr(rl_policy, "_drive_timing_trip_reason",
                            lambda *_args, **_kwargs: None)

    result = rl_policy._run_drive_session_impl(  # noqa: SLF001
        drive, _Command(), rot60=False, hold_weights=None)
    return SimpleNamespace(
        result=result, order=order, bus=bus, drive=drive,
        stream_targets=stream_targets, recovery_targets=recovery_targets,
    )


def test_drive_stale_stop_holds_last_successfully_written_target(monkeypatch):
    run = _run_drive_stop_harness(
        monkeypatch, fault="stale", hold_result=True)

    assert run.result["error"].endswith("held last written target")
    assert run.result["held_pose"] is True
    assert run.result["limped"] is False
    assert len(run.stream_targets) == 2
    assert len(run.recovery_targets) == 1
    np.testing.assert_allclose(run.recovery_targets[0], run.stream_targets[0])
    assert not np.array_equal(run.recovery_targets[0], run.stream_targets[1])
    assert "torque:False" not in run.order


def test_drive_stale_stop_unverified_hold_confirms_limp(monkeypatch):
    run = _run_drive_stop_harness(
        monkeypatch, fault="stale", hold_result=False)

    assert run.result["error"].endswith("hold unverified; limped")
    assert run.result["held_pose"] is False
    assert run.result["limped"] is True
    assert run.order[-1] == "torque:False"
    assert run.drive.armed is False
    assert run.drive.status == "rl drive limped after unverified stream hold"


def test_drive_timing_stop_unverified_hold_confirms_limp(monkeypatch):
    run = _run_drive_stop_harness(
        monkeypatch, fault="timing", hold_result=False)

    assert run.result["error"] == "synthetic drive timing stop"
    assert run.result["held_pose"] is False
    assert run.result["limped"] is True
    assert run.order[-1] == "torque:False"
    assert run.drive.armed is False
    assert run.drive.status == "rl drive limped after unverified stream hold"


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


def test_stale_imu_with_fresh_positions_confirms_imu_blind_hold(monkeypatch):
    # 2026-09-10 hexapod2: an I2C dropout froze the IMU cache (age 561-665 ms)
    # while all 18 servos kept answering; refusing the hold for that alone
    # limped a standing robot. Positions, pose envelope and servo health are
    # still verified; only the relative-tilt check is skipped.
    run = _run(monkeypatch, [
        _state(sequence=i, imu_age_ms=600.0)
        for i in range(1, rl_policy.DRIVE_STREAM_HOLD_CONFIRMATIONS + 2)
    ])

    assert run.held is True
    assert "limp" not in run.order
    sampled = [fields for name, fields in run.debug.events
               if name == "hold_after_stream_loss_sampled"]
    assert any(fields.get("imu_blind") for fields in sampled)
    assert "IMU blind" in run.drive.status


def test_stale_imu_does_not_excuse_stale_positions(monkeypatch):
    run = _run(monkeypatch, [
        _state(sequence=i, pos_age_ms=151.0, imu_age_ms=600.0)
        for i in range(1, rl_policy.DRIVE_STREAM_HOLD_MAX_ATTEMPTS + 1)
    ])

    assert run.held is False
    sampled = [fields for name, fields in run.debug.events
               if name == "hold_after_stream_loss_sampled"]
    assert all(fields["reason"] == "pos_age_ms_stale" for fields in sampled)


def test_stale_imu_still_rejects_pose_and_health_envelopes(monkeypatch):
    bad_pose = _fallback() + 0.5
    run = _run(monkeypatch, [
        _state(sequence=i, imu_age_ms=600.0, pose=bad_pose)
        for i in range(1, rl_policy.DRIVE_STREAM_HOLD_MAX_ATTEMPTS + 1)
    ])
    assert run.held is False
    run = _run(monkeypatch, [
        _state(sequence=i, imu_age_ms=600.0, current=3.0)
        for i in range(1, rl_policy.DRIVE_STREAM_HOLD_MAX_ATTEMPTS + 1)
    ])
    assert run.held is False
