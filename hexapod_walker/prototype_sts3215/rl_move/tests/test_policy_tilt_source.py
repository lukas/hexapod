"""Regression guard: the RL policy obs/reward path derives attitude from the
raw accel/gyro channels + the RobotState attribute, NOT from a pre-baked
``roll_deg``/``pitch_deg`` dict key.

If a future change makes the policy read a reported ``roll_deg`` field, it would
silently consume mount-uncorrected (uncalibrated) tilt.  These asserts keep the
attitude source raw so the uncal_*/body_* rename cannot regress it.
"""
from pathlib import Path

_HERE = Path(__file__).resolve()
_RL_MOVE = _HERE.parents[1]


def _src(rel: str) -> str:
    return (_RL_MOVE / rel).read_text()


def test_robot_state_computes_attitude_from_raw_channels_only():
    src = _src("robot_state.py")
    # It builds attitude from ax_g/ay_g/az_g via ComplementaryAttitude; it must
    # never read a reported roll_deg/pitch_deg key.
    assert "roll_deg" not in src
    assert "pitch_deg" not in src
    assert "ax_g" in src and "ComplementaryAttitude" in src


def test_env_never_reads_a_tilt_dict_key():
    src = _src("env.py")
    # env may WRITE info["roll_deg"] for logging, but must not READ tilt from a
    # feedback/imu dict (it uses the RobotState attribute state.imu_roll).
    assert 'get("roll_deg")' not in src and 'get("pitch_deg")' not in src
    assert 'imu["roll_deg"]' not in src and 'imu["pitch_deg"]' not in src
    assert "imu_roll" in src
