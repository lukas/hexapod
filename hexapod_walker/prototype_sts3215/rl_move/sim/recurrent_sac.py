"""From-scratch recurrent (GRU) actor+critic SAC with a genuine hidden
state (not frame-stacking) threaded across real rollout steps, trained
via truncated BPTT over short zero-start windows sampled from a
sequence-aware replay buffer.

WHY (walkcurr rl_only lower-role lineage, 2026-10-04, STATUS.md "Next"
item 1, now the lead lever): the converged L2+L5 2-leg terminal-support
habit survived every reward/curriculum/perturbation/actuator-capability
lever, AND a 3-seed population-level test of plain observation-history
stacking + current-sense (``obs.history_frames=16`` + ``obs.current_
sense=1``, no recurrence, just a wider instantaneous feature vector):
0/36 composed lower_ok EVERY seed, worse than every individual baseline
seed (walkcurr/STATUS.md CLOSED list, drramp-histcur16-acq1). That
closes "more/older raw frames in a feedforward net" as an explanation.
What is still untried is a policy that carries its OWN internal state
forward across time (a hidden vector updated every tick, not reset or
recomputed from a fixed window) -- the architecture class a GRU
provides and a plain MLP, however wide its input, structurally cannot.

SIMPLIFICATION (explicit, v1): training windows are "zero-start" --
the hidden state is initialized to zero at the start of EVERY sampled
training window (never carried in from a stored rollout hidden state,
R2D2-style). This is a known, accepted simpler variant (R2D2's own
"zero state" ablation baseline): weaker than stored-state, but it
already tests the real question in play (does ANY genuine within-
window recurrence beat a feedforward/frame-stack policy at this task),
and is far simpler to get right in one pass. If this shows a real
signal, stored-state hidden (threading the ACTUAL rollout hidden state
through the replay buffer) is the natural v2 refinement.

The ROLLOUT/eval-time hidden state (used to actually drive the robot,
in ``RecurrentSAC._sample_action`` and in ``RecurrentSACPolicy.
predict``) is the REAL thing: a persistent GRU hidden vector carried
across every real env tick within an episode, reset only at episode
boundaries -- exactly the contract the existing ``--gru``/
``RecurrentActorCriticPolicy`` (PPO) path already uses (``gru_policy.
RecurrentPredictor``), which is why this module deliberately mirrors
that policy's ``predict(obs, state, episode_start, deterministic)``
call convention and exposes a (duck-typed, non-functional) ``lstm_
actor`` attribute: every existing generic dispatcher in this codebase
that gates recurrent-aware handling on ``getattr(model.policy,
"lstm_actor", None) is not None`` (``gru_policy.wrap_recurrent_
predictor``, ``eval_checkpoint.evaluate``) picks this policy up for
free, with zero changes to those call sites.

Wired into train_ppo_mjx.py behind ``--algo sac --recurrent-sac``
(default off; plain ``--algo sac`` is bit-exact unaffected -- see
``_build_sac_model``). Nothing in this module runs unless a caller
explicitly asks for it.
"""
from __future__ import annotations

from collections import deque
from typing import Any, NamedTuple

import numpy as np
import torch as th
from torch import nn
from gymnasium import spaces

from stable_baselines3.common.off_policy_algorithm import OffPolicyAlgorithm
from stable_baselines3.common.policies import BasePolicy
from stable_baselines3.common.preprocessing import (
    get_action_dim, get_flattened_obs_dim,
)
from stable_baselines3.common.distributions import (
    SquashedDiagGaussianDistribution,
)
from stable_baselines3.common.utils import polyak_update, get_device

LOG_STD_MIN = -20.0
LOG_STD_MAX = 2.0


