"""dr.link_len_bias_pct / dr.link_len_bias_group -- structured, CONCENTRATED
per-leg link-length bias (2026-09-17, speed track).

Background: DESIGN.md's mechanism inventory names "body/link mass, CoM
and inertia" and "link length and per-leg asymmetric manufacturing
error" as two SEPARATE families. The mass/inertia half was already
built+probed in concentrated form (``leg_mass_bias_pct``/-group,
09-14) and came back a clean NULL -- the mechanistic reason given was
that mass is a LOAD-domain perturbation this policy's position-
controlled (kp/kv) actuators absorb without the joint drifting off its
commanded angle. Link LENGTH is a different, POSITION/KINEMATIC-domain
defect: the policy's own IK still assumes NOMINAL segment lengths, so
a genuine length mismatch is a persistent geometric error the gait
carries forward every step -- the same domain that made joint backlash
the best-to-date (~29-31%) PS200 roll-signature match. Every existing
length knob (``link_len_scale_pct``/``link_len_leg_pct``) is symmetric
global or per-leg-independent jitter; this is the CONCENTRATED form
(one named leg group gets one persistent bias), modeling a real
build/assembly defect (a leg reprinted at the wrong scale, a servo horn
seated one spline off, a bent link from a fall) rather than random
per-leg noise.

Contract under test (RESEARCH_RULES "Tests": fast, mechanics-only):
- default OFF ((0.0, 0.0) pct) is bit-exact: no rng consumed relative
  to the pre-change stream, ``link_len_bias_scale`` stays all-ones;
- guarded draw (drawn LAST, after leg_mass_bias): enabling the axis
  never shifts any earlier draw, including leg_mass_bias's own;
- scaled(): the pct range shrinks toward nominal with s; the
  categorical group name does not;
- the draw is a SINGLE scalar magnitude (not independent per leg,
  unlike ``link_len_leg_pct``) -- every masked leg gets the exact
  same bias;
- ``leg_group_mask`` reuse: "" -> all-legs biased identically; named
  groups match ``dof_group_mask``'s leg-only masks; unknown/axis-only
  names raise with this param's own name in the message;
- ``apply_to_model`` wiring: enabling the axis multiplies the masked
  legs' coxa/femur/tibia attachment offset AND CoM shift (both, so the
  leg is genuinely longer/shorter, not just re-weighted) by the
  sampled bias, ON TOP OF (not instead of) the existing global/per-leg
  jitter; unmasked legs and the default-off path are untouched.
"""
import numpy as np
import pytest

from rl_move.sim.domain_rand import (
    DomainRandomizer, N_LEGS, RandRanges, leg_group_mask,
)


# ------------------------------------------------------------- default off

def test_default_range_is_off():
    r = RandRanges()
    assert r.link_len_bias_pct == (0.0, 0.0)
    assert r.link_len_bias_group == ""


def test_default_off_sample_matches_massbias_golden():
    s = DomainRandomizer(RandRanges(), scale=1.0).sample(
        np.random.default_rng(7))
    # Same golden values test_domain_rand_massbias.py pins for this
    # seed -- any drift here means the new guarded draw shifted the
    # base stream.
    assert round(s.mass_scale, 12) == 1.07390100843
    assert round(s.cmd_drop_prob, 12) == 0.034184218667
    assert np.all(s.leg_mass_bias_scale == 1.0)
    assert np.all(s.link_len_bias_scale == 1.0)
    assert s.link_len_bias_scale.shape == (N_LEGS,)


def test_enabling_linklenbias_never_shifts_earlier_draws_incl_massbias():
    off = DomainRandomizer(RandRanges(
        leg_mass_bias_pct=(0.1, 0.3), leg_mass_bias_group="right"),
        scale=1.0).sample(np.random.default_rng(11))
    on = DomainRandomizer(RandRanges(
        leg_mass_bias_pct=(0.1, 0.3), leg_mass_bias_group="right",
        link_len_bias_pct=(0.05, 0.2)), scale=1.0).sample(
        np.random.default_rng(11))
    assert on.mass_scale == off.mass_scale
    assert np.array_equal(on.start_offset_rad, off.start_offset_rad)
    assert np.array_equal(on.leg_mass_bias_scale, off.leg_mass_bias_scale)
    assert np.all(on.link_len_bias_scale >= 1.05 - 1e-9)
    assert np.all(on.link_len_bias_scale <= 1.2 + 1e-9)


