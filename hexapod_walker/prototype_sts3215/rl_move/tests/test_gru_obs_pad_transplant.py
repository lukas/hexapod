"""GRU-to-WIDER-GRU obs-pad transplant (2026-09-24, standwalk rise
start-kind state-conditioning lever, ``rl_move/env.py::
rise_start_kind_sense_obs_dim``): the pre-existing ``--gru +
--obs-pad-transplant`` CLI guard blocked EVERY combination, but its own
docstring reason ("recurrent weights don't transplant from MLP
checkpoints") only applies to a genuine MLP->GRU architecture swap.
``pad_obs_transplant`` (``obs_transplant.py``) already zero-pads ANY
2-D tensor whose last dim equals the obs width by shape alone -- a
GRU's ``weight_ih_l0`` input-to-hidden matrix qualifies exactly like an
MLP's first-layer weight, no change needed there. What ``train_ppo_
mjx.py`` was missing was CONSTRUCTING the wider policy with the
checkpoint's own saved architecture (hidden size, dual/triple/experts,
log_std_split) instead of a hardcoded ``"MlpPolicy"`` -- fixed by
reusing ``old.policy_class``/``old.policy_kwargs`` when ``--gru`` is
armed. This bank proves:

  1. the underlying transplant mechanics on real GRU/Dual-GRU state
     dicts (zero-padded input-to-hidden columns, bit-identical output
     for the parent's original obs padded with zeros, exactly the
     ``pad_obs_transplant`` contract already proven for MLPs);
  2. the CLI guard now accepts a genuine GRU-checkpoint --init-from and
     still refuses a non-recurrent/missing --init-from (the case the
     restriction actually protects against).
"""
from __future__ import annotations

import numpy as np
import pytest
import torch as th
import gymnasium as gym
from gymnasium import spaces
from sb3_contrib import RecurrentPPO
from stable_baselines3.common.vec_env import DummyVecEnv

from rl_move.sim import train_ppo_mjx
from rl_move.sim.gru_policy import (DualGruActorCriticPolicy,
                                    GruActorCriticPolicy)
from rl_move.sim.obs_transplant import pad_obs_transplant

# DualGruActorCriticPolicy's core-routing gate is HARD-WIRED to read the
# LITERAL LAST 3 obs columns (gru_policy._N_LOCO_SLOTS, "walk/turn/quad"
# family one-hot) regardless of task -- appending new obs dims at the
# true tail would shift that one-hot away from the position `_gate`
# reads, silently breaking routing. Production code never hits this:
# `rl_move.env.build_obs` (where `obs.rise_start_kind_sense` inserts
# its 3 dims) always runs BEFORE `walk_task.py`'s own further
# `mode_onehot(mode)` tail append, so the new dims land BEFORE that
# real tail block already, by construction. A synthetic Dual test with
# a generic Box space has no such trailing block to protect, so it
# must use `--obs-pad-insert-at`-style mid-layout insertion (this is
# exactly the pre-existing `insert_at` parameter's documented use
# case) to model the real invariant.
_N_LOCO_SLOTS = 3

OLD_DIM = 20
NEW_DIM = 23
ACT_DIM = 6


def _env(dim):
    class _E(gym.Env):
        observation_space = spaces.Box(-10.0, 10.0, (dim,), dtype=np.float32)
        action_space = spaces.Box(-1.0, 1.0, (ACT_DIM,), dtype=np.float32)

        def reset(self, *, seed=None, options=None):
            return np.zeros(dim, dtype=np.float32), {}

        def step(self, action):
            return (np.zeros(dim, dtype=np.float32), 0.0, False, True, {})
    return _E


def _old_model(policy_cls, seed=1, **policy_kwargs):
    return RecurrentPPO(
        policy_cls, DummyVecEnv([_env(OLD_DIM)]),
        n_steps=8, batch_size=8, seed=seed, verbose=0, device="cpu",
        policy_kwargs=dict(net_arch=[16, 16], lstm_hidden_size=32,
                           **policy_kwargs))


def _wider_model_from_checkpoint(old, seed=2):
    """Mirrors the new train_ppo_mjx.py branch: reconstruct from the
    CHECKPOINT's own saved policy_class/policy_kwargs against a WIDER
    venv, instead of the CLI's own --net-arch/--gru-* flags."""
    return RecurrentPPO(
        old.policy_class, DummyVecEnv([_env(NEW_DIM)]),
        n_steps=8, batch_size=8, seed=seed, verbose=0, device="cpu",
        policy_kwargs=old.policy_kwargs)


