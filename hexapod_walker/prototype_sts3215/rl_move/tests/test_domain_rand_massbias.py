"""dr.leg_mass_bias_pct / dr.leg_mass_bias_group -- structured, CONCENTRATED
per-leg mass/inertia bias (2026-09-14, speed track).

Background: DR_JOINT_PANEL_2026-09-13's held-out training panel closed
6/6 (CTRL/WIDE/STRUCT/COMBO/ADAPT/BACKLASH-training, speed/STATUS.md
2026-09-14 ~12:0x). Of the frozen-policy diagnostic probes that
followed, joint backlash CONCENTRATED on one side (right leg group) is
the only mechanism to date that reproduces a genuine, monotonic SIGNED
roll bias (~29-31% of the 16.78-deg PS200 hardware signature) --
load-coupled latency and per-foot stick-slip were both clean NULLs.
Every prior mass/CoM/link-length mechanism in this codebase
(``mass_scale``/``leg_mass_jitter_pct``/``com_offset_m``/
``link_len_leg_pct``) is drawn SYMMETRICALLY and independently per
leg/link -- exactly the "uniform" shape that was NULL for backlash too.
This is the analogous CONCENTRATED form for the mass/CoM family named
in DESIGN.md's own mechanism inventory ("body/link mass, CoM and
inertia ... per-leg asymmetric manufacturing error") but never built:
a single persistent bias magnitude applied to one named leg group's
mass+inertia, modeling a real build asymmetry (battery/wiring routed
to one side, uneven print infill between left/right leg sets).

Contract under test (RESEARCH_RULES "Tests": fast, mechanics-only):
- default OFF ((0.0, 0.0) pct) is bit-exact: no rng consumed relative
  to the pre-change stream, ``leg_mass_bias_scale`` stays all-ones;
- guarded draw: enabling the axis never shifts any earlier base draw;
- scaled(): the pct range shrinks toward nominal with s; the
  categorical group name does not;
- the draw is a SINGLE scalar magnitude (not independent per leg,
  unlike ``leg_mass_jitter_pct``) -- every masked leg gets the exact
  same bias;
- ``leg_group_mask`` reuse: "" -> all-legs biased identically; named
  groups match ``dof_group_mask``'s leg-only masks; unknown/axis-only
  names raise with this param's own name in the message;
- ``apply_to_model`` wiring: enabling the axis multiplies
  ``body_mass``/``body_inertia`` on the masked legs' three bodies
  (yaw/femur/tibia) by the sampled bias, ON TOP OF (not instead of)
  the existing per-part jitter; unmasked legs and the default-off path
  are untouched.
"""
import numpy as np
import pytest

from rl_move.sim.domain_rand import (
    DomainRandomizer, N_LEGS, RandRanges, leg_group_mask,
)


# ------------------------------------------------------------- default off

def test_default_range_is_off():
    r = RandRanges()
    assert r.leg_mass_bias_pct == (0.0, 0.0)
    assert r.leg_mass_bias_group == ""


def test_default_off_sample_matches_stickslip_golden():
    s = DomainRandomizer(RandRanges(), scale=1.0).sample(
        np.random.default_rng(7))
    # Same golden values test_domain_rand_stickslip.py pins for this
    # seed -- any drift here means the new guarded draw shifted the
    # base stream.
    assert round(s.mass_scale, 12) == 1.07390100843
    assert round(s.cmd_drop_prob, 12) == 0.034184218667
    assert np.all(s.leg_mass_bias_scale == 1.0)
    assert s.leg_mass_bias_scale.shape == (N_LEGS,)


def test_enabling_massbias_never_shifts_base_or_stickslip_draws():
    off = DomainRandomizer(RandRanges(
        foot_stickslip_gain=(0.3, 1.5)), scale=1.0).sample(
        np.random.default_rng(11))
    on = DomainRandomizer(RandRanges(
        foot_stickslip_gain=(0.3, 1.5),
        leg_mass_bias_pct=(0.1, 0.3)), scale=1.0).sample(
        np.random.default_rng(11))
    assert on.mass_scale == off.mass_scale
    assert np.array_equal(on.start_offset_rad, off.start_offset_rad)
    assert np.array_equal(on.foot_stickslip_gain, off.foot_stickslip_gain)
    assert np.all(on.leg_mass_bias_scale >= 1.1 - 1e-9)
    assert np.all(on.leg_mass_bias_scale <= 1.3 + 1e-9)


