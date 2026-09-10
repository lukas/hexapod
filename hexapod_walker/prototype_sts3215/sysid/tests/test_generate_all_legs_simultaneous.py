import json
from pathlib import Path

import pytest

from sysid.generate_all_legs_simultaneous import compose


def _source(tmp_path: Path, leg: int, *, rows=None, **overrides) -> Path:
    if rows is None:
        rows = [
            [0.0] * 18,
            [0.0] * 18,
            [0.0] * 18,
        ]
        rows[1][leg * 3 + 1] = -51.14 + leg
        rows[1][leg * 3 + 2] = 34.56 + leg
    protocol = {
        "sysid_protocol": 1,
        "name": f"l{leg}_belly_rest_radial_shear_hysteresis_repeat6_v1",
        "created": "2026-09-10T07:15:00-07:00",
        "description": f"L{leg} source",
        "hz": 10,
        "write_speed": 180,
        "write_acc": 10,
        "soft_torque": 700,
        "max_current_a": 0.75,
        "current_trip_polls": 3,
        "hard_current_a": 3,
        "home_deg": [0] * 18,
        "segments": [
            {
                "kind": "traj",
                "label": f"L{leg}_seg",
                "t_s": [0.0, 0.1, 0.2],
                "q_deg": rows,
            }
        ],
    }
    protocol.update(overrides)
    path = tmp_path / f"l{leg}.json"
    path.write_text(json.dumps(protocol), encoding="utf-8")
    return path


def _all_six(tmp_path: Path) -> list[Path]:
    return [_source(tmp_path, leg) for leg in range(6)]


def test_union_copies_every_source_column_verbatim(tmp_path: Path) -> None:
    sources = _all_six(tmp_path)
    merged = compose(sources, "all6_x_v1", None)["segments"][0]["q_deg"]

    assert len(merged) == 3
    for leg, path in enumerate(sources):
        source = json.loads(path.read_text())["segments"][0]["q_deg"]
        for column in (leg * 3 + 1, leg * 3 + 2):
            assert [row[column] for row in merged] == [
                row[column] for row in source
            ]
    # Yaw columns stay at zero and the run starts and ends at home.
    assert all(row[leg * 3] == 0.0 for row in merged for leg in range(6))
    assert merged[0] == [0.0] * 18 and merged[-1] == [0.0] * 18


def test_shared_bus_contract_and_timebase_are_preserved(tmp_path: Path) -> None:
    protocol = compose(_all_six(tmp_path), "all6_x_v1", None)
    assert protocol["name"] == "all6_x_v1"
    assert protocol["hz"] == 10
    assert protocol["soft_torque"] == 700
    assert protocol["max_current_a"] == 0.75
    assert protocol["hard_current_a"] == 3
    assert protocol["current_trip_polls"] == 3
    assert protocol["segments"][0]["t_s"] == [0.0, 0.1, 0.2]


def test_overlapping_sources_are_rejected(tmp_path: Path) -> None:
    sources = _all_six(tmp_path)
    # Make the leg-0 source also drive leg 3's knee.
    protocol = json.loads(sources[0].read_text())
    protocol["segments"][0]["q_deg"][1][3 * 3 + 2] = 5.0
    sources[0].write_text(json.dumps(protocol), encoding="utf-8")

    with pytest.raises(SystemExit, match="moves non-0 joints"):
        compose(sources, "all6_x_v1", None)


def test_mismatched_row_count_is_rejected(tmp_path: Path) -> None:
    sources = _all_six(tmp_path)
    protocol = json.loads(sources[2].read_text())
    protocol["segments"][0]["t_s"] = [0.0, 0.1]
    protocol["segments"][0]["q_deg"] = protocol["segments"][0]["q_deg"][:2]
    sources[2].write_text(json.dumps(protocol), encoding="utf-8")

    with pytest.raises(SystemExit, match="different t_s timebase"):
        compose(sources, "all6_x_v1", None)


def test_mismatched_current_limit_is_rejected(tmp_path: Path) -> None:
    sources = _all_six(tmp_path)
    protocol = json.loads(sources[4].read_text())
    protocol["hard_current_a"] = 6
    sources[4].write_text(json.dumps(protocol), encoding="utf-8")

    with pytest.raises(SystemExit, match="disagrees on 'hard_current_a'"):
        compose(sources, "all6_x_v1", None)


def test_duplicate_leg_is_rejected(tmp_path: Path) -> None:
    sources = _all_six(tmp_path)
    dup = tmp_path / "dup"
    dup.mkdir()
    sources[5] = _source(dup, 4)

    with pytest.raises(SystemExit, match="one source per leg"):
        compose(sources, "all6_x_v1", None)
