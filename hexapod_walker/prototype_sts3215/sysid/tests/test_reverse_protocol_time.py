from copy import deepcopy

import pytest

from linux_control.sysid_protocol import protocol_hash
from sysid.reverse_protocol_time import reverse_protocol_time


def _protocol() -> dict:
    return {
        "sysid_protocol": 1,
        "name": "source",
        "description": "source trajectory",
        "hz": 10,
        "home_deg": [0.0] * 18,
        "soft_torque": 700,
        "max_current_a": 0.75,
        "hard_current_a": 3.0,
        "current_trip_polls": 3,
        "segments": [{
            "kind": "traj",
            "label": "cycle",
            "t_s": [0.0, 0.1, 0.2, 0.3],
            "q_deg": [[float(i)] * 18 for i in range(4)],
        }],
    }


def test_reversal_changes_only_command_order_and_metadata():
    source = _protocol()
    original = deepcopy(source)
    result = reverse_protocol_time(source, name="reversed", description="reverse")

    assert source == original
    assert result["segments"][0]["q_deg"] == list(
        reversed(source["segments"][0]["q_deg"])
    )
    assert result["segments"][0]["t_s"] == source["segments"][0]["t_s"]
    for key in (
        "hz", "home_deg", "soft_torque", "max_current_a",
        "hard_current_a", "current_trip_polls",
    ):
        assert result[key] == source[key]
    assert result["trajectory_transform"] == {
        "method": "reverse_outbound_inbound_temporal_order",
        "preserve_command_values": True,
        "preserve_dwells": True,
        "source_protocol_hash": protocol_hash(source),
    }


def test_reversal_rejects_non_trajectory_protocol():
    source = _protocol()
    source["segments"] = [{
        "kind": "step", "label": "step", "joint": 16,
        "amp_deg": 1.0, "hold_s": 1.0, "repeats": 1,
    }]
    with pytest.raises(ValueError, match="trajectory-only"):
        reverse_protocol_time(source, name="reversed", description="reverse")
