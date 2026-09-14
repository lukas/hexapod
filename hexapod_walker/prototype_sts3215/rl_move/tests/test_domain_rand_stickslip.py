"""dr.foot_stickslip_gain / dr.foot_stickslip_group — per-foot Coulomb
stick-slip ground-contact friction (2026-09-14, speed track).

Background: the DR_JOINT_PANEL/speed saga's own next-step list named
TWO untried structurally-different dynamic-mechanism candidates after
the joint-backlash right-side/intersection ladder plateaued at ~29-31%
of the PS200 16.78-deg roll signature (STATUS.md ~03:5x): "load-coupled
control-latency" (built ~04:4x, a clean NULL -- no roll effect at any
dose, because this slow creep gait's trapezoidal profile always catches
up within the gait's own phase duration regardless of latency) and
"stick-slip/velocity-dependent ground contact" (this file/mechanism).
Unlike both prior candidates (actuator-chain mechanisms), this targets
the FOOT-GROUND CONTACT itself: MuJoCo's constant-coefficient friction
model does not express real rubber feet's static-exceeds-kinetic
Coulomb behavior at all.

Contract under test (RESEARCH_RULES "Tests": fast, mechanics-only):
- default OFF ((0.0, 0.0) gain) is bit-exact: no rng consumed relative
  to the pre-change stream, sim_env never touches geom_friction from
  the new per-tick hook;
- guarded draw: enabling the axis never shifts any earlier base draw;
- scaled(): the gain range shrinks toward nominal with s; the velocity
  reference constant and group name do not scale;
- ``stickslip_friction_mult``: 1+gain at zero sliding speed, ramps
  linearly to exactly 1.0 (pure baseline) at/above vel_ref_mps,
  vel_ref_mps<=0 degenerates to the SAFE (always-baseline) value;
- ``leg_group_mask``: "" -> all-true; named leg groups match
  ``dof_group_mask``'s own leg-only masks; axis-only / unknown names
  raise with the caller's own param_name in the message;
- sim_env wiring: enabling the axis installs a nonzero per-leg gain and
  a short rollout runs without error, DYNAMICALLY changing
  model.geom_friction on the foot rows tick-to-tick; disabled leaves
  geom_friction on the foot rows completely untouched by the new hook.
"""
import numpy as np
import pytest

from rl_move.sim.domain_rand import (
    DomainRandomizer, N_LEGS, RandRanges, leg_group_mask,
    stickslip_friction_mult,
)


# ------------------------------------------------------------- default off

def test_default_range_is_off():
    r = RandRanges()
    assert r.foot_stickslip_gain == (0.0, 0.0)
    assert r.foot_stickslip_group == ""
    assert r.foot_stickslip_vel_ref_mps == 0.02


def test_default_off_sample_matches_backlash_golden():
    s = DomainRandomizer(RandRanges(), scale=1.0).sample(
        np.random.default_rng(7))
    # Same golden values test_domain_rand_joint_backlash.py /
    # test_domain_rand_latency_load.py pin for this seed -- any drift
    # here means the new guarded draw shifted the base stream.
    assert round(s.mass_scale, 12) == 1.07390100843
    assert round(s.cmd_drop_prob, 12) == 0.034184218667
    assert np.all(s.foot_stickslip_gain == 0.0)
    assert s.foot_stickslip_vel_ref_mps == 0.02


def test_enabling_stickslip_never_shifts_base_or_latency_draws():
    off = DomainRandomizer(RandRanges(
        latency_load_gain=(0.5, 2.0)), scale=1.0).sample(
        np.random.default_rng(11))
    on = DomainRandomizer(RandRanges(
        latency_load_gain=(0.5, 2.0),
        foot_stickslip_gain=(0.3, 1.5)), scale=1.0).sample(
        np.random.default_rng(11))
    assert on.mass_scale == off.mass_scale
    assert np.array_equal(on.start_offset_rad, off.start_offset_rad)
    assert np.array_equal(on.latency_load_gain, off.latency_load_gain)
    assert np.all(on.foot_stickslip_gain >= 0.3 - 1e-9)
    assert np.all(on.foot_stickslip_gain <= 1.5 + 1e-9)


# ------------------------------------------------------------- scaled()

def test_scaled_shrinks_ranges_toward_zero():
    r = RandRanges(foot_stickslip_gain=(0.4, 2.0),
                    foot_stickslip_vel_ref_mps=0.05,
                    foot_stickslip_group="right")
    half = r.scaled(0.5)
    assert half.foot_stickslip_gain == (0.2, 1.0)
    # Modeling constant / categorical name, not randomization ranges:
    # never scaled.
    assert half.foot_stickslip_vel_ref_mps == 0.05
    assert half.foot_stickslip_group == "right"
    zero = r.scaled(0.0)
    assert zero.foot_stickslip_gain == (0.0, 0.0)


# ------------------------------------------------------- stickslip_friction_mult

def test_mult_is_one_plus_gain_at_zero_speed():
    assert stickslip_friction_mult(0.0, 0.02, 2.0) == pytest.approx(3.0)


def test_mult_decays_to_one_at_and_beyond_vel_ref():
    assert stickslip_friction_mult(0.02, 0.02, 2.0) == pytest.approx(1.0)
    assert stickslip_friction_mult(0.05, 0.02, 2.0) == pytest.approx(1.0)
    assert stickslip_friction_mult(1000.0, 0.02, 2.0) == pytest.approx(1.0)


