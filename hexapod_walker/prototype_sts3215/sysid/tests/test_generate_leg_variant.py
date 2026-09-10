"""Remapping one leg's columns to another is a function, not a work session.

Until 2026-09-10 this tool required its source protocol to be named ``l5_``
and read the source columns from leg 5's slice, because it was written for
the L5 ladder. The belly-rest hysteresis family's reviewed source is ``l2_``,
so the tool refused it and six per-leg protocols were hand-authored instead,
at roughly 45 minutes and $50 of agent work each.
"""
import copy
import json
from pathlib import Path

import pytest

from sysid.generate_leg_variant import remap_protocol_to_leg, source_leg_of

PROTOCOLS = Path(__file__).resolve().parents[1] / "protocols"
BELLY_REST = PROTOCOLS / "l2_belly_rest_radial_shear_hysteresis_repeat6_v1.json"


def _belly_rest():
    return json.loads(BELLY_REST.read_text())


@pytest.mark.parametrize("name,expected", [
    ("l0_air_radial_shear_hysteresis_control_v1", 0),
    ("l2_belly_rest_radial_shear_hysteresis_repeat6_v1", 2),
    ("l5_ground_radial_shear_hysteresis_v1", 5),
])
def test_source_leg_comes_from_the_protocol_name(name, expected):
    assert source_leg_of(name) == expected


@pytest.mark.parametrize("name", ["belly_rest_v1", "l6_thing_v1", "L2_thing"])
def test_an_unparseable_source_name_is_refused(name):
    with pytest.raises(ValueError, match="l<0-5>_"):
        source_leg_of(name)


@pytest.mark.parametrize("leg,joints", [(0, [1, 2]), (3, [10, 11]), (4, [13, 14])])
def test_an_l2_source_remaps_to_any_other_leg(leg, joints):
    """These are the three legs that were hand-authored one at a time."""
    protocol = remap_protocol_to_leg(
        _belly_rest(), leg, strict_independent=True)
    rows = protocol["segments"][0]["q_deg"]
    moving = sorted({
        joint for row in rows
        for joint, value in enumerate(row) if value != 0.0
    })
    assert moving == joints
    assert protocol["name"] == (
        f"l{leg}_belly_rest_radial_shear_hysteresis_repeat6_v1")
    assert f"L{leg}" in protocol["description"]
    assert rows[0] == rows[-1] == [0.0] * 18


def test_the_remap_changes_nothing_but_the_leg():
    """A silent trip-threshold or rate edit would be a safety change."""
    before = _belly_rest()
    after = remap_protocol_to_leg(copy.deepcopy(before), 4)
    for key in ("sysid_protocol", "hz", "soft_torque", "max_current_a",
                "current_trip_polls", "hard_current_a", "home_deg"):
        assert after[key] == before[key], key
    assert after["segments"][0]["t_s"] == before["segments"][0]["t_s"]
    assert len(after["segments"]) == 1


def test_remapping_a_protocol_onto_its_own_leg_is_refused():
    with pytest.raises(ValueError, match="already leg 2"):
        remap_protocol_to_leg(_belly_rest(), 2)


def test_conflicting_adjacent_and_independent_modes_are_refused():
    with pytest.raises(ValueError, match="conflicts"):
        remap_protocol_to_leg(
            _belly_rest(), 4, clear_adjacent=True, strict_independent=True)
