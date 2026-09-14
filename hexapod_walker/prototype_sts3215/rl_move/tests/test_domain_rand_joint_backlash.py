"""dr.joint_backlash_deg / dr.joint_backlash_load_gain — dynamic,
load-coupled joint backlash (2026-09-14, speed track: DR_JOINT_PANEL_
2026-09-13's own escalation after CTRL/WIDE/STRUCT/COMBO/ADAPT closed the
whole bounded-STATIC-parameter family 0/5 against the PS200 16.78-deg
roll signature — "very likely a DYNAMIC, load-coupled mechanism ...
that the simulator's parametric families do not express").

Contract under test (RESEARCH_RULES "Tests": fast, mechanics-only):
- default OFF ((0.0, 0.0) gap) is bit-exact: no rng consumed, model/env
  behavior identical to pre-change code;
- guarded draw: enabling the axis never shifts any earlier base draw;
- JointBacklash.apply is the textbook backlash (play) nonlinearity —
  identity at gap=0, holds inside the half-gap, releases past it, and
  the load-coupling widens (never shrinks) the gap, capped;
- scaled(): the gap/load-gain ranges shrink toward nominal with s; the
  load reference constant does not scale;
- sim_env wiring: constructing the env with the axis enabled installs a
  JointBacklash and a short rollout runs without error; disabled leaves
  ``env._backlash`` None with zero extra state.
"""
import dataclasses

import numpy as np
import pytest

from rl_move.sim.domain_rand import (
    DEG2RAD, JOINT_BACKLASH_LOAD_CAP, DomainRandomizer, EpisodeRandomization,
    JointBacklash, N_LEGS, RandRanges)
from rl_move.sim.servo_model import N_JOINTS


def _neutral_ep(**kw) -> EpisodeRandomization:
    base = DomainRandomizer(RandRanges(), scale=0.0).sample(
        np.random.default_rng(0))
    return dataclasses.replace(base, **kw)


# ------------------------------------------------------------- default off

def test_default_range_is_off():
    r = RandRanges()
    assert r.joint_backlash_deg == (0.0, 0.0)
    assert r.joint_backlash_load_gain == (0.0, 0.0)


def test_default_off_sample_matches_golden_and_zero_gap():
    s = DomainRandomizer(RandRanges(), scale=1.0).sample(
        np.random.default_rng(7))
    # Same golden values test_dr_struct_plumbing.py pins for this seed —
    # any drift here means the new guarded draw shifted the base stream.
    assert round(s.mass_scale, 12) == 1.07390100843
    assert round(s.cmd_drop_prob, 12) == 0.034184218667
    assert np.all(s.joint_backlash_gap_rad == 0.0)
    assert s.joint_backlash_load_gain == 0.0


def test_enabling_backlash_never_shifts_base_draws():
    off = DomainRandomizer(RandRanges(), scale=1.0).sample(
        np.random.default_rng(11))
    on = DomainRandomizer(RandRanges(
        joint_backlash_deg=(1.0, 6.0),
        joint_backlash_load_gain=(0.0, 1.5)), scale=1.0).sample(
        np.random.default_rng(11))
    assert on.mass_scale == off.mass_scale
    assert np.array_equal(on.start_offset_rad, off.start_offset_rad)
    assert np.array_equal(on.imu_mount_rot, off.imu_mount_rot)
    assert on.ext_push_peak_n == off.ext_push_peak_n
    assert np.all(on.foot_friction_scale == off.foot_friction_scale)
    assert np.all(on.joint_backlash_gap_rad >= DEG2RAD * 1.0 - 1e-9)
    assert np.all(on.joint_backlash_gap_rad <= DEG2RAD * 6.0 + 1e-9)


def test_load_gain_zero_range_stays_zero_no_extra_draw():
    # gap on, load_gain range (0,0): guarded sub-draw must not fire.
    on_a = DomainRandomizer(RandRanges(
        joint_backlash_deg=(1.0, 6.0)), scale=1.0).sample(
        np.random.default_rng(3))
    on_b = DomainRandomizer(RandRanges(
        joint_backlash_deg=(1.0, 6.0)), scale=1.0).sample(
        np.random.default_rng(3))
    assert on_a.joint_backlash_load_gain == 0.0
    assert np.array_equal(on_a.joint_backlash_gap_rad,
                          on_b.joint_backlash_gap_rad)


