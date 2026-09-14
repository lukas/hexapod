"""dr.latency_load_gain / dr.latency_load_group — dynamic, load-coupled
COMMAND LATENCY (2026-09-14, speed track: the joint_backlash_load_gain/
-group recipe's OTHER named untried dynamic-mechanism form, built after
the backlash right-side/intersection ladder plateaued at ~29-31% of the
PS200 16.78-deg roll signature — STATUS.md 2026-09-14 ~03:5x names
"load-coupled control-latency" as one of the two remaining untried
structurally-different mechanism families).

Contract under test (RESEARCH_RULES "Tests": fast, mechanics-only):
- default OFF ((0.0, 0.0) gain) is bit-exact: no rng consumed, model/env
  behavior identical to pre-change code;
- guarded draw: enabling the axis never shifts any earlier base draw
  (including joint_backlash's own gap draw, drawn just before it);
- ServoProfile.tick's load-coupled latency widens (never shrinks) the
  per-joint latency under load, capped, and is the identity (static
  latency) at gain 0 or load_nm=None;
- scaled(): the gain range shrinks toward nominal with s; the load
  reference constant and group name do not scale;
- dof_group_mask (the generalized form of backlash_group_mask) is
  reachable under its own param_name and reports latency_load_group in
  its error text, not joint_backlash_group;
- sim_env wiring: constructing the env with the axis enabled installs a
  nonzero er.latency_load_gain and a short rollout runs without error;
  disabled leaves it all-zero.
"""
import dataclasses

import numpy as np
import pytest

from rl_move.sim.domain_rand import (
    DEG2RAD, DomainRandomizer, EpisodeRandomization, N_LEGS, RandRanges,
    dof_group_mask,
)
from rl_move.sim.servo_model import (
    LATENCY_LOAD_FRAC_CAP, N_JOINTS, ServoProfile, SimServoParams,
)


def _params() -> SimServoParams:
    return SimServoParams.load()


# ------------------------------------------------------------- default off

def test_default_range_is_off():
    r = RandRanges()
    assert r.latency_load_gain == (0.0, 0.0)
    assert r.latency_load_group == ""


def test_default_off_sample_matches_backlash_golden():
    s = DomainRandomizer(RandRanges(), scale=1.0).sample(
        np.random.default_rng(7))
    # Same golden values test_domain_rand_joint_backlash.py pins for this
    # seed -- any drift here means the new guarded draw shifted the base
    # stream, including the joint_backlash draw just before it.
    assert round(s.mass_scale, 12) == 1.07390100843
    assert round(s.cmd_drop_prob, 12) == 0.034184218667
    assert np.all(s.latency_load_gain == 0.0)


def test_enabling_latency_load_never_shifts_base_or_backlash_draws():
    off = DomainRandomizer(RandRanges(
        joint_backlash_deg=(1.0, 6.0)), scale=1.0).sample(
        np.random.default_rng(11))
    on = DomainRandomizer(RandRanges(
        joint_backlash_deg=(1.0, 6.0),
        latency_load_gain=(0.5, 2.0)), scale=1.0).sample(
        np.random.default_rng(11))
    assert on.mass_scale == off.mass_scale
    assert np.array_equal(on.start_offset_rad, off.start_offset_rad)
    assert np.array_equal(on.joint_backlash_gap_rad, off.joint_backlash_gap_rad)
    assert on.joint_backlash_load_gain == off.joint_backlash_load_gain
    assert np.all(on.latency_load_gain >= 0.5 - 1e-9)
    assert np.all(on.latency_load_gain <= 2.0 + 1e-9)


# ------------------------------------------------------------- scaled()

def test_scaled_shrinks_ranges_toward_zero():
    r = RandRanges(latency_load_gain=(0.5, 2.0), latency_load_ref_nm=1.7,
                   latency_load_group="right")
    half = r.scaled(0.5)
    assert half.latency_load_gain == (0.25, 1.0)
    # Modeling constant / categorical name, not randomization ranges:
    # never scaled.
    assert half.latency_load_ref_nm == 1.7
    assert half.latency_load_group == "right"
    zero = r.scaled(0.0)
    assert zero.latency_load_gain == (0.0, 0.0)


# ------------------------------------------------------------- ServoProfile

def test_identity_at_zero_gain():
    q0 = np.zeros(N_JOINTS)
    p_off = ServoProfile(_params(), q0)
    p_on = ServoProfile(_params(), q0, latency_load_gain=np.zeros(N_JOINTS))
    p_off.command(np.full(N_JOINTS, 0.3))
    p_on.command(np.full(N_JOINTS, 0.3))
    for _ in range(20):
        a = p_off.tick(0.02)
        b = p_on.tick(0.02, load_nm=np.full(N_JOINTS, 5.0))
        assert np.allclose(a, b)


