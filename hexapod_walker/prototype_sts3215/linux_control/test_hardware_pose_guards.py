"""Off-robot boundary checks: unreachable paths never enable torque."""
from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest

import inplace_demos
import pinned_tip
import safe_zero
from api.core import CoreApi
from api.demos import DemosApi
from api.standup import StandupApi, validated_standup_frames
from api.zero import ZeroApi
from feetech_bus import joint_to_servo_id, robot_pose_to_raw_degrees


def pose(hip=0.0, knee=0.0):
    return [0.0, hip, knee] * 6


def forbid(*_args, **_kwargs):
    pytest.fail("preflight must refuse before motion or worker startup")


@pytest.fixture
def no_motion(monkeypatch):
    for name in ("_enable_torque", "_set_torque_limit", "_write_pose"):
        monkeypatch.setattr(inplace_demos, name, forbid)


def test_path_checks_relative_knee_and_trim_limits():
    safe_zero.validate_motor_pose_path([pose(20, 80), pose(-20, 100)])
    with pytest.raises(ValueError, match="pose 1"):
        safe_zero.validate_motor_pose_path([pose(), pose(-78, 148)])
    trims = [0.0] * 18
    trims[2] = 11.0
    with pytest.raises(ValueError):
        safe_zero.validate_motor_pose_path([pose(0, 140)], trims)


def test_planner_refuses_unreachable_current_pose():
    result = safe_zero.plan_safe_zero(pose(-78, 148), allow_loaded_blend=True)
    assert result["ok"] is False
    assert result["code"] == "motor_limits"


def test_executor_checks_later_stages_before_any_arm(no_motion, monkeypatch):
    monkeypatch.setattr(inplace_demos, "_live_robot_ids", forbid)
    result = safe_zero.run_safe_zero(SimpleNamespace(trims=None), [
        {"goal": pose(), "seconds": 1},
        {"goal": pose(-78, 148), "seconds": 1},
    ], prepare_torque=forbid)
    assert result["ok"] is False
    assert result["code"] == "motor_limits"


def test_executor_checks_current_pose_before_any_arm(no_motion, monkeypatch):
    monkeypatch.setattr(inplace_demos, "_live_robot_ids",
                        lambda bus: {joint_to_servo_id(j) for j in range(18)})
    monkeypatch.setattr(inplace_demos, "_read_pose", lambda *args: pose(-78, 148))
    result = safe_zero.run_safe_zero(SimpleNamespace(trims=None), [
        {"goal": pose(), "seconds": 1}], prepare_torque=forbid)
    assert result["ok"] is False
    assert "start pose" in result["error"]


def test_direct_pose_refuses_before_preemption_or_arm(no_motion):
    api = CoreApi.__new__(CoreApi)
    api.drive = SimpleNamespace(bus=SimpleNamespace(trims=None), dry_run=False)
    api._bus_admission_error = lambda: None
    result = api.command_pose(pose(-78, 148), force=True)
    assert result["ok"] is False
    assert result["code"] == "motor_limits"


def test_standup_validates_optional_replant():
    # The authored raw knee is 140, but the replant needs 152.
    with pytest.raises(ValueError):
        validated_standup_frames([{"q_deg": pose(-10, 130), "s": 1}])


def test_descent_starts_at_measured_support_and_preserves_waypoints():
    from api.standup import descent_frames_from_present
    frames = [(pose(20, 80), .8), (pose(10, 40), 2), (pose(), 2)]
    measured = pose(18, 87)
    result = descent_frames_from_present(frames, measured)
    assert result[0][0] == measured
    assert result[1:] == frames[1:]
    assert frames[0][0] == pose(20, 80)


def test_descent_refuses_unreachable_measured_pose():
    from api.standup import descent_frames_from_present
    with pytest.raises(ValueError):
        descent_frames_from_present([(pose(), 1)], pose(-78, 148))


def test_standup_refuses_authored_path_before_acquisition(no_motion):
    api = StandupApi()
    api.drive = SimpleNamespace(bus=SimpleNamespace(trims=None), dry_run=False)
    api._load_standup = lambda: {"modes": {"step": {"keyframes": [
        {"q_deg": pose(), "s": 1}, {"q_deg": pose(-78, 148), "s": 1}]}}}
    api._drive_active = lambda: False
    api._demo_thread = None
    api._acquire_start = forbid
    result = api.standup(force=True)
    assert result["ok"] is False
    assert result["code"] == "motor_limits"


def test_standup_failed_acquisition_does_not_arm_worker(no_motion, monkeypatch):
    monkeypatch.setattr(inplace_demos, "_live_robot_ids",
                        lambda bus: {joint_to_servo_id(j) for j in range(18)})
    api = StandupApi()
    api.drive = SimpleNamespace(
        bus=SimpleNamespace(trims=None), dry_run=False, armed=False,
        mode="idle", _lock=threading.RLock(), gait=SimpleNamespace(stop=lambda: None),
        arm_at_present=forbid)
    api._load_standup = lambda: {"modes": {"step": {"keyframes": [
        {"q_deg": pose(), "s": 1}]}}}
    api._present_pose18 = lambda: (pose(10, 20), [])
    api._normal_standing_pose = lambda q: None
    api._delta_vs_present = lambda q: (20.0, 1)
    api._acquire_start = lambda *args, **kwargs: {"ok": False, "error": "refused"}
    api._demo_gen = 1
    api._demo_abort = threading.Event()
    api._lock = threading.RLock()
    api._bus_hot_begin = api._bus_hot_end = lambda: None
    api._set_activity = lambda *args: None
    result = api.standup(sync_gen=1)
    assert result["ok"] is False
    assert "refused" in result["error"]
    assert not api.drive.armed


