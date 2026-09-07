"""Pure offline tests for deterministic sysid protocol materialization."""

from __future__ import annotations

import pytest
from sysid_protocol import N_JOINTS, materialize, validate


def _relative_pair(rows: list[tuple[float, float]]) -> dict:
    q_deg = []
    for l2, l5 in rows:
        row = [0.0] * N_JOINTS
        row[7] = l2
        row[16] = l5
        q_deg.append(row)
    return {
        "sysid_protocol": 1,
        "name": "relative_pair_test_v1",
        "hz": 10,
        "segments": [{
            "kind": "rel_traj",
            "t_s": [index / 10 for index in range(len(rows))],
            "active": [7, 16],
            "q_deg": q_deg,
        }],
    }


def test_relative_pair_materializes_as_simultaneous_relative_commands():
    protocol = _relative_pair([(0.0, 0.0), (0.5, 0.5), (-0.5, -0.5)])

    materialized = materialize(protocol)

    assert validate(protocol) == []
    assert [tick["active"] for tick in materialized["ticks"]] == [[7, 16]] * 3
    assert [tick["mode"] for tick in materialized["ticks"]] == ["rel"] * 3
    assert [tick["cmd"][7] for tick in materialized["ticks"]] == [0.0, 0.5, -0.5]
    assert [tick["cmd"][16] for tick in materialized["ticks"]] == [0.0, 0.5, -0.5]


@pytest.mark.parametrize(
    "mutation, expected",
    [
        (lambda segment: segment.update(active=[7, 7]), "unique joints"),
        (lambda segment: segment.update(active=[[7]]), "unique joints"),
        (lambda segment: segment["q_deg"][0].__setitem__(8, 0.1),
         "nonzero inactive"),
        (lambda segment: segment["q_deg"][0].__setitem__(7, 41.0),
         "offset exceeds"),
    ],
)
def test_relative_pair_rejects_ambiguous_or_excessive_commands(mutation, expected):
    protocol = _relative_pair([(0.0, 0.0)])
    mutation(protocol["segments"][0])

    assert any(expected in error for error in validate(protocol))
