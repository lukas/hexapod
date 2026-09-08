"""Local event matching regressions; no rollouts or training."""
import numpy as np
import pytest
from rl_move.sim import probe_turn_eventsync as es


def test_jitter_is_not_erased_by_a_favorable_event_from_another_cycle():
    plan = np.array([0, 75, 150, 225])
    actual = np.array([10, 100, 175, 250])
    matched = es._match_events(plan, actual, 75)
    assert np.array_equal(matched["offset_ticks"], [10, 25, 25, 25])
    assert np.percentile(matched["offset_ticks"], 75) > np.percentile(matched["offset_ticks"], 25)
    assert matched["matched_pairs"] == [[0, 10], [75, 100], [150, 175], [225, 250]]


def test_one_touchdown_cannot_fill_four_cycles():
    result = es._match_events(np.array([0, 75, 150, 225]), np.array([10]), 75)
    assert np.array_equal(result["offset_ticks"], [10])
    assert result["missing_planned_idx"] == [75, 150, 225]
    assert result["unmatched_actual_idx"] == []
    assert result["planned_n"] == 4 and result["actual_n"] == 1


def test_chatter_events_stay_unmatched_instead_of_becoming_extra_cycles():
    result = es._match_events(np.array([0, 75]), np.array([8, 10, 84, 86]), 75)
    assert result["matched_pairs"] == [[0, 8], [75, 84]]
    assert result["unmatched_actual_idx"] == [10, 86]


def test_assignment_preserves_order_and_maximum_cardinality():
    # Nearest-first would spend actual6 on plan5 and strand plan10.
    result = es._match_events(np.array([5, 10]), np.array([1, 6]), 10)
    assert result["matched_pairs"] == [[5, 1], [10, 6]]
    assert len({a for _, a in result["matched_pairs"]}) == 2


def test_half_period_ambiguous_events_are_explicitly_unmatched():
    result = es._match_events(np.array([10]), np.array([5, 15]), 10)
    assert result["matched_pairs"] == []
    assert result["missing_planned_idx"] == [10]
    assert result["unmatched_actual_idx"] == [5, 15]


def test_circular_seam_does_not_fabricate_huge_leg_differential():
    values = [370., -370., 370., -370., 370., -370.]
    center = es._circular_median(values, 750.)
    assert abs(center) == 375.
    assert es._circular_spread(values, 750.) == 10.
    assert np.max(np.abs(es._wrap(np.array(values)-center, 750.))) == 5.


def test_event_output_counts_matches_and_exposes_missing_contact_cycles():
    T = 310
    plan = np.zeros((T, 6), dtype=bool)
    contact = plan.copy()
    for t in [10, 85, 160, 235]:
        plan[t:t+20, :] = True
    contact[20:40, :] = True
    output = es.event_offsets(plan, contact, 75)
    leg = output["per_leg"][0]
    assert leg["touchdown_n"] == 1
    assert leg["touchdown_matching"]["missing_planned_idx"] == [85, 160, 235]
    assert leg["touchdown_matching"]["actual_n"] == 1


def test_two_foot_population_is_not_mislabeled_as_three_foot_support():
    loaded = np.zeros((4, 6), dtype=bool)
    loaded[:, [0, 2]] = True
    result = es.support_state_stats(loaded, np.array([.1, .2, .3, .4]), np.ones(4))
    assert result["states"]["pureA"]["n"] == 4  # legacy population unchanged
    assert "two-foot" in result["population_definition"]
    assert result["wz_counterfactual_mean"] == result["wz_observational_reweighted_mean"]
    assert "not a causal upper bound" in result["reweighting_scope"]


@pytest.mark.parametrize("period", [0, -1, float("nan"), float("inf")])
def test_invalid_period_rejected(period):
    with pytest.raises(ValueError):
        es._match_events(np.array([0]), np.array([1]), period)
