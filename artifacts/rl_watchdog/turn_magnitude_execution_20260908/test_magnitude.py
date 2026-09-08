"""Pure arithmetic/protocol checks; no helper import, model, or simulator run."""

import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
FROZEN = json.loads((HERE / "frozen_vectors.json").read_text())
TEMPLATES = FROZEN["templates"]
REFERENCES = json.loads((HERE / "reference_baselines.json").read_text())["baselines"]
RHO = math.sqrt(18) * .025


@pytest.fixture(scope="module")
def probe():
    # Only the execution module's pure API is used. Its execution/helper loader
    # must remain behind explicit function calls and the main guard.
    spec = importlib.util.spec_from_file_location(
        "magnitude_protocol_under_test", HERE / "probe_magnitude.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def metrics(**changes):
    result = dict(
        valid=True,
        d_yaw_rad=0.,
        endpoint_d_yaw_rad=0.,
        fwd_disp_m=1.,
        loaded_slip_m=1.,
        max_abs_roll_deg=2.,
        max_abs_pitch_deg=2.,
        nonwalk_ticks=0,
        terminated_in_window=False,
        window_ticks=80,
        window_state_samples=81,
    )
    result.update(changes)
    return result


def passing_state(wz=.15, positive_gain=.006, negative_gain=-.002, box_gain=.004):
    sign = math.copysign(1., wz)
    return [
        metrics(d_yaw_rad=sign * positive_gain),
        metrics(d_yaw_rad=sign * negative_gain),
        metrics(d_yaw_rad=sign * box_gain),
        metrics(),
    ]


def test_preregistered_sources_and_finite_rollout_ceiling():
    prereg = json.loads((HERE / "PREREGISTRATION.json").read_text())
    for filename, key in (
        ("frozen_vectors.json", "frozen_vectors_sha256"),
        ("reference_baselines.json", "reference_baselines_sha256"),
    ):
        assert hashlib.sha256((HERE / filename).read_bytes()).hexdigest() == prereg[key]
    assert len(TEMPLATES) == 4
    assert len(REFERENCES) == prereg["continuous_baselines"] == 4
    assert sum(len(t["source_members"]) for t in TEMPLATES) == prereg["branch_states"] == 8
    assert prereg["branch_slots"] == 8 * 5 == 40
    assert prereg["straight_rollouts"] == 2 * 3 == 6
    assert prereg["total_rollout_ceiling"] == 40 + 4 + 6 == 50


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t["template_id"])
def test_allocation_matches_each_frozen_vector_and_budget(probe, template):
    g = np.asarray(template["mean_central_secant"], dtype=np.float64)
    u = probe.capped_allocation(g)
    assert u.shape == (18,)
    assert np.isfinite(u).all()
    np.testing.assert_allclose(u, template["candidate_vector"], rtol=0., atol=2e-16)
    np.testing.assert_array_equal(np.sign(u), np.sign(g))
    assert np.linalg.norm(u) == pytest.approx(RHO, rel=0., abs=3e-16)
    assert np.max(np.abs(u)) <= .05
    assert np.flatnonzero(np.abs(u) == .05).tolist() == template["capped_coordinates"]
    # This is the promised surrogate improvement, not a dynamics assertion.
    assert g @ u > g @ np.asarray(template["comparator_vector"])


def test_naive_normalization_violates_the_existing_coordinate_cap():
    low_peaks = []
    for template in TEMPLATES:
        g = np.asarray(template["mean_central_secant"])
        peak = np.max(np.abs(g)) * RHO / np.linalg.norm(g)
        assert peak == pytest.approx(template["naive_normalization_peak_at_rho025"])
        low_peaks.append(peak)
    assert [p > .05 for p in low_peaks] == [True, False, True, True]
    assert all(2 * p > .05 for p in low_peaks)


@pytest.mark.parametrize(
    "g",
    [np.zeros(18), np.r_[np.ones(4), np.zeros(14)],
     np.r_[np.nan, np.ones(17)], np.r_[np.inf, np.ones(17)], np.ones(17)],
    ids=["zero", "insufficient-coordinates", "nan", "infinity", "wrong-shape"],
)
def test_invalid_allocation_input_is_not_replaced(probe, g):
    with pytest.raises(ValueError):
        probe.capped_allocation(g)


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t["template_id"])
def test_source_pairs_match_recorded_cells_and_phase_lookup(probe, template):
    assert {m["start_phase"] for m in template["source_members"]} == {0., math.pi}
    for member in template["source_members"]:
        reference = next(
            b for b in REFERENCES
            if b["cell"]["wz"] == .15 * template["wz_sign"]
            and b["cell"]["phase_offset"] == member["start_phase"]
        )
        p = member["original_tick"]
        phase = reference["metrics_" + str(p)]["phase_at_branch"]
        assert phase == member["original_phase"]
        assert member["heldout_target_phase"] == pytest.approx((phase + math.pi / 2) % math.tau)
        assert member["heldout_selection_ticks_inclusive"] == [p + 10, p + 25]
        assert p + 25 + 80 <= 755
        for turns in (-2, 0, 3):
            selected = probe.choose_template(TEMPLATES, .15 * template["wz_sign"], phase + turns * math.tau)
            assert selected["template_id"] == template["template_id"]


