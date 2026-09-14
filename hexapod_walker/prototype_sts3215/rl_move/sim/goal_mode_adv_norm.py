"""goal_mode_adv_norm.py — per-goal-mode advantage normalization: the
walkcurr hold-collapse STRUCTURAL fix (2026-09-13).

BACKGROUND: two independent s1-lineage continuations off the same
`lowerscoreprog-s1-termbleed-cont15m` checkpoint both destroyed `hold`
identically (a stable-looking stand with one functionally unloaded
foot that dies `hold_min_load` at 2.46s, every gate episode) while
`lower` kept improving — root-caused (walkcurr/STATUS.md, 09-13 ~23:4x
dig-in) to `lower`'s much larger raw reward magnitude (~200+/ep income)
DWARFING `hold`'s stakes (a hold death only cost ~37 against a 60 term-
fee cap) in the shared PPO batch. Two dose-shaped repairs were then
pre-registered against that exact cause and BOTH refuted at 6M:
`tb-holdfee-6m` (price hold's unloaded stance directly,
`reward.k_hold_min_load_short=10`) still ends hold 0/6 with
`env/hold_load_factor` pinned <=0.3 while the new per-tick fee visibly
charges the whole run (price-insensitive); `tb-holdmix-6m` (raise
hold's batch SHARE 0.25->0.45, no new prices) also still ends hold 0/6
despite 1.8x hold exposure (gradient-share explanation refuted too).
Both gates name the same escalation: "structural fix, not dose."

WHAT THIS BUILDS: SB3's own `ppo.py` normalizes advantages with ONE
global (mean, std) per minibatch. A minibatch is a random slice of the
WHOLE rollout, and with goal-mix `hold=0.25,lower=0.6` this recipe's
own 6M run, `lower`'s per-tick advantage scale is the majority AND
(per the root-cause above) the larger-magnitude signal -- so the
single shared divisor lets `lower` dominate exactly the way the dig-in
described, independent of how big a fee prices an unloaded `hold` foot
or how large `hold`'s batch share is; neither lever touches the
SCALE-parity problem at all. This module pre-normalizes
`rollout_buffer.advantages` IN PLACE, independently within each
`goal_mode` group (`info["goal_mode"]`, already emitted every tick by
`SimHexapodGoalEnv` for eval/diagnostic use — see `eval_checkpoint.py`,
`distill_gru.py`), to that group's OWN zero-mean/unit-std, immediately
BEFORE `super().train()` runs — the exact "per-...-group advantage
normalization" lever `heading_adv_norm.py` already proved out for
on/off-axis heading groups (candidate 2 of the 09-09 widen8 repair);
this module is the SAME mechanism keyed on goal-mode instead of
heading, generalized from 2 groups to N.

KEY DIFFERENCE FROM heading_adv_norm.py: that module derives its group
label from a fixed OBS COLUMN (requires `obs.mode_onehot`-free layout,
`obs.history_frames=1`, no phase/yaw-cmd tail -- an obs-index
contract). This module derives its label from `info["goal_mode"]`
directly, which every task already emits regardless of obs layout --
so it needs NO obs-layout contract and works on ANY policy/obs
configuration. The one thing it DOES need that heading_adv_norm
doesn't: `rollout_buffer.advantages` has no memory of per-step
`infos` (SB3 never persists them), so a companion callback
(`GoalModeCaptureCallback`) must run during `collect_rollouts()` to
record each step's per-env `goal_mode` into
`model._goal_mode_step_labels` for the `train()` hook to consume
after the fact.

RULE (a): touches ONLY the sign/scale of the SAME reward-derived GAE
advantage PPO's own surrogate loss already uses -- no new reward
channel, no teacher, no reference trajectory. Not a rule-(a)
violation.

RISK CONTAINMENT:
- New cfg key `train.goal_mode_adv_norm` (default 0 = OFF): OFF runs
  never construct the capture callback and `_goal_mode_adv_norm_step`
  returns before touching the rollout buffer -- bit-exact.
- Any group (mode) with fewer than `min_group` samples this rollout,
  or with degenerate std (<=1e-8), is left COMPLETELY UNCHANGED --
  a quiet/lopsided mode (e.g. `rise` sampled at 0.15) never gets its
  scale rewritten off too few samples, and never crashes.
- A capture-buffer/rollout-buffer shape mismatch (defensive: wrong
  wiring, a callback that didn't run, a VecEnv that dropped infos) is
  a clean no-op, never an index error.
- Composes with any other PPO-loss-level mixin the same way
  heading_adv_norm/BCAnchorPPO/MirrorPPO/YawCreditPPO already do
  (wraps whatever `algo_cls` already is).

See rl_move/tests/test_goal_mode_adv_norm.py.
"""
from __future__ import annotations

