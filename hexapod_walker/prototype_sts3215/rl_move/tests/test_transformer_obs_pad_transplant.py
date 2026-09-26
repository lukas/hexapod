"""Transformer-to-WIDER-transformer obs-pad transplant (2026-09-26,
standwalk foot-contact-sense lever, ``obs_transplant.py::
transformer_pad_obs_transplant``).

The pre-existing ``--transformer + --obs-pad-transplant`` CLI guard
blocked EVERY combination, but its documented reason ("transformer
weights don't transplant from MLP checkpoints") only applies to a
genuine MLP->transformer swap. A FrameStackTransformer touches raw obs
columns ONLY through its per-frame embed Linear (actor + critic
extractors), so a PER-FRAME TAIL widening of n_pad dims transplants by
zero-padding the last n_pad embed columns -- outputs bit-identical to
the parent for ANY value of the new dims until training moves the zero
columns (the ``pad_obs_transplant`` contract, per frame). NOTE the
n_pad semantics: per-frame widening; the flat obs widens by n_pad * K.
"""
from __future__ import annotations

import numpy as np
import pytest
import torch as th
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from rl_move.sim.obs_transplant import transformer_pad_obs_transplant
from rl_move.sim.transformer_policy import TransformerActorCriticPolicy

K = 4          # frames
W_OLD = 10     # per-frame width
N_PAD = 6      # per-frame widening (foot contact channel)
W_NEW = W_OLD + N_PAD
ACT_DIM = 6


def _env(flat_dim):
    class _E(gym.Env):
        observation_space = spaces.Box(-10.0, 10.0, (flat_dim,),
                                       dtype=np.float32)
        action_space = spaces.Box(-1.0, 1.0, (ACT_DIM,), dtype=np.float32)

        def reset(self, *, seed=None, options=None):
            return np.zeros(flat_dim, dtype=np.float32), {}

        def step(self, action):
            return (np.zeros(flat_dim, dtype=np.float32), 0.0, False,
                    True, {})
    return _E


def _model(flat_dim, seed):
    return PPO(
        TransformerActorCriticPolicy, DummyVecEnv([_env(flat_dim)]),
        n_steps=8, batch_size=8, seed=seed, verbose=0, device="cpu",
        policy_kwargs=dict(net_arch=[16], n_frames=K, d_model=16,
                           n_layers=1, n_heads=2, ff_dim=32))


def _widened_obs(obs_old, pad_vals):
    """Old (K*W_OLD,) obs -> (K*W_NEW,) with pad_vals at each frame tail."""
    frames = obs_old.reshape(K, W_OLD)
    return np.concatenate(
        [np.concatenate([f, pad_vals]) for f in frames]).astype(np.float32)


def test_transplant_bit_identical_for_any_new_dim_values():
    old = _model(K * W_OLD, seed=1)
    new = _model(K * W_NEW, seed=2)
    transformer_pad_obs_transplant(old, new, N_PAD)
    rng = np.random.default_rng(0)
    for _ in range(3):
        obs_old = rng.normal(size=(K * W_OLD,)).astype(np.float32)
        for pad in (np.zeros(N_PAD), rng.normal(size=N_PAD) * 5.0):
            obs_new = _widened_obs(obs_old, pad.astype(np.float32))
            a_old, _ = old.predict(obs_old, deterministic=True)
            a_new, _ = new.predict(obs_new, deterministic=True)
            np.testing.assert_array_equal(a_old, a_new)
            v_old = old.policy.predict_values(
                th.as_tensor(obs_old[None]))
            v_new = new.policy.predict_values(
                th.as_tensor(obs_new[None]))
            np.testing.assert_array_equal(
                v_old.detach().numpy(), v_new.detach().numpy())


def test_transplant_refuses_wrong_pad():
    old = _model(K * W_OLD, seed=1)
    new = _model(K * W_NEW, seed=2)
    with pytest.raises(SystemExit, match="per-frame"):
        transformer_pad_obs_transplant(old, new, N_PAD + 1)


def test_transplant_refuses_mlp_parent():
    mlp = PPO("MlpPolicy", DummyVecEnv([_env(K * W_OLD)]),
              n_steps=8, batch_size=8, seed=1, verbose=0, device="cpu",
              policy_kwargs=dict(net_arch=[16]))
    new = _model(K * W_NEW, seed=2)
    with pytest.raises(SystemExit):
        transformer_pad_obs_transplant(mlp, new, N_PAD)


def test_transplant_refuses_frame_count_mismatch():
    old = _model(K * W_OLD, seed=1)
    bad = PPO(
        TransformerActorCriticPolicy,
        DummyVecEnv([_env(2 * K * W_NEW)]),
        n_steps=8, batch_size=8, seed=2, verbose=0, device="cpu",
        policy_kwargs=dict(net_arch=[16], n_frames=2 * K, d_model=16,
                           n_layers=1, n_heads=2, ff_dim=32))
    with pytest.raises(SystemExit):
        transformer_pad_obs_transplant(old, bad, N_PAD)


def _inserted_obs(obs_old, pad_vals, at):
    frames = obs_old.reshape(K, W_OLD)
    return np.concatenate(
        [np.concatenate([f[:at], pad_vals, f[at:]])
         for f in frames]).astype(np.float32)


def test_mid_frame_insert_bit_identical():
    # The obs.current_sense case: the new channel lands INSIDE
    # build_obs, BEFORE walk_task's vel/phase tail extras -- per-frame
    # insert_at, not tail append.
    at = W_OLD - 4
    old = _model(K * W_OLD, seed=1)
    new = _model(K * W_NEW, seed=2)
    transformer_pad_obs_transplant(old, new, N_PAD, insert_at=at)
    rng = np.random.default_rng(1)
    obs_old = rng.normal(size=(K * W_OLD,)).astype(np.float32)
    for pad in (np.zeros(N_PAD), rng.normal(size=N_PAD) * 5.0):
        obs_new = _inserted_obs(obs_old, pad.astype(np.float32), at)
        a_old, _ = old.predict(obs_old, deterministic=True)
        a_new, _ = new.predict(obs_new, deterministic=True)
        np.testing.assert_array_equal(a_old, a_new)


def test_mid_frame_insert_out_of_range_refused():
    old = _model(K * W_OLD, seed=1)
    new = _model(K * W_NEW, seed=2)
    with pytest.raises(SystemExit, match="FRAME width"):
        transformer_pad_obs_transplant(old, new, N_PAD,
                                       insert_at=W_OLD + 1)