def test_draw_is_a_single_shared_magnitude_not_independent_per_leg():
    s = DomainRandomizer(RandRanges(
        link_len_bias_pct=(0.05, 0.5)), scale=1.0).sample(
        np.random.default_rng(3))
    # Every leg gets the identical bias (unlike link_len_leg_pct, which
    # is independent per leg/segment).
    assert len(set(np.round(s.link_len_bias_scale, 9))) == 1


# ------------------------------------------------------------- scaled()

def test_scaled_shrinks_ranges_toward_zero():
    r = RandRanges(link_len_bias_pct=(0.2, 0.6), link_len_bias_group="right")
    half = r.scaled(0.5)
    assert half.link_len_bias_pct == (0.1, 0.3)
    # Categorical name, not a magnitude range: never scaled.
    assert half.link_len_bias_group == "right"
    zero = r.scaled(0.0)
    assert zero.link_len_bias_pct == (0.0, 0.0)


# ------------------------------------------------------------- group masking

def test_sample_masks_bias_to_named_group():
    plain = DomainRandomizer(RandRanges(
        link_len_bias_pct=(0.2, 0.5)), scale=1.0).sample(
        np.random.default_rng(5))
    grouped = DomainRandomizer(RandRanges(
        link_len_bias_pct=(0.2, 0.5), link_len_bias_group="left"),
        scale=1.0).sample(np.random.default_rng(5))
    mask = leg_group_mask("left")
    biased = grouped.link_len_bias_scale - 1.0
    plain_biased = plain.link_len_bias_scale - 1.0
    assert np.array_equal(biased[mask], plain_biased[mask])
    assert np.all(biased[~mask] == 0.0)
    assert np.any(biased[mask] > 0.0)


def test_unknown_group_raises_with_this_params_own_name():
    with pytest.raises(ValueError, match="link_len_bias_group"):
        DomainRandomizer(RandRanges(
            link_len_bias_pct=(0.2, 0.5), link_len_bias_group="bogus"),
            scale=1.0).sample(np.random.default_rng(1))
    with pytest.raises(ValueError, match="link_len_bias_group"):
        DomainRandomizer(RandRanges(
            link_len_bias_pct=(0.2, 0.5), link_len_bias_group="knee"),
            scale=1.0).sample(np.random.default_rng(1))


# ------------------------------------------------------------- apply_to_model wiring

def test_env_wires_linklenbias_when_enabled_and_touches_body_pos():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg_off = {"dr": {}}
    cfg_on = {"dr": {"link_len_bias_pct": "0.3,0.3",
                      "link_len_bias_group": "right"}}
    env_off = SimHexapodJointWalkEnv(cfg=cfg_off, randomize=True, dr_scale=1.0)
    env_off.reset(seed=0)
    pos_off = env_off.model.body_pos.copy()
    env_off.close()

    env_on = SimHexapodJointWalkEnv(cfg=cfg_on, randomize=True, dr_scale=1.0)
    env_on.reset(seed=0)
    pos_on = env_on.model.body_pos.copy()
    env_on.close()

    # The two models are not identical once the bias is armed (some
    # body's attachment offset moved).
    assert not np.array_equal(pos_off, pos_on)


def test_default_off_leaves_link_len_bias_untouched():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    # Same seed, dr_scale=0.0 isolates every OTHER axis at nominal;
    # link_len_bias_pct defaults to (0.0, 0.0) either way.
    env = SimHexapodJointWalkEnv(cfg={"dr": {}}, randomize=True,
                                  dr_scale=0.0, seed=0)
    env.reset(seed=0)
    assert np.all(env._ep_rand.link_len_bias_scale == 1.0)
    env.close()
