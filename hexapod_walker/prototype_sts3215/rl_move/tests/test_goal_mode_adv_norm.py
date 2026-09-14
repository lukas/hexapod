"""Tests for goal_mode_adv_norm.py (walkcurr hold-collapse STRUCTURAL
fix, 09-13 -- see the module docstring for the tb-holdfee-6m /
tb-holdmix-6m FAIL-MECHANISM escalation this answers).

Layers: (1) the grouped-normalization math against synthetic advantage
arrays with known group membership and deliberately different raw
scales (mirrors test_heading_adv_norm.py's layer 2 but with a plain
string-label group instead of an obs-derived on/off-axis split); (2) a
real-PPO integration smoke test using a tiny multi-mode env, proving
the capture callback + train() hook actually rewrite
`rollout_buffer.advantages` per mode while leaving actions/obs/rewards
untouched, and that the off path is bit-exact.
"""
from __future__ import annotations

import numpy as np
import gymnasium as gym
from gymnasium import spaces
import pytest

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.logger import configure

from rl_move.sim.goal_mode_adv_norm import (
    attach_goal_mode_adv_norm,
    make_goal_mode_adv_norm_ppo_class,
    GoalModeCaptureCallback,
    goal_mode_adv_norm_wandb_payload,
    GOAL_MODE_ADV_NORM_WANDB_PREFIX,
    _grouped_renorm,
)


# ---------------------------------------------------------------------
# 1. Pure grouped-renormalization math (no PPO/env machinery).
# ---------------------------------------------------------------------

def test_grouped_renorm_each_big_group_zero_mean_unit_std():
    rng = np.random.default_rng(0)
    a = np.concatenate([rng.normal(50.0, 20.0, 100),
                       rng.normal(-3.0, 1.0, 100)])
    labels = np.asarray(["lower"] * 100 + ["hold"] * 100, dtype=object)
    out, stats = _grouped_renorm(a, labels, min_group=8)
    for lbl in ("lower", "hold"):
        mask = labels == lbl
        assert stats[lbl]["applied"] is True
        np.testing.assert_allclose(out[mask].mean(), 0.0, atol=1e-8)
        np.testing.assert_allclose(out[mask].std(), 1.0, atol=1e-8)


def test_grouped_renorm_small_group_left_unchanged():
    a = np.concatenate([np.full(20, 5.0), np.full(3, 100.0)])
    labels = np.asarray(["lower"] * 20 + ["rise"] * 3, dtype=object)
    out, stats = _grouped_renorm(a, labels, min_group=8)
    assert stats["rise"]["applied"] is False
    np.testing.assert_array_equal(out[20:], a[20:])  # untouched


def test_grouped_renorm_degenerate_std_left_unchanged():
    a = np.concatenate([np.full(20, 7.0), np.full(20, 3.0)])  # std=0
    labels = np.asarray(["lower"] * 20 + ["hold"] * 20, dtype=object)
    out, stats = _grouped_renorm(a, labels, min_group=8)
    assert stats["hold"]["applied"] is False
    np.testing.assert_array_equal(out[20:], a[20:])


def test_grouped_renorm_preserves_relative_order_within_group():
    a = np.array([1.0, 5.0, 3.0, 100.0, 500.0, 300.0])
    labels = np.asarray(["a"] * 3 + ["b"] * 3, dtype=object)
    out, _ = _grouped_renorm(a, labels, min_group=1)
    assert np.argsort(out[:3]).tolist() == np.argsort(a[:3]).tolist()
    assert np.argsort(out[3:]).tolist() == np.argsort(a[3:]).tolist()


# ---------------------------------------------------------------------
# 2. Real-PPO integration: a tiny 2-mode env (mode fixed per env
#    index, matching production's "one mode per episode" contract).
# ---------------------------------------------------------------------

_OBS_DIM = 6
_N_ACT = 3
_MODES = ("hold", "lower")