import numpy as np
from stable_baselines3.common.callbacks import BaseCallback

__all__ = [
    "attach_goal_mode_adv_norm",
    "make_goal_mode_adv_norm_ppo_class",
    "GoalModeCaptureCallback",
    "goal_mode_adv_norm_wandb_payload",
    "GOAL_MODE_ADV_NORM_WANDB_PREFIX",
]

GOAL_MODE_ADV_NORM_WANDB_PREFIX = "train/goal_mode_adv_norm_"


def attach_goal_mode_adv_norm(model, *, enabled: bool,
                              min_group: int = 8) -> None:
    """Sets the attributes `GoalModeAdvNormPPO.train()` /
    `GoalModeCaptureCallback` read. A no-op when `enabled` is falsy
    (mirrors `attach_heading_adv_norm`'s convention) -- no obs-layout
    validation needed since this module never reads `obs` at all."""
    if not enabled:
        return
    model.goal_mode_adv_norm_enabled = True
    model.goal_mode_adv_norm_min_group = int(min_group)
    model._goal_mode_step_labels = []


class GoalModeCaptureCallback(BaseCallback):
    """Records this rollout's per-step, per-env `info["goal_mode"]`
    into `model._goal_mode_step_labels` (a list of length-n_envs lists,
    one per collected step, reset at the start of every rollout) so
    `GoalModeAdvNormPPO.train()` can group `rollout_buffer.advantages`
    by mode before `super().train()` consumes the buffer. A pure
    no-op whenever `model.goal_mode_adv_norm_enabled` is not set
    (`attach_goal_mode_adv_norm` never ran, or ran with enabled=False)
    -- safe to construct unconditionally, though callers only append
    it when the cfg flag is on."""

    def _on_rollout_start(self) -> None:
        if getattr(self.model, "goal_mode_adv_norm_enabled", False):
            self.model._goal_mode_step_labels = []

    def _on_step(self) -> bool:
        if getattr(self.model, "goal_mode_adv_norm_enabled", False):
            infos = self.locals.get("infos") or ()
            self.model._goal_mode_step_labels.append(
                [str(info.get("goal_mode", "")) for info in infos])
        return True


def _grouped_renorm(adv_flat: np.ndarray, labels_flat: np.ndarray,
                    min_group: int):
    """Pure function, unit-testable without any PPO/env machinery: for
    each unique label in `labels_flat` with >= `min_group` members and
    non-degenerate std, rewrite that subset of `adv_flat` to zero-mean/
    unit-std. Groups below the threshold, or with std<=1e-8, are left
    UNCHANGED. Returns (out, per_group_stats)."""
    out = adv_flat.copy()
    stats: dict = {}
    for label in np.unique(labels_flat):
        mask = labels_flat == label
        n = int(mask.sum())
        key = str(label) if label else "_empty_"
        if n < min_group:
            stats[key] = {"n": n, "applied": False}
            continue
        std = float(adv_flat[mask].std())
        if std <= 1e-8:
            stats[key] = {"n": n, "applied": False, "std": std}
            continue
        mean = float(adv_flat[mask].mean())
        out[mask] = (adv_flat[mask] - mean) / std
        stats[key] = {"n": n, "applied": True, "std": std, "mean": mean}
    return out, stats