def test_mult_ramps_linearly_between():
    # Half of vel_ref -> half the frac -> 1 + gain/2.
    assert stickslip_friction_mult(0.01, 0.02, 2.0) == pytest.approx(2.0)


def test_mult_vectorized_over_legs():
    speed = np.array([0.0, 0.01, 0.02, 0.05, 0.0, 0.02])
    gain = np.array([1.0, 1.0, 1.0, 1.0, 0.0, 3.0])
    out = stickslip_friction_mult(speed, 0.02, gain)
    assert out.shape == (N_LEGS,)
    assert out[0] == pytest.approx(2.0)
    assert out[2] == pytest.approx(1.0)
    assert out[4] == pytest.approx(1.0)   # zero gain -> always baseline
    assert out[5] == pytest.approx(1.0)   # at vel_ref regardless of gain


def test_mult_zero_or_negative_vel_ref_degenerates_to_safe_baseline():
    # Misconfiguration guard resolves toward the historical no-op (always
    # baseline), never a permanently-stuck extra boost.
    assert stickslip_friction_mult(0.0, 0.0, 5.0) == pytest.approx(1.0)
    assert stickslip_friction_mult(0.0, -1.0, 5.0) == pytest.approx(1.0)


# ------------------------------------------------------------- leg_group_mask

def test_leg_group_mask_default_all_true():
    assert np.all(leg_group_mask(""))
    assert leg_group_mask("").shape == (N_LEGS,)


def test_leg_group_mask_named_groups_match_leg_indices():
    right = leg_group_mask("right")
    assert np.array_equal(np.flatnonzero(right), [3, 4, 5])
    left = leg_group_mask("left")
    assert np.array_equal(np.flatnonzero(left), [0, 1, 2])
    leg2 = leg_group_mask("leg2")
    assert np.array_equal(np.flatnonzero(leg2), [2])


def test_leg_group_mask_rejects_axis_only_and_unknown_names():
    with pytest.raises(ValueError, match="foot_stickslip_group"):
        leg_group_mask("knee")
    with pytest.raises(ValueError, match="foot_stickslip_group"):
        leg_group_mask("bogus")
    with pytest.raises(ValueError, match="custom_param"):
        leg_group_mask("bogus", param_name="custom_param")
    with pytest.raises(ValueError):
        leg_group_mask("leg9")


def test_sample_masks_gain_to_named_group():
    plain = DomainRandomizer(RandRanges(
        foot_stickslip_gain=(2.0, 5.0)), scale=1.0).sample(
        np.random.default_rng(5))
    grouped = DomainRandomizer(RandRanges(
        foot_stickslip_gain=(2.0, 5.0), foot_stickslip_group="left"),
        scale=1.0).sample(np.random.default_rng(5))
    mask = leg_group_mask("left")
    assert np.array_equal(
        grouped.foot_stickslip_gain[mask], plain.foot_stickslip_gain[mask])
    assert np.all(grouped.foot_stickslip_gain[~mask] == 0.0)
    assert np.any(grouped.foot_stickslip_gain[mask] > 0.0)


# ------------------------------------------------------------- env wiring

def test_env_wires_stickslip_when_enabled_and_friction_moves_dynamically():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = {"dr": {"foot_stickslip_gain": "2.0,4.0",
                  "foot_stickslip_group": "right"}}
    env = SimHexapodJointWalkEnv(cfg=cfg, randomize=True, dr_scale=1.0)
    env.reset(seed=0)
    mask = leg_group_mask("right")
    assert np.any(env._ep_rand.foot_stickslip_gain[mask] > 0.0)
    assert np.all(env._ep_rand.foot_stickslip_gain[~mask] == 0.0)
    assert env._stickslip_active is True
    base = env._stickslip_base_mu.copy()
    a = np.zeros(env.n_act, dtype=np.float32)
    seen = set()
    for _ in range(20):
        env.step(a)
        seen.add(tuple(np.round(
            env.model.geom_friction[env._stickslip_foot_gids, 0], 6)))
    # The right-leg rows must have moved off the static baseline at
    # least once over the rollout (left legs, gain 0, never move).
    assert len(seen) > 1
    right_idx = np.flatnonzero(mask)
    moved_right = any(
        not np.allclose(np.array(row)[right_idx], base[right_idx])
        for row in seen)
    assert moved_right
    left_idx = np.flatnonzero(~mask)
    for row in seen:
        assert np.allclose(np.array(row)[left_idx], base[left_idx])


def test_env_stickslip_inactive_and_friction_untouched_when_disabled():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    env = SimHexapodJointWalkEnv(cfg={}, randomize=True, dr_scale=1.0)
    env.reset(seed=0)
    assert np.all(env._ep_rand.foot_stickslip_gain == 0.0)
    assert env._stickslip_active is False
    base = env.model.geom_friction[env._stickslip_foot_gids, 0].copy()
    a = np.zeros(env.n_act, dtype=np.float32)
    for _ in range(10):
        env.step(a)
    after = env.model.geom_friction[env._stickslip_foot_gids, 0].copy()
    assert np.array_equal(base, after)


def test_env_cfg_override_rejects_unknown_group_at_reset():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = {"dr": {"foot_stickslip_gain": "2.0,4.0",
                  "foot_stickslip_group": "bogus"}}
    env = SimHexapodJointWalkEnv(cfg=cfg, randomize=True, dr_scale=1.0)
    with pytest.raises(ValueError):
        env.reset(seed=0)
