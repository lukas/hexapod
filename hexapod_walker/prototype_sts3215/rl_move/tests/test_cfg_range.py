"""cfg_set.cfg_range: bracket-lost list values must coerce or raise.

2026-09-25 incident: a --cfg-set stack rendered goal.rise_height_mm
without brackets ('79,87'); the old consumer did float('79,87'[0]) ->
7.0, a silent ~7 mm rise target that produced a wrong CANARY verdict.
"""
import pytest

from rl_move.sim.cfg_set import cfg_range


def test_list_passthrough():
    assert cfg_range([79, 87]) == [79.0, 87.0]
    assert cfg_range((2.5, 8.0)) == [2.5, 8.0]


def test_bracketless_comma_string_coerces():
    assert cfg_range("79,87") == [79.0, 87.0]
    assert cfg_range("[79, 87]") == [79.0, 87.0]


def test_garbage_raises_instead_of_silent_misparse():
    with pytest.raises(ValueError):
        cfg_range("79")           # scalar string: ambiguous
    with pytest.raises(ValueError):
        cfg_range(79.0)           # scalar number: ambiguous
    with pytest.raises(ValueError):
        cfg_range("a,b")
    with pytest.raises(ValueError):
        cfg_range([1, 2, 3])


def test_goal_task_range_keys_survive_string_form():
    # the three consumers hardened in goal_task.py parse identically
    for s, want in (("2.5,8.0", [2.5, 8.0]), ("10,30", [10.0, 30.0])):
        assert cfg_range(s) == want
