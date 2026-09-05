from types import SimpleNamespace
from pathlib import Path
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


@pytest.mark.parametrize("alpha", [float("nan"), float("inf"), -0.01, 1.01, "bad", []])
def test_drive_velocity_alpha_rejected_before_bus_access(alpha):
    # None drive would fail immediately if the runner reached its bus access.
    result = rl_policy.run_drive_session(None, None, velocity_filter_alpha=alpha)
    assert result["ok"] is False
    assert "velocity_filter_alpha" in result["error"]


@pytest.mark.parametrize("alpha", [None, 0.0, 0.8, 1.0])
def test_drive_velocity_alpha_is_local_and_reaches_real_estimator(alpha):
    cfg = {"velocity_filter": {"alpha": 0.3, "max_jump_rad": 0.5}}
    local_cfg = rl_policy._drive_filter_config(cfg, alpha)
    est = RobotStateEstimator(None, local_cfg)
    est._qd_filter.update(np.zeros(18), 1.0)
    velocity = est._qd_filter.update(np.full(18, 0.1), 1.1)
    expected = 0.3 if alpha is None else alpha
    assert np.allclose(velocity, expected)
    assert cfg["velocity_filter"] == {"alpha": 0.3, "max_jump_rad": 0.5}
    assert local_cfg["velocity_filter"]["max_jump_rad"] == 0.5


def test_drive_velocity_alpha_wrapper_forwards_override(monkeypatch):
    calls = []
    monkeypatch.setattr(rl_policy, "_run_drive_session_impl",
                        lambda *a, **kw: calls.append(kw) or {"ok": True})
    assert rl_policy.run_drive_session(None, None, velocity_filter_alpha=0.8)["ok"]
    assert calls[0]["velocity_filter_alpha"] == 0.8


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

    def step_all(self, _deg, *, speed, acc):
        self.steps += 1
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


