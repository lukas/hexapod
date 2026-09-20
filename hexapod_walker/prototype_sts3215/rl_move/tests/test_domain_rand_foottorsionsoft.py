"""dr.foot_torsion_soft_pct / dr.foot_torsion_soft_group -- structured,
CONCENTRATED per-foot torsional/rolling-friction reduction (2026-09-20,
speed track).

Background: MuJoCo's foot pad geom is condim=6 (full torsional +
rolling friction), but the existing ``foot_friction_scale`` axis only
ever touches ``geom_friction[:, 0]`` (SLIDING). A worn/rounded pad or a
bearing that lets a planted foot twist more freely under yaw reaction is
a physically distinct defect from sliding grip, and was never dosed by
any prior probe in this saga.

Contract under test (RESEARCH_RULES "Tests": fast, mechanics-only):
- default OFF ((0.0, 0.0) pct) is bit-exact: no rng consumed relative
  to the pre-change stream, ``foot_torsion_soft_scale`` stays all-ones;
- guarded draw (drawn LAST): enabling the axis never shifts any earlier
  draw, including foot_contact_soft's own;
- scaled(): the pct range shrinks toward nominal with s; the
  categorical group name does not;
- the draw is a SINGLE scalar magnitude (not independent per leg) --
  every masked leg gets the exact same reduction;
- unlike every prior "bias"/"soft" field, the dose is a DECREASE
  (``1 - magnitude``, floored at 0), never an increase;
- ``leg_group_mask`` reuse: "" -> all-feet softened identically; named
  groups match the leg-only masks; unknown/axis-only names raise with
  this param's own name in the message;
- ``apply_to_model`` wiring: enabling the axis multiplies ONLY the
  masked legs' named foot geom's torsional+rolling friction (indices 1
  and 2), leaving sliding friction (index 0) and every other geom
  untouched; unmasked legs and the default-off path are untouched.
"""
import numpy as np
import pytest

from rl_move.sim.domain_rand import (
    DomainRandomizer, N_LEGS, RandRanges, leg_group_mask,
)


def test_default_range_is_off():
    r = RandRanges()
    assert r.foot_torsion_soft_pct == (0.0, 0.0)
    assert r.foot_torsion_soft_group == ""


def test_default_off_sample_matches_footcontactsoft_golden():
    s = DomainRandomizer(RandRanges(), scale=1.0).sample(
        np.random.default_rng(7))
    assert round(s.mass_scale, 12) == 1.07390100843
    assert round(s.cmd_drop_prob, 12) == 0.034184218667
    assert np.all(s.foot_contact_soft_scale == 1.0)
    assert np.all(s.foot_torsion_soft_scale == 1.0)
    assert s.foot_torsion_soft_scale.shape == (N_LEGS,)


def test_enabling_foottorsionsoft_never_shifts_earlier_draws_incl_contactsoft():
    off = DomainRandomizer(RandRanges(
        foot_contact_soft_pct=(0.1, 0.3), foot_contact_soft_group="right"),
        scale=1.0).sample(np.random.default_rng(11))
    on = DomainRandomizer(RandRanges(
        foot_contact_soft_pct=(0.1, 0.3), foot_contact_soft_group="right",
        foot_torsion_soft_pct=(0.05, 0.2)), scale=1.0).sample(
        np.random.default_rng(11))
    assert on.mass_scale == off.mass_scale
    assert np.array_equal(on.start_offset_rad, off.start_offset_rad)
    assert np.array_equal(on.foot_contact_soft_scale, off.foot_contact_soft_scale)
    assert np.all(on.foot_torsion_soft_scale <= 0.95 + 1e-9)
    assert np.all(on.foot_torsion_soft_scale >= 0.8 - 1e-9)


def test_dose_is_a_decrease_not_an_increase():
    s = DomainRandomizer(RandRanges(
        foot_torsion_soft_pct=(0.5, 0.5)), scale=1.0).sample(
        np.random.default_rng(3))
    assert np.allclose(s.foot_torsion_soft_scale, 0.5)


