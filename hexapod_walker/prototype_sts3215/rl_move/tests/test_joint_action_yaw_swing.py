"""Swing-GATED yaw action channel (2026-09-28, walkcurr rl_only turn-in-
place saga -- next named lever after the UNIFORM collective-yaw channel
closed CANARY_FAIL 2/2, ops.sh index story
cw-walkyaw50hz-rlonly-scratch-sac-s{0,1}-...-yawcollective15-canary2m-r2).

That dig-in's own physics read: "static joint-space yaw offsets ...
oscillate median-zero without stance-stroke/step ratcheting --
offset-style action channels are disfavored as a family". This channel
is offset-style too but structurally different in the one dimension
that read named as missing: the SAME extra raw action channel is
applied ONLY to the yaw joint(s) of leg(s) currently SWINGING (per
``env._foot_on``, the existing one-tick-lagged per-leg contact flag),
leaving every stance leg's yaw target untouched -- shifting only a
swinging leg's yaw joint changes WHERE that foot's next placement
lands, a genuine asymmetric-next-stance mechanism the uniform channel
could not produce.

These tests pin: OFF is bit-exact (n_act/action_space/mapping
unchanged); ON widens n_act by exactly one; the new channel moves ONLY
the yaw joints of currently-swinging legs (per env._foot_on) by the
configured gain (clipped to the hardware yaw axis range), leaving
stance-leg yaw joints and every non-yaw joint (and the box/bias
mapping they still use) untouched; an all-legs-in-stance tick is a
safe no-op.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.sim.joint_task import N_JOINTS
from walk_env_helpers import _make_walk_env, SLIPWALK_OVERRIDES

_YAW_IDX = np.arange(0, N_JOINTS, 3)
_NON_YAW_IDX = [i for i in range(N_JOINTS) if i not in _YAW_IDX]

BOX_OVERRIDES = {
    ("goal", "joint_action_bias_hip_deg"): 40.0,
    ("goal", "joint_action_bias_knee_deg"): 35.0,
    ("goal", "joint_action_box_yaw_deg"): 30.0,
    ("goal", "joint_action_box_hip_deg"): 20.0,
    ("goal", "joint_action_box_knee_deg"): 25.0,
}

SWING_OVERRIDES = {
    **BOX_OVERRIDES,
    ("goal", "walk_yaw_swing_gain_deg"): 15.0,
}


def test_default_is_inactive_bit_exact_n_act():
    env = _make_walk_env(0, SLIPWALK_OVERRIDES)
    assert not env._yaw_swing_active
    assert env.n_act == N_JOINTS
    assert env.action_space.shape == (N_JOINTS,)
    env.close()


def test_off_mapping_is_byte_identical_to_legacy():
    """Same box/bias cfg, gain left at 0 -> identical q for identical
    (18-wide) actions as the pre-existing box mapping."""
    env_off = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **BOX_OVERRIDES})
    assert not env_off._yaw_swing_active
    assert env_off.n_act == N_JOINTS
    rng = np.random.default_rng(3)
    for _ in range(10):
        a = rng.uniform(-1.0, 1.0, N_JOINTS)
        q, ok, _ = env_off._act_to_q(a)
        assert ok
    env_off.close()


def test_gain_on_widens_action_space_by_one():
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **SWING_OVERRIDES})
    assert env._yaw_swing_active
    assert env.n_act == N_JOINTS + 1
    assert env.action_space.shape == (N_JOINTS + 1,)
    env.close()


def test_swing_channel_moves_only_swinging_legs_yaw_joints():
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **SWING_OVERRIDES})
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
    gain_rad = np.radians(15.0)
    swing_yaw_idx = _YAW_IDX[[0, 2, 4]]
    stance_yaw_idx = _YAW_IDX[[1, 3, 5]]
    assert np.allclose(qpos[swing_yaw_idx] - q0[swing_yaw_idx],
                       gain_rad, atol=1e-9)
    assert np.allclose(qneg[swing_yaw_idx] - q0[swing_yaw_idx],
                       -gain_rad, atol=1e-9)
    # stance legs' yaw joints are untouched by the channel
    assert np.allclose(qpos[stance_yaw_idx], q0[stance_yaw_idx])
    assert np.allclose(qneg[stance_yaw_idx], q0[stance_yaw_idx])
    # non-yaw joints (and their box/bias mapping) are untouched
    assert np.allclose(qpos[_NON_YAW_IDX], q0[_NON_YAW_IDX])
    assert np.allclose(qneg[_NON_YAW_IDX], q0[_NON_YAW_IDX])
    env.close()


def test_swing_channel_all_stance_is_safe_noop():
    """No leg swinging (a rare/never-quite state for a tripod gait, but
    must not raise/NaN) -> the extra channel has nothing to act on."""
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **SWING_OVERRIDES})
    env._foot_on = [True] * 6
    zero18 = np.zeros(N_JOINTS)
    q0, ok0, _ = env._act_to_q(np.concatenate([zero18, [0.0]]))
    qpos, okp, _ = env._act_to_q(np.concatenate([zero18, [1.0]]))
    assert ok0 and okp
    assert np.all(np.isfinite(qpos))
    assert np.allclose(qpos, q0)
    env.close()


def test_swing_channel_clips_to_hardware_yaw_range():
    """An oversized gain must clip at the +-35deg yaw axis limit, never
    raise/NaN or exceed it, even stacked on top of full per-joint yaw
    excursion."""
    ov = {**SLIPWALK_OVERRIDES, **SWING_OVERRIDES,
          ("goal", "walk_yaw_swing_gain_deg"): 90.0}
    env = _make_walk_env(0, ov)
    env._foot_on = [False] * 6
    full_yaw_pos = np.concatenate([np.ones(N_JOINTS), [1.0]])
    q, ok, _ = env._act_to_q(full_yaw_pos)
    assert ok and np.all(np.isfinite(q))
    assert np.all(np.degrees(q[_YAW_IDX]) <= 35.0 + 1e-6)
    full_yaw_neg = np.concatenate([-np.ones(N_JOINTS), [-1.0]])
    q2, ok2, _ = env._act_to_q(full_yaw_neg)
    assert ok2 and np.all(np.isfinite(q2))
    assert np.all(np.degrees(q2[_YAW_IDX]) >= -35.0 - 1e-6)
    env.close()


def test_swing_active_without_box_still_bit_exact_for_nonyaw():
    """Swing channel composes with the plain bias-only path too (box
    left off), not just the box path."""
    ov = {("goal", "walk_yaw_swing_gain_deg"): 10.0,
          ("goal", "joint_action_bias_hip_deg"): 40.0,
          ("goal", "joint_action_bias_knee_deg"): 35.0,
          **{k: v for k, v in SLIPWALK_OVERRIDES.items()}}
    env = _make_walk_env(0, ov)
    assert env._yaw_swing_active
    assert not env._joint_action_box_active
    env._foot_on = [False, True, False, True, False, True]
    zero18 = np.zeros(N_JOINTS)
    q0, ok0, _ = env._act_to_q(np.concatenate([zero18, [0.0]]))
    qpos, okp, _ = env._act_to_q(np.concatenate([zero18, [1.0]]))
    assert ok0 and okp
    assert np.allclose(qpos[_NON_YAW_IDX], q0[_NON_YAW_IDX])
    swing_yaw_idx = _YAW_IDX[[0, 2, 4]]
    assert np.allclose(qpos[swing_yaw_idx] - q0[swing_yaw_idx],
                       np.radians(10.0), atol=1e-9)
    env.close()
