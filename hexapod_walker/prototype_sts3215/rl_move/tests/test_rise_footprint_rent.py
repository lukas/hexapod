"""Mechanics-only bank for `footprint_rent_m()` and its cfg knobs
(2026-09-11 footprint-reprice-via-fade-shape DIG-IN follow-on).

Background (CURRENT_TRUTHS "CLOSED: the footprint-reprice-via-fade-
shape saga is dead", 2026-09-11 ~03:4x): 4 reward-shape configs x up to
3 seeds each all converged to the SAME ~66-107mm footprint splay
because both existing footprint terms stop charging once a policy
settles at a steady, non-improving distance -- `footprint_fade` (a
multiplicative income gate) saturates to a constant discount a policy
can simply tolerate forever, and `k_curl_progress` is potential-based
(pays only while distance is shrinking, so it's worth 0 at ANY stable
equilibrium). `footprint_rent_m` is a standalone, additive, never-
saturating per-tick debit applied OUTSIDE every multiplicative income
chain so no other reward stream can buy it off.

RESEARCH_RULES "Tests": fast, mechanics only, no rollout ranking, no
artifacts -- this bank only calls the pure function and cfg_get, never
steps a sim.
"""
from __future__ import annotations

import math

import pytest

from rl_move.sim.sim_env import PLANT_SPEC, footprint_rent_m
from rl_move.config import cfg_get


LEGACY_FREE_MM = PLANT_SPEC["footprint_err_mm"]  # 40.0


@pytest.mark.parametrize("fp_mm", [-100.0, -1.0, 0.0, 10.0, 39.9])
def test_inside_free_zone_is_zero_rent(fp_mm):
    assert footprint_rent_m(fp_mm, LEGACY_FREE_MM) == 0.0


def test_at_the_free_boundary_is_zero():
    assert footprint_rent_m(LEGACY_FREE_MM, LEGACY_FREE_MM) == 0.0


@pytest.mark.parametrize("fp_mm,want_m", [
    (40.0, 0.0),
    (41.0, 0.001),
    (50.0, 0.010),
    (90.0, 0.050),
    (140.0, 0.100),
])
def test_linear_rent_beyond_the_free_zone(fp_mm, want_m):
    got = footprint_rent_m(fp_mm, LEGACY_FREE_MM)
    assert got == pytest.approx(want_m, abs=1e-12)


def test_rent_is_monotonically_nondecreasing_and_unbounded():
    # The whole point vs footprint_fade: no saturation -- a policy that
    # drifts from 90mm to 150mm keeps paying MORE, never plateaus.
    vals = [footprint_rent_m(v, LEGACY_FREE_MM)
            for v in (40.0, 60.0, 90.0, 150.0, 500.0, 5000.0)]
    assert vals == sorted(vals)
    assert vals[0] == 0.0
    assert vals[-1] > vals[-2] > vals[-3]  # still climbing, no cap


def test_stable_equilibrium_keeps_paying_the_same_nonzero_rent_every_tick():
    # The exact defect this term exists to fix: a policy parked at a
    # CONSTANT distance outside the free zone must cost the same every
    # single tick for as long as it stays there (unlike a potential-
    # based term, which would price this at 0 once distance stops
    # changing).
    fp_mm = 90.0
    rents = [footprint_rent_m(fp_mm, LEGACY_FREE_MM) for _ in range(5)]
    assert all(r == rents[0] for r in rents)
    assert rents[0] > 0.0


def test_output_never_negative_and_always_finite():
    for fp_mm in (-1e6, -1.0, 0.0, 1e6):
        for free_mm in (0.0, 25.0, 40.0, 100.0):
            v = footprint_rent_m(fp_mm, free_mm)
            assert v >= 0.0
            assert math.isfinite(v)


def test_cfg_default_free_zone_matches_legacy_walkable_band_when_unset():
    cfg = {"reward": {}}
    free_mm = float(cfg_get(cfg, "reward", "rise_footprint_pen_free_mm",
                             default=PLANT_SPEC["footprint_err_mm"]))
    assert free_mm == LEGACY_FREE_MM


def test_cfg_gain_defaults_to_off():
    cfg = {"reward": {}}
    k = float(cfg_get(cfg, "reward", "k_rise_footprint_pen", default=0.0))
    assert k == 0.0


def test_cfg_override_moves_the_free_zone_and_enables_the_gain():
    cfg = {"reward": {"k_rise_footprint_pen": 5.0,
                       "rise_footprint_pen_free_mm": 20.0}}
    k = float(cfg_get(cfg, "reward", "k_rise_footprint_pen", default=0.0))
    free_mm = float(cfg_get(cfg, "reward", "rise_footprint_pen_free_mm",
                             default=PLANT_SPEC["footprint_err_mm"]))
    assert (k, free_mm) == (5.0, 20.0)
    assert footprint_rent_m(30.0, free_mm) == pytest.approx(0.010)
