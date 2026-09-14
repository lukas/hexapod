"""goal_mode_batch_split.py -- per-goal-mode DISJOINT minibatch PPO
training: the walkcurr hold-collapse escalation named by the
`goal_mode_adv_norm` gate (2026-09-14, `cw-stance50hz-rlonly-
lowerscoreprog-s1-tb-modeadvnorm-6m` FAIL-MECHANISM).

BACKGROUND: three independent structural/dose repairs targeting the
same hold-collapse (a stable-looking stand that dies `hold_min_load`
at ~2.46s, every gate episode, while `lower` keeps improving) have now
each been refuted in turn --

- `tb-holdfee-6m` (price the unloaded hold foot directly): hold stays
  0/6, the fee visibly charges every tick and the policy pays it
  anyway -- price-insensitive.
- `tb-holdmix-6m` (raise hold's nominal batch SHARE 0.25->0.45): hold
  stays 0/6 despite 1.8x nominal exposure -- gradient-share-by-mix
  explanation refuted.
- `tb-modeadvnorm-6m` (per-goal-mode advantage RE-SCALING, this
  module's direct predecessor -- `goal_mode_adv_norm.py`): hold stays
  0/6 (`env/hold_load_factor` final 0.133) DESPITE
  `goal_mode_adv_norm_applied=1` firing on 100% of logged rollouts and
  visibly re-centering hold's advantage group to its own zero-mean/
  unit-std every update (`hold_std_pre` measured 13.1, confirming the
  raw-scale gap this lever targeted was real and WAS corrected) --
  refuting per-group SCALE PARITY as the bottleneck.

Root cause per the modeadvnorm verdict: hold's raw tick COUNT in the
shared rollout buffer is tiny regardless of nominal goal-mix share,
because hold episodes that are about to fail terminate in under a
second (`goal_mode_adv_norm_hold_n` cumulative ~1228 vs `lower_n`
~21480 over the same run -- ~5% of ticks despite a nominal 0.25 mix).
SB3's own minibatch loop draws ONE random permutation across the WHOLE
flattened buffer and chunks it into fixed-size minibatches -- with
hold this scarce, a random minibatch is overwhelmingly lower/rise
samples, and even a PERFECTLY rescaled hold advantage is diluted to a
near-zero share of that minibatch's mean gradient. Rescaling ON ITS
OWN can't fix a representation problem.

WHAT THIS BUILDS: the gate's own named escalation, "sequential/
alternating-batch mode separation (train hold-only and lower-only
sub-batches in disjoint updates)". Rather than one shared random
permutation over the whole buffer, this module partitions the
flattened rollout buffer's indices BY `info["goal_mode"]` first, then
runs SB3's identical per-minibatch PPO update (same clip/value/entropy
/KL-early-stop loss, reimplemented here because SB3 offers no hook to
substitute the minibatch SOURCE without substituting the whole loop)
against each mode-group's indices independently, group by group, epoch
by epoch -- so no single optimizer step ever sees a gradient averaged
across two different goal modes. A minority mode's ticks get their own
full-strength, undiluted update instead of being averaged away inside
a majority-mode minibatch. Modes below `min_group` samples this
rollout are skipped entirely for that rollout (never merged into
another group's minibatch -- preserves the "never mixed" contract
exactly, mirrors `goal_mode_adv_norm`'s own small-group handling).

RULE (a): still trains PPO's own surrogate/value/entropy loss on the
SAME rollout-collected (obs, action, reward)-derived advantages/returns
-- no new reward channel, no teacher, no reference trajectory. Only
the grouping of which samples share a minibatch (and therefore a
gradient step) changes. Not a rule-(a) violation.

RISK CONTAINMENT:
- New cfg key `train.goal_mode_batch_split` (default 0 = OFF): OFF
  runs take the untouched `super().train()` path, bit-exact.
- Missing/mismatched per-step goal_mode capture (callback never ran,
  shape drift) is a clean fallback to `super().train()`, never an
  index error.
- No qualifying group this rollout (every mode below `min_group`) also
  falls back to `super().train()` unchanged (still trains something
  useful rather than silently skipping the whole rollout).
- Reuses `goal_mode_adv_norm.GoalModeCaptureCallback` for the per-step
  label capture -- same `model._goal_mode_step_labels` contract, so
  the two mechanisms never duplicate capture wiring (only one is
  expected enabled per run, per the modeadvnorm gate's own "instead
  of another shared-batch re-weighting" framing, but sharing the
  attribute is harmless either way).
- Composes with any other PPO-loss-level mixin the same way
  heading_adv_norm/goal_mode_adv_norm/BCAnchorPPO/MirrorPPO already
  do (wraps whatever `algo_cls` already is) -- though this module
  fully REPLACES `train()`'s body rather than running a pre/post step,
  since the whole minibatch-sourcing loop must change, not just the
  advantages tensor.

See rl_move/tests/test_goal_mode_batch_split.py.
"""
from __future__ import annotations

import numpy as np

from .goal_mode_adv_norm import GoalModeCaptureCallback  # re-exported below

