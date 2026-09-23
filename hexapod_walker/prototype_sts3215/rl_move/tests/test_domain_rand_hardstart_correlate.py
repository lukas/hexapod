"""dr.hard_start_correlate_frac -- correlated hard-start compound corner
(2026-09-23, standwalk track).

Background: ``bad_start_joints`` (a placement-slop joint way off) and
``tipped_start`` (episode begins already leaning) are drawn INDEPENDENTLY
in ``DomainRandomizer.sample`` -- so the compound "already tipped over AND
a joint is way off" corner is rare (product of two small per-episode
probabilities). This exact compound draw (tipped_roll_deg~=12.7,
bad_start_joints hitting a knee-axis joint) was root-caused this cycle as
the FIXED eval-seed case behind the dr=0.4 rise/hold/lower lower-phase
"severe-tip" outlier that reproduced BIT-IDENTICALLY (height_err_end_mm
25.4, same joint indices [10, 1]) across 3 independently-trained
checkpoints, after two prior reward-side levers (k_tilt_guard,
goal.lower_stage_gate) both failed to fix it -- evidence the combination
is under-sampled during training, not a reward-shape or contact-mechanism
defect.

Contract under test (RESEARCH_RULES "Tests": fast, mechanics-only):
- default OFF (0.0) is bit-exact: no rng consumed relative to the
  pre-change stream (same golden numbers test_domain_rand_footcatch.py
  pins for seed=7/scale=1.0);
- guarded: the extra draw only ever happens when EXACTLY ONE of
  {bad_start_joints, tipped_start} already triggered this episode (xor);
  if neither ever triggers (both base probs 0), frac has NO effect and
  consumes NO extra rng, regardless of its value;
- when armed (frac>0) and the xor condition holds, drawing < frac forces
  the OTHER axis too -- bad_start alone can gain a forced tip, tipped
  alone can gain a forced bad joint;
- frac follows the dr_scale curriculum via ``scaled()``, same convention
  as tipped_start_prob.
"""
import numpy as np

from rl_move.sim.domain_rand import DomainRandomizer, RandRanges


def test_default_is_off():
    assert RandRanges().hard_start_correlate_frac == 0.0


def test_default_off_sample_matches_prior_golden_bit_exact():
    s = DomainRandomizer(RandRanges(), scale=1.0).sample(
        np.random.default_rng(7))
    # Same golden numbers test_domain_rand_footcatch.py pins -- adding
    # hard_start_correlate_frac (default 0.0, guarded) must not shift them.
    assert round(s.mass_scale, 12) == 1.07390100843
    assert round(s.cmd_drop_prob, 12) == 0.034184218667
    assert s.bad_start_joints == []
    assert s.tipped_roll_deg == 0.0


def test_neither_base_axis_ever_triggers_frac_has_no_effect():
    # Both base probabilities 0 -> the xor guard is always False -> the
    # extra rng.random() is never called, so frac=1.0 vs frac=0.0 must
    # be bit-for-bit identical draws (including unrelated later fields).
    off = RandRanges(bad_start_prob=0.0, tipped_start_prob=0.0,
                      hard_start_correlate_frac=0.0)
    on = RandRanges(bad_start_prob=0.0, tipped_start_prob=0.0,
                     hard_start_correlate_frac=1.0)
    for seed in range(10):
        so = DomainRandomizer(off, scale=1.0).sample(
            np.random.default_rng(seed))
        sn = DomainRandomizer(on, scale=1.0).sample(
            np.random.default_rng(seed))
        assert so.mass_scale == sn.mass_scale
        assert so.friction_scale == sn.friction_scale
        assert so.bad_start_joints == [] == sn.bad_start_joints
        assert so.tipped_roll_deg == 0.0 == sn.tipped_roll_deg


def test_forces_tipped_when_only_bad_start_triggers():
    r = RandRanges(bad_start_prob=1.0, tipped_start_prob=0.0,
                    hard_start_correlate_frac=1.0)
    for seed in range(20):
        s = DomainRandomizer(r, scale=1.0).sample(np.random.default_rng(seed))
        assert s.bad_start_joints != []
        assert s.tipped_roll_deg != 0.0


def test_forces_bad_start_when_only_tipped_triggers():
    r = RandRanges(bad_start_prob=0.0, tipped_start_prob=1.0,
                    hard_start_correlate_frac=1.0)
    for seed in range(20):
        s = DomainRandomizer(r, scale=1.0).sample(np.random.default_rng(seed))
        assert s.tipped_roll_deg != 0.0
        assert s.bad_start_joints != []


def test_frac_zero_never_forces_even_when_one_axis_always_triggers():
    r = RandRanges(bad_start_prob=1.0, tipped_start_prob=0.0,
                    hard_start_correlate_frac=0.0)
    for seed in range(20):
        s = DomainRandomizer(r, scale=1.0).sample(np.random.default_rng(seed))
        assert s.tipped_roll_deg == 0.0


def test_scaled_probability_follows_curriculum():
    r = RandRanges(hard_start_correlate_frac=0.8).scaled(0.5)
    assert round(r.hard_start_correlate_frac, 6) == 0.4
    r0 = RandRanges(hard_start_correlate_frac=0.8).scaled(0.0)
    assert r0.hard_start_correlate_frac == 0.0