@pytest.mark.parametrize("policy_cls,extra_kw,insert_at", [
    (GruActorCriticPolicy, {}, -1),
    # Dual's routing gate needs the 3 trailing "loco" columns preserved
    # at the true tail -- insert the new pad BEFORE them (see the
    # module docstring above `_N_LOCO_SLOTS`).
    (DualGruActorCriticPolicy, {}, OLD_DIM - _N_LOCO_SLOTS),
])
def test_gru_weight_ih_widens_like_an_mlp_first_layer(tmp_path, policy_cls,
                                                       extra_kw, insert_at):
    old = _old_model(policy_cls, **extra_kw)
    ckpt = tmp_path / "old.zip"
    old.save(ckpt)
    old_reloaded = RecurrentPPO.load(ckpt, device="cpu")
    new = _wider_model_from_checkpoint(old_reloaded)
    assert new.observation_space.shape[0] == NEW_DIM

    pad_obs_transplant(old_reloaded, new, NEW_DIM - OLD_DIM,
                       insert_at=insert_at)
    sd_old = old_reloaded.policy.state_dict()
    sd_new = new.policy.state_dict()
    n_pad = NEW_DIM - OLD_DIM
    ins = insert_at if insert_at >= 0 else OLD_DIM
    widened = [k for k in sd_old if sd_old[k].shape != sd_new[k].shape]
    assert any(k.endswith("weight_ih_l0") for k in widened), widened
    for k in widened:
        assert k.endswith("weight_ih_l0"), (
            f"unexpected widened tensor {k} (only input-to-hidden "
            "weights should depend on obs width)")
        w_old, w_new = sd_old[k], sd_new[k]
        assert w_new.shape[1] == NEW_DIM and w_old.shape[1] == OLD_DIM
        assert th.equal(w_new[:, :ins], w_old[:, :ins])
        assert th.equal(w_new[:, ins + n_pad:], w_old[:, ins:])
        assert th.count_nonzero(w_new[:, ins:ins + n_pad]) == 0
    # Every non-widened tensor (weight_hh, biases, action_net, log_std,
    # value_net, ...) copies EXACTLY -- same contract as the MLP case.
    unwidened = [k for k in sd_old if k not in widened]
    assert len(unwidened) > 4  # sanity: the loop actually exercised tensors
    for k in unwidened:
        assert th.equal(sd_new[k], sd_old[k]), k


@pytest.mark.parametrize("policy_cls,extra_kw,insert_at", [
    (GruActorCriticPolicy, {}, -1),
    (DualGruActorCriticPolicy, {}, OLD_DIM - _N_LOCO_SLOTS),
])
def test_gru_transplant_is_bit_identical_for_zero_padded_obs(tmp_path,
                                                              policy_cls,
                                                              extra_kw,
                                                              insert_at):
    old = _old_model(policy_cls, **extra_kw)
    ckpt = tmp_path / "old.zip"
    old.save(ckpt)
    old_reloaded = RecurrentPPO.load(ckpt, device="cpu")
    new = _wider_model_from_checkpoint(old_reloaded)
    n_pad = NEW_DIM - OLD_DIM
    pad_obs_transplant(old_reloaded, new, n_pad, insert_at=insert_at)
    ins = insert_at if insert_at >= 0 else OLD_DIM

    rng = np.random.default_rng(0)
    for _ in range(5):
        obs_old = rng.standard_normal(OLD_DIM).astype(np.float32)
        obs_new = np.concatenate(
            [obs_old[:ins], np.zeros(n_pad, dtype=np.float32),
             obs_old[ins:]])
        act_old, _ = old_reloaded.predict(obs_old, deterministic=True)
        act_new, _ = new.predict(obs_new, deterministic=True)
        np.testing.assert_allclose(act_old, act_new, atol=1e-5)


# ---------------------------------------------------------------------------
# CLI wiring (train_ppo_mjx.main early validation)
# ---------------------------------------------------------------------------

def _run_main_expect_exit(monkeypatch, argv, match):
    monkeypatch.setattr(train_ppo_mjx, "mjx_is_available", lambda: True)
    with pytest.raises(SystemExit, match=match):
        train_ppo_mjx.main(argv)


def test_gru_obs_pad_transplant_still_refused_without_init_from(
        monkeypatch):
    _run_main_expect_exit(
        monkeypatch,
        ["--run-name", "t", "--no-wandb", "--gru", "--obs-pad-transplant",
         "3"],
        "needs --init-from a GRU/recurrent checkpoint")


def test_gru_obs_pad_transplant_still_refused_for_a_non_recurrent_file(
        monkeypatch, tmp_path):
    # A plain MLP checkpoint (the genuinely unsupported case named in
    # the guard's own message: no recurrent weights exist to copy).
    from stable_baselines3 import PPO
    mlp = PPO("MlpPolicy", DummyVecEnv([_env(OLD_DIM)]),
             n_steps=8, batch_size=8, verbose=0, device="cpu")
    fake = tmp_path / "mlp.zip"
    mlp.save(fake)
    _run_main_expect_exit(
        monkeypatch,
        ["--run-name", "t", "--no-wandb", "--gru", "--obs-pad-transplant",
         "3", "--init-from", str(fake)],
        "needs --init-from a GRU/recurrent checkpoint")


def test_gru_obs_pad_transplant_accepted_for_a_real_recurrent_checkpoint(
        monkeypatch, tmp_path):
    """A genuine GRU checkpoint must pass the new guard cleanly -- i.e.
    ``main()`` must proceed PAST this specific check. This test supplies
    none of the other required training plumbing, so ``main()`` goes on
    to fail later for an unrelated reason (either a later CLI
    SystemExit validation, or -- in a test environment without mujoco-
    mjx/jax installed -- a RuntimeError constructing the vec env);
    asserting neither of THIS guard's own messages appears proves the
    guard itself no longer blocks the legitimate case, without needing
    a full mjx/mujoco training stack to actually complete a step."""
    old = _old_model(GruActorCriticPolicy)
    ckpt = tmp_path / "old.zip"
    old.save(ckpt)
    monkeypatch.setattr(train_ppo_mjx, "mjx_is_available", lambda: True)
    with pytest.raises((SystemExit, RuntimeError)) as exc:
        train_ppo_mjx.main(
            ["--run-name", "t", "--no-wandb", "--gru",
             "--obs-pad-transplant", "3", "--init-from", str(ckpt)])
    msg = str(exc.value)
    assert "needs --init-from a GRU/recurrent checkpoint" not in msg
    assert "recurrent weights don't transplant from MLP" not in msg
