"""Synthetic reward-accounting regressions recovered from the retired bank.

These exercise plain helpers: no sim model, rollout, or generated artifacts.
"""
import pytest

from rl_move.sim.walk_task import (
    transition_window_liftoff,
    transition_window_tick,
    transition_window_touchdown,
    walk_legduty_ratio_charge,
)


def test_touchdown_does_not_charge_airborne_approach():
    history, remaining = transition_window_touchdown(td_ticks=3)
    assert remaining == 3
    assert history == []
    assert transition_window_liftoff(history) is None


def test_stationary_loaded_stance_has_no_slip_charge():
    history, remaining = transition_window_touchdown(td_ticks=3)
    for _ in range(5):
        remaining, history, charge = transition_window_tick(
            remaining, history, meaningful=True, ex_w=0.0, lo_ticks=3)
        assert charge in (None, 0.0)
    assert transition_window_liftoff(history) == 0.0


def test_touchdown_window_charges_exactly_its_contact_tick_count():
    history, remaining = transition_window_touchdown(td_ticks=3)
    charges = []
    for _ in range(8):
        remaining, history, charge = transition_window_tick(
            remaining, history, meaningful=True, ex_w=1.0, lo_ticks=3)
        charges.append(charge)
    assert charges == [1.0, 1.0, 1.0, None, None, None, None, None]
    assert remaining == 0


def test_low_force_contact_gap_exhausts_touchdown_window():
    history, remaining = transition_window_touchdown(td_ticks=3)
    for _ in range(3):
        remaining, history, charge = transition_window_tick(
            remaining, history, meaningful=False, ex_w=9.0, lo_ticks=3)
        assert charge is None
    assert remaining == 0
    _, _, charge = transition_window_tick(
        remaining, history, meaningful=True, ex_w=5.0, lo_ticks=3)
    assert charge is None


def test_low_force_contact_gap_expires_liftoff_spike():
    history, remaining = transition_window_touchdown(td_ticks=3)
    remaining, history, _ = transition_window_tick(
        remaining, history, meaningful=True, ex_w=9.0, lo_ticks=3)
    for _ in range(3):
        remaining, history, _ = transition_window_tick(
            remaining, history, meaningful=False, ex_w=9.0, lo_ticks=3)
    assert history == [0.0, 0.0, 0.0]
    assert transition_window_liftoff(history) == 0.0


def test_liftoff_charge_uses_only_recent_loaded_history():
    # Different old slip must not change the price of identical recent contact.
    charges = []
    for old_slip in (0.0, 100.0):
        history, remaining = transition_window_touchdown(td_ticks=3)
        for slip in (old_slip, 2.0, 4.0):
            remaining, history, _ = transition_window_tick(
                remaining, history, meaningful=True, ex_w=slip, lo_ticks=2)
        charges.append(transition_window_liftoff(history))
    assert charges == [3.0, 3.0]


@pytest.mark.parametrize("agg", ["min", "sum"])
@pytest.mark.parametrize("duty", [0.0, 0.25, 1.0])
def test_balanced_duty_has_no_shortfall(duty, agg):
    charge, ratios = walk_legduty_ratio_charge([duty] * 6, 1.0, agg=agg)
    assert ratios == pytest.approx([1.0] * 6)
    assert charge == 0.0


def test_swing_floor_disabled_and_default_aggregation_are_inert():
    duty = [0.0, 0.0, 1.0, 1.0, 1.0, 1.0]
    baseline = walk_legduty_ratio_charge(duty, 1.0)
    assert walk_legduty_ratio_charge(duty, 1.0, agg="min") == baseline
    assert walk_legduty_ratio_charge(
        duty, 1.0, swing_counts=None, swing_min_count=2.0) == baseline
    assert walk_legduty_ratio_charge(
        duty, 1.0, swing_counts=[0] * 6, swing_min_count=0.0) == baseline


def test_swing_floor_charges_low_count_without_changing_reported_ratios():
    duty = [1.0] * 6
    baseline, ratios = walk_legduty_ratio_charge(duty, 1.0)
    charge, floored_ratios = walk_legduty_ratio_charge(
        duty, 1.0, swing_counts=[0, 2, 2, 2, 2, 2], swing_min_count=2.0)
    assert baseline == 0.0
    assert charge == 1.0
    assert floored_ratios == ratios


@pytest.mark.parametrize("duty", [[1.0] * 6, [0.0, 1.0, 1.0, 1.0, 1.0, 1.0]])
def test_swing_counts_at_floor_preserve_duty_charge(duty):
    assert walk_legduty_ratio_charge(
        duty, 1.0, swing_counts=[2] * 6, swing_min_count=2.0
    ) == walk_legduty_ratio_charge(duty, 1.0)


@pytest.mark.parametrize("starved_legs", [1, 2])
def test_sum_aggregation_charges_each_starved_leg(starved_legs):
    duty = [0.0] * starved_legs + [1.0] * (6 - starved_legs)
    worst, ratios = walk_legduty_ratio_charge(duty, 1.0)
    total, summed_ratios = walk_legduty_ratio_charge(duty, 1.0, agg="sum")
    assert worst == 1.0
    assert total == float(starved_legs)
    assert summed_ratios == ratios


def test_sum_aggregation_includes_each_swing_floor_shortfall():
    charge, ratios = walk_legduty_ratio_charge(
        [1.0] * 6, 1.0, swing_counts=[0, 0, 2, 2, 2, 2],
        swing_min_count=2.0, agg="sum")
    assert charge == 2.0
    assert ratios == [1.0] * 6
