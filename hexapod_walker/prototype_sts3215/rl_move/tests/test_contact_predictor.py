from __future__ import annotations

import numpy as np

from rl_move.contact_predictor import (
    ContactLatch,
    classification_metrics,
    fit_linear_contact_model,
    leg_feature_values,
)


def test_leg_features_distinguish_lift_from_plant() -> None:
    plant = leg_feature_values(
        [0.0, 20.0, 80.0],
        [0.0, 20.0, 80.0],
        [0.0, -0.02, 0.04],
        vertical_speed_mm_s=-3.0,
    )
    lifted = leg_feature_values(
        [0.0, 5.0, 65.0],
        [0.0, 6.0, 66.0],
        [0.0, 0.01, 0.02],
        vertical_speed_mm_s=12.0,
    )

    assert abs(plant["command_clearance_mm"]) < 1e-9
    assert lifted["command_clearance_mm"] > 20.0
    assert lifted["measured_clearance_mm"] > 15.0
    assert lifted["tracking_error_deg"] == 1.0
    assert plant["current_sum_a"] == 0.06
    assert plant["current_max_a"] == 0.04
    assert plant["abs_vertical_speed_mm_s"] == 3.0


def test_linear_predictor_learns_separable_contact_confidence() -> None:
    features = np.asarray([
        [15.0, 12.0],
        [10.0, 8.0],
        [7.0, 6.0],
        [1.0, 0.5],
        [0.0, 1.0],
        [-2.0, 0.0],
    ])
    contact = np.asarray([False, False, False, True, True, True])
    model = fit_linear_contact_model(
        features, contact, ("clearance", "speed"), iterations=1200
    )
    probability = model.predict_proba(features)

    assert np.all(probability[:3] < 0.5)
    assert np.all(probability[3:] > 0.5)
    assert classification_metrics(contact, probability >= 0.5)["accuracy"] == 1.0


def test_contact_latch_requires_confirmed_hysteretic_evidence() -> None:
    latch = ContactLatch(confirm_s=0.03)

    assert latch.update(0.9, 0.01) is False
    assert latch.update(0.9, 0.01) is False
    assert latch.update(0.9, 0.01) is True
    assert latch.update(0.5, 0.10) is True
    assert latch.update(0.1, 0.02) is True
    assert latch.update(0.1, 0.01) is False
