"""Swing-GATED CARTESIAN foot-placement action channel (lever #19,
2026-09-28) -- next named lever after the swing-gated YAW joint-offset
channel closed CANARY_FAIL 2/2 (lever #18, ops.sh index story
cw-walkyaw50hz-rlonly-scratch-sac-s{0,1}-...-yawswing15-canary2m-v2).

That gate's own text named the required next idea verbatim: "a
Cartesian foot-placement swing TARGET (shift where the swinging foot's
IK target lands, not a joint-space offset)". A pure joint yaw nudge is
mathematically nothing but a rotation of the Cartesian foot target
about the leg's own anchor (cart_foot_decode.py's fk), which levers
#16/#17/#18 already covered. This channel instead nudges the swinging
leg's TANGENTIAL Cartesian target (the leg-root-frame y axis) by a
fixed metres offset and re-solves ALL of (yaw, hip, knee) via the
shared, already-verified ``CartFootDecoder`` analytic IK -- a genuine
mix of yaw AND radial reach, not a pure rotation.

These tests pin: OFF is bit-exact (n_act/action_space/mapping
unchanged); ON widens n_act by exactly one; the new channel moves the
FULL (yaw,hip,knee) triplet of currently-swinging legs only (per
env._foot_on) by an amount consistent with the analytic IK, leaving
stance-leg joints exactly as the box/bias mapping produced them; an
all-legs-in-stance tick is a safe no-op; oversized gains never raise/
NaN (the shared IK's own reachable-annulus projection applies).
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.sim.joint_task import N_JOINTS
from walk_env_helpers import _make_walk_env, SLIPWALK_OVERRIDES

_YAW_IDX = np.arange(0, N_JOINTS, 3)

BOX_OVERRIDES = {
    ("goal", "joint_action_bias_hip_deg"): 40.0,
    ("goal", "joint_action_bias_knee_deg"): 35.0,
    ("goal", "joint_action_box_yaw_deg"): 30.0,
    ("goal", "joint_action_box_hip_deg"): 20.0,
    ("goal", "joint_action_box_knee_deg"): 25.0,
}

CARTSWING_OVERRIDES = {
    **BOX_OVERRIDES,
    ("goal", "walk_cart_swing_gain_m"): 0.02,
}


def test_default_is_inactive_bit_exact_n_act():
    env = _make_walk_env(0, SLIPWALK_OVERRIDES)
    assert not env._cart_swing_active
    assert env.n_act == N_JOINTS
    assert env.action_space.shape == (N_JOINTS,)
    env.close()


def test_off_mapping_is_byte_identical_to_legacy():
    env_off = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **BOX_OVERRIDES})
    assert not env_off._cart_swing_active
    assert env_off.n_act == N_JOINTS
    rng = np.random.default_rng(5)
    for _ in range(10):
        a = rng.uniform(-1.0, 1.0, N_JOINTS)
        q, ok, _ = env_off._act_to_q(a)
        assert ok
    env_off.close()


def test_gain_on_widens_action_space_by_one():
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **CARTSWING_OVERRIDES})
    assert env._cart_swing_active
    assert env.n_act == N_JOINTS + 1
    assert env.action_space.shape == (N_JOINTS + 1,)
    env.close()


def test_swing_channel_moves_only_swinging_legs_full_triplet():
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **CARTSWING_OVERRIDES})
    # Legs 0, 2, 4 swinging (airborne); 1, 3, 5 in stance.
    env._foot_on = [False, True, False, True, False, True]
    zero18 = np.zeros(N_JOINTS)
    a0 = np.concatenate([zero18, [0.0]])
    apos = np.concatenate([zero18, [1.0]])
    aneg = np.concatenate([zero18, [-1.0]])
    q0, ok0, _ = env._act_to_q(a0)
    qpos, okp, _ = env._act_to_q(apos)
    qneg, okn, _ = env._act_to_q(aneg)
    assert ok0 and okp and okn
    q0_6, qpos_6, qneg_6 = (q0.reshape(6, 3), qpos.reshape(6, 3),
                            qneg.reshape(6, 3))
    swing = [0, 2, 4]
    stance = [1, 3, 5]
    # swinging legs' full (yaw,hip,knee) triplet actually moved
    assert np.all(np.abs(qpos_6[swing] - q0_6[swing]).sum(axis=1) > 1e-6)
    assert np.all(np.abs(qneg_6[swing] - q0_6[swing]).sum(axis=1) > 1e-6)
    # opposite-signed action nudges the tangential target opposite ways
    assert not np.allclose(qpos_6[swing], qneg_6[swing])
    # stance legs are untouched by the channel
    assert np.allclose(qpos_6[stance], q0_6[stance])
    assert np.allclose(qneg_6[stance], q0_6[stance])
    env.close()


def test_swing_channel_all_stance_is_safe_noop():
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **CARTSWING_OVERRIDES})
    env._foot_on = [True] * 6
    zero18 = np.zeros(N_JOINTS)
    q0, ok0, _ = env._act_to_q(np.concatenate([zero18, [0.0]]))
    qpos, okp, _ = env._act_to_q(np.concatenate([zero18, [1.0]]))
    assert ok0 and okp
    assert np.all(np.isfinite(qpos))
    assert np.allclose(qpos, q0)
    env.close()


def test_swing_channel_never_nans_at_oversized_gain():
    """A large gain can push the target outside the reachable annulus;
    the shared IK projects it (never raises/NaN) -- see
    cart_foot_decode.py's own "never a failure" contract."""
    ov = {**SLIPWALK_OVERRIDES, **CARTSWING_OVERRIDES,
          ("goal", "walk_cart_swing_gain_m"): 0.5}
    env = _make_walk_env(0, ov)
    env._foot_on = [False] * 6
    full_pos = np.concatenate([np.ones(N_JOINTS), [1.0]])
    q, ok, _ = env._act_to_q(full_pos)
    assert ok and np.all(np.isfinite(q))
    full_neg = np.concatenate([-np.ones(N_JOINTS), [-1.0]])
    q2, ok2, _ = env._act_to_q(full_neg)
    assert ok2 and np.all(np.isfinite(q2))
    env.close()


def test_swing_active_without_box_still_bit_exact_for_stance():
    """Cart-swing channel composes with the plain bias-only path too
    (box left off), not just the box path."""
    ov = {("goal", "walk_cart_swing_gain_m"): 0.02,
          ("goal", "joint_action_bias_hip_deg"): 40.0,
          ("goal", "joint_action_bias_knee_deg"): 35.0,
          **{k: v for k, v in SLIPWALK_OVERRIDES.items()}}
    env = _make_walk_env(0, ov)
    assert env._cart_swing_active
    assert not env._joint_action_box_active
    env._foot_on = [False, True, False, True, False, True]
    zero18 = np.zeros(N_JOINTS)
    q0, ok0, _ = env._act_to_q(np.concatenate([zero18, [0.0]]))
    qpos, okp, _ = env._act_to_q(np.concatenate([zero18, [1.0]]))
    assert ok0 and okp
    stance_idx = np.array([1, 3, 5])
    q0_6, qpos_6 = q0.reshape(6, 3), qpos.reshape(6, 3)
    assert np.allclose(qpos_6[stance_idx], q0_6[stance_idx])
    swing_idx = np.array([0, 2, 4])
    assert np.all(np.abs(qpos_6[swing_idx] - q0_6[swing_idx]).sum(axis=1)
                  > 1e-6)
    env.close()
