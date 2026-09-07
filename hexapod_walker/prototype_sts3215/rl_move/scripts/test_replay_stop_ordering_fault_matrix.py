from pathlib import Path

import pytest

from rl_move.scripts.replay_stop_ordering_fault_matrix import FAULT_CASES, run_case, run_matrix


@pytest.mark.parametrize("fault_case", FAULT_CASES)
def test_fallback_write_precedes_resample_for_every_fault(fault_case):
    result = run_case(fault_case)
    assert result["held"] is True
    assert result["fallback_write_precedes_foreground_resample"] is True
    assert result["fallback_write_precedes_torque_refresh"] is True
    assert result["reanchor_requires_valid_fresh_state"] is True


def test_rejects_fresh_but_tipped_reanchor():
    from rl_move.scripts import replay_stop_ordering_fault_matrix as matrix

    assert matrix.rl_policy._stream_loss_reanchor_is_safe(  # noqa: SLF001
        matrix._state(roll_deg=26.0), matrix._state()) is False


def test_matrix_preserves_sealed_interlock():
    source = Path.home() / "Library/Application Support/Hexapod Lab/data/experiments/6a632f8ba4bc4b14812e27e6f87eaa42"
    if not source.is_dir():
        pytest.skip("sealed Robot Lab source is not installed")
    result = run_matrix(
        source,
        "ee01117989adc676d03ee2653ec34dac82e6c11e21fdf40b6e0770ca4d9ba258",
    )
    assert result["passed"] is True
    assert result["robot_contacted"] is False
    assert result["robot_motion"] is False