@pytest.mark.parametrize("wz", [-.15, .15])
def test_lookup_boundary_ties_use_phase_index_not_list_order(probe, wz):
    pair = sorted((t for t in TEMPLATES if t["wz_sign"] == math.copysign(1, wz)),
                  key=lambda t: t["phase_index"])
    mid = (pair[0]["phase_center_rad"] + pair[1]["phase_center_rad"]) / 2
    for boundary in (mid, (mid + math.pi) % math.tau):
        for delta in (0., -2e-13, 2e-13):
            selected = probe.choose_template(list(reversed(TEMPLATES)), wz, boundary + delta)
            assert selected["phase_index"] == 0
    assert probe.choose_template(TEMPLATES, wz, mid - 2e-12)["phase_index"] == 0
    assert probe.choose_template(TEMPLATES, wz, mid + 2e-12)["phase_index"] == 1


def test_exact_zero_command_has_no_template(probe):
    for phase in (0., math.pi, -1., 20.):
        assert probe.choose_template(TEMPLATES, 0., phase) is None
        assert probe.choose_template(TEMPLATES, -0., phase) is None


@pytest.mark.parametrize("p", [600, 638])
@pytest.mark.parametrize("offset", [10, 25])
def test_tick_selection_includes_both_bounds_and_uses_preaction_index(probe, p, offset):
    trace = np.zeros(755)
    n = p + offset
    trace[n - 1] = .7
    assert probe.select_tick(trace, p, .7) == n


def test_tick_selection_is_circular_and_earliest_on_exact_tie(probe):
    trace = np.full(755, 2.)
    trace[611 - 1] = math.tau - .01
    trace[622 - 1] = math.tau - .01
    assert probe.select_tick(trace, 600, 0.) == 611


def test_tick_selection_does_not_replace_with_better_outside_window(probe):
    trace = np.zeros(755)
    trace[609 - 1] = trace[626 - 1] = .7
    trace[615 - 1] = .6
    assert probe.select_tick(trace, 600, .7) == 615


def test_missing_selection_window_is_unavailable(probe):
    assert probe.select_tick(np.zeros(609), 600, .7) is None
    assert probe.select_tick(np.zeros(624), 600, .7) is None
    trace = np.zeros(755)
    trace[619 - 1] = np.nan
    with pytest.raises(ValueError):
        probe.select_tick(trace, 600, .7)


@pytest.mark.parametrize("reference", REFERENCES, ids=lambda r: str(r["cell"]))
def test_actual_source_baselines_pass_their_own_retention(probe, reference):
    for p in (600, 638):
        baseline = reference["metrics_" + str(p)]
        assert probe.retention(baseline, baseline)


def test_retention_inclusive_original_thresholds_and_straight_window(probe):
    baseline = metrics()
    on_boundaries = metrics(fwd_disp_m=.9, loaded_slip_m=1.25,
                            max_abs_roll_deg=5., max_abs_pitch_deg=5.)
    assert probe.retention(on_boundaries, baseline)
    baseline = metrics(window_ticks=1300, window_state_samples=1301)
    assert probe.retention(baseline, baseline, window_ticks=1300)
    assert not probe.retention(metrics(window_ticks=1299, window_state_samples=1300), baseline, window_ticks=1300)


@pytest.mark.parametrize("change", [
    {"fwd_disp_m": .899999}, {"loaded_slip_m": 1.250001},
    {"max_abs_roll_deg": 5.000001}, {"max_abs_pitch_deg": 5.000001},
    {"nonwalk_ticks": 1}, {"terminated_in_window": True},
    {"window_ticks": 79}, {"valid": False},
])
def test_retention_rejects_each_original_failure(probe, change):
    assert not probe.retention(metrics(**change), metrics())


@pytest.mark.parametrize("key", [
    "valid", "fwd_disp_m", "loaded_slip_m", "max_abs_roll_deg",
    "max_abs_pitch_deg", "nonwalk_ticks", "terminated_in_window", "window_ticks",
])
def test_retention_missing_metrics_fail_closed(probe, key):
    branch = metrics()
    del branch[key]
    assert not probe.retention(branch, metrics())


