"""walk_task.walk_yaw_init_wz_decision -- the shared, pure gating +
arithmetic function all three execution engines (CPU sim_env.py,
in-process MjxVecEnv, sharded MjxShardedVecEnv workers) call for the
walkyaw RSI-style initial-wz curriculum lever. See
`test_walk_yaw_init_wz.py`'s module docstring for the full mechanism
rationale/provenance; this file is the single, dependency-free
correctness check every engine's own thin wrapper defers to.
"""
from __future__ import annotations

from rl_move.sim.walk_task import walk_yaw_init_wz_decision as decide


def test_default_frac_zero_returns_zero_regardless_of_draw():
    assert decide(0.0, 0.0, 0.27, 0.0, 0.5, 0.0) == 0.0


def test_scale_zero_returns_zero_even_with_frac_one():
    assert decide(0.0, 0.0, 0.27, 1.0, 0.0, 0.0) == 0.0


def test_qualifying_turn_in_place_with_winning_draw():
    assert decide(0.0, 0.0, 0.27, 1.0, 0.5, 0.0) == 0.5 * 0.27


def test_negative_command_preserves_sign():
    assert decide(0.0, 0.0, -0.27, 1.0, 0.5, 0.0) == 0.5 * -0.27


def test_losing_draw_returns_zero():
    assert decide(0.0, 0.0, 0.27, 0.3, 0.5, 0.5) == 0.0


def test_draw_exactly_at_frac_boundary_loses():
    # draw < frac required; draw == frac must NOT select.
    assert decide(0.0, 0.0, 0.27, 0.3, 0.5, 0.3) == 0.0


def test_linear_command_disqualifies_even_with_real_wz():
    assert decide(0.05, 0.0, 0.27, 1.0, 0.5, 0.0) == 0.0
    assert decide(0.0, 0.05, 0.27, 1.0, 0.5, 0.0) == 0.0


def test_zero_wz_disqualifies():
    assert decide(0.0, 0.0, 0.0, 1.0, 0.5, 0.0) == 0.0


def test_tiny_wz_at_noise_floor_disqualifies():
    assert decide(0.0, 0.0, 1e-4, 1.0, 0.5, 0.0) == 0.0


def test_negative_scale_flips_sign_relative_to_command():
    assert decide(0.0, 0.0, 0.27, 1.0, -0.5, 0.0) == -0.5 * 0.27
