"""Current-headroom-gated rise_score_prog income
(reward.rise_score_income_headroom_gate, walkcurr track, 2026-09-13).

Background (STATUS.md 09-13 "holdbias-riselower15m" dig-in, confirmed
by cw-stance50hz-rlonly-risebridge-s1-15m's own FAIL-MECHANISM): the
flat-rise sprawl push pins servo current at the 2.64A torque-saturation
rail and trips over_current, but `reward_rise_score_prog` pays for ANY
new height/posture score regardless of current draw -- it funds the
doomed push all the way to the trip. `k_torque_headroom` already prices
a SUSTAINED current debt post-hoc and did not stop this (income kept
paying regardless of any accruing debt); this instead discounts the
INCOME itself at the instant of a saturating tick, using the same
"redness" shape as `torque_headroom_debt_step`.

Contract under test:
  - `current_headroom_income_factor` is pure math: 1.0 well below the
    cap, 0.0 at/above the rail, linear in between, always in [0, 1].

RESEARCH_RULES "Tests": fast, mechanics only, no rollout ranking, no
artifacts.
"""
from __future__ import annotations

import pytest

from rl_move.sim.balance_helpers import current_headroom_income_factor


# ---------------------------------------------------------------------------
# Pure math


@pytest.mark.parametrize("cur,cap,margin,want", [
    (0.0, 2.64, 0.3, 1.0),
    (1.0, 2.64, 0.3, 1.0),          # well under the red zone
    (2.34, 2.64, 0.3, 1.0),         # exactly at the red-zone edge
    (2.49, 2.64, 0.3, 0.5),         # halfway into the red zone
    (2.64, 2.64, 0.3, 0.0),         # exactly at the rail
    (3.0, 2.64, 0.3, 0.0),          # past the rail: still clamped to 0
    (-2.64, 2.64, 0.3, 0.0),        # magnitude, not raw sign
])
def test_current_headroom_income_factor_math(cur, cap, margin, want):
    got = current_headroom_income_factor(abs(cur), cap, margin)
    assert got == pytest.approx(want, abs=1e-9)


def test_current_headroom_income_factor_always_unit_clamped():
    for cur in (-1000.0, -1.0, 0.0, 1.0, 2.64, 5.0, 1000.0):
        for cap, margin in ((2.64, 0.3), (0.5, 0.5), (10.0, 0.01)):
            f = current_headroom_income_factor(abs(cur), cap, margin)
            assert 0.0 <= f <= 1.0


def test_current_headroom_income_factor_degenerate_zero_margin():
    # margin_a -> 0 would divide by zero in a naive implementation.
    f = current_headroom_income_factor(5.0, 2.64, 0.0)
    assert 0.0 <= f <= 1.0