@pytest.mark.parametrize("key", [
    "fwd_disp_m", "loaded_slip_m", "max_abs_roll_deg", "max_abs_pitch_deg",
])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_branch_or_baseline_retention_metrics_fail_closed(probe, key, value):
    assert not probe.retention(metrics(**{key: value}), metrics())
    assert not probe.retention(metrics(), metrics(**{key: value}))


@pytest.mark.parametrize("forward", [0., -.1])
def test_baseline_requires_positive_body_forward_distance(probe, forward):
    assert not probe.retention(metrics(), metrics(fwd_disp_m=forward))


@pytest.mark.parametrize("wz", [-.15, .15])
def test_five_mrad_gate_uses_commanded_direction_and_last_solve_yaw(probe, wz):
    state = passing_state(wz, positive_gain=.005)
    state[0]["endpoint_d_yaw_rad"] = -math.copysign(1., wz)
    result = probe.allocation_state_pass(*state, wz=wz)
    assert result["authority"]
    assert result["allocation"]
    state[0]["d_yaw_rad"] = math.copysign(1., wz) * .004999
    state[0]["endpoint_d_yaw_rad"] = math.copysign(1., wz)
    result = probe.allocation_state_pass(*state, wz=wz)
    assert not result["authority"]
    assert not result["allocation"]


def test_gain_subtracts_the_shared_zero_baseline(probe):
    state = passing_state()
    for branch in state:
        branch["d_yaw_rad"] += .03
    result = probe.allocation_state_pass(*state, wz=.15)
    assert result["authority"] and result["allocation"]
    state[0]["d_yaw_rad"] = .031
    assert not probe.allocation_state_pass(*state, wz=.15)["authority"]


@pytest.mark.parametrize("negative_gain", [.006, .007])
def test_even_facilitation_does_not_supply_odd_direction_support(probe, negative_gain):
    result = probe.allocation_state_pass(*passing_state(negative_gain=negative_gain), wz=.15)
    assert not result["authority"]
    assert not result["allocation"]


def test_positive_odd_is_sufficient_without_stronger_five_mrad_reversal(probe):
    result = probe.allocation_state_pass(*passing_state(negative_gain=.001), wz=.15)
    assert result["authority"] and result["allocation"]


@pytest.mark.parametrize("branch_index", [0, 1])
def test_candidate_retention_is_required_for_both_vector_signs(probe, branch_index):
    state = passing_state()
    state[branch_index]["loaded_slip_m"] = 1.26
    result = probe.allocation_state_pass(*state, wz=.15)
    assert not result["authority"] and not result["allocation"]


@pytest.mark.parametrize("box_gain", [.006, .007])
def test_comparator_tie_or_advantage_fails_only_allocation(probe, box_gain):
    result = probe.allocation_state_pass(*passing_state(box_gain=box_gain), wz=.15)
    assert result["authority"]
    assert not result["allocation"]


@pytest.mark.parametrize("change", [
    {"window_ticks": 79}, {"valid": False},
    {"d_yaw_rad": float("nan")}, {"d_yaw_rad": float("inf")},
])
def test_incomplete_or_nonfinite_comparator_cannot_support_allocation(probe, change):
    state = passing_state()
    state[2].update(change)
    result = probe.allocation_state_pass(*state, wz=.15)
    assert not result["allocation"]


def test_missing_comparator_primary_metric_cannot_support_allocation(probe):
    state = passing_state()
    del state[2]["d_yaw_rad"]
    assert not probe.allocation_state_pass(*state, wz=.15)["allocation"]


def test_finite_complete_comparator_may_fail_locomotion_retention(probe):
    state = passing_state()
    state[2].update(fwd_disp_m=.7, loaded_slip_m=2., max_abs_roll_deg=7., nonwalk_ticks=1)
    assert not probe.retention(state[2], state[3])
    result = probe.allocation_state_pass(*state, wz=.15)
    assert result["authority"] and result["allocation"]


@pytest.mark.parametrize("branch_index", [0, 1, 3])
def test_missing_candidate_or_baseline_yaw_fails_authority(probe, branch_index):
    state = passing_state()
    del state[branch_index]["d_yaw_rad"]
    result = probe.allocation_state_pass(*state, wz=.15)
    assert not result["authority"] and not result["allocation"]


def test_clipping_preserves_reported_authority_but_blocks_allocation_claim(probe):
    result = probe.allocation_state_pass(*passing_state(), wz=.15, clip_hits=1)
    assert result["authority"]
    assert not result["allocation"]


def test_decision_does_not_mutate_metric_records(probe):
    state = passing_state()
    original = copy.deepcopy(state)
    probe.allocation_state_pass(*state, wz=.15)
    assert state == original


