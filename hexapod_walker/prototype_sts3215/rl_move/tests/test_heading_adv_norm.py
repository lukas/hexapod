"""Tests for heading_adv_norm.py (candidate 2 of the widen8 off-axis-
heading leg-sacrifice repair, walkcurr, 09-09 -- see the module
docstring for the closure this answers).

Layers: (1) attach-time validation (reuses heading_selfdistill's index
math -- confirms the SAME layout contract, not a re-derivation); (2)
the grouped-normalization math against synthetic advantage arrays with
known on/off-axis membership and deliberately different raw scales;
(3) a real-PPO integration smoke test checking the off path (disabled)
is bit-exact and the armed path actually rewrites
``rollout_buffer.advantages`` while leaving everything else (actions,
observations, rewards) untouched."""
from __future__ import annotations

import numpy as np
import pytest

from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from rl_move.sim.heading_adv_norm import (
    attach_heading_adv_norm,
    heading_adv_norm_wandb_payload,
    make_heading_adv_norm_ppo_class,
    HEADING_ADV_NORM_WANDB_KEYS,
)
from rl_move.sim.heading_selfdistill import (
    heading_frame_width,
    heading_vref_index,
)
# Re-use the exact same tiny env / obs-width contract as
# test_heading_selfdistill.py so both modules are proven to agree on
# the same obs layout independently.
from rl_move.tests.test_heading_selfdistill import (
    _N_ACT,
    _OBS_DIM,
    _TinyHeadingEnv,
    _FakeModel,
)


# ---------------------------------------------------------------------
# 1. Attach-time validation (shares heading_selfdistill's index math).
# ---------------------------------------------------------------------

def test_attach_is_noop_when_disabled():
    m = _FakeModel(obs_dim=999, act_dim=18)  # deliberately bad obs dim
    attach_heading_adv_norm(m, enabled=False, cos_max=0.5, cfg={})
    assert not hasattr(m, "heading_adv_norm_enabled")


def test_attach_raises_on_obs_width_mismatch():
    m = _FakeModel(obs_dim=999, act_dim=18)
    with pytest.raises(SystemExit, match="obs-width mismatch"):
        attach_heading_adv_norm(m, enabled=True, cos_max=0.5, cfg={})


def test_attach_raises_on_nonzero_phase_obs():
    m = _FakeModel(obs_dim=heading_frame_width(18), act_dim=18)
    cfg = {"goal": {"walk_phase_obs": 1.0}}
    with pytest.raises(SystemExit, match="walk_phase_obs"):
        attach_heading_adv_norm(m, enabled=True, cos_max=0.5, cfg=cfg)


def test_attach_raises_on_history_frames_gt_1():
    m = _FakeModel(obs_dim=heading_frame_width(18) * 2, act_dim=18)
    cfg = {"obs": {"history_frames": 2}}
    with pytest.raises(SystemExit, match="history_frames"):
        attach_heading_adv_norm(m, enabled=True, cos_max=0.5, cfg=cfg)


def test_attach_succeeds_and_sets_attrs_on_valid_config():
    n_act = 18
    m = _FakeModel(obs_dim=heading_frame_width(n_act), act_dim=n_act)
    attach_heading_adv_norm(m, enabled=True, cos_max=0.3, cfg={})
    assert m.heading_adv_norm_enabled is True
    assert m.heading_adv_norm_cos_max == 0.3
    assert m._heading_adv_norm_vref_idx == heading_vref_index(n_act)


# ---------------------------------------------------------------------
# 2. Real-PPO integration (same tiny env contract as
#    test_heading_selfdistill.py -- n_act=4, obs width = 58).
# ---------------------------------------------------------------------

def _make_ppo(cls, seed=0):
    venv = DummyVecEnv([lambda: _TinyHeadingEnv(i) for i in range(4)])
    m = cls("MlpPolicy", venv, n_steps=16, batch_size=32, n_epochs=2,
            seed=seed, device="cpu", policy_kwargs=dict(net_arch=[16]))
    m.set_random_seed(seed)
    return m


