"""Off-robot checks for gait-survey soft versus hard safety handling."""
from __future__ import annotations

from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from rl_move.scripts import run_scripted_gait_suite as survey
from rl_move.scripts.analyze_apriltag_gait_motion import (
    _body_yaw_deg, _reference_axis,
)
from rl_move.scripts.analyze_scripted_gait_comparison import _motion_groups
from rl_move.scripts.analyze_scripted_gait_comparison import (
    _trusted_hardware_tilt,
)


class _Recorder:
    def assert_live(self) -> None:
        pass


def _args() -> SimpleNamespace:
    return SimpleNamespace(
        robot_url="http://unused.invalid",
        temp_trip_c=55.0,
        temp_trip_samples=3,
        temp_clear_samples=3,
        thermal_cooldown_timeout_s=2.0,
        thermal_cooldown_poll_s=0.0,
        voltage_trip_v=9.5,
        current_hard_a=3.0,
        current_sustained_a=2.4,
        tilt_trip_deg=22.0,
        tilt_trip_samples=3,
        soft_recovery=True,
        current_pause_a=1.8,
        tilt_pause_deg=14.0,
        temp_pause_c=50.0,
        voltage_pause_v=10.5,
        center_target_floor_m=None,
    )


def _feedback(*, current: float = 0.2, temp: float = 30.0,
              voltage: float = 12.0, roll: float = 0.0,
              pitch: float = 0.0, gyro: tuple[float, float, float] = (0, 0, 0)) -> dict:
    return {
        "ok": True,
        "live": 18,
        "roll_deg": roll,
        "pitch_deg": pitch,
        "gyro_dps": list(gyro),
        "joints": [
            {
                "deg": 0.0,
                "cur_a": current,
                "temp_c": temp,
                "load_pct": 0.0,
                "volt": voltage,
            }
            for _ in range(18)
        ],
    }


def test_pretrip_current_pauses_only_after_confirmation(tmp_path, monkeypatch):
    monkeypatch.setattr(survey, "_request", lambda *_args, **_kwargs: _feedback(
        current=1.9
    ))
    suite = survey.Suite(_args(), tmp_path, _Recorder())
    try:
        suite.sample_feedback()
        with pytest.raises(survey.SoftSafetyPause, match="pre-trip current"):
            suite.sample_feedback()
    finally:
        suite.close()


def test_hard_current_never_enters_recovery(tmp_path, monkeypatch):
    monkeypatch.setattr(survey, "_request", lambda *_args, **_kwargs: _feedback(
        current=3.1
    ))
    suite = survey.Suite(_args(), tmp_path, _Recorder())
    try:
        with pytest.raises(survey.HardSafetyTrip, match="hard trip"):
            suite.sample_feedback()
    finally:
        suite.close()


def test_temperature_trip_requires_three_same_joint_samples(
        tmp_path, monkeypatch):
    monkeypatch.setattr(
        survey, "_request", lambda *_args, **_kwargs: _feedback(temp=83.0)
    )
    suite = survey.Suite(_args(), tmp_path, _Recorder())
    try:
        suite.sample_feedback()
        suite.sample_feedback()
        with pytest.raises(
            survey.ThermalSafetyTrip, match="3 consecutive samples"
        ):
            suite.sample_feedback()
    finally:
        suite.close()


def test_health_check_ignores_one_fresh_missing_servo_scan(
        tmp_path, monkeypatch):
    suite = survey.Suite(_args(), tmp_path, _Recorder())
    states = iter([
        {
            "armed": True,
            "demo": {"running": False},
            "servo": {"live": 17, "missing": [1], "ts": 1.0,
                      "tripped": [], "max_temp_c": 30.0},
        },
        {
            "armed": True,
            "demo": {"running": False},
            "servo": {"live": 18, "missing": [], "ts": 2.0,
                      "tripped": [], "max_temp_c": 30.0},
        },
    ])
    monkeypatch.setattr(suite, "robot_state", lambda: next(states))
    try:
        suite.assert_robot_health(require_armed=True)
    finally:
        suite.close()


def test_health_check_requires_three_fresh_missing_servo_scans(
        tmp_path, monkeypatch):
    suite = survey.Suite(_args(), tmp_path, _Recorder())
    states = iter([
        {
            "armed": True,
            "demo": {"running": False},
            "servo": {"live": 17, "missing": [1], "ts": float(index),
                      "tripped": [], "max_temp_c": 30.0},
        }
        for index in range(3)
    ])
    monkeypatch.setattr(suite, "robot_state", lambda: next(states))
    try:
        with pytest.raises(RuntimeError, match="three fresh scans"):
            suite.assert_robot_health(require_armed=True)
    finally:
        suite.close()