def mock_predictor(probe, mode, p=2, action=None):
    """An action source and phase scalar only; no robot or dynamics objects."""
    if action is None:
        action = np.linspace(-.2, .2, 18, dtype=np.float32)
    model = SimpleNamespace(
        action=action, hidden=object(), calls=[],
        _state=object(), _episode_start=np.array([True]),
    )

    def predict(obs, deterministic=True):
        model.calls.append((obs, deterministic))
        return model.action, model.hidden

    model.predict = predict
    env = SimpleNamespace(
        _phase=TEMPLATES[0]["phase_center_rad"],
        action_space=SimpleNamespace(low=-np.ones(18), high=np.ones(18)),
    )
    state = dict(doses=[], zero_off_checked_ticks=0)
    job = dict(mode=mode, p=p, cell=dict(wz=-.15 if p is not None else 0.))
    wrapper = probe.WrappedPredictor(model, env, job, state, TEMPLATES)
    return wrapper, model, env, state


@pytest.mark.parametrize("mode", [
    "candidate_plus", "candidate_minus", "comparator_plus", "comparator_minus",
])
def test_wrapper_pulses_exactly_five_ticks_then_preserves_all_75_actions(probe, monkeypatch, mode):
    p = 2
    wrapper, model, env, state = mock_predictor(probe, mode, p=p)
    original_action = model.action.copy()
    selected = []
    choose = probe.choose_template

    def counted_choice(templates, wz, phase):
        selected.append((wz, phase))
        return choose(templates, wz, phase)

    monkeypatch.setattr(probe, "choose_template", counted_choice)
    vector_key = "candidate_vector" if mode.startswith("candidate") else "comparator_vector"
    frozen_delta = np.asarray(TEMPLATES[0][vector_key]) * (1 if mode.endswith("_plus") else -1)
    expected_action = (original_action.astype(np.float64) + frozen_delta).astype(np.float32)
    obs = object()
    for tick in range(p + 5 + 75):
        # Cross the phase boundary immediately after pulse onset. The selected
        # vector must remain the onset vector for the remaining four ticks.
        if tick > p:
            env._phase = TEMPLATES[1]["phase_center_rad"]
        action, hidden = wrapper.predict(obs, deterministic=False)
        assert hidden is model.hidden
        if p <= tick < p + 5:
            np.testing.assert_array_equal(action, expected_action)
            assert action is not model.action
        else:
            assert action is model.action
    assert selected == [(-.15, TEMPLATES[0]["phase_center_rad"])]
    assert state["mapping"]["template_id"] == TEMPLATES[0]["template_id"]
    assert [receipt["tick"] for receipt in state["doses"]] == list(range(p, p + 5))
    for receipt in state["doses"]:
        np.testing.assert_array_equal(receipt["requested"], frozen_delta)
        np.testing.assert_array_equal(receipt["applied"], expected_action - original_action)
        assert receipt["clip_hits"] == 0
    np.testing.assert_array_equal(model.action, original_action)
    assert model.calls == [(obs, False)] * (p + 5 + 75)


@pytest.mark.parametrize("mode", ["zero", "straight_candidate", "straight_comparator"])
def test_wrapper_zero_controls_preserve_original_action_object(probe, mode):
    straight = mode.startswith("straight_")
    wrapper, model, env, state = mock_predictor(probe, mode, p=None if straight else 2)
    original_action = model.action.copy()
    if straight:
        # Zero-off must not need a meaningful phase or a nonzero template.
        env._phase = float("nan")
    for _ in range(82):
        action, hidden = wrapper.predict(None)
        assert action is model.action
        assert hidden is model.hidden
    np.testing.assert_array_equal(model.action, original_action)
    assert state["doses"] == []
    assert state["zero_off_checked_ticks"] == (82 if straight else 0)


def test_wrapper_forwards_current_model_recurrent_state_and_episode_start(probe):
    wrapper, model, _, _ = mock_predictor(probe, "zero")
    assert wrapper._state is model._state
    assert wrapper._episode_start is model._episode_start
    first_state = model._state
    model._state = object()
    model._episode_start = np.array([False])
    assert wrapper._state is model._state
    assert wrapper._state is not first_state
    assert wrapper._episode_start is model._episode_start
    assert not wrapper._episode_start[0]


def test_wrapper_receipt_distinguishes_requested_and_clipped_dose(probe):
    box = np.asarray(TEMPLATES[0]["comparator_vector"])
    at_limit = np.sign(box).astype(np.float32)
    wrapper, model, _, state = mock_predictor(probe, "comparator_plus", p=0, action=at_limit)
    action, hidden = wrapper.predict(None)
    assert hidden is model.hidden
    np.testing.assert_array_equal(action, at_limit)
    assert len(state["doses"]) == 1
    receipt = state["doses"][0]
    assert receipt["tick"] == 0
    assert receipt["clip_hits"] == 18
    np.testing.assert_array_equal(receipt["requested"], box)
    np.testing.assert_array_equal(receipt["applied"], np.zeros(18))
