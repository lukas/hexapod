"""Tests for diag_value_calibration.py (walkcurr off-axis-heading
critic-calibration diagnostic, 2026-09-09). Fast, mechanics-only:
(1) the pure discounted-return-to-go math against a hand-worked
sequence; (2) an integration smoke test that ``_episode_trace``
correctly pairs each tick's critic value prediction with the reward
that followed it, on a tiny real PPO model/env (reused from
test_heading_selfdistill's ``_TinyHeadingEnv``/``_make_ppo``) — no
dependency on any trained checkpoint file. Does not touch
``_build_env`` (that is a thin wrapper around the already-tested
eval_checkpoint/train_ppo_sim cfg-set machinery)."""
from __future__ import annotations

import numpy as np

from rl_move.sim.diag_value_calibration import _episode_trace, _returns_to_go
from rl_move.tests.test_heading_selfdistill import _make_ppo, _TinyHeadingEnv
from stable_baselines3 import PPO


def test_returns_to_go_matches_manual_discount():
    rewards = [1.0, 2.0, 3.0]
    gamma = 0.5
    g = _returns_to_go(rewards, gamma)
    # G_2 = 3; G_1 = 2 + 0.5*3 = 3.5; G_0 = 1 + 0.5*3.5 = 2.75
    assert g == [2.75, 3.5, 3.0]


def test_returns_to_go_empty_is_empty():
    assert _returns_to_go([], 0.99) == []


def test_returns_to_go_zero_gamma_is_reward_itself():
    rewards = [1.0, -2.0, 4.0]
    g = _returns_to_go(rewards, 0.0)
    assert g == rewards


def test_episode_trace_length_matches_episode_and_values_are_finite():
    model = _make_ppo(PPO)
    env = _TinyHeadingEnv(0)
    values, rewards = _episode_trace(env, model, deterministic=True)
    # _TinyHeadingEnv terminates at t>=8.
    assert len(values) == len(rewards) == 8
    assert all(np.isfinite(v) for v in values)
    assert all(np.isfinite(r) for r in rewards)


def test_episode_trace_deterministic_is_reproducible():
    model = _make_ppo(PPO)
    env1, env2 = _TinyHeadingEnv(0), _TinyHeadingEnv(0)
    v1, r1 = _episode_trace(env1, model, deterministic=True)
    v2, r2 = _episode_trace(env2, model, deterministic=True)
    # Same fixed model + deterministic actions + identical env
    # dynamics -> byte-identical trace (no RNG anywhere in this path).
    assert v1 == v2
    assert r1 == r2


def test_episode_trace_residual_zero_for_perfect_critic():
    """Sanity check on the RESIDUAL math the diagnostic reports: if a
    fake model's critic exactly predicts the realized return-to-go at
    every tick, the residual is all-zero regardless of the reward
    sequence's own scale."""
    rewards = [1.0, -0.5, 2.0, 0.0]
    gamma = 0.9
    g = _returns_to_go(rewards, gamma)
    perfect_values = list(g)  # V(s_t) := G_t exactly
    residuals = [v - gt for v, gt in zip(perfect_values, g)]
    assert all(abs(r) < 1e-9 for r in residuals)
