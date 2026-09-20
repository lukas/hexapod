"""sensor_to_body_tilt_deg: the single shared IMU mount-frame rotation."""
import math

from imu_calibrate import apply_imu_calib, sensor_to_body_tilt_deg


def test_returns_none_without_a_valid_body_frame():
    assert sensor_to_body_tilt_deg(1.0, 2.0, None) is None
    # axis norm < 0.5 is rejected by _valid_body_frame
    assert sensor_to_body_tilt_deg(
        1.0, 2.0, {"pitch_axis_roll": 0.1, "pitch_axis_pitch": 0.1}) is None


def test_pure_pitch_axis_maps_pitch_through_and_negates_roll():
    bf = {"pitch_axis_roll": 0.0, "pitch_axis_pitch": 1.0, "pitch_sign": 1.0}
    body_roll, body_pitch = sensor_to_body_tilt_deg(5.0, 10.0, bf)
    assert math.isclose(body_pitch, 10.0)
    assert math.isclose(body_roll, -5.0)


def test_rotated_axis_mixes_axes():
    # A 45deg-rotated mount: a pure sensor-pitch shows up equally in both axes.
    s = math.sqrt(0.5)
    bf = {"pitch_axis_roll": s, "pitch_axis_pitch": s, "pitch_sign": 1.0}
    body_roll, body_pitch = sensor_to_body_tilt_deg(0.0, 10.0, bf)
    assert math.isclose(body_pitch, 10.0 * s, rel_tol=1e-9)
    assert math.isclose(body_roll, 10.0 * s, rel_tol=1e-9)


def test_apply_imu_calib_matches_the_factored_rotation():
    # apply_imu_calib must produce exactly what the shared function returns.
    bf = {"pitch_axis_roll": 0.2, "pitch_axis_pitch": 0.98, "pitch_sign": 1.0}
    calib = {
        "gyro_bias_dps": {"x": 0.0, "y": 0.0, "z": 0.0},
        "accel_bias_g": {"x": 0.0, "y": 0.0, "z": 0.0},
        "body_frame": bf,
    }
    sample = {"gx_dps": 0.0, "gy_dps": 0.0, "gz_dps": 0.0,
              "ax_g": 0.1, "ay_g": 0.05, "az_g": 0.99}
    out = apply_imu_calib(sample, calib)
    assert out["body_frame_calibrated"] is True
    expect = sensor_to_body_tilt_deg(out["roll_deg"], out["pitch_deg"], bf)
    assert math.isclose(out["body_roll_deg"], expect[0])
    assert math.isclose(out["body_pitch_deg"], expect[1])