# --------------------------------------------------------------------
# Networks
# --------------------------------------------------------------------
class GRUGaussianActor(nn.Module):
    """Single-layer GRU actor: obs_t, h_{t-1} -> (mean, log_std), h_t.

    Conditions ONLY on observations (never its own past actions) so its
    hidden state at any tick is a pure function of the observation
    sequence alone -- the whole burn-in-free window can be processed in
    one batched pass regardless of which actions end up being evaluated
    at each tick (see ``action_log_prob_seq``).
    """

    def __init__(self, obs_dim: int, act_dim: int, hidden_size: int):
        super().__init__()
        self.obs_dim = int(obs_dim)
        self.act_dim = int(act_dim)
        self.hidden_size = int(hidden_size)
        self.cell = nn.GRUCell(self.obs_dim, self.hidden_size)
        self.mu = nn.Linear(self.hidden_size, self.act_dim)
        self.log_std = nn.Linear(self.hidden_size, self.act_dim)
        self.action_dist = SquashedDiagGaussianDistribution(self.act_dim)

    def step(self, obs_t: th.Tensor, h_prev: th.Tensor):
        h = self.cell(obs_t, h_prev)
        mu = self.mu(h)
        log_std = th.clamp(self.log_std(h), LOG_STD_MIN, LOG_STD_MAX)
        return mu, log_std, h

    def forward_seq(self, obs_seq: th.Tensor, h0: th.Tensor):
        """``obs_seq``: (B, T, obs_dim). Returns mu/log_std (B,T,act_dim)
        and h_seq (B,T,hidden) (hidden AFTER each step)."""
        B, T, _ = obs_seq.shape
        h = h0
        mus, log_stds, hs = [], [], []
        for t in range(T):
            mu, log_std, h = self.step(obs_seq[:, t, :], h)
            mus.append(mu)
            log_stds.append(log_std)
            hs.append(h)
        return (th.stack(mus, dim=1), th.stack(log_stds, dim=1),
                th.stack(hs, dim=1))

    def action_log_prob_seq(self, obs_seq: th.Tensor, h0: th.Tensor):
        B, T, _ = obs_seq.shape
        mu_seq, log_std_seq, h_seq = self.forward_seq(obs_seq, h0)
        flat_mu = mu_seq.reshape(B * T, self.act_dim)
        flat_log_std = log_std_seq.reshape(B * T, self.act_dim)
        action_flat, log_prob_flat = self.action_dist.log_prob_from_params(
            flat_mu, flat_log_std)
        action_seq = action_flat.reshape(B, T, self.act_dim)
        log_prob_seq = log_prob_flat.reshape(B, T, 1)
        return action_seq, log_prob_seq, h_seq

    def act_step(self, obs_t: th.Tensor, h_prev: th.Tensor,
                 deterministic: bool = False):
        mu, log_std, h = self.step(obs_t, h_prev)
        if deterministic:
            action = self.action_dist.actions_from_params(
                mu, log_std, deterministic=True)
        else:
            action, _log_prob = self.action_dist.log_prob_from_params(
                mu, log_std)
        return action, h


class _GRUQNet(nn.Module):
    """One Q network of the twin-Q critic: (obs_t, act_t), h_{t-1} -> q_t, h_t."""

    def __init__(self, obs_dim: int, act_dim: int, hidden_size: int):
        super().__init__()
        self.cell = nn.GRUCell(obs_dim + act_dim, hidden_size)
        self.q = nn.Linear(hidden_size, 1)

    def step(self, obs_t: th.Tensor, act_t: th.Tensor, h_prev: th.Tensor):
        x = th.cat([obs_t, act_t], dim=-1)
        h = self.cell(x, h_prev)
        return self.q(h), h

    def forward_seq(self, obs_seq: th.Tensor, act_seq: th.Tensor,
                    h0: th.Tensor):
        B, T, _ = obs_seq.shape
        h = h0
        qs, hs = [], []
        for t in range(T):
            q, h = self.step(obs_seq[:, t, :], act_seq[:, t, :], h)
            qs.append(q)
            hs.append(h)
        return th.stack(qs, dim=1), th.stack(hs, dim=1)


