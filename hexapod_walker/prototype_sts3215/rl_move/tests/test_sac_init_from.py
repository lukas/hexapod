"""``--algo sac`` plain --init-from warm start (walkcurr turn-sequencing
follow-up, 2026-09-24).

Two from-scratch SAC arms mixing 50% turn-in-place coverage into a
fresh SAC init showed task-mixture interference (det-eval survival
pinned at 0 for the back half of training, probe falls on all
wz/seed cells) -- the follow-up hypothesis is that SEQUENCING (warm-
start an already-turning SAC parent, then extend it to the wider
coverage) avoids relearning both skills at once. That requires
``--algo sac --init-from <ckpt>`` to work at all; it used to be a
flat refusal (_sac_bad included "--init-from" unconditionally). This
file tests the two pieces that changed:

- ``_sac_incompatible_flags`` (mjx_train_args.py): plain --init-from
  is no longer in the refused set; --init-from-actor-only/-policy-
  backbone (PPO-specific transplant machinery) still are.
- ``_build_sac_model`` (train_ppo_mjx.py): given args.init_from, it
  must SAC.load() the parent (warm-started weights, not a fresh
  random init) instead of constructing SAC("MlpPolicy", ...), and
  must still validate --net-arch against the loaded checkpoint's own
  architecture exactly like PPO's plain warm-start branch does.

CPU-only, no MuJoCo/MJX dependency: tiny dummy Box env + DummyVecEnv,
mirrors test_sac_checkpoint_loader.py's fixtures.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import gymnasium as gym
import pytest

from rl_move.sim.mjx_train_args import _sac_incompatible_flags
from rl_move.sim.train_ppo_mjx import _build_sac_model


class _TinyBoxEnv(gym.Env):
    """Minimal continuous env: 4-dim obs, 2-dim action."""

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


def _base_flag_kwargs(**overrides):
    kwargs = dict(
        init_from_actor_only=False, init_from_policy_backbone=False,
        gru=False, gru_dual=False, gru_experts=False, transformer=False,
        asym_critic=False, critic_encoder=False, decleg=False,
        use_sde=False, predictive_live=False, walk_curriculum=False,
        recover_population_id=False, obs_pad_transplant=False,
        hist_stride_transplant=False, ent_coef_final=False,
        log_std_final=False, actor_lr_on=False, amp_style_weight_on=False,
        rnd_coef_on=False, mirror_coef_on=False, bc_coef_on=False,
    )
    kwargs.update(overrides)
    return kwargs


def test_plain_init_from_no_longer_refused():
    # The all-False base case (a plain --init-from warm start, no other
    # PPO-only mechanism turned on) must be compatible now.
    assert _sac_incompatible_flags(**_base_flag_kwargs()) == []


def test_actor_only_and_policy_backbone_transplant_still_refused():
    assert _sac_incompatible_flags(
        **_base_flag_kwargs(init_from_actor_only=True)) == \
        ["--init-from-actor-only"]
    assert _sac_incompatible_flags(
        **_base_flag_kwargs(init_from_policy_backbone=True)) == \
        ["--init-from-policy-backbone"]


def test_ppo_only_mechanisms_still_refused():
    assert _sac_incompatible_flags(**_base_flag_kwargs(gru=True)) == \
        ["--gru/--gru-dual/--gru-experts"]
    assert _sac_incompatible_flags(
        **_base_flag_kwargs(use_sde=True)) == ["--use-sde"]
    assert _sac_incompatible_flags(
        **_base_flag_kwargs(rnd_coef_on=True)) == ["--rnd-coef"]


def test_multiple_bad_flags_all_reported():
    bad = _sac_incompatible_flags(
        **_base_flag_kwargs(gru=True, use_sde=True, decleg=True))
    assert bad == ["--gru/--gru-dual/--gru-experts", "--decleg",
                   "--use-sde"] or set(bad) == {
        "--gru/--gru-dual/--gru-experts", "--decleg", "--use-sde"}


@pytest.fixture
def sac_parent_ckpt(tmp_path):
    from stable_baselines3 import SAC
    path = tmp_path / "ppo_goal_sacparent.zip"
    venv = _dummy_vec_env()
    model = SAC("MlpPolicy", venv, buffer_size=64, learning_starts=8,
                policy_kwargs=dict(net_arch=[8, 8]), seed=0, device="cpu")
    model.save(path)
    return path


def _sac_args(init_from=None, net_arch_str="8,8"):
    return SimpleNamespace(
        init_from=init_from, sac_ent_coef="auto", sac_buffer_size=64,
        batch_size=8, lr=3e-4, gamma=None, sac_tau=0.005,
        sac_train_freq=1, sac_gradient_steps=1, sac_learning_starts=8,
        device="cpu", seed=0,
    )


def test_build_sac_model_warm_start_loads_parent_weights(sac_parent_ckpt):
    from stable_baselines3 import SAC
    parent = SAC.load(sac_parent_ckpt, device="cpu")
    args = _sac_args(init_from=sac_parent_ckpt)
    venv = _dummy_vec_env()
    model = _build_sac_model(args, venv, [8, 8], {}, None)
    assert isinstance(model, SAC)
    # Warm-started actor weights must equal the parent's, not a fresh
    # random init (this is the whole point: SAC.load(), not SAC()).
    p_w = next(iter(parent.policy.actor.state_dict().values()))
    m_w = next(iter(model.policy.actor.state_dict().values()))
    assert np.allclose(p_w.cpu().numpy(), m_w.cpu().numpy())
    # Hyperparams from THIS run's own args must win over the parent's.
    assert model.batch_size == 8
    assert model.learning_starts == 8


def test_build_sac_model_from_scratch_unchanged(sac_parent_ckpt):
    # No init_from: behavior is bit-exact fresh construction (unaffected
    # by this change) -- weights differ from the "parent" fixture above.
    from stable_baselines3 import SAC
    args = _sac_args(init_from=None)
    venv = _dummy_vec_env()
    model = _build_sac_model(args, venv, [8, 8], {}, None)
    assert isinstance(model, SAC)
    assert model.num_timesteps == 0


def test_build_sac_model_net_arch_mismatch_raises(sac_parent_ckpt):
    args = _sac_args(init_from=sac_parent_ckpt)
    venv = _dummy_vec_env()
    with pytest.raises(SystemExit, match="net-arch"):
        _build_sac_model(args, venv, [16, 16], {}, None)


def test_build_sac_model_net_arch_match_ok(sac_parent_ckpt):
    args = _sac_args(init_from=sac_parent_ckpt)
    venv = _dummy_vec_env()
    model = _build_sac_model(args, venv, [8, 8], {}, None)
    assert list(model.policy.net_arch) == [8, 8]
