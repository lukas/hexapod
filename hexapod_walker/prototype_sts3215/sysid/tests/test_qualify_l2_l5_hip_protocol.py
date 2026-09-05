from sysid import PROTO_DIR
from sysid.qualify_l2_l5_hip_protocol import NAME, offsets, qualify


def test_exact_protocol_is_runner_compatible_and_qualified():
    protocol, report = qualify(PROTO_DIR)

    assert protocol["name"] == NAME
    assert report["qualified"] is True
    assert report["runner_compatibility"]["passed"] is True
    assert report["timing_validation"] == {
        "passed": True,
        "sample_rate_hz": 10.0,
        "sample_count": 900,
        "duration_seconds": 90.0,
        "pre_baseline_seconds": 5,
        "post_baseline_seconds": 5,
        "cycles": 4,
    }
    assert report["joint_limit_validation"]["active_joints"] == {
        "L2_hip": 7,
        "L5_hip": 16,
    }
    assert report["joint_limit_validation"]["maximum_slew_deg_per_s"] <= 0.5
    assert report["robot_contacted"] is False
    assert report["robot_motion"] is False
    assert report["inspection_clearance_granted"] is False


def test_cycle_timing_and_amplitudes_are_exact():
    values = offsets()

    assert len(values) == 900
    assert values[:50] == [0.0] * 50
    assert values[-50:] == [0.0] * 50
    for start in (50, 250, 450, 650):
        cycle = values[start:start + 200]
        assert cycle[39] == 2.0
        assert cycle[40:60] == [2.0] * 20
        assert cycle[139] == -2.0
        assert cycle[140:160] == [-2.0] * 20
        assert cycle[199] == 0.0