def test_dose_floors_at_zero_not_negative():
    s = DomainRandomizer(RandRanges(
        foot_torsion_soft_pct=(1.5, 1.5)), scale=1.0).sample(
        np.random.default_rng(3))
    assert np.all(s.foot_torsion_soft_scale == 0.0)


def test_scaled_shrinks_ranges_toward_zero():
    r = RandRanges(foot_torsion_soft_pct=(0.2, 0.6),
                    foot_torsion_soft_group="right")
    half = r.scaled(0.5)
    assert half.foot_torsion_soft_pct == (0.1, 0.3)
    assert half.foot_torsion_soft_group == "right"
    zero = r.scaled(0.0)
    assert zero.foot_torsion_soft_pct == (0.0, 0.0)


def test_sample_masks_soft_to_named_group():
    plain = DomainRandomizer(RandRanges(
        foot_torsion_soft_pct=(0.2, 0.5)), scale=1.0).sample(
        np.random.default_rng(5))
    grouped = DomainRandomizer(RandRanges(
        foot_torsion_soft_pct=(0.2, 0.5), foot_torsion_soft_group="left"),
        scale=1.0).sample(np.random.default_rng(5))
    mask = leg_group_mask("left")
    assert np.array_equal(grouped.foot_torsion_soft_scale[mask],
                           plain.foot_torsion_soft_scale[mask])
    assert np.all(grouped.foot_torsion_soft_scale[~mask] == 1.0)
    assert np.any(grouped.foot_torsion_soft_scale[mask] < 1.0)


def test_unknown_group_raises_with_this_params_own_name():
    with pytest.raises(ValueError, match="foot_torsion_soft_group"):
        DomainRandomizer(RandRanges(
            foot_torsion_soft_pct=(0.2, 0.5), foot_torsion_soft_group="bogus"),
            scale=1.0).sample(np.random.default_rng(1))
    with pytest.raises(ValueError, match="foot_torsion_soft_group"):
        DomainRandomizer(RandRanges(
            foot_torsion_soft_pct=(0.2, 0.5), foot_torsion_soft_group="knee"),
            scale=1.0).sample(np.random.default_rng(1))


def test_env_wires_foottorsionsoft_when_enabled_and_touches_only_torsion():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg_off = {"dr": {}}
    cfg_on = {"dr": {"foot_torsion_soft_pct": "0.6,0.6",
                      "foot_torsion_soft_group": "right"}}
    env_off = SimHexapodJointWalkEnv(cfg=cfg_off, randomize=True, dr_scale=1.0)
    env_off.reset(seed=0)
    fric_off = env_off.model.geom_friction.copy()
    env_off.close()

    env_on = SimHexapodJointWalkEnv(cfg=cfg_on, randomize=True, dr_scale=1.0)
    env_on.reset(seed=0)
    fric_on = env_on.model.geom_friction.copy()
    model = env_on.model
    env_on.close()

    import mujoco
    changed = False
    for i in range(N_LEGS):
        gid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, f"L{i}_foot")
        # Sliding friction (index 0) untouched by this axis.
        assert np.isclose(fric_off[gid, 0], fric_on[gid, 0])
        if leg_group_mask("right")[i]:
            if not np.isclose(fric_off[gid, 1], fric_on[gid, 1]):
                changed = True
                assert fric_on[gid, 1] < fric_off[gid, 1]
                assert fric_on[gid, 2] < fric_off[gid, 2]
        else:
            assert np.isclose(fric_off[gid, 1], fric_on[gid, 1])
            assert np.isclose(fric_off[gid, 2], fric_on[gid, 2])
    assert changed, "no right-leg foot torsional friction moved"


def test_default_off_leaves_foot_torsion_soft_untouched():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    env = SimHexapodJointWalkEnv(cfg={"dr": {}}, randomize=True,
                                  dr_scale=0.0, seed=0)
    env.reset(seed=0)
    assert np.all(env._ep_rand.foot_torsion_soft_scale == 1.0)
    env.close()
