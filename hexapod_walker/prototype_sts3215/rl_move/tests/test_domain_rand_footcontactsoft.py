"""dr.foot_contact_soft_pct / dr.foot_contact_soft_group -- structured,
CONCENTRATED per-foot contact compliance (2026-09-20, speed track).

Background (rl_docs/tracks/speed/STATUS.md 09-20; `rl_docs/
HEXAPOD2_DIGITAL_TWIN_2026-09-12.md`): DESIGN.md's mechanism inventory
names "ground and per-foot friction/compliance" but every prior probe in
this saga only ever exercised FRICTION (foot_friction_scale) or a
GLOBAL, uniform solref timeconst multiplier applied to every geom alike
(contact_stiff_scale -- ground and feet together). The digital-twin
replay study separately built and REJECTED a chassis/leg-ROOT flex
mechanism (leg_mount_flex): it moves the PS200 hardware-vs-sim roll gap
the WRONG direction and invents roll in negative controls, so it stays
closed. Foot-level contact softening -- a worn/soft pad, or a squashed
print -- was never dosed by that study or this saga; it is a genuinely
different, per-FOOT-concentrated persistent defect.

Contract under test (RESEARCH_RULES "Tests": fast, mechanics-only):
- default OFF ((0.0, 0.0) pct) is bit-exact: no rng consumed relative
  to the pre-change stream, ``foot_contact_soft_scale`` stays all-ones;
- guarded draw (drawn LAST): enabling the axis never shifts any earlier
  draw, including link_len_bias's own;
- scaled(): the pct range shrinks toward nominal with s; the
  categorical group name does not;
- the draw is a SINGLE scalar magnitude (not independent per leg) --
  every masked leg gets the exact same softening;
- ``leg_group_mask`` reuse: "" -> all-feet softened identically; named
  groups match the leg-only masks; unknown/axis-only names raise with
  this param's own name in the message;
- ``apply_to_model`` wiring: enabling the axis multiplies ONLY the
  masked legs' named foot geom's solref timeconst (index 0), leaving
  the ground/terrain geoms and every other geom's solref untouched,
  ON TOP OF (not instead of) the existing global contact_stiff_scale;
  unmasked legs and the default-off path are untouched.
"""
import numpy as np
import pytest

from rl_move.sim.domain_rand import (
    DomainRandomizer, N_LEGS, RandRanges, leg_group_mask,
)


# ------------------------------------------------------------- default off

def test_default_range_is_off():
    r = RandRanges()
    assert r.foot_contact_soft_pct == (0.0, 0.0)
    assert r.foot_contact_soft_group == ""


def test_default_off_sample_matches_linklenbias_golden():
    s = DomainRandomizer(RandRanges(), scale=1.0).sample(
        np.random.default_rng(7))
    # Same golden values test_domain_rand_linklenbias.py pins for this
    # seed -- any drift here means the new guarded draw shifted the
    # base stream.
    assert round(s.mass_scale, 12) == 1.07390100843
    assert round(s.cmd_drop_prob, 12) == 0.034184218667
    assert np.all(s.link_len_bias_scale == 1.0)
    assert np.all(s.foot_contact_soft_scale == 1.0)
    assert s.foot_contact_soft_scale.shape == (N_LEGS,)


def test_enabling_footcontactsoft_never_shifts_earlier_draws_incl_linklenbias():
    off = DomainRandomizer(RandRanges(
        link_len_bias_pct=(0.1, 0.3), link_len_bias_group="right"),
        scale=1.0).sample(np.random.default_rng(11))
    on = DomainRandomizer(RandRanges(
        link_len_bias_pct=(0.1, 0.3), link_len_bias_group="right",
        foot_contact_soft_pct=(0.05, 0.2)), scale=1.0).sample(
        np.random.default_rng(11))
    assert on.mass_scale == off.mass_scale
    assert np.array_equal(on.start_offset_rad, off.start_offset_rad)
    assert np.array_equal(on.link_len_bias_scale, off.link_len_bias_scale)
    assert np.all(on.foot_contact_soft_scale >= 1.05 - 1e-9)
    assert np.all(on.foot_contact_soft_scale <= 1.2 + 1e-9)


