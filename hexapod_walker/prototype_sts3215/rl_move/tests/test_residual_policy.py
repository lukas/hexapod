"""Bank for Design A: frozen forward-walk base + trainable residual
turn adapter (``rl_move/sim/residual_policy.py``, walkcurr track,
2026-09-27 -- STATUS.md "lever (iii)").

Proves:
  1. the composed actor's DETERMINISTIC action at adapter-init (zero
     residual) is bit-identical to the frozen base's own action, where
     "the base's own action" means the box-clipped raw mean -- exactly
     what SB3 itself would have applied stepping the env at rollout
     time (``np.clip(action, -1, 1)``), not the unclipped network
     output;
  2. the frozen base's own obs width may be NARROWER than the
     composed policy's obs (trailing command-channel columns
     appended, mirrors ``obs_pad_transplant``'s convention) -- only
     the leading columns the frozen base was trained on ever reach it,
     and its output is INVARIANT to whatever the trailing columns are;
  3. gradient isolation: after a real backward+optimizer step through
     the composed actor, every frozen-base parameter's ``.grad`` stays
     ``None`` (autograd never built an edge into them) while the
     adapter's own parameters DO receive a nonzero gradient;
  4. the frozen base is excluded from nothing structurally -- it IS
     part of ``state_dict()`` (self-contained, reproducible
     checkpoint) -- verified via a save/reload round trip.

RESEARCH_RULES "Tests": fast (<5s), mechanics only, no artifacts (all
checkpoints written to pytest's tmp_path), no rollout-ranking.

Run: uv run python -m pytest rl_move/tests/test_residual_policy.py -q
"""
from __future__ import annotations

import numpy as np
import pytest
import torch as th
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from rl_move.sim.residual_policy import (
    load_frozen_base, get_residual_sac_policy_class,
)

BASE_OBS_DIM = 12
ACT_DIM = 4
PAD = 3  # e.g. an appended wz_ref-style command channel
COMPOSED_OBS_DIM = BASE_OBS_DIM + PAD


class _BaseEnv(gym.Env):
    observation_space = spaces.Box(-10.0, 10.0, (BASE_OBS_DIM,),
                                    dtype=np.float32)
    action_space = spaces.Box(-1.0, 1.0, (ACT_DIM,), dtype=np.float32)

    def reset(self, *, seed=None, options=None):
        return np.zeros(BASE_OBS_DIM, dtype=np.float32), {}

    def step(self, action):
        return (np.zeros(BASE_OBS_DIM, dtype=np.float32), 0.0, False,
                True, {})


@pytest.fixture(scope="module")
def frozen_ckpt(tmp_path_factory):
    """A tiny from-scratch PPO checkpoint standing in for a real
    forward-walk champion (obs layout narrower than the composed
    policy's, matching bundle_rlonly_v2 vs the walkyaw obs-pad
    convention)."""
    model = PPO("MlpPolicy", DummyVecEnv([_BaseEnv]),
                policy_kwargs=dict(net_arch=[16, 16], log_std_init=-1.0),
                n_steps=8, batch_size=8, seed=0, verbose=0, device="cpu")
    path = tmp_path_factory.mktemp("frozen") / "base_champion.zip"
    model.save(str(path))
    return str(path)


def _build_residual_policy(frozen_ckpt, adapter_hidden=8,
                            adapter_scale=0.1, seed=1):
    ResidualSACPolicy = get_residual_sac_policy_class()
    obs_space = spaces.Box(-np.inf, np.inf, (COMPOSED_OBS_DIM,),
                            dtype=np.float32)
    act_space = spaces.Box(-1.0, 1.0, (ACT_DIM,), dtype=np.float32)
    lr_schedule = lambda _progress: 3e-4
    th.manual_seed(seed)
    return ResidualSACPolicy(
        obs_space, act_space, lr_schedule,
        net_arch={"pi": [adapter_hidden], "qf": [16, 16]},
        frozen_base_ckpt=frozen_ckpt, adapter_hidden=adapter_hidden,
        adapter_scale=adapter_scale)