__all__ = [
    "attach_goal_mode_batch_split",
    "make_goal_mode_batch_split_ppo_class",
    "GoalModeCaptureCallback",
    "goal_mode_batch_split_wandb_payload",
    "GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX",
]

GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX = "train/goal_mode_batch_split_"


def attach_goal_mode_batch_split(model, *, enabled: bool,
                                 min_group: int = 8) -> None:
    """Sets the attributes `GoalModeBatchSplitPPO.train()` /
    `GoalModeCaptureCallback` read. A no-op when `enabled` is falsy."""
    if not enabled:
        return
    model.goal_mode_batch_split_enabled = True
    model.goal_mode_batch_split_min_group = int(min_group)
    if not hasattr(model, "_goal_mode_step_labels"):
        model._goal_mode_step_labels = []


def _labels_to_flat(labels, n_steps: int, n_envs: int):
    """Validates the captured (n_steps, n_envs) label rows and returns
    them flattened in the SAME env-major order `RolloutBuffer.
    swap_and_flatten` uses (`arr.swapaxes(0, 1).reshape(-1, ...)`,
    i.e. index = env * n_steps + step) -- the order the buffer's own
    arrays end up in once `.get()` has run once. Returns None if the
    capture is missing or shape-mismatched (defensive no-op signal)."""
    if not labels or len(labels) != n_steps:
        return None
    if any(len(row) != n_envs for row in labels):
        return None
    arr = np.asarray(labels, dtype=object)  # (n_steps, n_envs)
    return arr.T.reshape(-1)  # (n_envs, n_steps) -> flat, env-major