def test_draw_is_a_single_shared_magnitude_not_independent_per_leg():
    s = DomainRandomizer(RandRanges(
        foot_contact_soft_pct=(0.05, 0.5)), scale=1.0).sample(
        np.random.default_rng(3))
    assert len(set(np.round(s.foot_contact_soft_scale, 9))) == 1


# ------------------------------------------------------------- scaled()

def test_scaled_shrinks_ranges_toward_zero():
    r = RandRanges(foot_contact_soft_pct=(0.2, 0.6),
                    foot_contact_soft_group="right")
    half = r.scaled(0.5)
    assert half.foot_contact_soft_pct == (0.1, 0.3)
    # Categorical name, not a magnitude range: never scaled.
    assert half.foot_contact_soft_group == "right"
    zero = r.scaled(0.0)
    assert zero.foot_contact_soft_pct == (0.0, 0.0)


# ------------------------------------------------------------- group masking

def test_sample_masks_soft_to_named_group():
    plain = DomainRandomizer(RandRanges(
        foot_contact_soft_pct=(0.2, 0.5)), scale=1.0).sample(
        np.random.default_rng(5))
    grouped = DomainRandomizer(RandRanges(
        foot_contact_soft_pct=(0.2, 0.5), foot_contact_soft_group="left"),
        scale=1.0).sample(np.random.default_rng(5))
    mask = leg_group_mask("left")
    soft = grouped.foot_contact_soft_scale - 1.0
    plain_soft = plain.foot_contact_soft_scale - 1.0
    assert np.array_equal(soft[mask], plain_soft[mask])
    assert np.all(soft[~mask] == 0.0)
    assert np.any(soft[mask] > 0.0)


def test_unknown_group_raises_with_this_params_own_name():
    with pytest.raises(ValueError, match="foot_contact_soft_group"):
        DomainRandomizer(RandRanges(
            foot_contact_soft_pct=(0.2, 0.5), foot_contact_soft_group="bogus"),
            scale=1.0).sample(np.random.default_rng(1))
    with pytest.raises(ValueError, match="foot_contact_soft_group"):
        DomainRandomizer(RandRanges(
            foot_contact_soft_pct=(0.2, 0.5), foot_contact_soft_group="knee"),
            scale=1.0).sample(np.random.default_rng(1))


# ------------------------------------------------------------- apply_to_model wiring

def test_env_wires_footcontactsoft_when_enabled_and_touches_only_feet():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg_off = {"dr": {}}
    cfg_on = {"dr": {"foot_contact_soft_pct": "0.5,0.5",
                      "foot_contact_soft_group": "right"}}
    env_off = SimHexapodJointWalkEnv(cfg=cfg_off, randomize=True, dr_scale=1.0)
    env_off.reset(seed=0)
    solref_off = env_off.model.geom_solref.copy()
    env_off.close()

    env_on = SimHexapodJointWalkEnv(cfg=cfg_on, randomize=True, dr_scale=1.0)
    env_on.reset(seed=0)
    solref_on = env_on.model.geom_solref.copy()
    model = env_on.model
    env_on.close()

    import mujoco
    changed = False
    for i in range(N_LEGS):
        gname = f"L{i}_foot"
        gid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, gname)
        if leg_group_mask("right")[i]:
            if not np.isclose(solref_off[gid, 0], solref_on[gid, 0]):
                changed = True
        else:
            assert np.isclose(solref_off[gid, 0], solref_on[gid, 0]), (
                f"unmasked leg {i} foot solref changed")
    assert changed, "no right-leg foot solref moved"
    # Ground/terrain untouched relative to the off run.
    for gname in ("floor", "terrain"):
        gid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, gname)
        if gid >= 0:
            assert np.isclose(solref_off[gid, 0], solref_on[gid, 0])


def test_default_off_leaves_foot_contact_soft_untouched():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    env = SimHexapodJointWalkEnv(cfg={"dr": {}}, randomize=True,
                                  dr_scale=0.0, seed=0)
    env.reset(seed=0)
    assert np.all(env._ep_rand.foot_contact_soft_scale == 1.0)
    env.close()
