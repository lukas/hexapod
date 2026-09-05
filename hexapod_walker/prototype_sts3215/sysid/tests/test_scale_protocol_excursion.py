import copy

import pytest

from sysid.scale_protocol_excursion import scale_protocol


def _protocol():
    return {
        "sysid_protocol": 1,
        "name": "source",
        "hz": 10,
        "soft_torque": 700,
        "max_current_a": 0.75,
        "current_trip_polls": 3,
        "hard_current_a": 3.0,
        "home_deg": [0.0] * 18,
        "segments": [{
            "kind": "traj",
            "t_s": [0.0, 0.1],
            "q_deg": [[0.0] * 18, [0.0] * 16 + [-20.0, 12.0]],
        }],
    }


def test_scales_only_excursion_and_embeds_provenance():
    source = _protocol()
    before = copy.deepcopy(source)
    result = scale_protocol(
        source, scale=0.5, name="half", description="half excursion"
    )

    assert source == before
    assert result["segments"][0]["t_s"] == [0.0, 0.1]
    assert result["segments"][0]["q_deg"][1][-2:] == [-10.0, 6.0]
    assert result["soft_torque"] == 700
    assert result["max_current_a"] == 0.75
    assert result["current_trip_polls"] == 3
    assert result["hard_current_a"] == 3.0
    assert result["trajectory_transform"] == {
        "method": "scale_joint_deviation_from_home",
        "scale": 0.5,
        "source_protocol_hash": "56a86b3c0650",
    }


@pytest.mark.parametrize("scale", [0.0, -0.5, 1.01])
def test_rejects_non_bounded_scale(scale):
    with pytest.raises(ValueError, match="scale must be"):
        scale_protocol(
            _protocol(), scale=scale, name="bad", description="invalid"
        )
