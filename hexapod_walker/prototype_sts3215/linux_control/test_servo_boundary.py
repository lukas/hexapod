"""The servo boundary: robot_abs poses <-> the knee servo's femur-relative hinge.

History this test exists to end (see HARDWARE_JOINT_FRAME.md / CURRENT_TRUTHS
2026-09-27): the contract says femur and tibia are absolute angles, the knee
servo measures the hinge, and the conversion was built on 2026-09-14
(hexapod 4fcc7969) but never reached main -- for six weeks every command ran
20 deg (= the hip) more knee-flexed on the robot than in the simulator. The
ceiling camera measured it (foot radius 164 mm at telemetry hip 19 / knee 78;
the contract predicts 230). These tests pin the boundary in the bus driver:
every full-pose WRITE converts, every position READ converts back, a knee
without its hip is unknown, and the sim uses the same arithmetic.
"""
from __future__ import annotations

import math
import struct

import pytest

from feetech_bus import (
    N_JOINTS, JOINT_SIGN, count_to_deg, deg_to_count, joint_to_servo_id,
    raw_degree_to_count, raw_feedback_to_robot_feedback,
    raw_positions_to_robot_degrees, robot_pose_to_raw_degrees,
)
from hexapod_core.joint_frame import (
    FRAME_ROBOT_ABS, robot_abs_rad_to_mujoco_rel_rad, robot_abs_to_servo_relative,
    servo_relative_to_robot_abs, walk_start_pose_degrees,
)
from mcu_feetech_bus import encode_sync_frame
from test_mcu_stream import _fw_snapshot_frame, _fw_snapshot_payload, _mk_bus

STAND = [0.0, 20.0, 100.0] * 6          # robot_abs: tibia 100 = the servo's "knee 80"


def _pose(hip=20.0, tibia=100.0, yaw=3.0):
    return [yaw, hip, tibia] * 6


def test_roundtrip_with_trims_and_negative_hip():
    trims = [0.5 * j for j in range(N_JOINTS)]
    q = [1.0, -30.0, 40.0] * 6            # negative hip: raw knee = 40 - (-30) = 70
    raw = robot_pose_to_raw_degrees(q, trims)
    for leg in range(6):
        assert raw[3 * leg + 1] == pytest.approx(-30.0 + trims[3 * leg + 1])
        assert raw[3 * leg + 2] == pytest.approx(70.0 + trims[3 * leg + 2])
    back = raw_positions_to_robot_degrees(dict(enumerate(raw)), trims)
    assert [back[j] for j in range(N_JOINTS)] == pytest.approx(q)


def test_bus_and_simulator_share_one_conversion():
    """The MuJoCo boundary and the servo boundary are the same arithmetic."""
    for hip in (-40.0, -10.0, 0.0, 16.0, 20.0, 35.0):
        q = _pose(hip=hip, tibia=100.0)
        sim = [math.degrees(v) for v in robot_abs_rad_to_mujoco_rel_rad(
            [math.radians(v) for v in q])]
        bus = robot_pose_to_raw_degrees(q, None, validate=False)
        assert bus == pytest.approx(sim)
        assert bus == pytest.approx(robot_abs_to_servo_relative(q))
    assert servo_relative_to_robot_abs([0.0, 20.0, 80.0] * 6) == pytest.approx(STAND)


def test_walk_start_is_the_servo_knee_80_stance():
    assert walk_start_pose_degrees() == pytest.approx(STAND)
    raw = robot_pose_to_raw_degrees(walk_start_pose_degrees())
    assert raw[1::3] == pytest.approx([20.0] * 6) and raw[2::3] == pytest.approx([80.0] * 6)