def test_off_path_is_bit_exact():
    """enabled=False (never attached) -> _heading_adv_norm_step is a
    hard no-op: PPO's own train() must produce identical params to the
    un-wrapped class."""
    plain = _make_ppo(PPO)
    wrapped = _make_ppo(make_heading_adv_norm_ppo_class(PPO))
    assert wrapped.heading_adv_norm_enabled is False
    for p_plain, p_wrap in zip(plain.policy.parameters(),
                              wrapped.policy.parameters()):
        p_wrap.data.copy_(p_plain.data)

    from stable_baselines3.common.logger import configure
    plain.set_logger(configure(None, ["stdout"]))
    wrapped.set_logger(configure(None, ["stdout"]))
    plain.set_random_seed(0)
    plain.learn(total_timesteps=32)
    wrapped.set_random_seed(0)
    wrapped.learn(total_timesteps=32)
    for p_plain, p_wrap in zip(plain.policy.parameters(),
                              wrapped.policy.parameters()):
        np.testing.assert_allclose(
            p_plain.detach().numpy(), p_wrap.detach().numpy(),
            atol=1e-6,
            err_msg="heading_adv_norm disabled changed training output")


def test_attached_but_disabled_is_also_bit_exact():
    """Attaching with enabled=False is a no-op too (defensive: a caller
    that always calls attach_heading_adv_norm but gates enabled must
    still be bit-exact off)."""
    cls = make_heading_adv_norm_ppo_class(PPO)
    m = _make_ppo(cls)
    attach_heading_adv_norm(m, enabled=False, cos_max=0.5, cfg={})
    assert not hasattr(m, "_heading_adv_norm_vref_idx")
    _, callback = m._setup_learn(total_timesteps=16, callback=None)
    m.collect_rollouts(m.env, callback=callback,
                      rollout_buffer=m.rollout_buffer, n_rollout_steps=16)
    adv_before = np.asarray(m.rollout_buffer.advantages).copy()
    m._heading_adv_norm_step()
    np.testing.assert_array_equal(adv_before,
                                  np.asarray(m.rollout_buffer.advantages))


def test_armed_renormalizes_each_group_to_zero_mean_unit_std():
    """Real rollout: after the step, BOTH the on-axis and off-axis
    subsets of buf.advantages must independently read mean~0/std~1,
    even though the tiny env's two headings drive very different raw
    reward/advantage scales."""
    cls = make_heading_adv_norm_ppo_class(PPO)
    m = _make_ppo(cls)
    attach_heading_adv_norm(m, enabled=True, cos_max=0.5, cfg={})
    _, callback = m._setup_learn(total_timesteps=16, callback=None)
    m.collect_rollouts(m.env, callback=callback,
                      rollout_buffer=m.rollout_buffer, n_rollout_steps=16)

    idx = m._heading_adv_norm_vref_idx
    obs = np.asarray(m.rollout_buffer.observations)
    n_steps, n_envs, obs_dim = obs.shape
    obs_flat = obs.reshape(n_steps * n_envs, obs_dim)
    from rl_move.sim.heading_selfdistill import heading_cos
    cos_h = heading_cos(obs_flat[:, idx:idx + 2])
    off_axis = cos_h <= 0.5

    m._heading_adv_norm_step()

    adv_flat = np.asarray(m.rollout_buffer.advantages).reshape(-1)
    if off_axis.sum() >= 8 and (~off_axis).sum() >= 8:
        np.testing.assert_allclose(adv_flat[off_axis].mean(), 0.0,
                                   atol=1e-6)
        np.testing.assert_allclose(adv_flat[off_axis].std(), 1.0,
                                   atol=1e-6)
        np.testing.assert_allclose(adv_flat[~off_axis].mean(), 0.0,
                                   atol=1e-6)
        np.testing.assert_allclose(adv_flat[~off_axis].std(), 1.0,
                                   atol=1e-6)