class GRUTwinQ(nn.Module):
    """``n_critics`` fully-independent ``_GRUQNet`` (separate weights
    throughout, mirroring SB3's own ``ContinuousCritic`` -- NOT a
    shared trunk with two heads, to keep the twin-Q decorrelation SAC
    relies on for overestimation-bias control)."""

    def __init__(self, obs_dim: int, act_dim: int, hidden_size: int,
                 n_critics: int = 2):
        super().__init__()
        self.hidden_size = int(hidden_size)
        self.qnets = nn.ModuleList(
            [_GRUQNet(obs_dim, act_dim, hidden_size)
             for _ in range(n_critics)])

    def forward_seq(self, obs_seq: th.Tensor, act_seq: th.Tensor,
                    h0: th.Tensor):
        q_list, h_list = [], []
        for qnet in self.qnets:
            q_seq, h_seq = qnet.forward_seq(obs_seq, act_seq, h0)
            q_list.append(q_seq)
            h_list.append(h_seq)
        return q_list, h_list


# --------------------------------------------------------------------
# Policy
# --------------------------------------------------------------------
class RecurrentSACPolicy(BasePolicy):
    """SAC policy wrapping ``GRUGaussianActor``/``GRUTwinQ``.

    ``predict(observation, state, episode_start, deterministic)``
    mirrors sb3-contrib's ``RecurrentActorCriticPolicy.predict`` exactly
    (state: a plain (n_envs, hidden_size) ndarray here, not an LSTM
    tuple-pair) so every existing hidden-state-threading shim in this
    codebase (``gru_policy.RecurrentPredictor``) works UNMODIFIED.
    """

    def __init__(self, observation_space: spaces.Space,
                 action_space: spaces.Box, lr_schedule,
                 hidden_size: int = 128, n_critics: int = 2,
                 **kwargs: Any):
        super().__init__(observation_space, action_space,
                         squash_output=True)
        if kwargs:
            # Accept-and-ignore unknown policy_kwargs (e.g. a shared
            # --net-arch/--activation-fn the CLI always passes) rather
            # than crash -- this architecture does not use them (its
            # own --rsac-hidden-size is the one knob), but refusing an
            # ignored, harmless kwarg here would make this the only
            # SAC variant in the codebase that can't share the common
            # CLI plumbing.
            pass
        self.obs_dim = int(get_flattened_obs_dim(observation_space))
        self.act_dim = int(get_action_dim(action_space))
        self.hidden_size = int(hidden_size)
        self.n_critics = int(n_critics)
        self.actor = GRUGaussianActor(self.obs_dim, self.act_dim,
                                      self.hidden_size)
        self.critic = GRUTwinQ(self.obs_dim, self.act_dim,
                               self.hidden_size, self.n_critics)
        self.critic_target = GRUTwinQ(self.obs_dim, self.act_dim,
                                      self.hidden_size, self.n_critics)
        self.critic_target.load_state_dict(self.critic.state_dict())
        for p in self.critic_target.parameters():
            p.requires_grad_(False)
        self.critic_target.eval()
        # Duck-typed marker ONLY: every existing generic dispatcher in
        # this codebase gates hidden-state-threading wraps on
        # ``getattr(policy, "lstm_actor", None) is not None`` (NOT an
        # isinstance/class check) -- see gru_policy.wrap_recurrent_
        # predictor / eval_checkpoint.evaluate. Pointing it at the
        # actor's own GRUCell (any non-None module works; it is never
        # called as an LSTM) makes this policy recognized by every one
        # of those call sites for free.
        self.lstm_actor = self.actor.cell

    def _get_constructor_parameters(self) -> dict:
        data = super()._get_constructor_parameters()
        data.update(hidden_size=self.hidden_size, n_critics=self.n_critics)
        return data

    def _build_optimizers(self, lr_schedule) -> None:
        self.actor.optimizer = th.optim.Adam(self.actor.parameters(),
                                             lr=lr_schedule(1))
        self.critic.optimizer = th.optim.Adam(self.critic.parameters(),
                                              lr=lr_schedule(1))

    def set_training_mode(self, mode: bool) -> None:
        self.actor.train(mode)
        self.critic.train(mode)
        self.training = mode

    def _predict(self, observation: th.Tensor,
                deterministic: bool = False) -> th.Tensor:
        """Stateless single-call fallback (zero hidden state) for
        generic SB3 tooling that calls ``_predict`` directly. NEVER use
        this for a real rollout/eval episode -- it re-zeros the hidden
        state every call, exactly the "lobotomy" ``RecurrentPredictor``
        exists to avoid. Real rollout/eval always goes through
        ``predict()`` (state-threaded) or ``RecurrentSAC._sample_action``
        (rollout-hidden-threaded)."""
        n = observation.shape[0]
        h0 = th.zeros(n, self.hidden_size, device=observation.device)
        action, _h = self.actor.act_step(observation, h0,
                                         deterministic=deterministic)
        return action

    def predict(self, observation, state=None, episode_start=None,
               deterministic: bool = False):
        self.set_training_mode(False)
        obs_tensor, vectorized_env = self.obs_to_tensor(observation)
        n_envs = obs_tensor.shape[0]
        if state is None:
            h = np.zeros((n_envs, self.hidden_size), dtype=np.float32)
        else:
            h = np.asarray(state, dtype=np.float32)
        if episode_start is None:
            episode_start = np.zeros((n_envs,), dtype=bool)
        episode_start = np.asarray(episode_start, dtype=bool)
        h = h.copy()
        h[episode_start] = 0.0
        h_t = th.as_tensor(h, device=self.device)
        with th.no_grad():
            action_t, h_new = self.actor.act_step(
                obs_tensor, h_t, deterministic=deterministic)
        actions = action_t.cpu().numpy().reshape(
            (-1, *self.action_space.shape))
        if isinstance(self.action_space, spaces.Box):
            if self.squash_output:
                actions = self.unscale_action(actions)
            else:
                actions = np.clip(actions, self.action_space.low,
                                  self.action_space.high)
        new_state = h_new.cpu().numpy()
        if not vectorized_env:
            actions = actions.squeeze(axis=0)
        return actions, new_state


