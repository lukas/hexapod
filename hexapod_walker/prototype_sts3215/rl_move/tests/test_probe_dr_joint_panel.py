"""Mechanics tests for the DR joint sensitivity panel (speed sim2real).

Fast, pure sampling/scoring mechanics -- no MuJoCo model, no rollouts,
no artifacts (RESEARCH_RULES "Tests").
"""
import dataclasses
import math

import numpy as np

from rl_move.sim.domain_rand import DomainRandomizer
from rl_move.sim.probe_dr_joint_panel import (
    HELDOUT_SEEDS,
    HELDOUT_STRIDE,
    MODES,
    PanelBounds,
    SEARCH_SEEDS,
    ensemble_episode,
    neutral_params,
    provisional_score,
    sample_ensembles,
    signature_score,
)

B = PanelBounds()


def _all(seed=7, n=9):
    return sample_ensembles(seed, n, B)


def test_sampling_deterministic():
    a = _all()
    b = _all()
    assert len(a) == len(b) == 9 * len(MODES)
    for ea, eb in zip(a, b):
        assert ea.name == eb.name and ea.split == eb.split
        assert ea.params == eb.params and ea.latents == eb.latents
    # A different panel seed changes the draws.
    c = sample_ensembles(8, 9, B)
    assert any(ea.params != ec.params for ea, ec in zip(a, c))


def test_bounds_respected_all_modes():
    for e in _all(seed=3, n=12):
        p = e.params
        assert B.mass_scale[0] <= p["mass_scale"] <= B.mass_scale[1]
        assert all(abs(v) <= B.com_xy_m + 1e-9
                   for v in p["com_offset_m"][:2])
        assert abs(p["com_offset_m"][2]) <= B.com_z_m + 1e-9
        assert B.friction_scale[0] - 1e-9 <= p["friction_scale"] \
            <= B.friction_scale[1] + 1e-9
        for v in p["foot_friction_scale"]:
            assert B.foot_friction_scale[0] - 1e-9 <= v <= 1.0 + 1e-9 \
                or v <= B.foot_friction_scale[1] + 1e-9
        assert B.torque_scale[0] - 1e-9 <= p["torque_scale"] \
            <= B.torque_scale[1] + 1e-9
        assert B.latency_scale[0] - 1e-9 <= p["latency_scale"] \
            <= B.latency_scale[1] + 1e-9
        assert B.deadband_scale[0] - 1e-9 <= p["deadband_scale"] \
            <= B.deadband_scale[1] + 1e-9
        assert B.vel_scale[0] - 1e-9 <= p["vel_scale"] \
            <= B.vel_scale[1] + 1e-9
        assert 0.0 <= p["cmd_drop_prob"] <= B.cmd_drop_prob[1] + 1e-9
        assert all(abs(v) <= B.zero_bias_deg + 1e-9
                   for v in p["joint_zero_bias_deg"])
        assert B.ground_tilt_deg[0] <= p["ground_tilt_deg"] \
            <= B.ground_tilt_deg[1] + 1e-9
        for row in p["kp_scale"], p["kv_scale"]:
            for v in row:
                assert 0.5 <= v <= 1.5
        assert len(p["leg_mass_scale"]) == 6
        assert len(p["link_scale"]) == 6


def test_heldout_split_stable_and_disjoint():
    ens = _all(seed=11, n=9)
    held = {e.name for e in ens if e.split == "heldout"}
    search = {e.name for e in ens if e.split == "search"}
    assert held and search and not held & search
    for e in ens:
        want = ("heldout" if e.index % HELDOUT_STRIDE == HELDOUT_STRIDE - 1
                else "search")
        assert e.split == want
    assert not set(SEARCH_SEEDS) & set(HELDOUT_SEEDS)


def test_correlated_battery_latent_couples_torque_and_vel():
    ens = [e for e in _all(seed=5, n=30) if e.mode == "correlated"]
    sag = np.array([e.latents["battery_sag"] for e in ens])
    tq = np.array([e.params["torque_scale"] for e in ens])
    vel = np.array([e.params["vel_scale"] for e in ens])
    # Deeper sag -> lower torque AND lower speed, deterministically.
    assert np.corrcoef(sag, tq)[0, 1] < -0.99
    assert np.corrcoef(sag, vel)[0, 1] < -0.99
    assert np.corrcoef(tq, vel)[0, 1] > 0.99


def test_asymmetric_confined_to_target_legs():
    ens = [e for e in _all(seed=9, n=30) if e.mode == "asymmetric"]
    assert ens
    for e in ens:
        legs = set(e.latents["legs"])
        others = set(range(6)) - legs
        p = e.params
        for leg in others:
            for j in (3 * leg, 3 * leg + 1, 3 * leg + 2):
                assert p["kp_scale"][j] == 1.0
                assert p["joint_zero_bias_deg"][j] == 0.0
            assert p["leg_torque_scale"][leg] == 1.0
            assert p["foot_friction_scale"][leg] == 1.0
            assert p["leg_mass_scale"][leg] == [1.0, 1.0, 1.0]
        assert any(p["kp_scale"][3 * leg] != 1.0 for leg in legs)


def test_ensemble_episode_neutral_identity_and_overrides():
    rng = np.random.default_rng(0)
    base = DomainRandomizer(None, scale=0.0).sample(rng)
    ep = ensemble_episode(base, neutral_params())
    assert ep.mass_scale == 1.0
    assert np.allclose(ep.com_offset_m, 0.0)
    assert np.allclose(ep.kp_scale, 1.0)
    assert np.allclose(ep.gravity_vec, [0.0, 0.0, -9.80665])
    assert ep.zero_drift_cmd_frame  # frame-coupled, physically correct
    # Untouched fields survive replace().
    assert np.allclose(ep.start_offset_rad, base.start_offset_rad)
    p = neutral_params()
    p.update(mass_scale=1.2, torque_scale=0.6, ground_tilt_deg=3.0,
             ground_tilt_az_deg=90.0)
    p["joint_zero_bias_deg"] = [2.0] * 18
    ep2 = ensemble_episode(base, p)
    assert ep2.mass_scale == 1.2 and ep2.torque_scale == 0.6
    assert abs(ep2.gravity_vec[1]) > 0.3  # tilt along +Y
    assert np.allclose(ep2.joint_zero_bias_rad, math.radians(2.0))


def test_scores_rank_signature_over_nominal():
    nominal = {"med_peak_abs_roll_deg": 1.3, "med_recurrent_peaks": 0.0,
               "fall_frac": 0.0, "med_speed_m_s": 0.049}
    hit = {"med_peak_abs_roll_deg": 16.5, "med_recurrent_peaks": 4.0,
           "fall_frac": 0.0, "med_speed_m_s": 0.032}
    fallen = dict(hit, fall_frac=1.0)
    s_nom = provisional_score(nominal, 0.049)
    s_hit = provisional_score(hit, 0.049)
    s_fall = provisional_score(fallen, 0.049)
    assert s_hit > s_nom and s_hit > s_fall
    ctr_low = [{"med_peak_abs_roll_deg": 5.0}]
    ctr_high = [{"med_peak_abs_roll_deg": 16.0}]
    sel = signature_score(hit, ctr_low, 0.049)
    nonsel = signature_score(hit, ctr_high, 0.049)
    assert sel["final_score"] > nonsel["final_score"]
    assert sel["selectivity_score"] == 1.0
