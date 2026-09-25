"""``BankDownweightReplayBuffer`` (walkcurr, 2026-09-25): a genuinely
different mechanism SHAPE for the SAC lower-role bank-curriculum
regression than the two already-closed exposure-TIMING levers
(`goal.lower_start_bank_frac_ramp_steps`/`_delay_steps`, both FAIL,
`walkcurr/STATUS.md` 2026-09-24 ~19:2x/~23:1x) — this one reweights the
REPLAY SAMPLER instead of the environment's own draw schedule.

CPU-only, no MuJoCo/MJX dependency: tiny dummy Box env + DummyVecEnv,
matches test_sac_init_from.py's fixtures.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import gymnasium as gym
import pytest

from rl_move.sim.sac_bank_buffer import BankDownweightReplayBuffer
from rl_move.sim.train_ppo_mjx import _build_sac_model


class _TinyBoxEnv(gym.Env):
    observation_space = gym.spaces.Box(-1.0, 1.0, (4,), np.float32)
    action_space = gym.spaces.Box(-1.0, 1.0, (2,), np.float32)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        return np.zeros(4, np.float32), {}

    def step(self, action):
        return np.zeros(4, np.float32), 0.0, False, False, {}


def _dummy_vec_env():
    from stable_baselines3.common.vec_env import DummyVecEnv
    return DummyVecEnv([lambda: _TinyBoxEnv()])


def _make_buffer(bank_downweight=1.0, buffer_size=16, n_envs=1,
                  bank_info_values=("post_walk_lower",)):
    env = _TinyBoxEnv()
    return BankDownweightReplayBuffer(
        buffer_size, env.observation_space, env.action_space,
        n_envs=n_envs, bank_downweight=bank_downweight,
        bank_info_values=bank_info_values)


def _add_rows(buf, n, start_kinds):
    """Add n single-env transitions; start_kinds[i] is that row's
    info['start_kind']."""
    for i in range(n):
        buf.add(
            obs=np.zeros((1, 4), np.float32),
            next_obs=np.zeros((1, 4), np.float32),
            action=np.zeros((1, 2), np.float32),
            reward=np.array([float(i)]),
            done=np.array([False]),
            infos=[{"start_kind": start_kinds[i]}])


def test_default_downweight_is_off_and_bit_exact_rng_sequence():
    """bank_downweight=1.0 (default) must call the PARENT class's own
    sample() (same RNG draw), not the custom weighted path."""
    buf_default = _make_buffer(bank_downweight=1.0)
    buf_plain = _make_buffer(bank_downweight=1.0)  # separate instance
    kinds = ["post_walk_lower", "plant"] * 4
    _add_rows(buf_default, 8, kinds)
    _add_rows(buf_plain, 8, kinds)
    np.random.seed(123)
    s1 = buf_default.sample(4)
    np.random.seed(123)
    from stable_baselines3.common.buffers import ReplayBuffer
    s2 = ReplayBuffer.sample(buf_plain, 4)
    assert np.allclose(s1.rewards.numpy(), s2.rewards.numpy())


def test_bank_flags_recorded_from_info_dict():
    buf = _make_buffer(bank_downweight=0.1)
    kinds = ["post_walk_lower", "plant", "plant", "post_walk_lower"]
    _add_rows(buf, 4, kinds)
    expect = np.array([k == "post_walk_lower" for k in kinds])
    assert np.array_equal(buf.bank_flags[:4, 0], expect)


def test_zero_downweight_never_samples_bank_rows_when_alternative_exists():
    buf = _make_buffer(bank_downweight=0.0, buffer_size=64)
    kinds = ["post_walk_lower"] * 10 + ["plant"] * 10
    _add_rows(buf, 20, kinds)
    np.random.seed(0)
    for _ in range(20):
        s = buf.sample(32)
        # reward i is the row index; bank rows are 0-9, plant rows 10-19
        assert np.all(s.rewards.numpy() >= 10.0)


def test_downweight_reduces_bank_sampling_frequency_vs_uniform():
    kinds = ["post_walk_lower"] * 10 + ["plant"] * 10
    buf_uniform = _make_buffer(bank_downweight=1.0, buffer_size=64)
    buf_down = _make_buffer(bank_downweight=0.1, buffer_size=64)
    _add_rows(buf_uniform, 20, kinds)
    _add_rows(buf_down, 20, kinds)
    np.random.seed(42)
    frac_uniform = np.mean(buf_uniform.sample(4000).rewards.numpy() < 10.0)
    np.random.seed(42)
    frac_down = np.mean(buf_down.sample(4000).rewards.numpy() < 10.0)
    assert frac_uniform > 0.35  # ~50% expected (10/20 rows are bank)
    assert frac_down < 0.15     # heavily downweighted, well below uniform


def test_multi_env_pairing_keeps_bank_flag_matched_to_its_own_env():
    """Regression guard for the exact bug this class's docstring warns
    about: env_indices must be PAIRED to the chosen time index, not
    drawn independently, or a bank flag at (t, env=0) could get
    attached to env=1's unrelated data."""
    env = _TinyBoxEnv()
    buf = BankDownweightReplayBuffer(
        32, env.observation_space, env.action_space, n_envs=2,
        bank_downweight=0.0, bank_info_values=("post_walk_lower",))
    # One tick: env0 is bank-origin, env1 is not. Encode which env a row
    # came from in the reward value (100 + env_idx) so we can check it.
    for t in range(10):
        buf.add(
            obs=np.zeros((2, 4), np.float32),
            next_obs=np.zeros((2, 4), np.float32),
            action=np.zeros((2, 2), np.float32),
            reward=np.array([100.0, 101.0]),
            done=np.array([False, False]),
            infos=[{"start_kind": "post_walk_lower"}, {"start_kind": "plant"}])
    np.random.seed(7)
    s = buf.sample(200)
    # bank_downweight=0.0 with env0 always bank-origin and env1 never ->
    # every sampled row must be env1's reward (101.0), never env0's (100.0).
    assert np.all(s.rewards.numpy() == 101.0)


def test_build_sac_model_wires_bank_buffer_when_downweight_below_one():
    args = SimpleNamespace(
        init_from=None, sac_ent_coef="auto", sac_buffer_size=64,
        batch_size=8, lr=3e-4, gamma=None, sac_tau=0.005,
        sac_train_freq=1, sac_gradient_steps=1, sac_learning_starts=8,
        device="cpu", seed=0,
        sac_bank_downweight=0.2, sac_bank_info_value="post_walk_lower")
    venv = _dummy_vec_env()
    model = _build_sac_model(args, venv, [8, 8], {}, None)
    assert isinstance(model.replay_buffer, BankDownweightReplayBuffer)
    assert model.replay_buffer.bank_downweight == pytest.approx(0.2)


def test_build_sac_model_default_uses_plain_replay_buffer():
    from stable_baselines3.common.buffers import ReplayBuffer
    args = SimpleNamespace(
        init_from=None, sac_ent_coef="auto", sac_buffer_size=64,
        batch_size=8, lr=3e-4, gamma=None, sac_tau=0.005,
        sac_train_freq=1, sac_gradient_steps=1, sac_learning_starts=8,
        device="cpu", seed=0)
    venv = _dummy_vec_env()
    model = _build_sac_model(args, venv, [8, 8], {}, None)
    assert type(model.replay_buffer) is ReplayBuffer