class _TinyModeEnv(gym.Env):
    """Deterministic tiny env: each instance is permanently one mode
    (set by env index, like a goal-mix'd SimHexapodGoalEnv episode),
    emits `info["goal_mode"]` every step (the exact key
    GoalModeCaptureCallback reads), and rewards actions near a
    per-mode target at a DELIBERATELY different scale (lower's reward
    ~100x hold's, mirroring the real dig-in's magnitude gap) so the
    two groups carry very different raw advantage scales."""

    metadata = {}

    def __init__(self, env_idx: int):
        super().__init__()
        self.observation_space = spaces.Box(-10, 10, (_OBS_DIM,),
                                            dtype=np.float32)
        self.action_space = spaces.Box(-1, 1, (_N_ACT,), dtype=np.float32)
        self._mode = _MODES[env_idx % len(_MODES)]
        self._t = 0

    def reset(self, *, seed=None, options=None):
        self._t = 0
        return np.zeros(_OBS_DIM, dtype=np.float32), {}

    def step(self, action):
        self._t += 1
        target = 1.0 if self._mode == "lower" else -1.0
        scale = 100.0 if self._mode == "lower" else 1.0
        reward = -scale * float(np.mean(
            (np.asarray(action) - target) ** 2))
        term = self._t >= 8
        return (np.zeros(_OBS_DIM, dtype=np.float32), reward, term,
                False, {"goal_mode": self._mode})


def _make_ppo(cls, seed=0, n_envs=8):
    venv = DummyVecEnv([lambda i=i: _TinyModeEnv(i) for i in range(n_envs)])
    m = cls("MlpPolicy", venv, n_steps=16, batch_size=32, n_epochs=2,
            seed=seed, device="cpu", policy_kwargs=dict(net_arch=[16]))
    m.set_random_seed(seed)
    return m


def _collect(m):
    _, callback = m._setup_learn(total_timesteps=16, callback=None)
    from stable_baselines3.common.callbacks import CallbackList
    cb = CallbackList([callback, GoalModeCaptureCallback()])
    cb.init_callback(m)
    m.collect_rollouts(m.env, callback=cb, rollout_buffer=m.rollout_buffer,
                      n_rollout_steps=16)


def test_off_path_is_bit_exact():
    plain = _make_ppo(PPO)
    wrapped = _make_ppo(make_goal_mode_adv_norm_ppo_class(PPO))
    assert wrapped.goal_mode_adv_norm_enabled is False
    for p_plain, p_wrap in zip(plain.policy.parameters(),
                              wrapped.policy.parameters()):
        p_wrap.data.copy_(p_plain.data)
    plain.set_logger(configure(None, ["stdout"]))
    wrapped.set_logger(configure(None, ["stdout"]))
    plain.set_random_seed(0)
    plain.learn(total_timesteps=32)
    wrapped.set_random_seed(0)
    wrapped.learn(total_timesteps=32)
    for p_plain, p_wrap in zip(plain.policy.parameters(),
                              wrapped.policy.parameters()):
        np.testing.assert_allclose(
            p_plain.detach().numpy(), p_wrap.detach().numpy(), atol=1e-6,
            err_msg="goal_mode_adv_norm disabled changed training output")


def test_attached_but_disabled_is_also_bit_exact():
    cls = make_goal_mode_adv_norm_ppo_class(PPO)
    m = _make_ppo(cls)
    attach_goal_mode_adv_norm(m, enabled=False, min_group=8)
    assert not hasattr(m, "_goal_mode_step_labels")
    _collect(m)
    adv_before = np.asarray(m.rollout_buffer.advantages).copy()
    m._goal_mode_adv_norm_step()
    np.testing.assert_array_equal(
        adv_before, np.asarray(m.rollout_buffer.advantages))