def test_nonhard_stationary_failure_preserves_armed_pose(
        tmp_path, monkeypatch):
    suite = survey.Suite(_args(), tmp_path, _Recorder())
    monkeypatch.setattr(suite, "robot_state", lambda: {
        "armed": True, "mode": "idle", "activity": "armed",
        "demo": {"running": False},
    })
    monkeypatch.setattr(
        suite, "emergency_stop",
        lambda _reason: pytest.fail("stationary pause must not limp"),
    )
    try:
        suite.pause_without_posture_change("camera unavailable")
    finally:
        suite.close()


def test_nonhard_walking_failure_uses_phase_aware_stop(
        tmp_path, monkeypatch):
    suite = survey.Suite(_args(), tmp_path, _Recorder())
    monkeypatch.setattr(suite, "robot_state", lambda: {
        "armed": True, "mode": "walk", "activity": "walking",
        "demo": {"running": False},
    })
    stopped = []
    monkeypatch.setattr(suite, "stop_walk", lambda label: stopped.append(label))
    monkeypatch.setattr(
        suite, "emergency_stop",
        lambda _reason: pytest.fail("successful gait stop must not limp"),
    )
    try:
        suite.pause_without_posture_change("camera unavailable")
        assert stopped == ["failure pause"]
    finally:
        suite.close()


def test_tilt_trip_requires_three_valid_samples(tmp_path, monkeypatch):
    monkeypatch.setattr(
        survey, "_request", lambda *_args, **_kwargs: _feedback(roll=30.0)
    )
    suite = survey.Suite(_args(), tmp_path, _Recorder())
    try:
        suite.sample_feedback(allow_soft_pause=False)
        suite.sample_feedback(allow_soft_pause=False)
        with pytest.raises(
            survey.HardSafetyTrip, match="3 valid samples"
        ):
            suite.sample_feedback(allow_soft_pause=False)
    finally:
        suite.close()


def test_impossible_180_tilt_jump_with_quiet_gyro_is_ignored(
        tmp_path, monkeypatch):
    samples = iter([
        _feedback(roll=0.6, pitch=1.6),
        _feedback(roll=-179.87, pitch=20.11, gyro=(-2.24, -0.73, -1.07)),
        _feedback(roll=-179.87, pitch=20.11, gyro=(-2.24, -0.73, -1.07)),
        _feedback(roll=-179.87, pitch=20.11, gyro=(-2.24, -0.73, -1.07)),
        _feedback(roll=-2.9, pitch=-3.5),
    ])
    monkeypatch.setattr(
        survey, "_request", lambda *_args, **_kwargs: next(samples)
    )
    suite = survey.Suite(_args(), tmp_path, _Recorder())
    try:
        for _ in range(5):
            suite.sample_feedback()
        assert suite.high_tilt_count == 0
    finally:
        suite.close()


def test_thermal_cooldown_records_until_three_clear_samples(
        tmp_path, monkeypatch):
    suite = survey.Suite(_args(), tmp_path, _Recorder())
    samples = iter([
        {"live": 18, "max_temp_c": 60.0},
        {"live": 18, "max_temp_c": 49.0},
        {"live": 18, "max_temp_c": 48.0},
        {"live": 18, "max_temp_c": 47.0},
    ])
    monkeypatch.setattr(suite, "sample_feedback", lambda **_kwargs: next(samples))
    events = []
    monkeypatch.setattr(
        suite, "log_event", lambda event, detail="": events.append((event, detail))
    )
    try:
        assert suite.monitor_thermal_cooldown("test heat")
        assert events[-1][0] == "thermal_cooldown_complete"
        assert events[-1][1]["clear_samples"] == 3
    finally:
        suite.close()


def test_comparison_uses_longest_contiguous_attempt_after_recovery():
    rows = [
        {"phase": "gait_11_forward", "elapsed_s": str(value)}
        for value in (1.0, 1.2, 1.4, 10.0, 10.2, 10.4, 10.6)
    ]
    grouped = _motion_groups(rows)
    assert [row["elapsed_s"] for row in grouped["gait_11_forward"]] == [
        "10.0", "10.2", "10.4", "10.6"
    ]


def test_comparison_rejects_quiet_impossible_euler_jump():
    rows = [
        {
            "elapsed_s": "0.0", "roll_deg": "1.0", "pitch_deg": "2.0",
            "body_roll_deg": "", "body_pitch_deg": "",
            "gyro_xyz_dps": "[0,0,0]",
        },
        {
            "elapsed_s": "0.1", "roll_deg": "-179.0", "pitch_deg": "20.0",
            "body_roll_deg": "", "body_pitch_deg": "",
            "gyro_xyz_dps": "[1,1,1]",
        },
        {
            "elapsed_s": "0.2", "roll_deg": "3.0", "pitch_deg": "4.0",
            "body_roll_deg": "", "body_pitch_deg": "",
            "gyro_xyz_dps": "[1,1,1]",
        },
    ]
    roll, pitch, rejected = _trusted_hardware_tilt(rows)
    assert rejected == 1
    assert roll.tolist() == [1.0, 3.0]
    assert pitch.tolist() == [2.0, 4.0]


