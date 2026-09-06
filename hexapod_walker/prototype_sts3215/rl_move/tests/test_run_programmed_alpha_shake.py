from __future__ import annotations

import pytest

from rl_move.scripts.run_programmed_alpha_shake import (
    CONDITIONS,
    _selected_conditions,
)


def test_selected_conditions_defaults_to_proven_four_cell_order() -> None:
    assert _selected_conditions(None) == CONDITIONS


def test_selected_conditions_preserves_requested_bounded_subset_order() -> None:
    selected = _selected_conditions(["low_alpha_40", "high_alpha_40"])

    assert [condition["name"] for condition in selected] == [
        "low_alpha_40",
        "high_alpha_40",
    ]
    assert [condition["vx_mm_s"] for condition in selected] == [40.0, 40.0]


def test_selected_conditions_rejects_duplicate_walking_cells() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        _selected_conditions(["low_alpha_40", "low_alpha_40"])