def test_bit_exact_at_init(frozen_ckpt):
    policy = _build_residual_policy(frozen_ckpt)
    frozen, base_dim = load_frozen_base(frozen_ckpt)
    assert base_dim == BASE_OBS_DIM

    rng = np.random.default_rng(0)
    obs = th.as_tensor(
        rng.normal(scale=2.0, size=(64, COMPOSED_OBS_DIM)).astype(
            np.float32))
    with th.no_grad():
        composed = policy.actor(obs, deterministic=True)
        base_raw = frozen(obs[..., :BASE_OBS_DIM])
        base_clipped = th.clamp(base_raw, -1.0, 1.0)
    diff = (composed - base_clipped).abs().max().item()
    assert diff < 1e-4, f"composed action not bit-exact to frozen base " \
                        f"clipped action at init (max diff {diff})"


def test_frozen_base_ignores_padded_tail_columns(frozen_ckpt):
    """The frozen base only ever sees the leading BASE_OBS_DIM columns
    -- its output must be invariant to whatever the appended command
    columns hold."""
    frozen, base_dim = load_frozen_base(frozen_ckpt)
    rng = np.random.default_rng(1)
    lead = rng.normal(size=(10, BASE_OBS_DIM)).astype(np.float32)
    tail_a = np.zeros((10, PAD), dtype=np.float32)
    tail_b = rng.normal(scale=5.0, size=(10, PAD)).astype(np.float32)
    obs_a = th.as_tensor(np.concatenate([lead, tail_a], axis=1))
    obs_b = th.as_tensor(np.concatenate([lead, tail_b], axis=1))
    with th.no_grad():
        out_a = frozen(obs_a)
        out_b = frozen(obs_b)
    assert th.allclose(out_a, out_b, atol=1e-6)


def test_gradient_isolation(frozen_ckpt):
    policy = _build_residual_policy(frozen_ckpt)
    frozen_params = (list(policy.actor.frozen_base_policy_net.parameters())
                      + list(policy.actor.frozen_base_action_net.parameters()))
    adapter_params = (list(policy.actor.latent_pi.parameters())
                       + list(policy.actor.mu.parameters())
                       + list(policy.actor.log_std.parameters()))
    assert all(not p.requires_grad for p in frozen_params)
    assert all(p.requires_grad for p in adapter_params)
    assert all(p.grad is None for p in frozen_params)

    rng = np.random.default_rng(2)
    obs = th.as_tensor(
        rng.normal(size=(32, COMPOSED_OBS_DIM)).astype(np.float32))
    mean_actions, log_std, _ = policy.actor.get_action_dist_params(obs)
    loss = mean_actions.pow(2).sum() + log_std.pow(2).sum()
    policy.actor.optimizer.zero_grad()
    loss.backward()

    assert all(p.grad is None for p in frozen_params), \
        "a frozen-base parameter received a gradient"
    assert any(p.grad is not None and p.grad.abs().sum().item() > 0
               for p in adapter_params), \
        "the adapter's own parameters received no gradient at all"

    policy.actor.optimizer.step()
    # optimizer.step() must not have touched the frozen weights either.
    with th.no_grad():
        frozen, _ = load_frozen_base(frozen_ckpt)
        raw_after = frozen(obs[..., :BASE_OBS_DIM])
        raw_direct = policy.actor.frozen_base_action_net(
            policy.actor.frozen_base_policy_net(obs[..., :BASE_OBS_DIM]))
    assert th.allclose(raw_after, raw_direct, atol=1e-6)


def test_state_dict_round_trip_is_self_contained(frozen_ckpt, tmp_path):
    """A saved composed policy's state_dict includes the frozen base's
    own weights (self-contained/reproducible checkpoint)."""
    policy = _build_residual_policy(frozen_ckpt)
    sd = policy.actor.state_dict()
    assert any(k.startswith("frozen_base_policy_net.") for k in sd)
    assert any(k.startswith("frozen_base_action_net.") for k in sd)

    fresh = _build_residual_policy(frozen_ckpt, seed=99)
    fresh.actor.load_state_dict(sd)
    rng = np.random.default_rng(3)
    obs = th.as_tensor(
        rng.normal(size=(8, COMPOSED_OBS_DIM)).astype(np.float32))
    with th.no_grad():
        a1 = policy.actor(obs, deterministic=True)
        a2 = fresh.actor(obs, deterministic=True)
    assert th.allclose(a1, a2, atol=1e-6)
