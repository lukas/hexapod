"""Mechanics-only bank for `footprint_fade()` and its cfg knobs
(2026-09-11 stand50hz footprint-splay dig-in).

Background (CURRENT_TRUTHS "SHARPENING" entry, 2026-09-11): the
rise-plant footprint term paid FULL income everywhere <= the 40mm hard
eval cliff (`PLANT_SPEC["footprint_err_mm"]`) and only started fading
OUTSIDE it (40->80mm), so a policy that splays its feet just past the
gate (measured: 46-48mm) out-earns one that stays honestly inside the
walkable band -- a reward<->eval misalignment (08-21 ruling), not a
training-dynamics bug. The fix pulls the fade math into a pure
function and exposes its two endpoints as cfg
(`reward.rise_footprint_full_mm` / `rise_footprint_zero_mm`) so a
tightened band (e.g. full=25, zero=40 -- fade ENDS at the gate cliff
instead of starting there) can be dialed in without touching any other
reward term. Defaults must reproduce the legacy numbers bit-exact.

RESEARCH_RULES "Tests": fast, mechanics only, no rollout ranking, no
artifacts -- this bank only calls the pure function and cfg_get, never
steps a sim.
"""
from __future__ import annotations

import pytest

from rl_move.sim.sim_env import PLANT_SPEC, footprint_fade
from rl_move.config import cfg_get


LEGACY_FULL_MM = PLANT_SPEC["footprint_err_mm"]        # 40.0
LEGACY_ZERO_MM = 2.0 * PLANT_SPEC["footprint_err_mm"]   # 80.0


def _legacy_fp_f(fp_mm: float) -> float:
    """The original inline formula, kept here as an independent oracle."""
    return min(max((2.0 * PLANT_SPEC["footprint_err_mm"] - fp_mm)
                    / PLANT_SPEC["footprint_err_mm"], 0.0), 1.0)


@pytest.mark.parametrize("fp_mm", [0.0, 10.0, 25.0, 39.9, 40.0, 40.1,
                                    47.0, 60.0, 79.9, 80.0, 100.0, -5.0])
def test_default_band_matches_legacy_formula_bit_exact(fp_mm):
    got = footprint_fade(fp_mm, LEGACY_FULL_MM, LEGACY_ZERO_MM)
    want = _legacy_fp_f(fp_mm)
    assert got == pytest.approx(want, abs=1e-12)


def test_legacy_band_pays_full_at_exactly_the_40mm_eval_cliff():
    # The defect this bank guards against: at the exact gate boundary
    # the legacy band still pays 1.0, so nothing inside the reward
    # discourages sitting right at (or just past) the cliff.
    assert footprint_fade(40.0, LEGACY_FULL_MM, LEGACY_ZERO_MM) == 1.0
    assert footprint_fade(47.0, LEGACY_FULL_MM, LEGACY_ZERO_MM) \
        == pytest.approx(0.825, abs=1e-9)


def test_tightened_band_pays_zero_at_the_eval_cliff():
    # The fix: full=25, zero=40 -- the fade ENDS exactly at the 40mm
    # hard cliff, so anything the gate would fail already earns nothing
    # from this term, and full pay only holds inside a safety margin.
    full_mm, zero_mm = 25.0, 40.0
    assert footprint_fade(0.0, full_mm, zero_mm) == 1.0
    assert footprint_fade(25.0, full_mm, zero_mm) == 1.0
    assert footprint_fade(40.0, full_mm, zero_mm) == 0.0
    assert footprint_fade(47.0, full_mm, zero_mm) == 0.0
    # interior point: 32.5mm is halfway between 25 and 40 -> 0.5
    assert footprint_fade(32.5, full_mm, zero_mm) == pytest.approx(0.5)


def test_tightened_band_strictly_dominates_widening_past_the_cliff():
    # The exact misalignment this reprice removes: under the tightened
    # band, ANY point outside the 40mm gate earns less than ANY point
    # inside it -- widening past the cliff can never out-earn staying
    # inside, by construction.
    full_mm, zero_mm = 25.0, 40.0
    inside = [footprint_fade(v, full_mm, zero_mm)
              for v in (0.0, 10.0, 25.0, 39.9)]
    outside = [footprint_fade(v, full_mm, zero_mm)
               for v in (40.0, 40.1, 47.0, 60.0, 90.0)]
    assert min(inside) > max(outside)


def test_output_always_clamped_to_unit_interval():
    for fp_mm in (-1000.0, -1.0, 0.0, 1000.0):
        for full_mm, zero_mm in ((40.0, 80.0), (25.0, 40.0), (0.0, 1.0)):
            v = footprint_fade(fp_mm, full_mm, zero_mm)
            assert 0.0 <= v <= 1.0


def test_degenerate_zero_width_band_does_not_divide_by_zero():
    # zero_mm == full_mm would divide by zero in a naive implementation;
    # the function guards the denominator instead of raising/NaN-ing.
    v = footprint_fade(30.0, 30.0, 30.0)
    assert v in (0.0, 1.0)  # a hard step either way is fine; no NaN/inf
    import math
    assert math.isfinite(v)


def test_cfg_defaults_reproduce_legacy_endpoints_when_unset():
    # The cfg_get() call sites in sim_env use these exact keys/defaults;
    # pin the defaults here so a future cfg-plumbing refactor cannot
    # silently move the legacy band.
    cfg = {"reward": {}}
    full_mm = float(cfg_get(cfg, "reward", "rise_footprint_full_mm",
                             default=PLANT_SPEC["footprint_err_mm"]))
    zero_mm = float(cfg_get(cfg, "reward", "rise_footprint_zero_mm",
                             default=2.0 * PLANT_SPEC["footprint_err_mm"]))
    assert full_mm == LEGACY_FULL_MM
    assert zero_mm == LEGACY_ZERO_MM


def test_cfg_override_moves_the_band():
    cfg = {"reward": {"rise_footprint_full_mm": 25.0,
                       "rise_footprint_zero_mm": 40.0}}
    full_mm = float(cfg_get(cfg, "reward", "rise_footprint_full_mm",
                             default=PLANT_SPEC["footprint_err_mm"]))
    zero_mm = float(cfg_get(cfg, "reward", "rise_footprint_zero_mm",
                             default=2.0 * PLANT_SPEC["footprint_err_mm"]))
    assert (full_mm, zero_mm) == (25.0, 40.0)
    assert footprint_fade(40.0, full_mm, zero_mm) == 0.0