@pytest.mark.parametrize("q", [
    [0.0, 20.0, 160.0] * 6,      # raw knee 140 is fine, tibia 160 - 20 ... within? see limits below
    [0.0, -80.0, 100.0] * 6,     # raw knee 180: outside the axis limit
    [float("nan")] * N_JOINTS,
    [0.0] * 17,
])
def test_unreachable_or_malformed_pose_is_refused_before_any_write(q):
    from feetech_bus import joint_limits
    lo, hi = joint_limits(2)
    if len(q) == N_JOINTS and all(math.isfinite(v) for v in q) and lo <= q[2] - q[1] <= hi:
        pytest.skip("pose is reachable under the current knee limits")
    bus = _mk_bus(b"")
    with pytest.raises(ValueError):
        robot_pose_to_raw_degrees(q, bus.trims)
    with pytest.raises(ValueError):
        bus.step_all(q, speed=400, acc=20)
    assert bytes(bus._ser.tx) == b""


def test_step_all_writes_hinge_knees_and_reads_back_robot_abs():
    hip_counts, knee_counts = 2048 + 20 * 11, 2048 + 80 * 11   # ~20 deg hip, ~80 deg raw knee
    servos = [(2 + j, 1, {0: 2048, 1: hip_counts, 2: knee_counts}[j % 3], 0) for j in range(N_JOINTS)]
    reply = _fw_snapshot_frame(_fw_snapshot_payload(7, 1, 1, (0, 0, 16384, 0, 0, 0, 0), servos), 18)
    bus = _mk_bus(reply)
    snap = bus.step_all(STAND, speed=400, acc=20)
    # TX: the servos are told hinge knees (100 - 20 = 80), not 100.
    want = [(joint_to_servo_id(j), deg_to_count(j, [0.0, 20.0, 80.0][j % 3], 0.0), 400, 20)
            for j in range(N_JOINTS)]
    assert bytes(bus._ser.tx) == encode_sync_frame(ord("S"), want)
    # RX: positions come back in robot_abs; raw kept alongside.
    for leg in range(6):
        hip = count_to_deg(3 * leg + 1, hip_counts)
        knee_raw = count_to_deg(3 * leg + 2, knee_counts)
        assert snap["pos_deg"][3 * leg + 1] == pytest.approx(hip)
        assert snap["pos_deg"][3 * leg + 2] == pytest.approx(hip + knee_raw)
        assert snap["raw_pos_deg"][3 * leg + 2] == pytest.approx(knee_raw)
    assert snap["joint_frame"] == FRAME_ROBOT_ABS
    assert bus._pos_cache[2] == pytest.approx(snap["pos_deg"][2])


def test_missing_hip_leaves_its_knee_unknown_but_keeps_raw_health():
    servos = [(2 + j, 0 if j == 1 else 1, 2048 + 300, 0) for j in range(N_JOINTS)]   # L0 hip dead
    reply = _fw_snapshot_frame(_fw_snapshot_payload(1, 1, 1, (0, 0, 16384, 0, 0, 0, 0), servos), 18)
    bus = _mk_bus(reply)
    snap = bus.step_all(STAND, speed=400, acc=20)
    assert 1 not in snap["pos_deg"] and 2 not in snap["pos_deg"]      # hip missing -> knee unknown
    assert 2 in snap["raw_pos_deg"]                                    # servo itself was fine
    assert 5 in snap["pos_deg"]                                        # other legs unaffected
    fb = {j: {"joint": j, "id": j + 2, "deg": 10.0, "speed_deg_s": 1.0} for j in range(N_JOINTS) if j != 4}
    out = raw_feedback_to_robot_feedback(fb, None)
    assert out[5]["deg"] is None and out[5]["raw_deg"] == 10.0        # L1 knee: hip 4 missing
    assert out[2]["deg"] == pytest.approx(20.0)                        # L0 knee = 10 + 10
    assert out[2]["speed_deg_s"] == pytest.approx(2.0)                 # knee speed = raw knee + raw hip


def test_snapshot_speed_is_signed_and_knee_speed_sums_the_hip():
    servos = [(2 + j, 1, 2048, 100 if j % 3 else 0) for j in range(N_JOINTS)]
    reply = _fw_snapshot_frame(_fw_snapshot_payload(1, 1, 1, (0, 0, 16384, 0, 0, 0, 0), servos), 18)
    bus = _mk_bus(reply)
    snap = bus.step_all(STAND, speed=400, acc=20)
    per_count = 360.0 / 4096.0 * 100
    for leg in range(6):
        hip_s = JOINT_SIGN[3 * leg + 1] * per_count
        knee_s = JOINT_SIGN[3 * leg + 2] * per_count
        assert snap["speed_deg_s"][3 * leg + 1] == pytest.approx(hip_s)
        assert snap["speed_deg_s"][3 * leg + 2] == pytest.approx(hip_s + knee_s)