# ------------------------------------------------------------- scaled()

def test_scaled_shrinks_ranges_toward_zero():
    r = RandRanges(joint_backlash_deg=(2.0, 8.0),
                   joint_backlash_load_gain=(0.5, 2.0),
                   joint_backlash_load_ref_nm=1.7)
    half = r.scaled(0.5)
    assert half.joint_backlash_deg == (1.0, 4.0)
    assert half.joint_backlash_load_gain == (0.25, 1.0)
    # Modeling constant, not a randomization range: never scaled.
    assert half.joint_backlash_load_ref_nm == 1.7
    zero = r.scaled(0.0)
    assert zero.joint_backlash_deg == (0.0, 0.0)


# ------------------------------------------------------------- JointBacklash

def test_identity_at_zero_gap():
    jb = JointBacklash(np.zeros(N_JOINTS))
    jb.reset(np.zeros(N_JOINTS))
    target = np.linspace(-0.2, 0.2, N_JOINTS)
    out = jb.apply(target)
    assert np.allclose(out, target)


def test_holds_inside_half_gap_then_releases():
    gap = 0.10  # rad, one joint only
    g = np.zeros(N_JOINTS)
    g[0] = gap
    jb = JointBacklash(g)
    jb.reset(np.zeros(N_JOINTS))
    inside = np.zeros(N_JOINTS)
    inside[0] = 0.04  # < half-gap (0.05)
    out1 = jb.apply(inside)
    assert out1[0] == pytest.approx(0.0)
    past = np.zeros(N_JOINTS)
    past[0] = 0.20
    out2 = jb.apply(past)
    assert out2[0] == pytest.approx(0.20 - 0.05)
    # Reversal: must re-take-up the OTHER half-gap before moving again.
    small_back = np.zeros(N_JOINTS)
    small_back[0] = 0.20 - 0.05 - 0.03  # inside the reversed half-gap
    out3 = jb.apply(small_back)
    assert out3[0] == pytest.approx(out2[0])  # still held
    far_back = np.zeros(N_JOINTS)
    far_back[0] = 0.0
    out4 = jb.apply(far_back)
    assert out4[0] == pytest.approx(0.0 + 0.05)  # released the other way


def test_load_gain_widens_gap_and_is_capped():
    gap = 0.10
    g = np.full(N_JOINTS, gap)
    jb_noload = JointBacklash(g, load_gain=0.0)
    jb_noload.reset(np.zeros(N_JOINTS))
    jb_loaded = JointBacklash(g, load_gain=1.0, load_ref_nm=1.0)
    jb_loaded.reset(np.zeros(N_JOINTS))
    target = np.full(N_JOINTS, 0.5)
    load = np.full(N_JOINTS, 1.0)  # exactly load_ref -> gain doubles gap
    out_noload = jb_noload.apply(target, load)
    out_loaded = jb_loaded.apply(target, load)
    # Loaded joint holds back MORE (bigger effective half-gap) than an
    # identical unloaded joint given the same commanded target.
    assert out_loaded[0] < out_noload[0]
    assert out_noload[0] == pytest.approx(0.5 - gap / 2)
    assert out_loaded[0] == pytest.approx(0.5 - gap)  # gain=1 at ref load
    # Cap: an enormous load never blows the gap past load_gain*CAP.
    jb_huge = JointBacklash(g, load_gain=1.0, load_ref_nm=1.0)
    jb_huge.reset(np.zeros(N_JOINTS))
    huge_load = np.full(N_JOINTS, 1000.0)
    out_capped = jb_huge.apply(target, huge_load)
    max_half = gap * (1.0 + 1.0 * JOINT_BACKLASH_LOAD_CAP) / 2.0
    assert out_capped[0] == pytest.approx(0.5 - max_half)