def test_armed_renormalizes_each_mode_to_zero_mean_unit_std():
    cls = make_goal_mode_adv_norm_ppo_class(PPO)
    m = _make_ppo(cls, n_envs=8)
    attach_goal_mode_adv_norm(m, enabled=True, min_group=8)
    _collect(m)
    labels = np.asarray(
        [lbl for row in m._goal_mode_step_labels for lbl in row],
        dtype=object)
    m._goal_mode_adv_norm_step()
    adv_flat = np.asarray(m.rollout_buffer.advantages).reshape(-1)
    for lbl in _MODES:
        mask = labels == lbl
        if mask.sum() >= 8:
            np.testing.assert_allclose(adv_flat[mask].mean(), 0.0,
                                       atol=1e-6)
            np.testing.assert_allclose(adv_flat[mask].std(), 1.0,
                                       atol=1e-6)


def test_capture_buffer_mismatch_is_a_clean_noop():
    cls = make_goal_mode_adv_norm_ppo_class(PPO)
    m = _make_ppo(cls)
    attach_goal_mode_adv_norm(m, enabled=True, min_group=8)
    _collect(m)
    m._goal_mode_step_labels = m._goal_mode_step_labels[:-1]  # corrupt
    adv_before = np.asarray(m.rollout_buffer.advantages).copy()
    m._goal_mode_adv_norm_step()
    np.testing.assert_array_equal(
        adv_before, np.asarray(m.rollout_buffer.advantages))


def test_only_advantages_change_actions_obs_rewards_untouched():
    cls = make_goal_mode_adv_norm_ppo_class(PPO)
    m = _make_ppo(cls)
    attach_goal_mode_adv_norm(m, enabled=True, min_group=8)
    _collect(m)
    obs_before = np.asarray(m.rollout_buffer.observations).copy()
    act_before = np.asarray(m.rollout_buffer.actions).copy()
    rew_before = np.asarray(m.rollout_buffer.rewards).copy()
    ret_before = np.asarray(m.rollout_buffer.returns).copy()
    m._goal_mode_adv_norm_step()
    np.testing.assert_array_equal(
        obs_before, np.asarray(m.rollout_buffer.observations))
    np.testing.assert_array_equal(
        act_before, np.asarray(m.rollout_buffer.actions))
    np.testing.assert_array_equal(
        rew_before, np.asarray(m.rollout_buffer.rewards))
    np.testing.assert_array_equal(
        ret_before, np.asarray(m.rollout_buffer.returns))


def test_logs_diagnostics_on_armed_success():
    cls = make_goal_mode_adv_norm_ppo_class(PPO)
    m = _make_ppo(cls)
    attach_goal_mode_adv_norm(m, enabled=True, min_group=8)
    _collect(m)

    class _FakeLogger:
        def __init__(self):
            self.name_to_value = {}

        def record(self, key, value):
            self.name_to_value[key] = value

    fake_logger = _FakeLogger()
    m.set_logger(fake_logger)
    m._goal_mode_adv_norm_step()
    assert fake_logger.name_to_value.get(
        GOAL_MODE_ADV_NORM_WANDB_PREFIX + "applied") == 1
    payload = goal_mode_adv_norm_wandb_payload(fake_logger)
    assert payload[GOAL_MODE_ADV_NORM_WANDB_PREFIX + "applied"] == 1.0


def test_wandb_payload_none_logger_is_empty():
    assert goal_mode_adv_norm_wandb_payload(None) == {}


def test_wandb_payload_only_forwards_prefixed_keys():
    class _FakeLogger:
        def __init__(self):
            self.name_to_value = {}

        def record(self, k, v):
            self.name_to_value[k] = v

    fake_logger = _FakeLogger()
    fake_logger.record(GOAL_MODE_ADV_NORM_WANDB_PREFIX + "applied", 1)
    fake_logger.record(GOAL_MODE_ADV_NORM_WANDB_PREFIX + "hold_n", 12)
    fake_logger.record("train/entropy_loss", -1.0)  # unrelated
    payload = goal_mode_adv_norm_wandb_payload(fake_logger)
    assert payload == {
        GOAL_MODE_ADV_NORM_WANDB_PREFIX + "applied": 1.0,
        GOAL_MODE_ADV_NORM_WANDB_PREFIX + "hold_n": 12.0,
    }
