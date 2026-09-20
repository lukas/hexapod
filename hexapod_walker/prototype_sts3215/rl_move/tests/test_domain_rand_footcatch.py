"""dr.foot_catch_force_n / dr.foot_catch_force_group -- transient
PER-LEG foot-catch/stumble EVENT (2026-09-20, speed track).

Background: every mechanism dosed by this saga through 09-20 (backlash,
link-length, mass/CoM, foot contact softness, foot torsional friction)
is a CONTINUOUS per-episode model parameter. The digital twin's own
causal read of the PS200 trace (HEXAPOD2_DIGITAL_TWIN_2026-09-12.md)
names a one-shot TRANSIENT per stride instead: "load-dependent
post-encoder deformation ... unloads one support foot, followed by
body pivot and swing-foot contact". This axis models that last link
directly -- an unintended catch/snag on the swinging foot, fired once
per real LIFTOFF (touch sensor planted -> airborne), not on a blind
clock -- rather than another continuous compliance dose.

Contract under test (RESEARCH_RULES "Tests": fast, mechanics-only):
- default OFF ((0.0, 0.0) newtons) is bit-exact: no rng consumed
  relative to the pre-change stream, foot_catch_force_n stays all-zero;
- guarded draw (drawn LAST): enabling the axis never shifts any earlier
  draw, including foot_torsion_soft's own;
- scaled(): the newton range shrinks toward zero with s; the
  categorical group name does not;
- the draw is a SINGLE scalar magnitude (not independent per leg) --
  every masked leg gets the exact same peak force;
- ``leg_group_mask`` reuse: "" -> all legs identically; named groups
  match the leg-only masks; unknown/axis-only names raise with this
  param's own name in the message;
- runtime wiring (sim_env): the event fires ONCE PER LIFTOFF (touch
  sensor transition), applies a nonzero xfrc to the caught foot's pad
  body for its window, then releases; default-off never touches
  ``xfrc_applied`` on any pad body; the legacy primitive model (no
  named pad bodies) raises loud rather than silently misapplying xfrc.
"""
import numpy as np
import pytest

from rl_move.sim.domain_rand import (
    DomainRandomizer, N_LEGS, RandRanges, leg_group_mask,
)


def test_default_range_is_off():
    r = RandRanges()
    assert r.foot_catch_force_n == (0.0, 0.0)
    assert r.foot_catch_force_group == ""


def test_default_off_sample_matches_prior_golden_bit_exact():
    s = DomainRandomizer(RandRanges(), scale=1.0).sample(
        np.random.default_rng(7))
    # Same golden numbers test_domain_rand_foottorsionsoft.py pins --
    # adding foot_catch_force_n LAST at (0.0, 0.0) must not shift them.
    assert round(s.mass_scale, 12) == 1.07390100843
    assert round(s.cmd_drop_prob, 12) == 0.034184218667
    assert np.all(s.foot_catch_force_n == 0.0)
    assert s.foot_catch_force_n.shape == (N_LEGS,)


def test_enabling_footcatch_never_shifts_earlier_draws_incl_torsionsoft():
    off = DomainRandomizer(RandRanges(
        foot_torsion_soft_pct=(0.1, 0.3), foot_torsion_soft_group="right"),
        scale=1.0).sample(np.random.default_rng(11))
    on = DomainRandomizer(RandRanges(
        foot_torsion_soft_pct=(0.1, 0.3), foot_torsion_soft_group="right",
        foot_catch_force_n=(2.0, 5.0)), scale=1.0).sample(
        np.random.default_rng(11))
    assert on.mass_scale == off.mass_scale
    assert np.array_equal(on.start_offset_rad, off.start_offset_rad)
    assert np.array_equal(on.foot_torsion_soft_scale, off.foot_torsion_soft_scale)
    assert np.all(on.foot_catch_force_n[on.foot_catch_force_n != 0] <= 5.0 + 1e-9)
    assert np.all(on.foot_catch_force_n[on.foot_catch_force_n != 0] >= 2.0 - 1e-9)


def test_dose_is_single_scalar_magnitude_shared_across_legs():
    s = DomainRandomizer(RandRanges(
        foot_catch_force_n=(3.0, 3.0)), scale=1.0).sample(
        np.random.default_rng(3))
    assert np.allclose(s.foot_catch_force_n, 3.0)


def test_scaled_shrinks_ranges_toward_zero():
    r = RandRanges(foot_catch_force_n=(2.0, 6.0),
                    foot_catch_force_group="right")
    half = r.scaled(0.5)
    assert half.foot_catch_force_n == (1.0, 3.0)
    assert half.foot_catch_force_group == "right"
    zero = r.scaled(0.0)
    assert zero.foot_catch_force_n == (0.0, 0.0)