def test_draw_is_a_single_shared_magnitude_not_independent_per_leg():
    s = DomainRandomizer(RandRanges(
        leg_mass_bias_pct=(0.05, 0.5)), scale=1.0).sample(
        np.random.default_rng(3))
    # Every leg gets the identical bias (unlike leg_mass_jitter_pct,
    # which is independent per leg/part).
    assert len(set(np.round(s.leg_mass_bias_scale, 9))) == 1


# ------------------------------------------------------------- scaled()

def test_scaled_shrinks_ranges_toward_zero():
    r = RandRanges(leg_mass_bias_pct=(0.2, 0.6), leg_mass_bias_group="right")
    half = r.scaled(0.5)
    assert half.leg_mass_bias_pct == (0.1, 0.3)
    # Categorical name, not a magnitude range: never scaled.
    assert half.leg_mass_bias_group == "right"
    zero = r.scaled(0.0)
    assert zero.leg_mass_bias_pct == (0.0, 0.0)


# ------------------------------------------------------------- group masking

def test_sample_masks_bias_to_named_group():
    plain = DomainRandomizer(RandRanges(
        leg_mass_bias_pct=(0.2, 0.5)), scale=1.0).sample(
        np.random.default_rng(5))
    grouped = DomainRandomizer(RandRanges(
        leg_mass_bias_pct=(0.2, 0.5), leg_mass_bias_group="left"),
        scale=1.0).sample(np.random.default_rng(5))
    mask = leg_group_mask("left")
    biased = grouped.leg_mass_bias_scale - 1.0
    plain_biased = plain.leg_mass_bias_scale - 1.0
    assert np.array_equal(biased[mask], plain_biased[mask])
    assert np.all(biased[~mask] == 0.0)
    assert np.any(biased[mask] > 0.0)


def test_unknown_group_raises_with_this_params_own_name():
    with pytest.raises(ValueError, match="leg_mass_bias_group"):
        DomainRandomizer(RandRanges(
            leg_mass_bias_pct=(0.2, 0.5), leg_mass_bias_group="bogus"),
            scale=1.0).sample(np.random.default_rng(1))
    with pytest.raises(ValueError, match="leg_mass_bias_group"):
        DomainRandomizer(RandRanges(
            leg_mass_bias_pct=(0.2, 0.5), leg_mass_bias_group="knee"),
            scale=1.0).sample(np.random.default_rng(1))


# ------------------------------------------------------------- apply_to_model wiring

def test_env_wires_massbias_when_enabled_and_touches_body_mass():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg_off = {"dr": {}}
    cfg_on = {"dr": {"leg_mass_bias_pct": "0.3,0.3",
                      "leg_mass_bias_group": "right"}}
    env_off = SimHexapodJointWalkEnv(cfg=cfg_off, randomize=True, dr_scale=1.0)
    env_off.reset(seed=0)
    mass_off = env_off.model.body_mass.copy()
    env_off.close()

    env_on = SimHexapodJointWalkEnv(cfg=cfg_on, randomize=True, dr_scale=1.0)
    env_on.reset(seed=0)
    mass_on = env_on.model.body_mass.copy()
    env_on.close()

    # The two models are not identical once the bias is armed (some
    # body's mass moved).
    assert not np.array_equal(mass_off, mass_on)


def test_default_off_leaves_body_mass_untouched_by_this_mechanism():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    # Same seed, dr_scale=0.0 isolates every OTHER axis at nominal;
    # leg_mass_bias_pct defaults to (0.0, 0.0) either way.
    env = SimHexapodJointWalkEnv(cfg={"dr": {}}, randomize=True,
                                  dr_scale=0.0, seed=0)
    env.reset(seed=0)
    assert np.all(env._ep_rand.leg_mass_bias_scale == 1.0)
    env.close()
