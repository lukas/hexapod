"""Tests for yaw_critic.py (standwalk reward-decomposed critic, 09-01).

Three layers: (1) pure-numpy GAE cross-checked bit-identical against
stable_baselines3's own ``RolloutBuffer.compute_returns_and_advantage``
on a random synthetic buffer; (2) policy-level unit tests (head
attach/idempotence, detach-trunk gradient isolation, off-path
bit-exactness); (3) a short real ``RecurrentPPO`` + ``DualGruActor
CriticPolicy`` integration smoke test (the ``_TinyDualEnv`` harness
from test_gru_policy.py, extended to emit ``info["reward_walk_yaw"]``)
that exercises the full ``_yaw_credit_step`` path end to end -- the
thing most likely to silently break (wrong buffer layout, wrong
hidden-state row, a shape mismatch that numpy/torch broadcast away
into a wrong-but-not-crashing result)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import torch as th

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "linux_control", ROOT / "linux_control" / "urt2_setup"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import gymnasium as gym  # noqa: E402
from gymnasium import spaces  # noqa: E402

from rl_move.sim.gru_policy import (  # noqa: E402
    DualGruActorCriticPolicy,
    N_MODE_OBS,
)
from rl_move.sim.yaw_critic import (  # noqa: E402
    attach_yaw_credit,
    attach_yaw_value_head,
    compute_gae,
    make_yaw_credit_collect_callback,
    make_yaw_credit_ppo_class,
    value_yaw_over_sequence,
)


def _onehot_tail(slot: int) -> np.ndarray:
    t = np.zeros(N_MODE_OBS, dtype=np.float32)
    t[slot] = 1.0
    return t


# ---------------------------------------------------------------------
# 1. compute_gae vs SB3's own implementation
# ---------------------------------------------------------------------

def test_compute_gae_matches_sb3_random_buffer():
    from stable_baselines3.common.buffers import RolloutBuffer

    rng = np.random.default_rng(0)
    n_steps, n_envs = 12, 3
    obs_space = spaces.Box(-1, 1, (2,), dtype=np.float32)
    act_space = spaces.Box(-1, 1, (1,), dtype=np.float32)
    buf = RolloutBuffer(n_steps, obs_space, act_space, device="cpu",
                        gae_lambda=0.9, gamma=0.97, n_envs=n_envs)
    rewards = rng.normal(size=(n_steps, n_envs)).astype(np.float32)
    values = rng.normal(size=(n_steps, n_envs)).astype(np.float32)
    ep_starts = (rng.uniform(size=(n_steps, n_envs)) < 0.15).astype(
        np.float32)
    ep_starts[0] = 0.0
    for t in range(n_steps):
        buf.add(np.zeros((n_envs, 2), np.float32),
                np.zeros((n_envs, 1), np.float32),
                rewards[t], ep_starts[t],
                th.as_tensor(values[t]), th.zeros(n_envs))
    last_values = rng.normal(size=n_envs).astype(np.float32)
    last_dones = rng.uniform(size=n_envs) < 0.3
    buf.compute_returns_and_advantage(
        th.as_tensor(last_values), last_dones)

    adv, ret = compute_gae(
        rewards, values, ep_starts, last_values, last_dones,
        gamma=0.97, gae_lambda=0.9)

    np.testing.assert_allclose(adv, buf.advantages, atol=1e-6)
    np.testing.assert_allclose(ret, buf.returns, atol=1e-6)


def test_compute_gae_lambda_one_is_monte_carlo_bootstrap():
    # gae_lambda=1, gamma=1, no resets, zero bootstrap: advantage at
    # step t collapses to the plain sum of future rewards minus V(t).
    rewards = np.array([[1.0], [1.0], [1.0]])
    values = np.array([[0.0], [0.0], [0.0]])
    ep_starts = np.zeros((3, 1))
    adv, ret = compute_gae(
        rewards, values, ep_starts, last_values=np.array([0.0]),
        last_dones=np.array([1.0]), gamma=1.0, gae_lambda=1.0)
    np.testing.assert_allclose(adv[:, 0], [3.0, 2.0, 1.0])
    np.testing.assert_allclose(ret[:, 0], [3.0, 2.0, 1.0])


# ---------------------------------------------------------------------
# 2. Policy-level unit tests
# ---------------------------------------------------------------------

def _dual_policy(hidden=8, act_dim=2):
    obs_space = spaces.Box(-1, 1, (3 + N_MODE_OBS,), dtype=np.float32)
    act_space = spaces.Box(-1, 1, (act_dim,), dtype=np.float32)
    return DualGruActorCriticPolicy(
        obs_space, act_space, lr_schedule=lambda _: 3e-4,
        lstm_hidden_size=hidden, net_arch=[16])


def test_attach_yaw_value_head_requires_dual_policy():
    from stable_baselines3.common.policies import ActorCriticPolicy
    obs_space = spaces.Box(-1, 1, (4,), dtype=np.float32)
    act_space = spaces.Box(-1, 1, (2,), dtype=np.float32)
    plain = ActorCriticPolicy(obs_space, act_space, lr_schedule=lambda _: 3e-4)
    with pytest.raises(ValueError):
        attach_yaw_value_head(plain)


def test_attach_yaw_value_head_idempotent_and_mirrors_value_net():
    from rl_move.sim.yaw_critic import _yaw_head
    pol = _dual_policy()
    main_groups_before = [dict(g) for g in pol.optimizer.param_groups]
    attach_yaw_value_head(pol)
    head = _yaw_head(pol)
    w1 = head.weight.clone()
    attach_yaw_value_head(pol)  # second call: no-op, no re-init
    assert _yaw_head(pol) is head
    assert th.equal(_yaw_head(pol).weight, w1)
    assert head.weight.shape == pol.value_net.weight.shape
    # The MAIN optimizer is untouched (own SEPARATE optimizer instead
    # -- see the docstring: an added param group there would change
    # the checkpoint's saved optimizer shape and break loading by any
    # yaw-credit-unaware tool).
    assert pol.optimizer.param_groups == main_groups_before
    yaw_ids = {id(p) for g in pol._yaw_value_optimizer.param_groups
              for p in g["params"]}
    assert all(id(p) in yaw_ids for p in head.parameters())
    # NOT a registered submodule -- must never appear in state_dict()
    # or policy.parameters() (see attach_yaw_value_head's docstring:
    # this is what keeps every checkpoint loadable by yaw-credit-
    # unaware tools).
    sd_keys = pol.state_dict().keys()
    assert not any("yaw" in k.lower() for k in sd_keys), sd_keys
    head_ids = {id(p) for p in head.parameters()}
    assert not any(id(p) in head_ids for p in pol.parameters())


def test_value_yaw_over_sequence_detach_trunk_isolates_gradient():
    pol = _dual_policy()
    attach_yaw_value_head(pol)
    n_seq, T = 2, 5
    obs = th.as_tensor(np.stack([
        np.concatenate([np.random.uniform(-1, 1, 3).astype(np.float32),
                        _onehot_tail(3)])
        for _ in range(n_seq * T)]))
    starts = th.zeros(n_seq * T)
    h0 = th.zeros(1, n_seq, pol.lstm_critic.hidden_size)

    for p in pol.parameters():
        p.grad = None
    v = value_yaw_over_sequence(pol, obs, starts, h0, detach_trunk=True)
    v.sum().backward()
    trunk = (list(pol.lstm_critic.core_a.parameters())
             + list(pol.mlp_extractor.value_net.parameters()))
    for p in trunk:
        assert p.grad is None or float(p.grad.abs().sum()) == 0.0, \
            "detach_trunk leaked gradient into the shared critic trunk"
    from rl_move.sim.yaw_critic import _yaw_head
    assert any(p.grad is not None and float(p.grad.abs().sum()) > 0.0
              for p in _yaw_head(pol).parameters())


def test_value_yaw_over_sequence_without_head_raises():
    pol = _dual_policy()
    obs = th.zeros(1, 3 + N_MODE_OBS)
    h0 = th.zeros(1, 1, pol.lstm_critic.hidden_size)
    with pytest.raises(RuntimeError):
        value_yaw_over_sequence(pol, obs, th.zeros(1), h0)


# ---------------------------------------------------------------------
# 3. Full RecurrentPPO integration smoke test
# ---------------------------------------------------------------------

class _TinyYawEnv(gym.Env):
    """Locomotion-gated (slot=3, core A) env whose reward carries an
    info['reward_walk_yaw'] component -- exactly the sim_env contract
    ``_yaw_credit_step`` reads."""

    def __init__(self):
        self.observation_space = spaces.Box(
            -1, 1, (3 + N_MODE_OBS,), dtype=np.float32)
        self.action_space = spaces.Box(-1, 1, (2,), dtype=np.float32)
        self._t = 0

    def _obs(self):
        core = self.np_random.uniform(-1, 1, 3).astype(np.float32)
        return np.concatenate([core, _onehot_tail(3)])

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self._t = 0
        return self._obs(), {}

    def step(self, action):
        self._t += 1
        yaw_income = float(action[0]) * 0.1
        info = {"reward_walk_yaw": yaw_income}
        return self._obs(), 1.0 + yaw_income, False, self._t >= 8, info


def _yaw_model(coef=1.0, vf_coef=0.5, n_envs=2):
    from sb3_contrib import RecurrentPPO
    from stable_baselines3.common.vec_env import DummyVecEnv

    cls = make_yaw_credit_ppo_class(RecurrentPPO)
    venv = DummyVecEnv([_TinyYawEnv for _ in range(n_envs)])
    model = cls(
        DualGruActorCriticPolicy, venv,
        n_steps=8, batch_size=8, n_epochs=1, seed=0, device="cpu",
        policy_kwargs=dict(lstm_hidden_size=8, net_arch=[16]))
    attach_yaw_value_head(model.policy)
    model.yaw_credit_coef = coef
    model.yaw_credit_vf_coef = vf_coef
    return model


class _DeterministicYawEnv(_TinyYawEnv):
    """Same contract as _TinyYawEnv but with NO gym np_random draws in
    the obs, so two independently-constructed envs (each with their
    own, otherwise unsynchronized, np_random stream) still produce
    identical observation sequences -- isolates the bit-exactness
    check to the training MATH, not to env-seeding plumbing."""

    def _obs(self):
        core = np.array([np.sin(self._t), np.cos(self._t),
                         0.1 * self._t], dtype=np.float32)
        return np.concatenate([core, _onehot_tail(3)])


def test_yaw_credit_checkpoint_loadable_by_a_plain_recurrentppo(tmp_path):
    """Regression for the 09-01 canary crash: the trainer's own
    background video helper (and probe_turn_authority/pod_eval/the
    gate harness -- every consumer that reconstructs the policy from
    ITS OWN saved policy_kwargs before calling set_parameters) loaded
    a yaw-credit checkpoint through a plain, yaw-credit-UNAWARE
    RecurrentPPO.load() and crashed: "Unexpected key(s) in
    state_dict(): value_net_yaw.weight/.bias". The yaw head must never
    appear in the saved state_dict at all."""
    from sb3_contrib import RecurrentPPO

    model = _yaw_model()
    ckpt = tmp_path / "yawcredit_ckpt.zip"
    model.save(ckpt)
    # Must load with the STOCK class, no yaw_critic knowledge at all.
    reloaded = RecurrentPPO.load(ckpt, device="cpu")
    assert isinstance(reloaded.policy, DualGruActorCriticPolicy)


def test_yaw_credit_off_path_is_bit_exact():
    """coef=0 and vf_coef=0 -> _yaw_credit_step is a hard no-op even
    with the collector wired and the head attached: PPO's own train()
    must produce identical params to the un-wrapped class."""
    from sb3_contrib import RecurrentPPO
    from stable_baselines3.common.vec_env import DummyVecEnv

    def _make(cls):
        venv = DummyVecEnv([_DeterministicYawEnv for _ in range(2)])
        m = cls(DualGruActorCriticPolicy, venv, n_steps=8, batch_size=8,
                n_epochs=1, seed=0, device="cpu",
                policy_kwargs=dict(lstm_hidden_size=8, net_arch=[16]))
        m.set_random_seed(0)
        return m

    plain = _make(RecurrentPPO)
    wrapped = _make(make_yaw_credit_ppo_class(RecurrentPPO))
    wrapped.callback = make_yaw_credit_collect_callback()
    assert wrapped.yaw_credit_coef == 0.0
    assert wrapped.yaw_credit_vf_coef == 0.0
    for p_plain, p_wrap in zip(plain.policy.parameters(),
                              wrapped.policy.parameters()):
        p_wrap.data.copy_(p_plain.data)

    from stable_baselines3.common.logger import configure
    plain.set_logger(configure(None, ["stdout"]))
    wrapped.set_logger(configure(None, ["stdout"]))
    # Torch/numpy RNG is a shared GLOBAL stream: running plain.learn()
    # first consumes draws from it, so wrapped.learn() must reseed
    # immediately before its own call to start from the same point
    # plain did (both class' constructors already reseeded to 0
    # earlier, but that reseed is stale by the time we get here).
    plain.set_random_seed(0)
    plain.learn(total_timesteps=16)
    wrapped.set_random_seed(0)
    wrapped.learn(total_timesteps=16)
    for p_plain, p_wrap in zip(plain.policy.parameters(),
                              wrapped.policy.parameters()):
        np.testing.assert_allclose(
            p_plain.detach().numpy(), p_wrap.detach().numpy(),
            atol=1e-6,
            err_msg="yaw_credit_coef=0/vf_coef=0 changed training output")


def test_yaw_credit_step_runs_and_trains_yaw_head():
    """End-to-end: collect a real rollout with the collector callback,
    call train() once, and check the mechanism actually did something
    (yaw value head moved, no exception, sane logged scalars) without
    crashing on shape/layout mistakes."""
    model = _yaw_model()
    from stable_baselines3.common.logger import configure
    model.set_logger(configure(None, ["stdout"]))
    cb = make_yaw_credit_collect_callback()
    from stable_baselines3.common.callbacks import CallbackList
    model.learn(total_timesteps=16, callback=CallbackList([cb]))
    val = model.logger.name_to_value
    assert "train/yaw_credit_vf_loss" in val
    assert "train/yaw_credit_pg_loss" in val
    assert np.isfinite(val["train/yaw_credit_vf_loss"])
    assert np.isfinite(val["train/yaw_credit_pg_loss"])


def test_yaw_credit_step_restores_training_mode():
    """Regression for the 09-01 canary crash: collect_rollouts leaves
    the policy in eval mode (set_training_mode(False)) before
    train() runs; a cuDNN RNN backward pass on GPU REQUIRES training
    mode to have been set before the matching forward, so
    _yaw_credit_step must flip it back to True before it does any of
    its own forward+backward work (CPU torch does not enforce this,
    so a CPU-only test cannot reproduce the crash directly -- this
    pins the fix's observable effect instead)."""
    model = _yaw_model()
    from stable_baselines3.common.logger import configure
    model.set_logger(configure(None, ["stdout"]))
    cb = make_yaw_credit_collect_callback()
    from stable_baselines3.common.callbacks import CallbackList
    model._setup_learn(16, CallbackList([cb]))
    callback = CallbackList([cb])
    callback.init_callback(model)
    callback.on_training_start(locals(), globals())
    model.collect_rollouts(model.env, callback, model.rollout_buffer,
                           model.n_steps)
    assert model.policy.training is False, \
        "test precondition: collect_rollouts should leave eval mode"
    model._yaw_credit_step()  # must not raise, must restore train mode
    assert model.policy.training is True


def test_yaw_credit_step_noop_without_collector_callback():
    """If the collector callback is never wired (a wiring bug),
    _yaw_credit_step must silently no-op, never crash training."""
    model = _yaw_model()
    from stable_baselines3.common.logger import configure
    model.set_logger(configure(None, ["stdout"]))
    model.learn(total_timesteps=16)  # no yaw-credit callback attached
    assert "train/yaw_credit_vf_loss" not in model.logger.name_to_value


def test_yaw_credit_grad_clip_default_off_is_bit_exact():
    """train.yaw_credit_grad_clip defaults to 0.0 (OFF, no clip) --
    with coef/vf_coef > 0 (the pg/vf steps DO run), a wrapped model
    with grad_clip left at its default 0.0 must produce IDENTICAL
    params to one that explicitly sets grad_clip=0.0 (both take the
    unclipped optimizer.step() path); this is the off-path-preserves-
    existing-behavior contract for the 09-01 grad-clip follow-up."""
    model_default = _yaw_model()
    model_explicit_zero = _yaw_model()
    assert model_default.yaw_credit_grad_clip == 0.0  # class default
    model_explicit_zero.yaw_credit_grad_clip = 0.0
    for p_a, p_b in zip(model_default.policy.parameters(),
                        model_explicit_zero.policy.parameters()):
        p_b.data.copy_(p_a.data)
    from stable_baselines3.common.logger import configure
    model_default.set_logger(configure(None, ["stdout"]))
    model_explicit_zero.set_logger(configure(None, ["stdout"]))
    cb_a, cb_b = (make_yaw_credit_collect_callback(),
                 make_yaw_credit_collect_callback())
    from stable_baselines3.common.callbacks import CallbackList
    model_default.set_random_seed(0)
    model_default.learn(total_timesteps=16, callback=CallbackList([cb_a]))
    model_explicit_zero.set_random_seed(0)
    model_explicit_zero.learn(total_timesteps=16,
                              callback=CallbackList([cb_b]))
    for p_a, p_b in zip(model_default.policy.parameters(),
                        model_explicit_zero.policy.parameters()):
        np.testing.assert_allclose(p_a.detach().numpy(),
                                   p_b.detach().numpy(), atol=1e-6)


def test_yaw_credit_grad_clip_actually_clips_the_pg_step():
    """With a large yaw_credit_coef (an artificially huge pg gradient)
    and a tiny grad_clip, the logged train/yaw_credit_grad_norm must
    read ABOVE the clip value (proving clip_grad_norm_ saw a real
    over-budget gradient to clip) and the resulting parameter step
    must be SMALLER than the unclipped sibling's -- the whole point of
    the 09-01 canary-FAIL follow-up (yawcredit-canary-rr1 read worse
    turn authority than its coef=0 control; the extra actor step had
    no trust region at all)."""
    model_clip = _yaw_model(coef=50.0, vf_coef=0.0)
    model_clip.yaw_credit_grad_clip = 1e-3
    model_noclip = _yaw_model(coef=50.0, vf_coef=0.0)
    for p_a, p_b in zip(model_clip.policy.parameters(),
                        model_noclip.policy.parameters()):
        p_b.data.copy_(p_a.data)
    before = {id(p): p.detach().clone()
              for p in model_clip.policy.parameters()}
    from stable_baselines3.common.logger import configure
    model_clip.set_logger(configure(None, ["stdout"]))
    model_noclip.set_logger(configure(None, ["stdout"]))
    from stable_baselines3.common.callbacks import CallbackList
    model_clip.set_random_seed(0)
    model_clip.learn(total_timesteps=16,
                     callback=CallbackList([make_yaw_credit_collect_callback()]))
    model_noclip.set_random_seed(0)
    model_noclip.learn(total_timesteps=16,
                       callback=CallbackList([make_yaw_credit_collect_callback()]))
    val = model_clip.logger.name_to_value
    assert "train/yaw_credit_grad_norm" in val
    assert val["train/yaw_credit_grad_norm"] > model_clip.yaw_credit_grad_clip
    step_clip = sum(
        float(th.norm(p.detach() - before[id(p)]).item())
        for p in model_clip.policy.parameters())
    step_noclip = sum(
        float(th.norm(p_a.detach() - p_b.detach()).item())
        for p_a, p_b in zip(model_noclip.policy.parameters(),
                            model_clip.policy.parameters()))
    assert step_clip > 0.0  # the clipped step still moved something
    # (no direct clip-vs-noclip magnitude comparison across two
    # independently-trained models beyond the grad_norm check above --
    # PPO's own super().train() step also moves params, so a coarse
    # "total drift" comparison would conflate the two updates. The
    # grad_norm assertion above is the decisive, isolated check.)


def test_attach_yaw_credit_wires_grad_clip():
    """attach_yaw_credit's grad_clip kwarg must set the attribute the
    train() override reads, defaulting to 0.0 (off) when omitted."""
    from sb3_contrib import RecurrentPPO
    from stable_baselines3.common.vec_env import DummyVecEnv

    venv = DummyVecEnv([_TinyYawEnv for _ in range(2)])
    cls = make_yaw_credit_ppo_class(RecurrentPPO)
    model = cls(DualGruActorCriticPolicy, venv, n_steps=8, batch_size=8,
               n_epochs=1, seed=0, device="cpu",
               policy_kwargs=dict(lstm_hidden_size=8, net_arch=[16]))
    attach_yaw_credit(model, coef=1.0, vf_coef=0.5,
                      cfg={"reward": {"k_walk_yaw": 1.0}})
    assert model.yaw_credit_grad_clip == 0.0
    attach_yaw_credit(model, coef=1.0, vf_coef=0.5, grad_clip=0.75,
                      cfg={"reward": {"k_walk_yaw": 1.0}})
    assert model.yaw_credit_grad_clip == 0.75


def test_attach_yaw_credit_requires_dual_policy():
    from sb3_contrib import RecurrentPPO
    from stable_baselines3.common.vec_env import DummyVecEnv
    from rl_move.sim.gru_policy import GruActorCriticPolicy

    venv = DummyVecEnv([_TinyYawEnv for _ in range(2)])
    model = RecurrentPPO(
        GruActorCriticPolicy, venv, n_steps=8, batch_size=8,
        n_epochs=1, seed=0, device="cpu",
        policy_kwargs=dict(lstm_hidden_size=8, net_arch=[16]))
    with pytest.raises(SystemExit):
        attach_yaw_credit(model, coef=1.0, vf_coef=0.0,
                          cfg={"reward": {"k_walk_yaw": 1.0}})


def test_attach_yaw_credit_requires_live_reward_channel():
    model = _yaw_model(coef=0.0, vf_coef=0.0)
    with pytest.raises(SystemExit):
        attach_yaw_credit(model, coef=1.0, vf_coef=0.0,
                          cfg={"reward": {"k_walk_yaw": 0.0}})
