"""``BankDownweightReplayBuffer`` — an SB3 ``ReplayBuffer`` subclass that
biases off-policy SAMPLING away from transitions whose originating episode
drew a curriculum "bank" state injection (``goal.lower_start_bank`` and
siblings, ``info["start_kind"]`` in the set this module treats as
bank-origin), without changing the ENVIRONMENT's own draw probability
(``goal.*_start_bank_frac`` stays exactly as configured).

Built 2026-09-25 (walkcurr, `rl_only` lower-role SAC thread): the two prior
exposure-TIMING mechanisms for this same regression (a gradual ramp,
`goal.lower_start_bank_frac_ramp_steps`, and a hard delayed cutoff,
`goal.lower_start_bank_delay_steps`) both landed on the same seed-fragile,
sub-baseline signature and were closed + removed
(`walkcurr/STATUS.md` 2026-09-24 ~19:2x / ~23:1x). Both changed WHEN the
environment starts drawing bank episodes. This is a genuinely different
mechanism SHAPE: the environment draws bank episodes at the configured
frac from step 0 as normal (SAC's replay buffer sees them immediately),
but the buffer's own sampler downweights them so SAC's off-policy gradient
mix stays mostly non-bank early on (while `full=False`/the buffer is still
filling with a low ratio of bank rows) and gradually converges to the
environment's true bank ratio as the buffer fills and turns over — no
extra step-count schedule, no arming/gating callback, purely a buffer-side
sampling reweight.

Default OFF / bit-exact: ``bank_downweight=1.0`` (the default) makes
``sample()`` delegate straight to the parent class's own implementation,
so the RNG call sequence (and therefore training trajectory) is IDENTICAL
to plain ``ReplayBuffer`` — this class is only even instantiated when a
caller explicitly passes ``bank_downweight<1.0`` (see
``train_ppo_mjx._build_sac_model``); at the default config nothing in this
file executes during training at all.

Only supports ``optimize_memory_usage=False`` (this codebase's SAC builds
never set that flag) — fails loud rather than silently mis-sampling if a
caller ever does.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from stable_baselines3.common.buffers import ReplayBuffer
from stable_baselines3.common.type_aliases import ReplayBufferSamples
from stable_baselines3.common.vec_env import VecNormalize


class BankDownweightReplayBuffer(ReplayBuffer):
    """See module docstring. New kwargs (all optional, keyword-only via
    SB3's ``replay_buffer_kwargs``):

    - ``bank_downweight`` (float, default 1.0): per-transition sampling
      WEIGHT for bank-origin rows relative to 1.0 for everything else
      (0.0 = never sampled once any non-bank row exists; 1.0 = uniform,
      i.e. off/identical to the parent class).
    - ``bank_info_key`` (str, default ``"start_kind"``): the per-step
      ``infos[i]`` key this buffer reads to classify a transition.
    - ``bank_info_values`` (tuple[str, ...], default
      ``("post_walk_lower",)``): the set of that key's values counted as
      bank-origin. ``rl_move.env.start_kind_of`` emits
      ``"post_walk_lower"`` for a ``goal.lower_start_bank`` draw,
      ``"post_lower"`` for ``goal.rise_start_bank``, ``"post_rise_hold"``
      for ``goal.hold_start_bank``, and ``"bank"`` for
      ``goal.walk_entry_bank`` — pass the value(s) matching whichever
      role/bank this training run actually arms.
    """

    def __init__(self, *args: Any,
                 bank_downweight: float = 1.0,
                 bank_info_key: str = "start_kind",
                 bank_info_values: tuple[str, ...] = ("post_walk_lower",),
                 **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.optimize_memory_usage:
            raise ValueError(
                "BankDownweightReplayBuffer does not support "
                "optimize_memory_usage=True (this codebase's SAC builds "
                "never set it; if that changes, extend this class first)")
        self.bank_downweight = float(bank_downweight)
        if not (0.0 <= self.bank_downweight <= 1.0):
            raise ValueError(
                f"bank_downweight must be in [0.0, 1.0], got "
                f"{self.bank_downweight}")
        self._bank_info_key = str(bank_info_key)
        self._bank_info_values = frozenset(bank_info_values)
        self.bank_flags = np.zeros((self.buffer_size, self.n_envs),
                                    dtype=bool)

    def add(self, obs, next_obs, action, reward, done, infos) -> None:  # noqa: D102
        pos = self.pos
        super().add(obs, next_obs, action, reward, done, infos)
        self.bank_flags[pos] = np.array(
            [info.get(self._bank_info_key) in self._bank_info_values
             for info in infos], dtype=bool)

    def sample(self, batch_size: int,
               env: VecNormalize | None = None) -> ReplayBufferSamples:
        if self.bank_downweight >= 1.0:
            # Off/bit-exact: identical RNG call sequence to the parent.
            return super().sample(batch_size=batch_size, env=env)
        upper_bound = self.buffer_size if self.full else self.pos
        if upper_bound <= 0:
            return super().sample(batch_size=batch_size, env=env)
        flags = self.bank_flags[:upper_bound]  # (upper_bound, n_envs)
        weights = np.where(flags, self.bank_downweight, 1.0).reshape(-1)
        total = float(weights.sum())
        if total <= 0.0:
            # Degenerate (every stored row is bank-origin and downweight
            # is 0): fall back to uniform rather than dividing by zero.
            return super().sample(batch_size=batch_size, env=env)
        probs = weights / total
        flat_idx = np.random.choice(
            upper_bound * self.n_envs, size=batch_size, p=probs)
        batch_inds, env_indices = np.unravel_index(
            flat_idx, (upper_bound, self.n_envs))
        return self._get_samples_paired(batch_inds, env_indices, env=env)

    def _get_samples_paired(self, batch_inds: np.ndarray,
                             env_indices: np.ndarray,
                             env: VecNormalize | None = None
                             ) -> ReplayBufferSamples:
        """Same body as ``ReplayBuffer._get_samples`` but with the
        ``env_indices`` supplied explicitly (paired to ``batch_inds``)
        instead of drawn independently — required so a downweighted
        SAMPLE TIME index and its ORIGINATING env stay matched; the
        parent class's own env_indices are IID per call, which would let
        this buffer's per-(time,env) bank flag get silently decoupled
        from which env's data is actually returned."""
        next_obs = self._normalize_obs(
            self.next_observations[batch_inds, env_indices, :], env)
        data = (
            self._normalize_obs(
                self.observations[batch_inds, env_indices, :], env),
            self.actions[batch_inds, env_indices, :],
            next_obs,
            (self.dones[batch_inds, env_indices]
             * (1 - self.timeouts[batch_inds, env_indices])).reshape(-1, 1),
            self._normalize_reward(
                self.rewards[batch_inds, env_indices].reshape(-1, 1), env),
        )
        return ReplayBufferSamples(*tuple(map(self.to_torch, data)))