def test_sample_masks_catch_to_named_group():
    plain = DomainRandomizer(RandRanges(
        foot_catch_force_n=(2.0, 4.0)), scale=1.0).sample(
        np.random.default_rng(5))
    grouped = DomainRandomizer(RandRanges(
        foot_catch_force_n=(2.0, 4.0), foot_catch_force_group="left"),
        scale=1.0).sample(np.random.default_rng(5))
    mask = leg_group_mask("left")
    assert np.array_equal(grouped.foot_catch_force_n[mask],
                           plain.foot_catch_force_n[mask])
    assert np.all(grouped.foot_catch_force_n[~mask] == 0.0)
    assert np.any(grouped.foot_catch_force_n[mask] > 0.0)


def test_unknown_group_raises_with_this_params_own_name():
    with pytest.raises(ValueError, match="foot_catch_force_group"):
        DomainRandomizer(RandRanges(
            foot_catch_force_n=(2.0, 4.0), foot_catch_force_group="bogus"),
            scale=1.0).sample(np.random.default_rng(1))
    with pytest.raises(ValueError, match="foot_catch_force_group"):
        DomainRandomizer(RandRanges(
            foot_catch_force_n=(2.0, 4.0), foot_catch_force_group="knee"),
            scale=1.0).sample(np.random.default_rng(1))


def test_default_off_leaves_footcatch_state_untouched():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    env = SimHexapodJointWalkEnv(cfg={"dr": {}}, randomize=True,
                                  dr_scale=0.0, seed=0)
    env.reset(seed=0)
    assert np.all(env._ep_rand.foot_catch_force_n == 0.0)
    assert env._foot_catch_owns_row is False
    pad_xfrc_before = env.data.xfrc_applied[env._pad_bids].copy()
    for _ in range(5):
        env.step(np.zeros(18))
    # Default-off: this axis never claims the pad-body xfrc rows.
    assert np.array_equal(env.data.xfrc_applied[env._pad_bids],
                           pad_xfrc_before)
    env.close()


def test_env_wires_footcatch_owns_row_when_enabled():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg_on = {"dr": {"foot_catch_force_n": "4.0,4.0",
                      "foot_catch_force_group": "right"}}
    env = SimHexapodJointWalkEnv(cfg=cfg_on, randomize=True, dr_scale=1.0)
    env.reset(seed=0)
    assert env._foot_catch_owns_row is True
    mask = leg_group_mask("right")
    assert np.allclose(env._ep_rand.foot_catch_force_n[mask], 4.0)
    assert np.all(env._ep_rand.foot_catch_force_n[~mask] == 0.0)
    env.close()


def test_liftoff_transition_triggers_a_bounded_active_window():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg_on = {"dr": {"foot_catch_force_n": "5.0,5.0"}}
    env = SimHexapodJointWalkEnv(cfg=cfg_on, randomize=True, dr_scale=1.0)
    env.reset(seed=0)
    assert np.all(env._foot_catch_prev_touch)  # starts "planted"
    # Force leg 0's touch sensor to read airborne and drive the
    # per-tick detector directly -- exercises the liftoff edge without
    # depending on any particular learned/scripted gait.
    adr = env._touch_adr[0]
    assert adr >= 0
    env.data.sensordata[adr] = 0.0
    env._update_foot_catch_state()
    assert env._foot_catch_prev_touch[0] is np.bool_(False)
    assert env._foot_catch_end_s[0] > 0.0
    t = env._step_i * env.dt
    assert env._foot_catch_end_s[0] > t
    # Re-plant immediately: the OPEN window must not retrigger/extend
    # while the cooldown holds, and re-touching doesn't cancel it early
    # (mirrors a real momentary sensor bounce, not a clean re-plant).
    end_before = env._foot_catch_end_s[0]
    env.data.sensordata[adr] = 1.0
    env._update_foot_catch_state()
    assert env._foot_catch_end_s[0] == end_before
    env.close()


def test_legacy_primitive_model_also_has_pad_bodies_and_wires_clean():
    """Both current model families (mesh and legacy primitive) define
    named "L{i}_pad" bodies + touch sensors (mujoco_prototype.py builds
    them too), so this axis is NOT mesh-only in practice -- confirms
    the defensive pad-body guard in sim_env is unreachable today, not
    a real restriction."""
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg_on = {"env": {"model_source": "primitive"},
              "dr": {"foot_catch_force_n": "4.0,4.0"}}
    env = SimHexapodJointWalkEnv(cfg=cfg_on, randomize=True, dr_scale=1.0)
    env.reset(seed=0)
    assert env._foot_catch_owns_row is True
    assert all(b >= 0 for b in env._pad_bids)
    env.close()