def test_noop_when_one_group_too_small(monkeypatch):
    """cos_max set so essentially every tick lands in ONE group ->
    fewer than 8 samples in the other -> clean no-op (advantages
    byte-identical, no crash)."""
    cls = make_heading_adv_norm_ppo_class(PPO)
    m = _make_ppo(cls)
    attach_heading_adv_norm(m, enabled=True, cos_max=-2.0, cfg={})
    _, callback = m._setup_learn(total_timesteps=16, callback=None)
    m.collect_rollouts(m.env, callback=callback,
                      rollout_buffer=m.rollout_buffer, n_rollout_steps=16)
    adv_before = np.asarray(m.rollout_buffer.advantages).copy()
    m._heading_adv_norm_step()
    np.testing.assert_array_equal(adv_before,
                                  np.asarray(m.rollout_buffer.advantages))


def test_only_advantages_change_actions_obs_rewards_untouched():
    cls = make_heading_adv_norm_ppo_class(PPO)
    m = _make_ppo(cls)
    attach_heading_adv_norm(m, enabled=True, cos_max=0.5, cfg={})
    _, callback = m._setup_learn(total_timesteps=16, callback=None)
    m.collect_rollouts(m.env, callback=callback,
                      rollout_buffer=m.rollout_buffer, n_rollout_steps=16)
    obs_before = np.asarray(m.rollout_buffer.observations).copy()
    act_before = np.asarray(m.rollout_buffer.actions).copy()
    rew_before = np.asarray(m.rollout_buffer.rewards).copy()
    ret_before = np.asarray(m.rollout_buffer.returns).copy()
    m._heading_adv_norm_step()
    np.testing.assert_array_equal(
        obs_before, np.asarray(m.rollout_buffer.observations))
    np.testing.assert_array_equal(
        act_before, np.asarray(m.rollout_buffer.actions))
    np.testing.assert_array_equal(
        rew_before, np.asarray(m.rollout_buffer.rewards))
    np.testing.assert_array_equal(
        ret_before, np.asarray(m.rollout_buffer.returns))


def test_logs_diagnostics_on_armed_success():
    cls = make_heading_adv_norm_ppo_class(PPO)
    m = _make_ppo(cls)
    attach_heading_adv_norm(m, enabled=True, cos_max=0.5, cfg={})
    _, callback = m._setup_learn(total_timesteps=16, callback=None)
    m.collect_rollouts(m.env, callback=callback,
                      rollout_buffer=m.rollout_buffer, n_rollout_steps=16)

    class _FakeLogger:
        def __init__(self):
            self.values = {}
            self.name_to_value = self.values

        def record(self, key, value):
            self.values[key] = value

    fake_logger = _FakeLogger()
    m.set_logger(fake_logger)
    m._heading_adv_norm_step()
    if fake_logger.values.get("train/heading_adv_norm_applied") == 1:
        assert "train/heading_adv_norm_on_std_pre" in fake_logger.values
        assert "train/heading_adv_norm_off_std_pre" in fake_logger.values
    assert "train/heading_adv_norm_off_axis_frac" in fake_logger.values
    assert 0.0 <= fake_logger.values[
        "train/heading_adv_norm_off_axis_frac"] <= 1.0


# ---------------------------------------------------------------------
# 3. W&B forwarding.
# ---------------------------------------------------------------------

def test_wandb_payload_none_logger_is_empty():
    assert heading_adv_norm_wandb_payload(None) == {}


def test_wandb_payload_forwards_recorded_keys():
    class _FakeLogger:
        def __init__(self):
            self.name_to_value = {}

        def record(self, k, v):
            self.name_to_value[k] = v

    fake_logger = _FakeLogger()
    fake_logger.record("train/heading_adv_norm_off_axis_frac", 0.3)
    fake_logger.record("train/heading_adv_norm_applied", 1)
    fake_logger.record("train/heading_adv_norm_on_std_pre", 2.5)
    fake_logger.record("train/heading_adv_norm_off_std_pre", 0.8)
    fake_logger.record("train/entropy_loss", -1.0)  # unrelated, must not leak
    payload = heading_adv_norm_wandb_payload(fake_logger)
    assert payload == {
        "train/heading_adv_norm_off_axis_frac": 0.3,
        "train/heading_adv_norm_applied": 1.0,
        "train/heading_adv_norm_on_std_pre": 2.5,
        "train/heading_adv_norm_off_std_pre": 0.8,
    }
    assert set(HEADING_ADV_NORM_WANDB_KEYS) == set(payload)
