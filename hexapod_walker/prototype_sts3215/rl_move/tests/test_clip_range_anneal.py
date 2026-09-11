"""Unit tests for the tail clip-range schedule
(_parse_clip_range_anneal / _clip_range_anneal_value), built in the
09-11 stand50hz dig-in: the dqfix stance recipe learns all three
goal clauses by ~5M steps, then one late PPO update event
(train/approx_kl 0.36, clip_fraction 0.32-0.42, log_std pinned at its
-4.0 anneal floor for the prior 3M steps) scrambles a clause;
target_kl=0.02 was already on and fires only AFTER the damaging
minibatch. The schedule holds the constructor clip range through
acquisition and tightens it across the training tail. Pure-function
tests only (mirrors test_log_std_anneal_multi.py); mujoco/GPU-free,
mechanics not measurements.
"""
from __future__ import annotations

import pytest

from rl_move.sim.train_ppo_mjx import (
    _clip_range_anneal_value,
    _parse_clip_range_anneal,
)


def test_none_is_off():
    # --clip-range-final unset => None => no callback constructed.
    assert _parse_clip_range_anneal(None, 0.5, 0.2) is None


def test_parse_valid_returns_pair():
    assert _parse_clip_range_anneal(0.05, 0.5, 0.2) == (0.05, 0.5)
    # final == init is allowed (a no-op schedule, not an error).
    assert _parse_clip_range_anneal(0.2, 1.0, 0.2) == (0.2, 1.0)


def test_parse_rejects_nonpositive_final():
    with pytest.raises(SystemExit):
        _parse_clip_range_anneal(0.0, 0.5, 0.2)
    with pytest.raises(SystemExit):
        _parse_clip_range_anneal(-0.1, 0.5, 0.2)


def test_parse_rejects_widening():
    # Tail TIGHTENING only: final above the launch clip range refuses.
    with pytest.raises(SystemExit):
        _parse_clip_range_anneal(0.3, 0.5, 0.2)


def test_parse_rejects_bad_frac():
    for frac in (0.0, -0.5, 1.5):
        with pytest.raises(SystemExit):
            _parse_clip_range_anneal(0.05, frac, 0.2)


def test_value_holds_init_before_tail():
    # frac=0.5 of 6M steps: the first 3M hold the constructor value.
    for t in (0, 1_000_000, 2_999_999):
        assert _clip_range_anneal_value(t, 6_000_000, 0.2, 0.05,
                                        0.5) == pytest.approx(0.2)


def test_value_reaches_and_holds_final():
    v_end = _clip_range_anneal_value(6_000_000, 6_000_000, 0.2, 0.05,
                                     0.5)
    assert v_end == pytest.approx(0.05)
    # Past --steps (overshoot rollouts) it holds, never extrapolates.
    v_past = _clip_range_anneal_value(7_000_000, 6_000_000, 0.2, 0.05,
                                      0.5)
    assert v_past == pytest.approx(0.05)


def test_value_monotone_nonincreasing_in_tail():
    vals = [_clip_range_anneal_value(t, 6_000_000, 0.2, 0.05, 0.5)
            for t in range(3_000_000, 6_000_001, 500_000)]
    assert all(a >= b for a, b in zip(vals, vals[1:]))
    # Midpoint of the tail sits strictly between init and final.
    mid = _clip_range_anneal_value(4_500_000, 6_000_000, 0.2, 0.05, 0.5)
    assert 0.05 < mid < 0.2


def test_value_frac_one_anneals_whole_run():
    # tail_frac=1.0 => linear from step 0 (log-std-anneal-like).
    assert _clip_range_anneal_value(0, 6_000_000, 0.2, 0.05,
                                    1.0) == pytest.approx(0.2)
    assert _clip_range_anneal_value(3_000_000, 6_000_000, 0.2, 0.05,
                                    1.0) == pytest.approx(0.125)