@pytest.mark.parametrize("persistent_missing", [False, True])
def test_persistent_drive_uses_combined_snapshot_every_policy_tick(
        monkeypatch, persistent_missing):
    clock = [10.0]
    monkeypatch.setattr(rl_policy.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(rl_policy.time, "sleep",
                        lambda dt: clock.__setitem__(0, clock[0] + dt))

    class Bus(_AsyncHealthBus):
        def __init__(self):
            super().__init__()
            self.steps = 0

        def step_all(self, _degrees, **_kwargs):
            self.steps += 1
            return self.read_snapshot()

        def read_snapshot(self):
            snap = super().read_snapshot()
            if persistent_missing and self.steps:
                del snap["pos_deg"][4]
            return snap

    bus = Bus()
    torque_calls = []
    drive = SimpleNamespace(bus=bus, dry_run=False, _lock=threading.Lock(),
                            gait=SimpleNamespace(stop=lambda: None),
                            _torque_all=torque_calls.append)
    cfg = {"control": {"hz": 100, "inner_hz": 100, "drive_write_hz": 50},
           "sensing": {"full_feedback_hz": 10}}
    policy = SimpleNamespace(meta={
        "obs_dim": 74, "phase_hz": 1.333333, "training_hz": 100,
        "control_hz": 100, "joint_frame": "robot_abs",
        "joint_contract": rl_policy.JOINT_CONTRACT,
        "walk_speed_min_m_s": 0.08, "walk_speed_max_m_s": 0.08,
    }, act=lambda _obs: np.zeros(18), reset=lambda: None)
    monkeypatch.setattr(rl_policy, "load_config", lambda _path: cfg)
    monkeypatch.setattr(rl_policy, "NumpyPolicy", lambda _path: policy)
    monkeypatch.setattr(rl_policy, "preflight", lambda *_a, **_kw: (
        True, "", {"start_pose": "sim_walk_start"}))
    monkeypatch.setattr(rl_policy, "_preflight_start_target_deg",
                        lambda *_a, **_kw: (np.zeros(18), ""))
    monkeypatch.setattr(rl_policy, "_probe_async_transport",
                        lambda _bus: {"async_capable": True})
    monkeypatch.setattr(rl_policy, "_set_weight_bearing_torque", lambda _bus: None)
    monkeypatch.setattr(rl_policy, "_refresh_verified_start_pose",
                        lambda _bus, est, *_a, **_kw: (
                            est.update(want_full_feedback=True), {}, ""))
    debug = SimpleNamespace(name="fake", event=lambda *_a, **_kw: None,
                            attach=lambda _result: None, close=lambda *_a: None)
    monkeypatch.setattr(rl_policy, "_RunDebug", lambda *_a, **_kw: debug)
    ticks, params = [], []

    def episode_log(*_a, **kw):
        params.append(kw["params"])
        return SimpleNamespace(obs_dim=74,
                               tick=lambda *a, **kw: ticks.append((a[0], kw)),
                               close=lambda _result: "fake.csv")

    monkeypatch.setattr(rl_policy, "_EpisodeLog", episode_log)
    monkeypatch.setattr(rl_policy, "_AsyncSnapshotSampler",
                        lambda *_a, **_kw: pytest.fail("drive started async sampler"))
    command = SimpleNamespace(get=lambda: (0.08, 0.0, 0.0, 0.0, 0.0, False),
                              publish=lambda _state: None)
    result = rl_policy.run_drive_session(
        drive, command, abort_check=lambda: bus.steps >= 5,
        velocity_filter_alpha=0.8)

    if persistent_missing:
        assert result["error"] == "persistent missing servo positions: [4]"
        assert result["limped"] is True
        assert torque_calls[-1] is False
        assert bus.steps == 1
        return
    assert result["error"] == "aborted"
    assert result["transport"] == "step_all"
    assert result["velocity_filter_alpha"] == 0.8
    assert result["drive_write_hz"] == 100.0
    assert result["drive_write_every_ticks"] == 1
    assert params[0]["drive_snapshot"]["mode"] == "step_all"
    active = [(t, kw) for t, kw in ticks if kw.get("walk_engaged")]
    assert len(active) == bus.steps == 5
    assert np.diff([t for t, _ in active]) == pytest.approx([0.01] * 4)
    assert all(kw["bus_write_due"] for _, kw in active)


@pytest.mark.parametrize("bad_snapshot", [
    _snapshot(8), _snapshot(7), _snapshot(9, pos_age_ms=151),
    _snapshot(9, imu_age_ms=float("nan")),
])
def test_direct_drive_rejects_bad_snapshot_before_filtering(bad_snapshot):
    bus = _FakeStepBus([bad_snapshot])
    est = _FakeEstimator([])
    state = _state(timestamp=time.monotonic(), timing={
        "snapshot_seq": 8, "pos_age_ms": 1, "imu_age_ms": 1})
    result = rl_policy._stream_target(
        bus, est, np.zeros(18), np.zeros(18),
        t_next=time.monotonic(), inner_steps=1, inner_dt=0.001,
        write_speed=400, write_acc=20, abort_check=lambda: False,
        last_good_state=state, max_state_age_s=0.15)
    assert result[3] == "feedback stale during stream"
    assert est.snapshots == []
    assert bus.steps == 1 and bus.writes == 0


def test_direct_drive_stale_previous_state_prevents_next_write():
    bus = _FakeStepBus()
    state = _state(timestamp=time.monotonic() - 0.16, timing={
        "snapshot_seq": 8, "pos_age_ms": 1, "imu_age_ms": 1})
    result = rl_policy._stream_target(
        bus, _FakeEstimator([]), np.zeros(18), np.zeros(18),
        t_next=time.monotonic(), inner_steps=1, inner_dt=0.001,
        write_speed=400, write_acc=20, abort_check=lambda: False,
        last_good_state=state, max_state_age_s=0.15)
    assert result[3] == "feedback stale during stream"
    assert bus.steps == bus.writes == 0


@pytest.mark.parametrize("missing_reads, rotating", [(1, False), (2, False),
                                                   (3, False), (3, True)])
def test_direct_drive_retries_missing_positions_without_new_targets(
        monkeypatch, missing_reads, rotating):
    clock = [10.0]
    monkeypatch.setattr(rl_policy.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(rl_policy.time, "sleep",
                        lambda dt: clock.__setitem__(0, clock[0] + dt))
    snaps = [_snapshot(seq) for seq in (9, 10, 11)]
    for index, snap in enumerate(snaps[:missing_reads]):
        del snap["pos_deg"][4 + index if rotating else 4]
    bus = _FakeStepBus(snaps)
    retries = []

    def read_only():
        retries.append(1)
        return bus.snaps.pop(0)

    bus.read_snapshot = read_only
    est = _FakeEstimator([_state(timestamp=clock[0])])
    state = _state(timestamp=clock[0], timing={
        "snapshot_seq": 8, "pos_age_ms": 1, "imu_age_ms": 1})
    result = rl_policy._stream_target(
        bus, est, np.zeros(18), np.zeros(18),
        t_next=clock[0], inner_steps=1, inner_dt=0.01,
        write_speed=400, write_acc=20, abort_check=lambda: False,
        last_good_state=state, max_state_age_s=0.15)
    assert bus.steps == 1 and bus.writes == 0
    assert len(retries) == min(2, missing_reads)
    if missing_reads < 3:
        assert result[3] == ""
        assert len(est.snapshots) == 1
        assert len(est.snapshots[0]["pos_deg"]) == 18
    else:
        assert result[3] == ("feedback stale during stream" if rotating else
                             "persistent missing servo positions: [4]")
        assert est.snapshots == []


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


def test_drive_walk_engages_on_first_real_command():
    assert rl_policy.DRIVE_WALK_ENGAGE_S == pytest.approx(0.0)


def test_drive_zero_dwell_keeps_walk_through_brief_neutral_input():
    keep, zero_since = rl_policy._drive_zero_dwell(  # noqa: SLF001
        "walk", False, None, 9.63
    )
    assert keep is True
    assert zero_since == pytest.approx(9.63)

    keep, zero_since = rl_policy._drive_zero_dwell(  # noqa: SLF001
        "walk", False, zero_since, 9.63 + rl_policy.DRIVE_HOLD_SWITCH_S - 0.01
    )
    assert keep is True

    keep, zero_since = rl_policy._drive_zero_dwell(  # noqa: SLF001
        "walk", False, zero_since, 9.63 + rl_policy.DRIVE_HOLD_SWITCH_S
    )
    assert keep is False
    assert zero_since == pytest.approx(9.63)

    keep, zero_since = rl_policy._drive_zero_dwell(  # noqa: SLF001
        "walk", True, zero_since, 12.0
    )
    assert keep is False
    assert zero_since is None

    keep, zero_since = rl_policy._drive_zero_dwell(  # noqa: SLF001
        "hold", False, 9.63, 10.0
    )
    assert keep is False
    assert zero_since is None


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


@pytest.mark.parametrize("valid_count", [0, 17])
def test_async_sampler_partial_health_reaches_three_fresh_scan_debounce(
        monkeypatch, valid_count):
    # Reproduce the real 10 Hz failure: a new partial health frame, fresh
    # position/IMU, but the previous complete health frame is >150 ms old.
    clock = {"now": 10.0}
    monkeypatch.setattr(rl_policy.time, "monotonic", lambda: clock["now"])

    class PartialHealthBus(_AsyncHealthBus):
        def read_all_feedback(self):
            records = super().read_all_feedback()
            if self.feedback_reads == 1:
                return records
            return {j: records[j] for j in range(valid_count)}

    bus = PartialHealthBus()
    sampler = rl_policy._AsyncSnapshotSampler(bus, {}, hz=10.0)
    safety = rl_policy.SafetyLayer({})
    safety.set_nominal(np.zeros(rl_policy.N_JOINTS))
    frames, statuses = [], []

    class FourAcquisitions:
        def is_set(self):
            return len(frames) >= 4

        def wait(self, seconds):
            clock["now"] += seconds
            frame, age, stats = sampler.latest()
            frames.append((frame, age, stats))
            statuses.append(safety.check_servo_health(
                rl_policy._state_for_async_safety(frame)))
            # Repeated 100 Hz policy reads of the same 10 Hz frame do not
            # count as additional missing samples or repeat current checks.
            if len(frames) < 4:
                held, _, _ = sampler.latest()
                assert held.timing["async_feedback_fresh"] is False
                assert safety.check_servo_health(
                    rl_policy._state_for_async_safety(held)) is None
            return self.is_set()

    sampler._stop = FourAcquisitions()
    sampler._run(0.0)

    assert bus.feedback_reads == 4
    for frame, age, stats in frames:
        assert age < sampler.max_age_s
        assert frame.timing["async_health_ok"] is True
        assert frame.timing["async_feedback_fresh"] is True
        assert stats["feedback_age_ms"] == pytest.approx(100.0)
    assert frames[1][2]["health_age_ms"] == pytest.approx(200.0)
    assert frames[1][2]["feedback_valid_count"] == valid_count
    assert frames[1][2]["feedback_missing_ids"] == list(range(valid_count, 18))
    assert statuses[:3] == [None, None, None]
    assert statuses[3].terminate is True
    assert statuses[3].reason == "incomplete_feedback"


def test_async_sampler_recent_positions_do_not_refresh_health_acquisition(
        monkeypatch):
    clock = {"now": 10.0}
    monkeypatch.setattr(rl_policy.time, "monotonic", lambda: clock["now"])
    bus = _FakeBus()
    sampler = rl_policy._AsyncSnapshotSampler(
        bus, {}, initial_state=_state(
            timestamp=10.0, health=True, timing=_complete_health_timing()))
    sampler.mark_motion_ready()
    clock["now"] = 10.16
    # A producer publishing new position/IMU without acquiring health must
    # not extend the health clock using its newer state timestamp.
    sampler._latest_good = _state(timestamp=10.15, health=True, timing={
        "async_sample_seq": 1,
        "feedback_sample_fresh": False,
        "full_feedback_attempted": False,
    })
    state, age, stats = sampler.latest()
    assert age == pytest.approx(0.01)
    assert stats["feedback_age_ms"] == pytest.approx(160.0)
    assert state.timing["async_health_ok"] is False
    result = rl_policy._stream_target_async(
        bus, sampler, np.zeros(18), np.zeros(18),
        t_next=clock["now"], inner_steps=1, inner_dt=0.01,
        write_speed=0, write_acc=0, abort_check=lambda: False,
        last_good_state=state)
    assert "stale" in result[3]
    assert bus.writes == 0


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
    assert err == "feedback stale during stream"
    assert rl_policy._stream_state_is_stale(state)  # noqa: SLF001
    diag = state.timing["stale_diag"]
    assert diag["transport"] == "step_all"
    assert diag["step_all_none"] is True
    assert diag["fallback_suppressed"] == "stream_firmware"
    assert diag["stale_ticks_after"] == 4
    assert diag["max_stale_ticks"] == 3
    assert diag["last_good_source"] == "fake_state"
    assert stale_ticks == 4
    assert stale_samples == 4
    assert bus.steps == 4
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
