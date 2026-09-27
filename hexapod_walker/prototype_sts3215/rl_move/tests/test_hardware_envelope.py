"""hexapod_core.hardware_envelope: the measured leg stops, clipped in the HINGE frame by the
shared SafetyLayer (sim + robot), stamped by the exporter.  2026-09-27: the teacher-free walker
learned hinge 147-149 inside the MJCF's 150 and stalled the real knee at 135.6 deg.

Run: uv run python -m pytest rl_move/tests/test_hardware_envelope.py -q
"""
from __future__ import annotations

import json
import math

import numpy as np
import pytest

from hexapod_core import hardware_envelope as he
from rl_move.robot_state import RobotState
from rl_move.safety import N_JOINTS, SafetyLayer

DEG = math.pi / 180.0


def _state(q):
    return RobotState(timestamp=0.0, joint_position=q.copy(), joint_velocity=np.zeros(N_JOINTS),
                      imu_roll=0.0, imu_pitch=0.0, imu_yaw=0.0, imu_gyro=np.zeros(3),
                      imu_accel=np.zeros(3), commanded_position=q.copy())


def _cfg(**safety):
    s = {"max_delta_q_deg": 400.0, "max_roll_deg": 25, "max_pitch_deg": 25}
    s.update(safety)
    return {"safety": s, "control": {"hz": 50}}


def _pose(hip, knee_abs, yaw=0.0):
    return np.array([yaw, hip, knee_abs] * 6, dtype=float)


def test_clip_robot_abs_is_a_hinge_clip():
    # hip -50, knee_abs 97 -> hinge 147 (the real trip) -> hinge 125 -> knee_abs 75
    out = he.clip_robot_abs(_pose(-50.0, 97.0), -52.0, 125.0)
    assert out[1] == -50.0 and out[2] == pytest.approx(75.0)
    # hip below the stop moves up; the absolute tibia angle is kept (component-wise, like the
    # legacy clip) and the hinge is re-checked against the clipped hip: 40 - (-52) = 92 <= 125
    out = he.clip_robot_abs(_pose(-70.0, 40.0), -52.0, 125.0)
    assert out[1] == -52.0 and out[2] == pytest.approx(40.0)
    # ... unless that hinge now exceeds the stop: hip -70 / knee_abs 80 -> hip -52, hinge 132 -> 125
    out = he.clip_robot_abs(_pose(-70.0, 80.0), -52.0, 125.0)
    assert out[1] == -52.0 and out[2] == pytest.approx(73.0)
    # in-range poses are untouched (the anchored walkers never leave hinge 64..104)
    q = _pose(20.0, 103.0)
    assert np.array_equal(he.clip_robot_abs(q, -52.0, 125.0), q)
    # radians round-trip
    out = he.clip_robot_abs(_pose(-50.0, 97.0) * DEG, -52.0, 125.0, radians=True)
    assert out[2] == pytest.approx(75.0 * DEG)


def test_stops_and_tightest():
    assert he.stops_for("hexapod2.local") == (-52.0, 125.0)
    assert he.stops_for("hexapod") == (he.SERVO_HIP_MIN_DEG, he.SERVO_KNEE_HINGE_MAX_DEG)
    assert he.tightest((-52.0, 125.0), (-60.0, 140.0), None) == (-52.0, 125.0)
    assert he.tightest((-40.0, 130.0), (-52.0, 125.0)) == (-40.0, 125.0)


def test_safety_layer_clips_the_hinge_when_configured():
    gate = SafetyLayer(_cfg(hip_min_deg=-52.0, knee_hinge_max_deg=125.0))
    q0 = _pose(20.0, 103.0) * DEG
    gate.set_nominal(q0) if hasattr(gate, "set_nominal") else None
    gate._last_safe = q0.copy()
    q, st = gate.filter(_pose(-50.0, 97.0) * DEG, _state(q0))
    assert st.ok
    assert q[1] == pytest.approx(-50.0 * DEG) and q[2] == pytest.approx(75.0 * DEG)
    assert (q[2::3] - q[1::3]).max() <= 125.0 * DEG + 1e-9


def test_safety_layer_without_the_keys_is_the_legacy_clip():
    gate = SafetyLayer(_cfg())
    assert gate.envelope_deg is None
    q0 = _pose(20.0, 103.0) * DEG
    gate._last_safe = q0.copy()
    q, _ = gate.filter(_pose(-50.0, 97.0) * DEG, _state(q0))
    assert q[1] == pytest.approx(-50.0 * DEG) and q[2] == pytest.approx(97.0 * DEG)   # untouched, as before


def test_set_envelope_only_tightens():
    gate = SafetyLayer(_cfg(hip_min_deg=-52.0, knee_hinge_max_deg=125.0))
    assert gate.set_envelope(-80.0, 150.0) == (-52.0, 125.0)       # a looser robot cannot loosen it
    assert gate.set_envelope(None, 120.0) == (-52.0, 120.0)
    assert gate.set_envelope(-45.0, None) == (-45.0, 120.0)
    legacy = SafetyLayer(_cfg())
    assert legacy.set_envelope(None, None) is None
    assert legacy.set_envelope(-52.0, 125.0) == (-52.0, 125.0)


def test_trained_safety_contract_from_command_and_sidecar(tmp_path):
    from rl_move.sim.trained_profile import trained_safety_contract
    ck = tmp_path / "ppo_goal_x.zip"; ck.write_bytes(b"0")
    cmd = "uv run python -m rl_move.sim.train_ppo_mjx --cfg-set safety.max_delta_q_deg=7.2 --cfg-set safety.max_current_a=100"
    assert trained_safety_contract(str(ck), cmd) == {"max_delta_q_deg": 7.2}
    resolved = str({"safety.max_delta_q_deg": 0.75, "safety.hip_min_deg": -52.0, "safety.knee_hinge_max_deg": 125.0})
    (tmp_path / "ppo_goal_x.training_complete.json").write_text(json.dumps({"resolved_config": resolved}))
    got = trained_safety_contract(str(ck), cmd)
    assert got == {"max_delta_q_deg": 0.75, "hip_min_deg": -52.0, "knee_hinge_max_deg": 125.0}   # sidecar wins
    best = tmp_path / "ppo_goal_x_best.zip"; best.write_bytes(b"0")
    assert trained_safety_contract(str(best), None)["knee_hinge_max_deg"] == 125.0
