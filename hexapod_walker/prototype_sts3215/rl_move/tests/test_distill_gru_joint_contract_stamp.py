"""distill_gru._stamp_and_save -- the joint-frame contract fix
(2026-09-11: cw-standwalk-stage2-dualbc7-massfix-anchor14coef1-canary
crashed on-pod with "checkpoint frame/contract is None/None" because
distill_gru.py's own student.save() was never updated to match
train_ppo_mjx.py's stamp when hexapod_core.joint_frame.
require_checkpoint_joint_contract landed 08-31; every distill_gru
checkpoint since then was silently unusable as an RL fine-tune
--init-from). Locks that _stamp_and_save always stamps before saving,
bit-exact otherwise (no weight change)."""
from __future__ import annotations

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from hexapod_core.joint_frame import (
    FRAME_ROBOT_ABS, JOINT_CONTRACT, require_checkpoint_joint_contract,
)
from rl_move.sim.distill_gru import _stamp_and_save
from rl_move.sim.gru_policy import GruActorCriticPolicy


class _TinyContinuousEnv(gym.Env):
    """Trivial continuous env -- enough API surface for RecurrentPPO."""

    def __init__(self):
        self.observation_space = spaces.Box(-1, 1, (3,), dtype=np.float32)
        self.action_space = spaces.Box(-1, 1, (2,), dtype=np.float32)
        self._t = 0

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self._t = 0
        return self.observation_space.sample(), {}

    def step(self, action):
        self._t += 1
        obs = self.observation_space.sample()
        return obs, 0.0, False, self._t >= 8, {}


def _make_student():
    from sb3_contrib import RecurrentPPO
    return RecurrentPPO(
        GruActorCriticPolicy, _TinyContinuousEnv(),
        n_steps=8, batch_size=16, n_epochs=1, seed=0, device="cpu",
        policy_kwargs=dict(lstm_hidden_size=8))


def test_stamp_and_save_stamps_the_contract(tmp_path):
    student = _make_student()
    out = tmp_path / "student.zip"
    _stamp_and_save(student, out)

    assert require_checkpoint_joint_contract(out) == JOINT_CONTRACT

    from sb3_contrib import RecurrentPPO
    reloaded = RecurrentPPO.load(out, device="cpu")
    assert reloaded.joint_frame == FRAME_ROBOT_ABS
    assert reloaded.joint_contract == JOINT_CONTRACT


def test_stamp_and_save_does_not_change_weights(tmp_path):
    student = _make_student()
    before = {k: v.clone() for k, v in student.policy.state_dict().items()}

    out = tmp_path / "student.zip"
    _stamp_and_save(student, out)

    from sb3_contrib import RecurrentPPO
    reloaded = RecurrentPPO.load(out, device="cpu")
    after = reloaded.policy.state_dict()
    assert set(before) == set(after)
    for k, v in before.items():
        assert (v == after[k]).all(), k