def test_telemetry_command_is_logical_and_raw_is_kept():
    servos = [(2 + j, 1, 2048, 0) for j in range(N_JOINTS)]
    reply = _fw_snapshot_frame(_fw_snapshot_payload(1, 1, 1, (0, 0, 16384, 0, 0, 0, 0), servos), 18)
    bus = _mk_bus(reply)
    records = []
    bus._telemetry_sink = lambda kind, payload: records.append((kind, payload))
    bus._emit_telemetry = lambda kind, payload: records.append((kind, payload))
    bus.step_all(STAND, speed=400, acc=20)
    kinds = [k for k, _ in records]
    assert "step" in kinds
    step = [p for k, p in records if k == "step"][0]
    assert step["command_deg"] == pytest.approx(STAND)
    assert step["raw_command_deg"][2::3] == pytest.approx([80.0] * 6)
    assert step["joint_frame"] == FRAME_ROBOT_ABS


def test_standup_frames_are_converted_after_the_hinge_cap(monkeypatch):
    import api.standup as standup
    # A baked hinge frame folding the knee past the cap: cap in hinge, then convert.
    kf = [{"q_deg": [0.0, -60.0, 148.0] * 6, "s": 1.0}]
    capped_hinge = min(148.0, standup.KNEE_FOLD_CAP_DEG)
    hip = max(-60.0, standup.HIP_FOLD_CAP_DEG)
    frames = [([min(float(v), standup.KNEE_FOLD_CAP_DEG) if (i % 3 == 2) else
                (max(float(v), standup.HIP_FOLD_CAP_DEG) if (i % 3 == 1) else float(v))
                for i, v in enumerate(k["q_deg"])], float(k["s"])) for k in kf]
    frames = [(servo_relative_to_robot_abs(q), s_) for q, s_ in frames]
    q = frames[0][0]
    assert q[2] == pytest.approx(capped_hinge + hip)
    # and the bus writes exactly the capped hinge back to the servo
    assert robot_pose_to_raw_degrees(q, None, validate=False)[2] == pytest.approx(capped_hinge)


def test_plant_pose_file_without_boundary_stamp_is_migrated(tmp_path, monkeypatch):
    import json
    import feetech_bus as fb
    legacy = tmp_path / "plant_pose.json"
    legacy.write_text(json.dumps({
        "joint_frame": "robot_abs", "joint_contract": "robot_abs_tibia_v2",
        "hip_deg": 20.0, "knee_deg": 80.0,                 # written pre-09-27: hinge numbers
        "joints_deg": [0.0, 20.0, 80.0] * 6}))
    monkeypatch.setattr(fb, "PLANT_PATH_CANDIDATES", (legacy,))
    plant = fb.load_plant_pose()
    assert plant["migrated_from_servo_relative"] is True
    assert plant["knee_deg"] == pytest.approx(100.0)
    assert plant["joints_deg"][2::3] == pytest.approx([100.0] * 6)
    stamped = tmp_path / "plant2.json"
    stamped.write_text(json.dumps({
        "joint_frame": "robot_abs", "joint_contract": "robot_abs_tibia_v2",
        "servo_boundary": "robot_abs", "hip_deg": 20.0, "knee_deg": 100.0}))
    monkeypatch.setattr(fb, "PLANT_PATH_CANDIDATES", (stamped,))
    plant = fb.load_plant_pose()
    assert plant["migrated_from_servo_relative"] is False and plant["knee_deg"] == pytest.approx(100.0)
    monkeypatch.setattr(fb, "PLANT_PATH_CANDIDATES", ())
    assert fb.load_plant_pose()["knee_deg"] == pytest.approx(fb.DEFAULT_STAND_KNEE_DEG + fb.DEFAULT_STAND_HIP_DEG)
