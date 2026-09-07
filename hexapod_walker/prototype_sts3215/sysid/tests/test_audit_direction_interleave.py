import json
from pathlib import Path

import pytest

from linux_control.sysid_protocol import protocol_hash
from sysid.audit_direction_interleave import audit_direction_interleave

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "sysid/protocols/l5_air_radial_shear_hysteresis_repeat6_v1.json"


def test_repeat6_stream_is_not_six_independent_equal_row_cycles():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    report = audit_direction_interleave(
        source,
        direction_order=[
            "normal",
            "reversed",
            "reversed",
            "normal",
            "normal",
            "reversed",
            "reversed",
            "normal",
        ],
        expected_rows=2080,
        max_allowed_adjacent_step_deg=1.6,
        expected_source_hash=protocol_hash(source),
    )

    assert report["admitted"] is False
    assert report["source_rows"] == 1560
    assert report["dwell_equivalence_report"] == {
        "detected_cycle_count": 6,
        "samples_per_side": [30],
        "preservable_by_unambiguous_composition": False,
    }
    assert report["cycle_boundary_overlaps"]
    assert report["materialized_trajectory_hash"] is None
    assert report["deterministic_replay_report"]["robot_contacted"] is False
    assert report["deterministic_replay_report"]["robot_motion"] is False


def test_source_hash_is_an_admission_guard():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="source protocol hash"):
        audit_direction_interleave(
            source,
            direction_order=["normal"],
            expected_rows=1560,
            max_allowed_adjacent_step_deg=1.0,
            expected_source_hash="000000000000",
        )


def test_explicit_non_overlapping_cycles_can_be_materialized():
    rows = []
    for value in (0.0, 1.0, 2.0, 0.0, 0.0, 1.0, 2.0, 0.0):
        row = [0.0] * 18
        row[16] = value
        rows.append(row)
    source = {
        "sysid_protocol": 1,
        "name": "explicit_cycles",
        "hz": 10,
        "semantic_cycles": [[0, 4], [4, 8]],
        "segments": [
            {
                "kind": "traj",
                "t_s": [index / 10 for index in range(8)],
                "q_deg": rows,
            }
        ],
    }

    report = audit_direction_interleave(
        source,
        direction_order=["normal", "reversed"],
        expected_rows=8,
        max_allowed_adjacent_step_deg=2.0,
    )

    assert report["admitted"] is True
    assert report["materialized_trajectory_hash"]
    assert report["adjacent_step_report"]["explicit_candidate_max_deg"] == 2.0
