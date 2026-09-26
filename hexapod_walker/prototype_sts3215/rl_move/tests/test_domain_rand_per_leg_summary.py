"""Per-leg DR summary fields (standwalk STATUS Next#1(b), 2026-09-26):
`EpisodeRandomization.summary()` used to collapse the whole robot's
sampled joint_zero_bias/link_scale into ONE min/max number
(`zero_bias_max_deg`, `link_scale_range`), so no consumer could ask
"which leg got the worst geometric draw this episode" -- the exact
question the walkable/unwalkable draw classifier needs answered before
it can correlate a leg's sampled bias/link-scale against whether THAT
leg ends up in the episode's `sacrificed_legs`. This adds two purely
additive per-leg fields; every existing key is unchanged.
"""
from __future__ import annotations

import numpy as np

from rl_move.sim.domain_rand import DomainRandomizer, N_LEGS, RandRanges


def test_per_leg_fields_present_and_shaped():
    r = RandRanges(joint_zero_bias_deg=3.0, link_len_leg_pct=0.05,
                   link_len_scale_pct=0.0)
    er = DomainRandomizer(r).sample(np.random.default_rng(0))
    s = er.summary()
    assert len(s["joint_zero_bias_deg_per_leg"]) == N_LEGS
    assert len(s["link_scale_per_leg"]) == N_LEGS
    # whole-robot max must equal the max of the per-leg breakdown
    assert max(s["joint_zero_bias_deg_per_leg"]) == s["zero_bias_max_deg"]
    lo, hi = s["link_scale_range"]
    assert lo <= min(s["link_scale_per_leg"])
    assert hi >= max(s["link_scale_per_leg"])


def test_per_leg_fields_off_at_zero_range():
    """Zero bias/link range -> every per-leg entry is exactly 0.0/1.0,
    not just the pre-existing whole-robot summary fields."""
    r = RandRanges(joint_zero_bias_deg=0.0, link_len_leg_pct=0.0,
                   link_len_scale_pct=0.0)
    er = DomainRandomizer(r).sample(np.random.default_rng(0))
    s = er.summary()
    assert s["joint_zero_bias_deg_per_leg"] == [0.0] * N_LEGS
    assert s["link_scale_per_leg"] == [1.0] * N_LEGS


def test_summary_still_deterministic_by_seed():
    """Unchanged pre-existing contract (test_fault_injection.py's
    s1.summary() == s2.summary() pattern): same seed -> byte-identical
    summary dict INCLUDING the two new per-leg keys."""
    r = RandRanges()
    s1 = DomainRandomizer(r).sample(np.random.default_rng(11)).summary()
    s2 = DomainRandomizer(r).sample(np.random.default_rng(11)).summary()
    assert s1 == s2