def make_goal_mode_adv_norm_ppo_class(base_cls):
    """`GoalModeAdvNormPPO`: `base_cls` (compose with BCAnchorPPO/
    MirrorPPO/YawCreditPPO/HeadingAdvNormPPO/... as needed) + one
    per-goal-mode-group advantage renormalization pre-step, run BEFORE
    `super().train()` touches (flattens in place) the rollout
    buffer."""

    class GoalModeAdvNormPPO(base_cls):
        goal_mode_adv_norm_enabled: bool = False
        goal_mode_adv_norm_min_group: int = 8

        def train(self) -> None:
            self._goal_mode_adv_norm_step()
            super().train()

        def _goal_mode_adv_norm_step(self) -> None:
            logger = getattr(self, "logger", None)
            if not getattr(self, "goal_mode_adv_norm_enabled", False):
                return
            buf = self.rollout_buffer
            if getattr(buf, "generator_ready", False):
                raise RuntimeError(
                    "_goal_mode_adv_norm_step must run before "
                    "super().train() consumes the rollout buffer")
            adv = np.asarray(buf.advantages)
            n_steps, n_envs = adv.shape[0], adv.shape[1]
            labels = getattr(self, "_goal_mode_step_labels", None)
            if (not labels or len(labels) != n_steps
                    or any(len(row) != n_envs for row in labels)):
                # Capture buffer missing/mismatched (callback never
                # ran, or a shape change mid-training) -- defensive
                # no-op, never index into a buffer that doesn't match.
                if logger is not None:
                    logger.record(
                        GOAL_MODE_ADV_NORM_WANDB_PREFIX + "applied", 0)
                return
            orig_shape = adv.shape
            orig_dtype = adv.dtype
            adv_flat = adv.reshape(-1).astype(np.float64)
            labels_flat = np.asarray(
                [lbl for row in labels for lbl in row], dtype=object)
            out, stats = _grouped_renorm(
                adv_flat, labels_flat,
                int(getattr(self, "goal_mode_adv_norm_min_group", 8)))
            buf.advantages = out.reshape(orig_shape).astype(orig_dtype)
            if logger is not None:
                any_applied = any(s["applied"] for s in stats.values())
                logger.record(
                    GOAL_MODE_ADV_NORM_WANDB_PREFIX + "applied",
                    int(any_applied))
                logger.record(
                    GOAL_MODE_ADV_NORM_WANDB_PREFIX + "n_groups",
                    len(stats))
                for label, s in stats.items():
                    logger.record(
                        f"{GOAL_MODE_ADV_NORM_WANDB_PREFIX}{label}_n",
                        s["n"])
                    if "std" in s:
                        logger.record(
                            f"{GOAL_MODE_ADV_NORM_WANDB_PREFIX}"
                            f"{label}_std_pre", s["std"])

    return GoalModeAdvNormPPO


def goal_mode_adv_norm_wandb_payload(logger) -> dict:
    """Pulls this module's SB3-logger keys (recorded by
    `_goal_mode_adv_norm_step` before `super().train()` runs each
    rollout) into a plain dict for a caller's own `wandb.log(payload)`
    call -- same W&B-forwarding gap `heading_adv_norm_wandb_payload`
    closes (train_ppo_mjx.py builds its W&B charts from a hand-built
    payload dict, not a generic SB3-logger bridge). Prefix-matched
    (not a fixed key tuple like heading_adv_norm's) because the group
    names -- and therefore the per-group key suffixes -- depend on
    whatever `goal_mode` strings this run's goal-mix actually visits.
    Zero-cost / additive-only: `logger=None` or no keys recorded this
    rollout yields an empty dict, never raises."""
    out: dict = {}
    if logger is None:
        return out
    name_to_value = getattr(logger, "name_to_value", None)
    if not name_to_value:
        return out
    for k, v in name_to_value.items():
        if k.startswith(GOAL_MODE_ADV_NORM_WANDB_PREFIX) and v is not None:
            out[k] = float(v)
    return out