def make_goal_mode_batch_split_ppo_class(base_cls):
    """`GoalModeBatchSplitPPO`: `base_cls` (compose with BCAnchorPPO/
    MirrorPPO/YawCreditPPO/... as needed) with `train()` REPLACED --
    when armed, every PPO minibatch is drawn from a single
    `goal_mode`'s indices only (never mixed across modes), group by
    group, epoch by epoch; when disarmed (or the capture is missing),
    falls through to `super().train()` unchanged."""

    class GoalModeBatchSplitPPO(base_cls):
        goal_mode_batch_split_enabled: bool = False
        goal_mode_batch_split_min_group: int = 8

        def train(self) -> None:
            if not getattr(self, "goal_mode_batch_split_enabled", False):
                super().train()
                return
            self._goal_mode_batch_split_train()

        def _goal_mode_batch_split_train(self) -> None:
            logger = getattr(self, "logger", None)
            buf = self.rollout_buffer
            labels_flat = _labels_to_flat(
                getattr(self, "_goal_mode_step_labels", None),
                buf.buffer_size, buf.n_envs)
            if labels_flat is None:
                if logger is not None:
                    logger.record(
                        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "applied", 0)
                super().train()
                return
            # Trigger the buffer's own one-time flatten (idempotent,
            # guarded by generator_ready) so labels_flat's env-major
            # order lines up with buf.observations/advantages/etc.
            # Replicates ONLY the flatten side-effect of
            # RolloutBuffer.get() (stable_baselines3/common/buffers.py)
            # directly -- calling buf.get() itself would also draw and
            # discard one real (mode-mixed) minibatch as a side
            # effect, which is wasted work and would make an external
            # spy on `_get_samples` see a bogus mixed call that never
            # feeds an optimizer step.
            if not buf.generator_ready:
                for _tensor in ("observations", "actions", "values",
                               "log_probs", "advantages", "returns"):
                    buf.__dict__[_tensor] = buf.swap_and_flatten(
                        buf.__dict__[_tensor])
                buf.generator_ready = True
            min_group = int(getattr(
                self, "goal_mode_batch_split_min_group", 8))
            groups = []
            for label in sorted(set(str(x) for x in labels_flat.tolist())):
                idx = np.nonzero(
                    labels_flat.astype(str) == label)[0]
                if len(idx) >= min_group:
                    groups.append((label, idx))
            if not groups:
                if logger is not None:
                    logger.record(
                        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "applied", 0)
                    logger.record(
                        GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "n_groups", 0)
                super().train()
                return
            self._goal_mode_batch_split_run(groups, logger)

        def _goal_mode_batch_split_run(self, groups, logger) -> None:
            import torch as th
            import torch.nn.functional as F
            from gymnasium import spaces
            from stable_baselines3.common.utils import explained_variance

            self.policy.set_training_mode(True)
            self._update_learning_rate(self.policy.optimizer)
            clip_range = self.clip_range(self._current_progress_remaining)
            clip_range_vf = None
            if self.clip_range_vf is not None:
                clip_range_vf = self.clip_range_vf(
                    self._current_progress_remaining)

            entropy_losses, pg_losses, value_losses = [], [], []
            clip_fractions, approx_kl_divs = [], []
            per_group_pg = {label: [] for label, _ in groups}
            rng = np.random.default_rng(self.num_timesteps)
            continue_training = True

            for _epoch in range(self.n_epochs):
                for label, idx in groups:
                    order = rng.permutation(len(idx))
                    shuffled = idx[order]
                    bs = int(self.batch_size) if self.batch_size \
                        else len(shuffled)
                    for start in range(0, len(shuffled), bs):
                        batch_inds = shuffled[start:start + bs]
                        if len(batch_inds) == 0:
                            continue
                        rollout_data = self.rollout_buffer._get_samples(
                            batch_inds)
                        actions = rollout_data.actions
                        if isinstance(self.action_space, spaces.Discrete):
                            actions = actions.long().flatten()
                        values, log_prob, entropy = (
                            self.policy.evaluate_actions(
                                rollout_data.observations, actions))
                        values = values.flatten()
                        advantages = rollout_data.advantages
                        if (self.normalize_advantage
                                and len(advantages) > 1):
                            advantages = (
                                (advantages - advantages.mean())
                                / (advantages.std() + 1e-8))
                        ratio = th.exp(log_prob - rollout_data.old_log_prob)
                        policy_loss_1 = advantages * ratio
                        policy_loss_2 = advantages * th.clamp(
                            ratio, 1 - clip_range, 1 + clip_range)
                        policy_loss = -th.min(
                            policy_loss_1, policy_loss_2).mean()
                        pg_losses.append(policy_loss.item())
                        per_group_pg[label].append(policy_loss.item())
                        clip_fraction = th.mean(
                            (th.abs(ratio - 1) > clip_range).float()
                        ).item()
                        clip_fractions.append(clip_fraction)
                        if clip_range_vf is None:
                            values_pred = values
                        else:
                            values_pred = rollout_data.old_values + th.clamp(
                                values - rollout_data.old_values,
                                -clip_range_vf, clip_range_vf)
                        value_loss = F.mse_loss(
                            rollout_data.returns, values_pred)
                        value_losses.append(value_loss.item())
                        if entropy is None:
                            entropy_loss = -th.mean(-log_prob)
                        else:
                            entropy_loss = -th.mean(entropy)
                        entropy_losses.append(entropy_loss.item())
                        loss = (policy_loss
                                + self.ent_coef * entropy_loss
                                + self.vf_coef * value_loss)
                        with th.no_grad():
                            log_ratio = log_prob - rollout_data.old_log_prob
                            approx_kl_div = th.mean(
                                (th.exp(log_ratio) - 1) - log_ratio
                            ).cpu().numpy()
                            approx_kl_divs.append(approx_kl_div)
                        if (self.target_kl is not None
                                and approx_kl_div > 1.5 * self.target_kl):
                            continue_training = False
                            break
                        self.policy.optimizer.zero_grad()
                        loss.backward()
                        th.nn.utils.clip_grad_norm_(
                            self.policy.parameters(), self.max_grad_norm)
                        self.policy.optimizer.step()
                    if not continue_training:
                        break
                self._n_updates += 1
                if not continue_training:
                    break

            explained_var = explained_variance(
                self.rollout_buffer.values.flatten(),
                self.rollout_buffer.returns.flatten())
            if logger is not None:
                logger.record("train/entropy_loss", float(
                    np.mean(entropy_losses)) if entropy_losses else 0.0)
                logger.record("train/policy_gradient_loss", float(
                    np.mean(pg_losses)) if pg_losses else 0.0)
                logger.record("train/value_loss", float(
                    np.mean(value_losses)) if value_losses else 0.0)
                logger.record("train/approx_kl", float(
                    np.mean(approx_kl_divs)) if approx_kl_divs else 0.0)
                logger.record("train/clip_fraction", float(
                    np.mean(clip_fractions)) if clip_fractions else 0.0)
                logger.record("train/explained_variance", explained_var)
                logger.record("train/n_updates", self._n_updates,
                              exclude="tensorboard")
                logger.record("train/clip_range", clip_range)
                if clip_range_vf is not None:
                    logger.record("train/clip_range_vf", clip_range_vf)
                logger.record(
                    GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "applied", 1)
                logger.record(
                    GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX + "n_groups",
                    len(groups))
                for label, idx in groups:
                    logger.record(
                        f"{GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX}{label}_n",
                        len(idx))
                    pgs = per_group_pg.get(label) or []
                    if pgs:
                        logger.record(
                            f"{GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX}"
                            f"{label}_pg_loss", float(np.mean(pgs)))

    return GoalModeBatchSplitPPO


def goal_mode_batch_split_wandb_payload(logger) -> dict:
    """Pulls this module's SB3-logger keys into a plain dict for a
    caller's own `wandb.log(payload)` call (same W&B-forwarding gap
    `goal_mode_adv_norm_wandb_payload` closes). Zero-cost/additive-
    only: `logger=None` or no keys recorded yields an empty dict."""
    out: dict = {}
    if logger is None:
        return out
    name_to_value = getattr(logger, "name_to_value", None)
    if not name_to_value:
        return out
    for k, v in name_to_value.items():
        if (k.startswith(GOAL_MODE_BATCH_SPLIT_WANDB_PREFIX)
                and v is not None):
            out[k] = float(v)
    return out
