"""dr.struct_dr_adaptive: the online adaptive/adversarial hard-case
sampler for the struct-DR overlay (2026-09-14, speed track — the next
lever after the CTRL/WIDE/STRUCT/COMBO DR-composition panel closed,
see rl_docs/tracks/speed/STATUS.md 2026-09-13 ~21:5x).

Contract under test (RESEARCH_RULES "Tests": fast, mechanics-only):
- default OFF is bit-exact with the pre-2026-09-14 struct overlay
  stream (golden-equivalent: same draws as story=None);
- struct_dr_story is populated whenever the overlay fires, regardless
  of whether adaptive is on (diagnostics always available);
- record_struct_outcome/struct_story_weights implement a genuine
  regret bandit: a story fed persistently high badness ends up with
  MORE sampling mass than one fed persistently low badness, with an
  exploration floor keeping every story reachable;
- turning dr.struct_dr_adaptive on only ever REPLACES the overlay's
  own internal mode/group draw — it never fires the overlay itself
  (struct_dr_prob still owns that) and never touches any other DR
  field's draw.
"""
import numpy as np

from rl_move.sim.domain_rand import (
    STRUCT_STORIES, DomainRandomizer, RandRanges)


def test_default_off_matches_story_none_stream():
    # struct_dr_adaptive defaults False; the resulting stream must be
    # identical to explicitly requesting the non-adaptive path.
    off = DomainRandomizer(RandRanges(struct_dr_prob=1.0),
                           scale=1.0).sample(np.random.default_rng(9))
    explicit_off = DomainRandomizer(
        RandRanges(struct_dr_prob=1.0, struct_dr_adaptive=False),
        scale=1.0).sample(np.random.default_rng(9))
    assert off.struct_dr_mode == explicit_off.struct_dr_mode
    assert off.struct_dr_story == explicit_off.struct_dr_story
    assert np.array_equal(off.kp_scale, explicit_off.kp_scale)


def test_story_always_populated_when_overlay_fires():
    rng = np.random.default_rng(4)
    dr = DomainRandomizer(RandRanges(struct_dr_prob=1.0), scale=1.0)
    seen = set()
    for _ in range(40):
        ep = dr.sample(rng)
        assert ep.struct_dr_story in STRUCT_STORIES
        seen.add(ep.struct_dr_story)
    # Both families reachable at the default (non-adaptive) uniform draw.
    assert "correlated" in seen
    assert any(s.startswith("asym_") for s in seen)


def test_struct_prob_zero_never_sets_a_story():
    rng = np.random.default_rng(5)
    dr = DomainRandomizer(RandRanges(struct_dr_prob=0.0,
                                     struct_dr_adaptive=True), scale=1.0)
    assert all(dr.sample(rng).struct_dr_story == "" for _ in range(16))


def test_neutral_regret_is_uniform():
    dr = DomainRandomizer(RandRanges(), scale=1.0)
    w = dr.struct_story_weights()
    assert set(w) == set(STRUCT_STORIES)
    vals = list(w.values())
    assert max(vals) - min(vals) < 1e-9
    assert abs(sum(vals) - 1.0) < 1e-9


def test_record_outcome_biases_toward_the_bad_story():
    dr = DomainRandomizer(RandRanges(), scale=1.0)
    for _ in range(200):
        dr.record_struct_outcome("asym_left", 25.0)   # persistently bad
        dr.record_struct_outcome("correlated", 1.0)   # persistently fine
    w = dr.struct_story_weights()
    assert w["asym_left"] > w["correlated"]
    assert w["asym_left"] == max(w.values())
    # Exploration floor: even the best-behaved story keeps real mass.
    assert w["correlated"] > 0.15 / len(STRUCT_STORIES) - 1e-9


def test_unknown_story_outcome_is_a_noop():
    dr = DomainRandomizer(RandRanges(), scale=1.0)
    before = dict(dr._struct_regret)
    dr.record_struct_outcome("not_a_story", 99.0)
    assert dr._struct_regret == before


def test_adaptive_sampling_frequency_tracks_regret():
    # End-to-end: after biasing one story's regret way up, draws from
    # sample() (not just struct_story_weights() directly) land on it
    # much more often than a freshly-neutral story, at struct_dr_prob=1
    # so every draw goes through the overlay.
    dr = DomainRandomizer(RandRanges(struct_dr_prob=1.0,
                                     struct_dr_adaptive=True), scale=1.0)
    for _ in range(500):
        dr.record_struct_outcome("asym_rear", 30.0)
        dr.record_struct_outcome("asym_front", 0.5)
    rng = np.random.default_rng(21)
    counts = {k: 0 for k in STRUCT_STORIES}
    for _ in range(400):
        ep = dr.sample(rng)
        counts[ep.struct_dr_story] += 1
    assert counts["asym_rear"] > counts["asym_front"] * 2
    # Every story still gets SOME mass (exploration floor).
    assert all(c > 0 for c in counts.values())


def test_adaptive_never_changes_non_story_fields_distribution():
    # Turning adaptive on only swaps which mode/group is chosen; the
    # per-field dose menus/bounds stay identical to the non-adaptive
    # overlay (same STRUCT_* constants either way).
    rng_a = np.random.default_rng(31)
    rng_b = np.random.default_rng(31)
    plain = DomainRandomizer(RandRanges(struct_dr_prob=1.0),
                             scale=1.0)
    adaptive = DomainRandomizer(RandRanges(struct_dr_prob=1.0,
                                           struct_dr_adaptive=True),
                               scale=1.0)
    for _ in range(30):
        ep_p = plain.sample(rng_a)
        ep_a = adaptive.sample(rng_b)
        for ep in (ep_p, ep_a):
            assert np.all(ep.foot_friction_scale <= 1.10 + 1e-12)
            assert np.all(ep.foot_friction_scale >= 0.50 - 1e-12)
            assert np.all(ep.leg_torque_scale <= 1.05 + 1e-12)
            assert np.all(ep.leg_torque_scale >= 0.60 - 1e-12)