# --------------------------------------------------------------------
# Sequence-aware replay buffer
# --------------------------------------------------------------------
class SequenceReplayBufferSamples(NamedTuple):
    observations: th.Tensor
    actions: th.Tensor
    rewards: th.Tensor
    next_observations: th.Tensor
    dones: th.Tensor
    mask: th.Tensor


class SequenceReplayBuffer:
    """Stores COMPLETE episodes (not flat transitions) and samples
    fixed-length, zero-start windows for truncated-BPTT SAC training.

    ``add()`` matches ``stable_baselines3.common.buffers.ReplayBuffer.
    add``'s exact call signature so it drops straight into
    ``OffPolicyAlgorithm._setup_model``'s ``replay_buffer_class``
    plug-in point (same pattern as ``sac_bank_buffer.
    BankDownweightReplayBuffer``) -- a per-env ongoing-episode list is
    finalized into the sampleable bank on ``done``, evicting the
    OLDEST complete episodes once the total stored transitions exceed
    ``buffer_size`` (never evicts mid-write episodes).

    A ``TimeLimit.truncated`` info flag zeroes the bootstrap-discount
    ``done`` the same way SB3's own ``ReplayBuffer`` does (a truncated-
    by-timeout episode must still bootstrap value past its last step;
    only a TRUE termination should not) -- episode BOUNDARY detection
    (when to finalize) still uses the raw ``done``, only the stored
    bootstrap flag is corrected.

    ``sample()`` picks episodes weighted by length (approximating
    per-transition-uniform sampling) then a uniform window start;
    episodes shorter than ``seq_len`` are right-padded with zeros and
    ``mask=0`` (real data occupies the window's front, so the hidden
    state entering the real region is never built from padding).
    """

    def __init__(self, buffer_size: int, observation_space: spaces.Space,
                action_space: spaces.Box, device: Any = "auto",
                n_envs: int = 1, optimize_memory_usage: bool = False,
                seq_len: int = 16,
                handle_timeout_termination: bool = True):
        if optimize_memory_usage:
            raise NotImplementedError(
                "SequenceReplayBuffer only supports "
                "optimize_memory_usage=False")
        self.buffer_size = int(buffer_size)
        self.observation_space = observation_space
        self.action_space = action_space
        self.obs_dim = int(get_flattened_obs_dim(observation_space))
        self.act_dim = int(get_action_dim(action_space))
        self.device = get_device(device)
        self.n_envs = int(n_envs)
        self.seq_len = int(seq_len)
        self.handle_timeout_termination = bool(handle_timeout_termination)
        self._cur: list[dict] = [
            dict(obs=[], next_obs=[], act=[], rew=[], done=[])
            for _ in range(self.n_envs)]
        self._episodes: deque = deque()
        self._total_transitions = 0

    def num_episodes(self) -> int:
        return len(self._episodes)

    def size(self) -> int:
        return self._total_transitions

    def add(self, obs, next_obs, action, reward, done, infos) -> None:
        obs = np.asarray(obs, dtype=np.float32).reshape(self.n_envs, -1)
        next_obs = np.asarray(next_obs,
                              dtype=np.float32).reshape(self.n_envs, -1)
        action = np.asarray(action,
                            dtype=np.float32).reshape(self.n_envs, -1)
        reward = np.asarray(reward, dtype=np.float32).reshape(self.n_envs)
        done = np.asarray(done, dtype=bool).reshape(self.n_envs)
        if self.handle_timeout_termination:
            bootstrap_done = np.array(
                [d and not bool(info.get("TimeLimit.truncated", False))
                 for d, info in zip(done, infos)])
        else:
            bootstrap_done = done
        for i in range(self.n_envs):
            c = self._cur[i]
            c["obs"].append(obs[i].copy())
            c["next_obs"].append(next_obs[i].copy())
            c["act"].append(action[i].copy())
            c["rew"].append(float(reward[i]))
            c["done"].append(bool(bootstrap_done[i]))
            if done[i]:
                self._finalize_episode(i)

    def _finalize_episode(self, i: int) -> None:
        c = self._cur[i]
        length = len(c["obs"])
        if length > 0:
            ep = dict(
                obs=np.stack(c["obs"]).astype(np.float32),
                next_obs=np.stack(c["next_obs"]).astype(np.float32),
                act=np.stack(c["act"]).astype(np.float32),
                rew=np.asarray(c["rew"], dtype=np.float32),
                done=np.asarray(c["done"], dtype=np.float32),
                length=length)
            self._episodes.append(ep)
            self._total_transitions += length
            while (self._total_transitions > self.buffer_size
                  and len(self._episodes) > 1):
                old = self._episodes.popleft()
                self._total_transitions -= old["length"]
        self._cur[i] = dict(obs=[], next_obs=[], act=[], rew=[], done=[])

    def sample(self, batch_size: int,
              device: Any = None) -> SequenceReplayBufferSamples:
        if not self._episodes:
            raise RuntimeError(
                "SequenceReplayBuffer.sample() called with zero "
                "completed episodes -- caller must gate on "
                "num_episodes() > 0 first")
        dev = self.device if device is None else device
        episodes = list(self._episodes)
        lengths = np.array([ep["length"] for ep in episodes],
                           dtype=np.float64)
        probs = lengths / lengths.sum()
        idxs = np.random.choice(len(episodes), size=batch_size, p=probs)
        L = self.seq_len
        obs_b = np.zeros((batch_size, L, self.obs_dim), dtype=np.float32)
        next_obs_b = np.zeros((batch_size, L, self.obs_dim),
                              dtype=np.float32)
        act_b = np.zeros((batch_size, L, self.act_dim), dtype=np.float32)
        rew_b = np.zeros((batch_size, L, 1), dtype=np.float32)
        done_b = np.zeros((batch_size, L, 1), dtype=np.float32)
        mask_b = np.zeros((batch_size, L), dtype=np.float32)
        for b, idx in enumerate(idxs):
            ep = episodes[idx]
            Le = ep["length"]
            if Le >= L:
                s = int(np.random.randint(0, Le - L + 1))
                sl = slice(s, s + L)
                obs_b[b] = ep["obs"][sl]
                next_obs_b[b] = ep["next_obs"][sl]
                act_b[b] = ep["act"][sl]
                rew_b[b, :, 0] = ep["rew"][sl]
                done_b[b, :, 0] = ep["done"][sl]
                mask_b[b] = 1.0
            else:
                obs_b[b, :Le] = ep["obs"]
                next_obs_b[b, :Le] = ep["next_obs"]
                act_b[b, :Le] = ep["act"]
                rew_b[b, :Le, 0] = ep["rew"]
                done_b[b, :Le, 0] = ep["done"]
                mask_b[b, :Le] = 1.0
        return SequenceReplayBufferSamples(
            observations=th.as_tensor(obs_b, device=dev),
            actions=th.as_tensor(act_b, device=dev),
            rewards=th.as_tensor(rew_b, device=dev),
            next_observations=th.as_tensor(next_obs_b, device=dev),
            dones=th.as_tensor(done_b, device=dev),
            mask=th.as_tensor(mask_b, device=dev))


