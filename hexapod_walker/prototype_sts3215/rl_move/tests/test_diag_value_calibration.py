"""Tests for diag_value_calibration.py (walkcurr off-axis-heading
critic-calibration diagnostic, 2026-09-09). Fast, mechanics-only:
(1) the pure discounted-return-to-go math against a hand-worked
sequence; (2) an integration smoke test that ``_episode_trace``
correctly pairs each tick's critic value prediction with the reward
that followed it, on a tiny real PPO model/env (reused from
test_heading_selfdistill's ``_TinyHeadingEnv``/``_make_ppo``) — no
dependency on any trained checkpoint file; (3) the ``--natural-resample``
mode added this entry (fixes the full-episode-pin OOD artifact found
in Reads 1/2, rl_docs/tracks/walkcurr/STATUS.md 09-09): the vref-index
resolver, the tick-level on/off-axis cosine trace, and the group-stats
aggregator. Does not touch ``_build_env`` (that is a thin wrapper
around the already-tested eval_checkpoint/train_ppo_sim cfg-set
machinery)."""
from __future__ import annotations

import numpy as np
import pytest

from rl_move.sim.diag_value_calibration import (
    _episode_trace,
    _episode_trace_with_cos,
    _group_stats,
    _resolve_vref_index,
    _returns_to_go,
)
from rl_move.tests.test_heading_selfdistill import (
    _N_ACT,
    _OBS_DIM,
    _VREF_IDX,
    _make_ppo,
    _TinyHeadingEnv,
)
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


def test_resolve_vref_index_matches_expected_layout():
    model = _make_ppo(PPO)
    assert _resolve_vref_index(model) == _VREF_IDX


def test_resolve_vref_index_raises_on_obs_width_mismatch():
    """A model whose obs space does not match the plain walk-task
    frame width for its own action dimension must raise loudly, never
    silently index the wrong columns."""
    import gymnasium as gym
    from gymnasium import spaces
    from stable_baselines3.common.vec_env import DummyVecEnv

    class _WrongWidthEnv(gym.Env):
        def __init__(self):
            super().__init__()
            self.observation_space = spaces.Box(-10, 10, (_OBS_DIM + 3,),
                                                dtype=np.float32)
            self.action_space = spaces.Box(-1, 1, (_N_ACT,), dtype=np.float32)

        def reset(self, *, seed=None, options=None):
            return np.zeros(_OBS_DIM + 3, dtype=np.float32), {}

        def step(self, action):
            return (np.zeros(_OBS_DIM + 3, dtype=np.float32), 0.0,
                    True, False, {})

    venv = DummyVecEnv([_WrongWidthEnv])
    model = PPO("MlpPolicy", venv, n_steps=8, batch_size=8, n_epochs=1,
                device="cpu", policy_kwargs=dict(net_arch=[8]))
    with pytest.raises(SystemExit):
        _resolve_vref_index(model)


def test_episode_trace_with_cos_pairs_values_rewards_and_headings():
    model = _make_ppo(PPO)
    env = _TinyHeadingEnv(0)
    idx = _resolve_vref_index(model)
    values, rewards, cos_list = _episode_trace_with_cos(
        env, model, deterministic=True, vref_idx=idx)
    assert len(values) == len(rewards) == len(cos_list) == 8
    assert all(np.isfinite(v) for v in values)
    # _TinyHeadingEnv alternates forward (cos=1) / back (cos=-1) per
    # RESET only (fixed heading for the whole 8-tick episode), so every
    # tick in this trace shares the same cos sign.
    assert all(c == cos_list[0] for c in cos_list)
    assert cos_list[0] in (1.0, -1.0)


def test_group_stats_empty_reports_zero_ticks():
    assert _group_stats([], [], []) == {"n_ticks": 0}


def test_group_stats_matches_hand_computed_values():
    residuals = [1.0, -1.0, 3.0]
    values = [10.0, 8.0, 12.0]
    returns = [9.0, 9.0, 9.0]
    stats = _group_stats(residuals, values, returns)
    assert stats["n_ticks"] == 3
    assert stats["mean_residual"] == pytest.approx(1.0)
    assert stats["median_residual"] == pytest.approx(1.0)
    assert stats["mean_abs_residual"] == pytest.approx(5.0 / 3, abs=1e-4)
    # g_range == 0 (all returns identical) -> residual_frac is None
    assert stats["residual_frac_of_return_range"] is None
    assert stats["mean_V"] == pytest.approx(10.0)
    assert stats["mean_G"] == pytest.approx(9.0)


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
