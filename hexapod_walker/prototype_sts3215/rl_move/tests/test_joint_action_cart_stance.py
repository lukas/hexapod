"""Stance-GATED CARTESIAN foot-placement action channel (lever #20,
2026-09-28) -- the structurally different next idea after the whole
SWING-phase offset/Cartesian-swing family (#16 uniform, #17 pricing,
#18 swing-gated yaw, #19 swing-gated Cartesian) closed CANARY_FAIL 2/2
seeds each (ops.sh index story cw-walkyaw50hz-rlonly-scratch-sac-
s{0,1}-...-cartswing02-canary2m and its ancestors).

Every closed lever nudged a SWING-phase (airborne) foot's future
touchdown point, which cannot generate a ground-reaction impulse until
the leg is already loaded -- the #16 dig-in's own physics read named
the missing ingredient as "stance-stroke/step ratcheting"
(OPERATOR_QUESTIONS q_20260928T1112Z). This channel instead nudges the
currently-STANCE (`env._foot_on` True) leg's TANGENTIAL Cartesian
target (the leg-root-frame y axis) by a fixed metres offset and
re-solves ALL of (yaw, hip, knee) via the shared, already-verified
`CartFootDecoder` analytic IK -- because the foot is grounded, moving
its logical target is a genuine lever-against-the-ground push, unlike
any swing-phase placement change.

These tests pin: OFF is bit-exact (n_act/action_space/mapping
unchanged); ON widens n_act by exactly one; the new channel moves the
FULL (yaw,hip,knee) triplet of currently-STANCE legs only (per
env._foot_on), leaving SWING-leg joints exactly as the box/bias
mapping produced them -- the opposite mask from the closed swing
channel; an all-legs-airborne tick is a safe no-op; oversized gains
never raise/NaN (the shared IK's own reachable-annulus projection
applies).
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

CARTSTANCE_OVERRIDES = {
    **BOX_OVERRIDES,
    ("goal", "walk_cart_stance_gain_m"): 0.02,
}


def test_default_is_inactive_bit_exact_n_act():
    env = _make_walk_env(0, SLIPWALK_OVERRIDES)
    assert not env._cart_stance_active
    assert env.n_act == N_JOINTS
    assert env.action_space.shape == (N_JOINTS,)
    env.close()


def test_off_mapping_is_byte_identical_to_legacy():
    env_off = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **BOX_OVERRIDES})
    assert not env_off._cart_stance_active
    assert env_off.n_act == N_JOINTS
    rng = np.random.default_rng(5)
    for _ in range(10):
        a = rng.uniform(-1.0, 1.0, N_JOINTS)
        q, ok, _ = env_off._act_to_q(a)
        assert ok
    env_off.close()


def test_gain_on_widens_action_space_by_one():
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **CARTSTANCE_OVERRIDES})
    assert env._cart_stance_active
    assert env.n_act == N_JOINTS + 1
    assert env.action_space.shape == (N_JOINTS + 1,)
    env.close()


def test_stance_channel_moves_only_stance_legs_full_triplet():
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **CARTSTANCE_OVERRIDES})
    # Legs 0, 2, 4 in stance (grounded); 1, 3, 5 swinging (airborne) --
    # the opposite convention from the closed swing-channel test.
    env._foot_on = [True, False, True, False, True, False]
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
    stance = [0, 2, 4]
    swing = [1, 3, 5]
    # stance legs' full (yaw,hip,knee) triplet actually moved
    assert np.all(np.abs(qpos_6[stance] - q0_6[stance]).sum(axis=1) > 1e-6)
    assert np.all(np.abs(qneg_6[stance] - q0_6[stance]).sum(axis=1) > 1e-6)
    # opposite-signed action nudges the tangential target opposite ways
    assert not np.allclose(qpos_6[stance], qneg_6[stance])
    # swing legs are untouched by the channel
    assert np.allclose(qpos_6[swing], q0_6[swing])
    assert np.allclose(qneg_6[swing], q0_6[swing])
    env.close()


def test_stance_channel_all_swing_is_safe_noop():
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **CARTSTANCE_OVERRIDES})
    env._foot_on = [False] * 6
    zero18 = np.zeros(N_JOINTS)
    q0, ok0, _ = env._act_to_q(np.concatenate([zero18, [0.0]]))
    qpos, okp, _ = env._act_to_q(np.concatenate([zero18, [1.0]]))
    assert ok0 and okp
    assert np.all(np.isfinite(qpos))
    assert np.allclose(qpos, q0)
    env.close()


def test_stance_channel_never_nans_at_oversized_gain():
    """A large gain can push the target outside the reachable annulus;
    the shared IK projects it (never raises/NaN) -- see
    cart_foot_decode.py's own "never a failure" contract."""
    ov = {**SLIPWALK_OVERRIDES, **CARTSTANCE_OVERRIDES,
          ("goal", "walk_cart_stance_gain_m"): 0.5}
    env = _make_walk_env(0, ov)
    env._foot_on = [True] * 6
    full_pos = np.concatenate([np.ones(N_JOINTS), [1.0]])
    q, ok, _ = env._act_to_q(full_pos)
    assert ok and np.all(np.isfinite(q))
    full_neg = np.concatenate([-np.ones(N_JOINTS), [-1.0]])
    q2, ok2, _ = env._act_to_q(full_neg)
    assert ok2 and np.all(np.isfinite(q2))
    env.close()


def test_stance_active_without_box_still_bit_exact_for_swing():
    """Cart-stance channel composes with the plain bias-only path too
    (box left off), not just the box path."""
    ov = {("goal", "walk_cart_stance_gain_m"): 0.02,
          ("goal", "joint_action_bias_hip_deg"): 40.0,
          ("goal", "joint_action_bias_knee_deg"): 35.0,
          **{k: v for k, v in SLIPWALK_OVERRIDES.items()}}
    env = _make_walk_env(0, ov)
    assert env._cart_stance_active
    assert not env._joint_action_box_active
    env._foot_on = [True, False, True, False, True, False]
    zero18 = np.zeros(N_JOINTS)
    q0, ok0, _ = env._act_to_q(np.concatenate([zero18, [0.0]]))
    qpos, okp, _ = env._act_to_q(np.concatenate([zero18, [1.0]]))
    assert ok0 and okp
    swing_idx = np.array([1, 3, 5])
    q0_6, qpos_6 = q0.reshape(6, 3), qpos.reshape(6, 3)
    assert np.allclose(qpos_6[swing_idx], q0_6[swing_idx])
    stance_idx = np.array([0, 2, 4])
    assert np.all(np.abs(qpos_6[stance_idx] - q0_6[stance_idx]).sum(axis=1)
                  > 1e-6)
    env.close()