def test_camera_center_anchor_uses_operator_approved_start(tmp_path, monkeypatch):
    suite = survey.Suite(_args(), tmp_path, _Recorder())
    observation = {
        "chassis_px": [1317.9, 868.9],
        "image_size_px": [1920, 1440],
        "floor_tag_ids": [12, 13, 15],
        "floor_fit_rms_mm": 0.7,
    }
    monkeypatch.setattr(
        suite, "camera_center_observation", lambda: observation
    )
    try:
        suite.capture_camera_center_anchor()
        assert suite.center_target_px.tolist() == [1317.9, 868.9]
    finally:
        suite.close()


def test_camera_center_anchor_preserves_explicit_floor_target(
        tmp_path, monkeypatch):
    args = _args()
    args.center_target_floor_m = [0.285, 0.697]
    suite = survey.Suite(args, tmp_path, _Recorder())
    observation = {
        "target_px": [421.5, 166.6],
        "target_floor_m": [0.285, 0.697],
        "image_size_px": [1280, 720],
        "floor_tag_ids": [100, 101, 103],
        "floor_fit_rms_mm": 1.2,
    }
    monkeypatch.setattr(
        suite, "camera_center_observation", lambda: observation
    )
    try:
        suite.capture_camera_center_anchor()
        assert suite.center_target_px is None
        assert suite.center_target_floor.tolist() == [0.285, 0.697]
    finally:
        suite.close()


def test_floor_homography_rejects_duplicate_id_at_wrong_location():
    size = 0.04
    specs = {
        "12": {"world_from_tag": {
            "translation_m": [0.0, 0.0, 0.0],
            "euler_xyz_deg": [0.0, 0.0, 0.0],
        }},
        "13": {"world_from_tag": {
            "translation_m": [0.6, 0.7, 0.0],
            "euler_xyz_deg": [0.0, 0.0, 3.0],
        }},
        "15": {"world_from_tag": {
            "translation_m": [0.6, 0.0, 0.0],
            "euler_xyz_deg": [0.0, 0.0, 180.0],
        }},
    }
    half = size / 2.0
    local = np.asarray([
        [-half, half], [half, half], [half, -half], [-half, -half]
    ], dtype=np.float32)
    floor_corners = {}
    for marker_id, entry in specs.items():
        tx, ty, _ = entry["world_from_tag"]["translation_m"]
        yaw = np.deg2rad(entry["world_from_tag"]["euler_xyz_deg"][2])
        rot = np.asarray([
            [np.cos(yaw), -np.sin(yaw)],
            [np.sin(yaw), np.cos(yaw)],
        ])
        floor_corners[int(marker_id)] = local @ rot.T + [tx, ty]
    floor_to_image = np.asarray([
        [900.0, 120.0, 300.0],
        [50.0, 820.0, 240.0],
        [0.2, 0.1, 1.0],
    ])
    correct = {
        marker_id: cv2.perspectiveTransform(
            corners.astype(np.float32).reshape(1, -1, 2), floor_to_image
        )[0]
        for marker_id, corners in floor_corners.items()
    }
    decoy_13 = correct[13] + np.asarray([700.0, -120.0])
    fit = survey._select_floor_homography(
        {12: [correct[12]], 13: [decoy_13, correct[13]], 15: [correct[15]]},
        specs,
        size,
    )
    assert fit is not None
    selected, _ids, _transform, _image, _floor, rms_mm = fit
    assert np.allclose(selected[13], correct[13])
    assert rms_mm < 0.01


def test_floor_motion_uses_gait9_axis_when_gait0_is_absent():
    phases = {
        "gait_9_forward": {
            "floor_projected_body_delta_xy_m": [0.01, 0.10],
        },
        "gait_9_backward": {
            "floor_projected_body_delta_xy_m": [-0.01, -0.08],
        },
        "gait_14_forward": {
            "floor_projected_body_delta_xy_m": [0.0, 0.11],
        },
    }
    axis, gait = _reference_axis(phases)
    assert gait == 9
    assert axis is not None
    assert axis[1] > 0.99


def test_floor_projected_body_yaw_applies_mount_offset():
    corners = np.asarray([
        [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0],
    ], dtype=np.float32)
    yaw = _body_yaw_deg(corners, np.eye(3), 0.0)
    assert yaw == pytest.approx(0.0)


def test_current_floor_tag_map_loads_in_metres():
    specs, size = survey._load_floor_tag_map(
        survey.LINUX_CONTROL / "floor_tag_map_20260903.json"
    )
    assert sorted(map(int, specs)) == [100, 101, 102, 103, 104, 105, 112]
    assert size == pytest.approx(0.0272)
    assert specs["103"]["world_from_tag"]["translation_m"] == pytest.approx(
        [0.6096, 0.0, 0.0]
    )
