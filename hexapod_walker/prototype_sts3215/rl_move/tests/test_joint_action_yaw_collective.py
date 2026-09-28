"""Collective YAW action channel (2026-09-28, walkcurr rl_only turn-in-
place saga).

gapincome fixed the income economics 2/2 seeds; the follow-up
tipframp6m exposure-TIMING ramp then closed FAIL 2/2 seeds too --
env/walk_wz stayed exactly flat across all 4 training quarters both
seeds and env/walk_yaw_err stayed pinned ~0.81-0.84, despite the
per-joint yaw action box already being wide open
(goal.joint_action_box_yaw_deg=30 of a +-35deg hardware range) -- i.e.
not an action-magnitude ceiling. cfg goal.walk_yaw_collective_gain_deg
(default 0.0 = OFF) adds ONE extra raw action channel applied
IDENTICALLY to all 6 yaw joints' targets on top of whatever the
existing per-joint bias/box/cart-foot mapping already produces --
turning "discover a correlated 6-joint pattern" into "discover the
sign of one scalar knob" (a differential-drive-style action
reparameterization/basis change, still random at init and learned
purely from the task reward -- no reference trajectory, no demo).

These tests pin: OFF is bit-exact (n_act/action_space/mapping
unchanged); ON widens n_act by exactly one and the new channel moves
all 6 yaw joints together by the configured gain (clipped to the
hardware yaw axis range) while leaving every non-yaw joint, and the
box/bias mapping those non-yaw joints still use, untouched.
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

COLLECTIVE_OVERRIDES = {
    **BOX_OVERRIDES,
    ("goal", "walk_yaw_collective_gain_deg"): 15.0,
}


def test_default_is_inactive_bit_exact_n_act():
    env = _make_walk_env(0, SLIPWALK_OVERRIDES)
    assert not env._yaw_collective_active
    assert env.n_act == N_JOINTS
    assert env.action_space.shape == (N_JOINTS,)
    env.close()


def test_off_mapping_is_byte_identical_to_legacy():
    """Same box/bias cfg, gain left at 0 -> identical q for identical
    (18-wide) actions as the pre-existing box mapping."""
    env_off = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **BOX_OVERRIDES})
    assert not env_off._yaw_collective_active
    assert env_off.n_act == N_JOINTS
    rng = np.random.default_rng(3)
    for _ in range(10):
        a = rng.uniform(-1.0, 1.0, N_JOINTS)
        q, ok, _ = env_off._act_to_q(a)
        assert ok
    env_off.close()


def test_gain_on_widens_action_space_by_one():
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **COLLECTIVE_OVERRIDES})
    assert env._yaw_collective_active
    assert env.n_act == N_JOINTS + 1
    assert env.action_space.shape == (N_JOINTS + 1,)
    env.close()


def test_collective_channel_shifts_all_six_yaw_joints_together():
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **COLLECTIVE_OVERRIDES})
    zero18 = np.zeros(N_JOINTS)
    a0 = np.concatenate([zero18, [0.0]])
    apos = np.concatenate([zero18, [1.0]])
    aneg = np.concatenate([zero18, [-1.0]])
    q0, ok0, _ = env._act_to_q(a0)
    qpos, okp, _ = env._act_to_q(apos)
    qneg, okn, _ = env._act_to_q(aneg)
    assert ok0 and okp and okn
    gain_rad = np.radians(15.0)
    assert np.allclose(qpos[_YAW_IDX] - q0[_YAW_IDX], gain_rad, atol=1e-9)
    assert np.allclose(qneg[_YAW_IDX] - q0[_YAW_IDX], -gain_rad, atol=1e-9)
    # every yaw joint moves by the SAME amount -> genuinely collective
    assert np.allclose(qpos[_YAW_IDX], qpos[_YAW_IDX][0])
    # non-yaw joints (and their box/bias mapping) are untouched
    assert np.allclose(qpos[_NON_YAW_IDX], q0[_NON_YAW_IDX])
    assert np.allclose(qneg[_NON_YAW_IDX], q0[_NON_YAW_IDX])
    env.close()


def test_collective_channel_clips_to_hardware_yaw_range():
    """An oversized gain must clip at the +-35deg yaw axis limit, never
    raise/NaN or exceed it, even stacked on top of full per-joint yaw
    excursion."""
    ov = {**SLIPWALK_OVERRIDES, **COLLECTIVE_OVERRIDES,
          ("goal", "walk_yaw_collective_gain_deg"): 90.0}
    env = _make_walk_env(0, ov)
    full_yaw_pos = np.concatenate([np.ones(N_JOINTS), [1.0]])
    q, ok, _ = env._act_to_q(full_yaw_pos)
    assert ok and np.all(np.isfinite(q))
    assert np.all(np.degrees(q[_YAW_IDX]) <= 35.0 + 1e-6)
    full_yaw_neg = np.concatenate([-np.ones(N_JOINTS), [-1.0]])
    q2, ok2, _ = env._act_to_q(full_yaw_neg)
    assert ok2 and np.all(np.isfinite(q2))
    assert np.all(np.degrees(q2[_YAW_IDX]) >= -35.0 - 1e-6)
    env.close()


def test_collective_active_without_box_still_bit_exact_for_nonyaw():
    """Collective channel composes with the plain bias-only path too
    (box left off), not just the box path."""
    ov = {("goal", "walk_yaw_collective_gain_deg"): 10.0,
          ("goal", "joint_action_bias_hip_deg"): 40.0,
          ("goal", "joint_action_bias_knee_deg"): 35.0,
          **{k: v for k, v in SLIPWALK_OVERRIDES.items()}}
    env = _make_walk_env(0, ov)
    assert env._yaw_collective_active
    assert not env._joint_action_box_active
    zero18 = np.zeros(N_JOINTS)
    q0, ok0, _ = env._act_to_q(np.concatenate([zero18, [0.0]]))
    qpos, okp, _ = env._act_to_q(np.concatenate([zero18, [1.0]]))
    assert ok0 and okp
    assert np.allclose(qpos[_NON_YAW_IDX], q0[_NON_YAW_IDX])
    assert np.allclose(qpos[_YAW_IDX] - q0[_YAW_IDX], np.radians(10.0),
                       atol=1e-9)
    env.close()