def test_apply_requires_reset_or_auto_inits_from_first_target():
    jb = JointBacklash(np.full(N_JOINTS, 0.1))
    first = np.full(N_JOINTS, 0.3)
    out = jb.apply(first)  # no explicit reset()
    assert np.allclose(out, first)


# ------------------------------------------------------------- env wiring

def test_env_wires_backlash_when_enabled_and_rollout_runs():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = {"dr": {"joint_backlash_deg": "3.0,6.0",
                  "joint_backlash_load_gain": "0.5,1.0"}}
    env = SimHexapodJointWalkEnv(cfg=cfg, randomize=True, dr_scale=1.0)
    env.reset(seed=0)
    assert env._backlash is not None
    a = np.zeros(env.n_act, dtype=np.float32)
    for _ in range(5):
        env.step(a)


def test_env_backlash_none_when_disabled():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    env = SimHexapodJointWalkEnv(cfg={}, randomize=True, dr_scale=1.0)
    env.reset(seed=0)
    assert env._backlash is None


# ------------------------------------------------------- group (asymmetric)
# dr.joint_backlash_group (2026-09-14): concentrate the dose on a named
# subset of joints instead of independently across all 18 -- the panel's
# own hard-region correlation study names per-joint/per-leg HETEROGENEITY,
# not global scale, as the strongest roll driver, so this is the
# untried-asymmetric form of the SAME already-built mechanism.

from rl_move.sim.domain_rand import BACKLASH_GROUPS, backlash_group_mask


def test_default_group_is_off_and_mask_all_true():
    assert RandRanges().joint_backlash_group == ""
    assert np.all(backlash_group_mask(""))


def test_leg_group_masks_exactly_three_joints_per_leg():
    for name, legs in (("left", (0, 1, 2)), ("right", (3, 4, 5)),
                       ("front", (0, 5)), ("rear", (2, 3))):
        mask = backlash_group_mask(name)
        expect = np.zeros(N_JOINTS, dtype=bool)
        for leg in legs:
            expect[3 * leg:3 * leg + 3] = True
        assert np.array_equal(mask, expect), name


def test_single_leg_group_masks_exactly_that_legs_three_joints():
    mask = backlash_group_mask("leg4")
    assert mask.sum() == 3
    assert np.all(mask[12:15])
    assert not np.any(mask[:12])
    assert not np.any(mask[15:])


def test_axis_group_masks_every_leg_same_axis():
    for name, axis in (("yaw", 0), ("pitch", 1), ("knee", 2)):
        mask = backlash_group_mask(name)
        assert mask.sum() == N_LEGS
        assert np.all(np.where(mask)[0] % 3 == axis)


def test_unknown_group_raises():
    with pytest.raises(ValueError):
        backlash_group_mask("nope")
    with pytest.raises(ValueError):
        backlash_group_mask("leg9")


def test_all_named_groups_are_registered_and_valid():
    for name in BACKLASH_GROUPS:
        mask = backlash_group_mask(name)
        assert mask.dtype == bool
        assert mask.any()


# ------------------------------------------------- compound leg+axis group
# "leg_group+axis_group" (2026-09-14, asymmetric-probe follow-up): the
# per-side backlash probe's own named next escalation -- intersect a leg
# group with an axis group to concentrate the dose onto FEWER joints per
# leg (e.g. "right+knee" = only the knee of the 3 right legs, 3 of 18
# joints) instead of all 3 axes of the side ("right" alone = 9 joints).

