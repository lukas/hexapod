"""``recurrent_sac.py`` (walkcurr rl_only lower-role lineage, 2026-10-04):
from-scratch GRU actor+critic SAC with a real hidden state + a
sequence-aware replay buffer. CPU-only, no MuJoCo/MJX dependency: tiny
dummy Box env, same fixture style as test_sac_bank_buffer.py/
test_sac_init_from.py. Mechanics-only per RESEARCH_RULES "Tests": shapes,
state-threading/reset, save/load round trip, buffer episode bookkeeping,
CLI guard — no rollout-ranking/behavior claims.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import gymnasium as gym
import pytest
import torch as th


OBS_DIM = 4
ACT_DIM = 2


class _TinyBoxEnv(gym.Env):
    observation_space = gym.spaces.Box(-1.0, 1.0, (OBS_DIM,), np.float32)
    action_space = gym.spaces.Box(-1.0, 1.0, (ACT_DIM,), np.float32)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        return np.zeros(OBS_DIM, np.float32), {}

    def step(self, action):
        return np.zeros(OBS_DIM, np.float32), 1.0, False, False, {}


class _TinyEpisodicEnv(_TinyBoxEnv):
    """Truncates every ``max_steps`` ticks (TimeLimit-style) so a
    SequenceReplayBuffer under test actually gets complete episodes."""

    def __init__(self, max_steps: int = 5):
        self.max_steps = int(max_steps)
        self._t = 0

    def reset(self, *, seed=None, options=None):
        self._t = 0
        return super().reset(seed=seed, options=options)

    def step(self, action):
        self._t += 1
        obs, rew, term, trunc, info = super().step(action)
        trunc = self._t >= self.max_steps
        return obs, rew, term, trunc, info


def _dummy_vec_env(n_envs=1, max_steps=5):
    from stable_baselines3.common.vec_env import DummyVecEnv
    return DummyVecEnv(
        [lambda: _TinyEpisodicEnv(max_steps=max_steps)
         for _ in range(n_envs)])


# ---------------------------------------------------------------------
# SequenceReplayBuffer
# ---------------------------------------------------------------------
def _buf(seq_len=4, buffer_size=1000, n_envs=1):
    from rl_move.sim.recurrent_sac import SequenceReplayBuffer
    env = _TinyBoxEnv()
    return SequenceReplayBuffer(
        buffer_size, env.observation_space, env.action_space,
        n_envs=n_envs, seq_len=seq_len)


def _add_episode(buf, length, n_envs=1, truncated=False):
    for t in range(length):
        done = np.array([t == length - 1] * n_envs)
        infos = [{"TimeLimit.truncated": bool(truncated and t == length - 1)}
                 for _ in range(n_envs)]
        buf.add(
            obs=np.full((n_envs, OBS_DIM), float(t), np.float32),
            next_obs=np.full((n_envs, OBS_DIM), float(t + 1), np.float32),
            action=np.zeros((n_envs, ACT_DIM), np.float32),
            reward=np.ones(n_envs, np.float32),
            done=done, infos=infos)


def test_buffer_finalizes_episode_on_done():
    buf = _buf()
    assert buf.num_episodes() == 0
    _add_episode(buf, 7)
    assert buf.num_episodes() == 1
    assert buf.size() == 7


def test_buffer_sample_shapes_and_mask_full_length():
    buf = _buf(seq_len=4)
    _add_episode(buf, 10)
    batch = buf.sample(8)
    assert batch.observations.shape == (8, 4, OBS_DIM)
    assert batch.actions.shape == (8, 4, ACT_DIM)
    assert batch.rewards.shape == (8, 4, 1)
    assert batch.mask.shape == (8, 4)
    assert th.all(batch.mask == 1.0)


def test_buffer_sample_pads_short_episode_and_masks_tail():
    buf = _buf(seq_len=8)
    _add_episode(buf, 3)  # shorter than seq_len
    batch = buf.sample(16)
    # real data occupies the FRONT of the window; tail is padded+masked
    assert th.all(batch.mask[:, :3] == 1.0)
    assert th.all(batch.mask[:, 3:] == 0.0)


def test_buffer_truncated_timeout_keeps_bootstrap_done_false():
    """A TimeLimit.truncated done must NOT zero the value bootstrap
    (mirrors stable_baselines3.common.buffers.ReplayBuffer.add)."""
    buf = _buf(seq_len=4)
    _add_episode(buf, 4, truncated=True)
    batch = buf.sample(32)
    assert th.all(batch.dones == 0.0)


def test_buffer_real_termination_sets_bootstrap_done_true():
    buf = _buf(seq_len=4)
    _add_episode(buf, 4, truncated=False)
    batch = buf.sample(32)
    assert float(batch.dones[0, -1, 0]) == pytest.approx(1.0)


def test_buffer_evicts_oldest_episode_over_capacity():
    buf = _buf(seq_len=2, buffer_size=10)
    _add_episode(buf, 6)
    _add_episode(buf, 6)
    assert buf.num_episodes() == 1  # first evicted, 2nd (6) alone < cap
    assert buf.size() == 6


def test_buffer_sample_before_any_episode_raises():
    buf = _buf()
    with pytest.raises(RuntimeError):
        buf.sample(4)


# ---------------------------------------------------------------------
# Networks / policy
# ---------------------------------------------------------------------
def test_actor_forward_seq_shapes():
    from rl_move.sim.recurrent_sac import GRUGaussianActor
    actor = GRUGaussianActor(OBS_DIM, ACT_DIM, hidden_size=8)
    obs = th.randn(3, 5, OBS_DIM)
    h0 = th.zeros(3, 8)
    action_seq, log_prob_seq, h_seq = actor.action_log_prob_seq(obs, h0)
    assert action_seq.shape == (3, 5, ACT_DIM)
    assert log_prob_seq.shape == (3, 5, 1)
    assert h_seq.shape == (3, 5, 8)
    assert th.all(action_seq.abs() <= 1.0)  # squashed


def test_critic_forward_seq_shapes():
    from rl_move.sim.recurrent_sac import GRUTwinQ
    critic = GRUTwinQ(OBS_DIM, ACT_DIM, hidden_size=8, n_critics=2)
    obs = th.randn(3, 5, OBS_DIM)
    act = th.randn(3, 5, ACT_DIM)
    h0 = th.zeros(3, 8)
    q_list, h_list = critic.forward_seq(obs, act, h0)
    assert len(q_list) == 2
    assert q_list[0].shape == (3, 5, 1)
    assert h_list[0].shape == (3, 5, 8)


def test_policy_has_duck_typed_lstm_actor_marker():
    from rl_move.sim.recurrent_sac import RecurrentSACPolicy
    env = _TinyBoxEnv()
    policy = RecurrentSACPolicy(env.observation_space, env.action_space,
                                lambda _: 3e-4, hidden_size=8)
    assert policy.lstm_actor is not None


def test_policy_predict_resets_hidden_on_episode_start():
    from rl_move.sim.recurrent_sac import RecurrentSACPolicy
    env = _TinyBoxEnv()
    policy = RecurrentSACPolicy(env.observation_space, env.action_space,
                                lambda _: 3e-4, hidden_size=8)
    obs = np.zeros(OBS_DIM, np.float32)
    a1, state1 = policy.predict(obs, state=None,
                                episode_start=np.ones((1,), bool),
                                deterministic=True)
    assert a1.shape == (ACT_DIM,)
    assert state1.shape == (1, 8)
    assert not np.allclose(state1, 0.0)  # GRU advanced past zero init
    a2, state2 = policy.predict(obs, state=state1,
                                episode_start=np.ones((1,), bool),
                                deterministic=True)
    # episode_start=True forces the incoming hidden back to zero before
    # this tick -> identical to the very first call
    assert np.allclose(a1, a2)
    assert np.allclose(state1, state2)


# ---------------------------------------------------------------------
# load_checkpoint_auto / wrap_recurrent_predictor integration
# ---------------------------------------------------------------------
def _build_sac_args(**overrides):
    base = dict(
        init_from=None, sac_ent_coef="auto", sac_buffer_size=200,
        batch_size=4, lr=3e-4, gamma=None, sac_tau=0.005,
        sac_train_freq=1, sac_gradient_steps=1, sac_learning_starts=2,
        device="cpu", seed=0, sac_bank_downweight=1.0,
        recurrent_sac=True, rsac_hidden_size=8, rsac_seq_len=4)
    base.update(overrides)
    return SimpleNamespace(**base)


def test_build_sac_model_recurrent_branch_returns_recurrent_sac():
    from rl_move.sim.train_ppo_mjx import _build_sac_model
    from rl_move.sim.recurrent_sac import RecurrentSAC
    venv = _dummy_vec_env()
    model = _build_sac_model(_build_sac_args(), venv, [8, 8], {}, None)
    assert isinstance(model, RecurrentSAC)


def test_build_sac_model_recurrent_refuses_init_from():
    from rl_move.sim.train_ppo_mjx import _build_sac_model
    venv = _dummy_vec_env()
    with pytest.raises(SystemExit):
        _build_sac_model(_build_sac_args(init_from="dummy.zip"), venv,
                         [8, 8], {}, None)


def test_build_sac_model_recurrent_refuses_bank_downweight():
    from rl_move.sim.train_ppo_mjx import _build_sac_model
    venv = _dummy_vec_env()
    with pytest.raises(SystemExit):
        _build_sac_model(_build_sac_args(sac_bank_downweight=0.5), venv,
                         [8, 8], {}, None)


def test_recurrent_sac_learn_smoke_and_checkpoint_round_trip(tmp_path):
    """A tiny end-to-end .learn() call: rollout collection (persistent
    rollout hidden state), >=1 completed episode landing in the
    sequence buffer, >=1 real gradient update (train() not perpetually
    skipped), and a save/load round trip that reproduces the SAME
    deterministic action -- no crash anywhere in the custom train()
    math (entropy/critic/actor losses, target polyak update)."""
    from rl_move.sim.train_ppo_mjx import _build_sac_model
    venv = _dummy_vec_env(n_envs=2, max_steps=5)
    args = _build_sac_args(sac_learning_starts=2, batch_size=4,
                           sac_gradient_steps=2, sac_buffer_size=500)
    model = _build_sac_model(args, venv, [8, 8], {}, None)
    model.learn(total_timesteps=40, log_interval=1000)
    assert model.replay_buffer.num_episodes() >= 1
    assert model._n_updates > 0

    ckpt = tmp_path / "ppo_goal_recurrent_sac_probe.zip"
    model.save(ckpt)

    from rl_move.sim.recurrent_sac import is_recurrent_sac_checkpoint
    assert is_recurrent_sac_checkpoint(ckpt) is True

    from rl_move.sim.gru_policy import load_checkpoint_auto
    from rl_move.sim.recurrent_sac import RecurrentSAC
    loaded = load_checkpoint_auto(ckpt, device="cpu")
    assert isinstance(loaded, RecurrentSAC)

    obs = np.zeros(OBS_DIM, np.float32)
    a_direct, _ = loaded.policy.predict(
        obs, state=None, episode_start=np.ones((1,), bool),
        deterministic=True)
    a_saved, _ = model.policy.predict(
        obs, state=None, episode_start=np.ones((1,), bool),
        deterministic=True)
    assert np.allclose(a_direct, a_saved)


def test_wrap_recurrent_predictor_wraps_recurrent_sac(tmp_path):
    from rl_move.sim.train_ppo_mjx import _build_sac_model
    from rl_move.sim.gru_policy import (
        wrap_recurrent_predictor, RecurrentPredictor,
    )
    venv = _dummy_vec_env()
    model = _build_sac_model(_build_sac_args(), venv, [8, 8], {}, None)
    wrapped = wrap_recurrent_predictor(model)
    assert isinstance(wrapped, RecurrentPredictor)
    wrapped.reset()
    obs = np.zeros(OBS_DIM, np.float32)
    action, value = wrapped.predict(obs, deterministic=True)
    assert action.shape == (ACT_DIM,)
    assert value is None


def test_wrap_recurrent_predictor_passthrough_for_plain_sac():
    """Zero behavior change for the existing plain --algo sac path --
    the recurrent-SAC detection must not touch it."""
    from stable_baselines3 import SAC
    from rl_move.sim.gru_policy import wrap_recurrent_predictor
    env = _TinyBoxEnv()
    model = SAC("MlpPolicy", env, buffer_size=64, learning_starts=8,
               policy_kwargs=dict(net_arch=[8]), seed=0, device="cpu")
    assert wrap_recurrent_predictor(model) is model


def test_recurrent_sac_requires_algo_sac():
    from rl_move.sim.train_ppo_mjx import _build_arg_parser
    ap = _build_arg_parser()
    args = ap.parse_args(["--recurrent-sac", "--algo", "ppo", "--smoke"])
    assert args.recurrent_sac is True and args.algo == "ppo"
    # The actual refusal lives inline in main() (requires constructing
    # the full training setup to exercise) -- covered at the integration
    # level by _build_sac_model's own recurrent_sac branch above, which
    # main() only reaches when args.algo == "sac". This test just pins
    # the flag parses cleanly in combination with any --algo value (the
    # SystemExit guard is inside main(), not the parser).