def zero_api():
    api = ZeroApi()
    api.drive = SimpleNamespace(bus=SimpleNamespace(trims=None), dry_run=False,
                                armed=False)
    api._present_pose18 = lambda: (pose(), [])
    return api


def test_untrap_refuses_before_worker_even_when_forced(no_motion, monkeypatch):
    monkeypatch.setattr(pinned_tip, "check_pinned_tip", lambda bus: {"pinned": True})
    monkeypatch.setattr(pinned_tip, "run_untrap_tuck", forbid)
    api = zero_api()
    result = api.untrap(force=True)
    assert result["ok"] is False
    assert result["code"] == "motor_limits"
    assert "raw servo joint 2 outside limits: 190" in result["error"]
    assert not api.drive.armed


def test_safe_zero_pinned_recovery_refuses_before_untrap(no_motion, monkeypatch):
    monkeypatch.setattr(pinned_tip, "check_pinned_tip", lambda bus: {"pinned": True})
    monkeypatch.setattr(pinned_tip, "run_untrap_tuck", forbid)
    api = zero_api()
    result = api._safe_zero_sync(abort_check=lambda: False)
    assert result["ok"] is False
    assert result["code"] == "motor_limits"
    assert not api.drive.armed


def test_stand_acquisition_checks_later_rise_before_safe_zero(no_motion, monkeypatch):
    monkeypatch.setattr(pinned_tip, "check_pinned_tip", lambda bus: {})
    api = zero_api()
    api._normal_standing_pose = lambda q: None
    api._fold_recent = lambda: False
    api._stand_route_decision = lambda *args, **kwargs: ("safe_zero", "test")
    api._safe_zero_sync = forbid
    api._load_standup = lambda: {"modes": {"step": {"keyframes": [
        {"q_deg": pose(), "s": 1}, {"q_deg": pose(-78, 148), "s": 1}]}}}
    result = api._acquire_start("stand", gen=1, on_progress=lambda p: None)
    assert result["ok"] is False
    assert result["code"] == "motor_limits"
    assert not api.drive.armed


def test_walk_ready_checks_all_planned_frames_before_arm(no_motion, monkeypatch):
    from hexapod_core import joint_frame
    import hexapod_core.walk_ready_transition as transition

    monkeypatch.setattr(joint_frame, "walk_start_pose_degrees", lambda: pose())
    monkeypatch.setattr(transition, "build_tripod_plant_transition", lambda *args: [
        SimpleNamespace(q_deg=pose()), SimpleNamespace(q_deg=pose(-78, 148))])
    monkeypatch.setattr(inplace_demos, "_live_robot_ids", forbid)
    api = DemosApi()
    api.drive = SimpleNamespace(bus=SimpleNamespace(trims=None), armed=False)
    api._present_pose18 = lambda: (pose(20, 50), [])
    api._pose_delta = lambda *args: 100.0
    result = api._step_to_rl_walk_ready_start_sync(abort_check=lambda: False)
    assert result["ok"] is False
    assert "plan walk-ready" in result["error"]
    assert not api.drive.armed


def test_stall_guard_uses_raw_knee_error_and_speed(monkeypatch):
    # Absolute knee already equals goal and moves with its hip, but the
    # physical knee motor is ten degrees short, stationary and fighting.
    current, goal = pose(20, 30), pose(10, 30)
    raw = robot_pose_to_raw_degrees(current)
    fb = {j: {"deg": current[j], "raw_deg": raw[j], "speed_deg_s": 90.0,
              "raw_speed_deg_s": 90.0, "current_a": 0.0, "temp_c": 25}
          for j in range(18)}
    fb[2].update(raw_speed_deg_s=0.0, current_a=3.0)
    bus = SimpleNamespace(trims=None, read_all_feedback=lambda: fb)
    live = {joint_to_servo_id(j) for j in range(18)}
    monkeypatch.setattr(inplace_demos, "_live_robot_ids", lambda bus: live)
    monkeypatch.setattr(inplace_demos, "_read_pose", lambda *args: current)
    monkeypatch.setattr(inplace_demos, "_glide_speed_acc", lambda *args: (100, 10))
    for name in ("_enable_torque", "_set_torque_limit", "_write_pose"):
        monkeypatch.setattr(inplace_demos, name, lambda *args, **kwargs: None)
    limped = []
    monkeypatch.setattr(inplace_demos, "_limp_all", lambda *args: limped.append(True))
    now = [100.0]
    monkeypatch.setattr(safe_zero, "time", SimpleNamespace(
        monotonic=lambda: now[0], sleep=lambda dt: now.__setitem__(0, now[0] + dt)))
    result = safe_zero.run_safe_zero(bus, [{"goal": goal, "seconds": 1.0}])
    assert result["ok"] is False and result["limp"] is True
    assert "stall-fight" in result["error"]
    assert "10° from target" in result["error"]
    assert limped