# --------------------------------------------------------------------
# Algorithm
# --------------------------------------------------------------------
class RecurrentSAC(OffPolicyAlgorithm):
    """From-scratch-only (no ``--init-from`` support in v1) recurrent
    SAC. See module docstring for the full design; ``train()`` below is
    the only place the math differs from plain SB3 ``SAC.train`` --
    every loss term mirrors it exactly, extended from single ticks to
    masked (B, seq_len) windows."""

    def __init__(self, policy, env, learning_rate: float = 3e-4,
                buffer_size: int = 1_000_000, learning_starts: int = 100,
                batch_size: int = 256, tau: float = 0.005,
                gamma: float = 0.99, train_freq=1, gradient_steps: int = 1,
                replay_buffer_class=None, replay_buffer_kwargs=None,
                ent_coef="auto", target_entropy="auto",
                target_update_interval: int = 1, seq_len: int = 16,
                tensorboard_log=None, policy_kwargs=None, verbose: int = 0,
                seed=None, device="auto", _init_setup_model: bool = True):
        if replay_buffer_class is None:
            replay_buffer_class = SequenceReplayBuffer
        replay_buffer_kwargs = dict(replay_buffer_kwargs or {})
        replay_buffer_kwargs.setdefault("seq_len", seq_len)
        super().__init__(
            policy, env, learning_rate, buffer_size, learning_starts,
            batch_size, tau, gamma, train_freq, gradient_steps,
            action_noise=None, replay_buffer_class=replay_buffer_class,
            replay_buffer_kwargs=replay_buffer_kwargs,
            policy_kwargs=policy_kwargs, tensorboard_log=tensorboard_log,
            verbose=verbose, device=device, seed=seed,
            supported_action_spaces=(spaces.Box,), support_multi_env=True)
        self.seq_len = int(seq_len)
        self.target_entropy = target_entropy
        self.ent_coef = ent_coef
        self.target_update_interval = int(target_update_interval)
        self.log_ent_coef = None
        self.ent_coef_optimizer = None
        self._rsac_prev_dones = None
        self._rollout_hidden = None
        if _init_setup_model:
            self._setup_model()

    def _setup_model(self) -> None:
        super()._setup_model()
        self.policy._build_optimizers(self.lr_schedule)
        self.actor = self.policy.actor
        self.critic = self.policy.critic
        self.critic_target = self.policy.critic_target
        if self.target_entropy == "auto":
            self.target_entropy = float(
                -np.prod(self.action_space.shape).astype(np.float32))
        else:
            self.target_entropy = float(self.target_entropy)
        if isinstance(self.ent_coef, str) and self.ent_coef.startswith("auto"):
            init_value = 1.0
            if "_" in self.ent_coef:
                init_value = float(self.ent_coef.split("_")[1])
                assert init_value > 0.0
            self.log_ent_coef = th.log(
                th.ones(1, device=self.device) * init_value
            ).requires_grad_(True)
            self.ent_coef_optimizer = th.optim.Adam(
                [self.log_ent_coef], lr=self.lr_schedule(1))
        else:
            self.ent_coef_tensor = th.tensor(float(self.ent_coef),
                                             device=self.device)

    def _excluded_save_params(self) -> list[str]:
        return super()._excluded_save_params() + [
            "actor", "critic", "critic_target"]

    def _get_torch_save_params(self):
        state_dicts = ["policy", "actor.optimizer", "critic.optimizer"]
        if self.ent_coef_optimizer is not None:
            saved_pytorch_variables = ["log_ent_coef"]
            state_dicts.append("ent_coef_optimizer")
        else:
            saved_pytorch_variables = ["ent_coef_tensor"]
        return state_dicts, saved_pytorch_variables

    # -- rollout: REAL hidden state, reset only at episode boundaries --
    def _sample_action(self, learning_starts: int, action_noise=None,
                       n_envs: int = 1):
        if self._rollout_hidden is None:
            self._rollout_hidden = np.zeros(
                (n_envs, self.policy.hidden_size), dtype=np.float32)
            self._rsac_prev_dones = np.ones((n_envs,), dtype=bool)
        if np.any(self._rsac_prev_dones):
            self._rollout_hidden[self._rsac_prev_dones] = 0.0
        if self.num_timesteps < learning_starts and not self.use_sde:
            unscaled_action = np.array(
                [self.action_space.sample() for _ in range(n_envs)])
        else:
            assert self._last_obs is not None
            obs_tensor, _ = self.policy.obs_to_tensor(self._last_obs)
            h_t = th.as_tensor(self._rollout_hidden, device=self.device)
            with th.no_grad():
                action_t, h_new = self.actor.act_step(
                    obs_tensor, h_t, deterministic=False)
            self._rollout_hidden = h_new.cpu().numpy()
            raw = action_t.cpu().numpy().reshape(
                (n_envs, *self.action_space.shape))
            unscaled_action = self.policy.unscale_action(raw)
        if isinstance(self.action_space, spaces.Box):
            scaled_action = self.policy.scale_action(unscaled_action)
            if action_noise is not None:
                scaled_action = np.clip(scaled_action + action_noise(),
                                        -1, 1)
            buffer_action = scaled_action
            action = self.policy.unscale_action(scaled_action)
        else:
            buffer_action = unscaled_action
            action = buffer_action
        return action, buffer_action

    def _store_transition(self, replay_buffer, buffer_action, new_obs,
                          reward, dones, infos) -> None:
        super()._store_transition(replay_buffer, buffer_action, new_obs,
                                  reward, dones, infos)
        self._rsac_prev_dones = np.asarray(dones, dtype=bool).copy()

    # -- training: masked truncated-BPTT SAC update over zero-start windows --
    def train(self, gradient_steps: int, batch_size: int = 64) -> None:
        self.policy.set_training_mode(True)
        optimizers = [self.actor.optimizer, self.critic.optimizer]
        if self.ent_coef_optimizer is not None:
            optimizers += [self.ent_coef_optimizer]
        self._update_learning_rate(optimizers)

        if self.replay_buffer.num_episodes() == 0:
            # No COMPLETE episode has landed yet (episodes run for
            # hundreds of ticks; learning_starts is sized for a flat
            # buffer and fires well before the first one finishes) --
            # skip this update round rather than crash; collection
            # continues and the next round retries.
            return

        ent_coef_losses, ent_coefs = [], []
        actor_losses, critic_losses = [], []
        L = self.seq_len

        for _ in range(gradient_steps):
            batch = self.replay_buffer.sample(batch_size, device=self.device)
            obs, actions = batch.observations, batch.actions
            rewards, next_obs = batch.rewards, batch.next_observations
            dones, mask = batch.dones, batch.mask
            B = obs.shape[0]
            h0 = th.zeros(B, self.policy.hidden_size, device=self.device)
            valid = mask.reshape(-1) > 0.5
            n_valid = max(int(valid.sum().item()), 1)

            actions_pi, log_prob, _ = self.actor.action_log_prob_seq(obs, h0)

            ent_coef_loss = None
            if self.ent_coef_optimizer is not None:
                ent_coef = th.exp(self.log_ent_coef.detach())
                lp_flat = log_prob.reshape(-1)[valid]
                ent_coef_loss = -(
                    self.log_ent_coef
                    * (lp_flat + self.target_entropy).detach()
                ).mean()
                ent_coef_losses.append(ent_coef_loss.item())
            else:
                ent_coef = self.ent_coef_tensor
            ent_coefs.append(ent_coef.item())
            if ent_coef_loss is not None:
                self.ent_coef_optimizer.zero_grad()
                ent_coef_loss.backward()
                self.ent_coef_optimizer.step()

            current_q_list, _ = self.critic.forward_seq(obs, actions, h0)

            with th.no_grad():
                next_actions, next_log_prob, _ = (
                    self.actor.action_log_prob_seq(next_obs, h0))
                _tgt_q_main, tgt_h_list = self.critic_target.forward_seq(
                    obs, actions, h0)
                boot_qs = []
                for i, qnet in enumerate(self.critic_target.qnets):
                    h_prev = tgt_h_list[i].reshape(B * L, -1)
                    nobs_flat = next_obs.reshape(B * L, -1)
                    nact_flat = next_actions.reshape(B * L, -1)
                    q_boot, _ = qnet.step(nobs_flat, nact_flat, h_prev)
                    boot_qs.append(q_boot.reshape(B, L, 1))
                boot_q = th.cat(boot_qs, dim=-1)
                min_q, _ = th.min(boot_q, dim=-1, keepdim=True)
                target_q = rewards + (1.0 - dones) * self.gamma * (
                    min_q - ent_coef * next_log_prob)

            critic_loss = th.zeros((), device=self.device)
            for q in current_q_list:
                err = (q - target_q) ** 2
                critic_loss = critic_loss + 0.5 * (
                    err.reshape(-1)[valid]).sum() / n_valid
            critic_losses.append(float(critic_loss.item()))
            self.critic.optimizer.zero_grad()
            critic_loss.backward()
            self.critic.optimizer.step()

            q_pi_list, _ = self.critic.forward_seq(obs, actions_pi, h0)
            q_pi = th.cat(q_pi_list, dim=-1)
            min_q_pi, _ = th.min(q_pi, dim=-1, keepdim=True)
            actor_loss_full = ent_coef * log_prob - min_q_pi
            actor_loss = (
                actor_loss_full.reshape(-1)[valid]).sum() / n_valid
            actor_losses.append(float(actor_loss.item()))
            self.actor.optimizer.zero_grad()
            actor_loss.backward()
            self.actor.optimizer.step()

            polyak_update(self.critic.parameters(),
                         self.critic_target.parameters(), self.tau)

        self._n_updates += gradient_steps
        self.logger.record("train/n_updates", self._n_updates,
                           exclude="tensorboard")
        self.logger.record("train/ent_coef", np.mean(ent_coefs))
        self.logger.record("train/actor_loss", np.mean(actor_losses))
        self.logger.record("train/critic_loss", np.mean(critic_losses))
        if ent_coef_losses:
            self.logger.record("train/ent_coef_loss",
                               np.mean(ent_coef_losses))


def is_recurrent_sac_checkpoint(path) -> bool:
    """True if the SB3 zip at ``path`` holds a ``RecurrentSACPolicy``."""
    from stable_baselines3.common.save_util import load_from_zip_file
    data, _, _ = load_from_zip_file(path, device="cpu", load_data=True)
    policy_class = data.get("policy_class")
    try:
        return bool(policy_class) and issubclass(
            policy_class, RecurrentSACPolicy)
    except TypeError:
        return False