def test_load_coupled_latency_delays_motion_more_under_load():
    # Fitted latencies here are 8.6-29.7 ms (per_joint("latency_ms")); a
    # gain of 3 at >= ref load caps load_frac at LATENCY_LOAD_FRAC_CAP
    # (4.0), so effective latency -> latency_s * 13 (111.6-386.1 ms).
    q0 = np.zeros(N_JOINTS)
    gain = np.full(N_JOINTS, 3.0)
    p_noload = ServoProfile(_params(), q0, latency_load_gain=gain,
                             latency_load_ref_nm=1.0)
    p_noload.command(np.full(N_JOINTS, 0.3))
    moved_noload = False
    for _ in range(3):  # 60 ms > every base (unloaded) latency
        out = p_noload.tick(0.02, load_nm=np.zeros(N_JOINTS))
        if np.any(out != 0.0):
            moved_noload = True
            break
    p_loaded = ServoProfile(_params(), q0, latency_load_gain=gain,
                             latency_load_ref_nm=1.0)
    p_loaded.command(np.full(N_JOINTS, 0.3))
    moved_loaded = False
    for _ in range(4):  # 80 ms < every loaded (x13) latency (111.6 ms+)
        out = p_loaded.tick(0.02, load_nm=np.full(N_JOINTS, 50.0))
        if np.any(out != 0.0):
            moved_loaded = True
            break
    assert moved_noload
    assert not moved_loaded


def test_load_gain_capped():
    q0 = np.zeros(N_JOINTS)
    gain = np.full(N_JOINTS, 1.0)
    p_capped = ServoProfile(_params(), q0, latency_load_gain=gain,
                             latency_load_ref_nm=1.0)
    p_huge = ServoProfile(_params(), q0, latency_load_gain=gain,
                           latency_load_ref_nm=1.0)
    p_capped.command(np.full(N_JOINTS, 0.3))
    p_huge.command(np.full(N_JOINTS, 0.3))
    # At exactly the cap vs 1000x the cap, the effective latency (and
    # thus first-motion tick) must be identical -- the cap bites.
    cap_load = np.full(N_JOINTS, LATENCY_LOAD_FRAC_CAP)  # load_frac==CAP
    huge_load = np.full(N_JOINTS, LATENCY_LOAD_FRAC_CAP * 1000.0)
    seq_capped = [np.array(p_capped.tick(0.02, load_nm=cap_load))
                  for _ in range(10)]
    seq_huge = [np.array(p_huge.tick(0.02, load_nm=huge_load))
                for _ in range(10)]
    for a, b in zip(seq_capped, seq_huge):
        assert np.allclose(a, b)


def test_none_load_nm_keeps_static_latency_even_with_gain_set():
    q0 = np.zeros(N_JOINTS)
    gain = np.full(N_JOINTS, 5.0)
    p = ServoProfile(_params(), q0, latency_load_gain=gain,
                      latency_load_ref_nm=1.0)
    p.command(np.full(N_JOINTS, 0.3))
    p_static = ServoProfile(_params(), q0)
    p_static.command(np.full(N_JOINTS, 0.3))
    for _ in range(10):
        a = p.tick(0.02, load_nm=None)
        b = p_static.tick(0.02)
        assert np.allclose(a, b)


# ------------------------------------------------------- group (dof_group_mask)

def test_group_default_off_mask_all_true():
    assert np.all(dof_group_mask(""))


def test_group_reports_own_param_name_in_error():
    with pytest.raises(ValueError, match="latency_load_group"):
        dof_group_mask("bogus", param_name="latency_load_group")
    with pytest.raises(ValueError, match="joint_backlash_group"):
        dof_group_mask("bogus", param_name="joint_backlash_group")


def test_sample_masks_gain_to_named_group():
    plain = DomainRandomizer(RandRanges(
        latency_load_gain=(2.0, 5.0)), scale=1.0).sample(
        np.random.default_rng(5))
    grouped = DomainRandomizer(RandRanges(
        latency_load_gain=(2.0, 5.0), latency_load_group="left"),
        scale=1.0).sample(np.random.default_rng(5))
    mask = dof_group_mask("left")
    assert np.array_equal(
        grouped.latency_load_gain[mask], plain.latency_load_gain[mask])
    assert np.all(grouped.latency_load_gain[~mask] == 0.0)
    assert np.any(grouped.latency_load_gain[mask] > 0.0)


# ------------------------------------------------------------- env wiring

def test_env_wires_latency_load_when_enabled_and_rollout_runs():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = {"dr": {"latency_load_gain": "2.0,4.0",
                  "latency_load_group": "right"}}
    env = SimHexapodJointWalkEnv(cfg=cfg, randomize=True, dr_scale=1.0)
    env.reset(seed=0)
    mask = dof_group_mask("right")
    assert np.any(env._ep_rand.latency_load_gain[mask] > 0.0)
    assert np.all(env._ep_rand.latency_load_gain[~mask] == 0.0)
    a = np.zeros(env.n_act, dtype=np.float32)
    for _ in range(5):
        env.step(a)


def test_env_latency_load_zero_when_disabled():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    env = SimHexapodJointWalkEnv(cfg={}, randomize=True, dr_scale=1.0)
    env.reset(seed=0)
    assert np.all(env._ep_rand.latency_load_gain == 0.0)


def test_env_cfg_override_rejects_unknown_group_at_reset():
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = {"dr": {"latency_load_gain": "2.0,4.0",
                  "latency_load_group": "bogus"}}
    env = SimHexapodJointWalkEnv(cfg=cfg, randomize=True, dr_scale=1.0)
    with pytest.raises(ValueError):
        env.reset(seed=0)