def test_compound_group_intersects_leg_and_axis():
    mask = backlash_group_mask("right+knee")
    assert mask.sum() == 3
    expect = backlash_group_mask("right") & backlash_group_mask("knee")
    assert np.array_equal(mask, expect)
    assert np.all(np.where(mask)[0] % 3 == 2)
    assert np.all(np.where(mask)[0] // 3 == np.array([3, 4, 5]))


def test_compound_group_single_leg_plus_axis():
    mask = backlash_group_mask("leg0+pitch")
    assert mask.sum() == 1
    assert mask[1]  # leg0's pitch joint is index 1 (3*0 + 1)


def test_compound_group_unknown_parts_raise():
    with pytest.raises(ValueError):
        backlash_group_mask("bogus+knee")
    with pytest.raises(ValueError):
        backlash_group_mask("right+bogus")
    with pytest.raises(ValueError):
        backlash_group_mask("right+knee+extra")


def test_compound_group_cfg_override_string_passthrough():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = {"dr": {"joint_backlash_deg": "4.0,8.0",
                  "joint_backlash_group": "right+pitch"}}
    env = SimHexapodJointWalkEnv(cfg=cfg, randomize=True, dr_scale=1.0)
    assert env.randomizer.ranges.joint_backlash_group == "right+pitch"
    env.reset(seed=0)  # must not raise: "+" compound resolves at reset too


def test_group_mask_is_bit_exact_noop_when_unset():
    # Empty group must leave the per-joint draw byte-identical to the
    # pre-2026-09-14 behavior for the SAME rng stream.
    off = DomainRandomizer(RandRanges(
        joint_backlash_deg=(2.0, 5.0)), scale=1.0).sample(
        np.random.default_rng(3))
    on = DomainRandomizer(RandRanges(
        joint_backlash_deg=(2.0, 5.0), joint_backlash_group=""),
        scale=1.0).sample(np.random.default_rng(3))
    assert np.array_equal(off.joint_backlash_gap_rad, on.joint_backlash_gap_rad)


def test_group_zeroes_gap_outside_named_joints_same_stream():
    plain = DomainRandomizer(RandRanges(
        joint_backlash_deg=(2.0, 5.0)), scale=1.0).sample(
        np.random.default_rng(5))
    grouped = DomainRandomizer(RandRanges(
        joint_backlash_deg=(2.0, 5.0), joint_backlash_group="leg2"),
        scale=1.0).sample(np.random.default_rng(5))
    # Same rng stream (mask applied post-draw, no extra consumption): the
    # IN-group joints match the ungrouped draw exactly; out-of-group are
    # forced to zero.
    mask = backlash_group_mask("leg2")
    assert np.array_equal(
        grouped.joint_backlash_gap_rad[mask], plain.joint_backlash_gap_rad[mask])
    assert np.all(grouped.joint_backlash_gap_rad[~mask] == 0.0)
    assert np.any(grouped.joint_backlash_gap_rad[mask] > 0.0)


def test_scaled_passes_group_through_unscaled():
    r = RandRanges(joint_backlash_group="right").scaled(0.3)
    assert r.joint_backlash_group == "right"


def test_cfg_override_passes_group_string_through_unparsed():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = {"dr": {"joint_backlash_deg": "4.0,8.0",
                  "joint_backlash_group": "leg3"}}
    env = SimHexapodJointWalkEnv(cfg=cfg, randomize=True, dr_scale=1.0)
    assert env.randomizer.ranges.joint_backlash_group == "leg3"
    # A comma-bearing NUMERIC override on a different field must still
    # parse to a tuple exactly as before (regression guard on the fix).
    assert env.randomizer.ranges.joint_backlash_deg == (4.0, 8.0)


def test_cfg_override_rejects_unknown_group_at_reset():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = {"dr": {"joint_backlash_deg": "4.0,8.0",
                  "joint_backlash_group": "bogus"}}
    env = SimHexapodJointWalkEnv(cfg=cfg, randomize=True, dr_scale=1.0)
    with pytest.raises(ValueError):
        env.reset(seed=0)


def test_env_wires_grouped_backlash_and_rollout_runs():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = {"dr": {"joint_backlash_deg": "4.0,8.0",
                  "joint_backlash_group": "right"}}
    env = SimHexapodJointWalkEnv(cfg=cfg, randomize=True, dr_scale=1.0)
    env.reset(seed=0)
    assert env._backlash is not None
    mask = backlash_group_mask("right")
    assert np.all(env._backlash.gap_rad[~mask] == 0.0)
    assert np.any(env._backlash.gap_rad[mask] > 0.0)
    a = np.zeros(env.n_act, dtype=np.float32)
    for _ in range(5):
        env.step(a)
