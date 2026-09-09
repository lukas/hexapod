"""heading_adv_norm.py — per-heading (on-axis vs off-axis) advantage
normalization, candidate 2 of the widen8 off-axis-heading leg-sacrifice
repair (walkcurr, 09-09).

WHY THIS EXISTS: CURRENT_TRUTHS 2026-09-09 ~19:4x/~20:3x recorded FIVE
independent mechanisms that all failed to move the DETERMINISTIC mean
off the chronic front-leg (leg0/leg5) sacrifice at the widen8/crutchoff
champion's 5 off-axis headings (heading-exposure reweighting, heading-
gain dose-scaling, wide-log_std hold, advantage-filtered self-
distillation, and a 100%-off-axis ISOLATION curriculum) — the entire
exposure/batch-composition axis is closed end-to-end, and the isolation
result additionally rules out "off-axis reward is just structurally
smaller/noisier and self-distillation's own filtering." Both closures
named exactly ONE remaining, genuinely different, PPO-LOSS-LEVEL
mechanism, never tried: **per-heading advantage normalization**, "so
off-axis timesteps aren't structurally under-weighted in the shared
PPO batch."

WHAT THIS BUILDS: sb3-contrib's ``RecurrentPPO.train()`` (and plain
SB3 ``PPO.train()``) normalizes advantages with ONE global (mean, std)
per minibatch (grep-confirmed:
``advantages = (advantages - advantages[mask].mean()) /
(advantages[mask].std() + 1e-8)``, ppo_recurrent.py:356; plain SB3's
``ppo.py`` does the identical thing). Every minibatch is a random slice
of the WHOLE rollout, and off-axis-heading ticks are a small, fixed
minority of every rollout by construction (5 of the walk-heading set's
directions are "broken", the rest — including "forward" itself — are
not sampled off-axis). If the RAW (pre-normalization) advantage scale
differs between on-axis and off-axis ticks (plausible: forward
progress is an easier, larger, less noisy signal than sideways/
backward progress under the same reward stack), the single SHARED
divisor is dominated by the majority group and the minority group's
advantages come out of normalization compressed relative to what they
would be normalized on their own — a smaller effective policy-gradient
step size for exactly the ticks this repair needs to move.

This module pre-normalizes ``rollout_buffer.advantages`` IN PLACE,
independently within the on-axis and off-axis groups (each rescaled to
its OWN zero-mean/unit-std), immediately BEFORE ``super().train()``
runs (matching this codebase's established aux-loss house style:
mirror.py/bc_anchor.py/yaw_critic.py/heading_selfdistill.py all run an
extra step around ``super().train()`` rather than editing sb3-contrib/
SB3 internals). Because both groups already carry equal statistical
footing over the WHOLE buffer, ``super().train()``'s own subsequent
per-minibatch renormalization can no longer let one group's raw
magnitude drown the other's — this is the literal "per-heading...
normalization" lever named by the closure, built as a buffer-level
pre-step rather than a fork of the library's internal minibatch loop
(safer: no vendored/monkeypatched copy of sb3-contrib's train() to
maintain, matches the codebase's existing pattern for every prior
PPO-adjacent mechanism).

RULE (a) READ: this touches ONLY the sign/scale of the SAME reward-
derived GAE advantage PPO's own surrogate loss already uses (computed
by the base class from this run's own reward+value function) — no new
reward channel, no teacher, no reference trajectory, no external
target. Not a rule-(a) violation.

RISK CONTAINMENT (RESEARCH_RULES: never let a new mechanism silently
reshape a shared default path):
- New cfg key ``train.heading_adv_norm`` (default 0 = OFF): off runs
  are bit-exact — ``_heading_adv_norm_step`` returns before touching
  the rollout buffer at all.
- ``attach_heading_adv_norm`` reuses ``heading_selfdistill``'s own
  obs-layout validation (identical plain-walk-task frame assumption,
  identical index math) and raises loudly (``SystemExit``) on an
  unsupported config instead of silently indexing the wrong columns.
- The step no-ops (leaves ``advantages`` byte-identical) whenever
  EITHER group has fewer than 8 samples this rollout, or a group's own
  std is degenerate (<=1e-8) — a quiet/lopsided rollout never distorts
  the other group's scale or crashes mid-training.
- Composes with BCAnchorPPO/MirrorPPO/YawCreditPPO/
  HeadingSelfDistillPPO the same way those already compose with each
  other (wraps whatever ``algo_cls`` already is).

See rl_move/tests/test_heading_adv_norm.py for the off-path bit-exact
test, the grouped-normalization math unit tests, and a real-PPO
integration smoke test.
"""
from __future__ import annotations

import numpy as np

from .heading_selfdistill import (
    heading_cos,
    heading_frame_width,
    heading_vref_index,
)

__all__ = [
    "attach_heading_adv_norm",
    "make_heading_adv_norm_ppo_class",
    "heading_adv_norm_wandb_payload",
    "HEADING_ADV_NORM_WANDB_KEYS",
]


def attach_heading_adv_norm(model, *, enabled: bool, cos_max: float,
                            cfg: dict | None) -> None:
    """Validates the plain-walk-task obs-layout assumption (identical
    to ``heading_selfdistill.attach_heading_selfdistill``) and sets the
    attributes ``HeadingAdvNormPPO.train()`` reads. Raises loudly
    (never a silent no-op at launch) on a config this module does not
    yet support. A no-op when ``enabled`` is falsy."""
    if not enabled:
        return
    from rl_move.config import cfg_get
    for section, leaf, label in (
            ("goal", "walk_phase_obs", "goal.walk_phase_obs"),
            ("goal", "walk_yaw_cmd", "goal.walk_yaw_cmd"),
            ("obs", "mode_onehot", "obs.mode_onehot"),
            ("obs", "recover_plant_q", "obs.recover_plant_q"),
            ("obs", "fault_health", "obs.fault_health")):
        if float(cfg_get(cfg, section, leaf, default=0.0) or 0.0) != 0.0:
            raise SystemExit(
                f"train.heading_adv_norm requires {label}=0 (this "
                "module's obs-index math assumes the plain walk-task "
                "frame layout only -- unbuilt for phase/yaw-cmd/mode/"
                "recover/fault obs tails)")
    hist_n = int(cfg_get(cfg, "obs", "history_frames", default=1) or 1)
    if hist_n != 1:
        raise SystemExit(
            "train.heading_adv_norm requires obs.history_frames=1 "
            "(unbuilt for stacked-history frames)")
    n_act = int(model.action_space.shape[0])
    idx = heading_vref_index(n_act)
    frame_w = heading_frame_width(n_act)
    obs_dim = int(model.observation_space.shape[0])
    if obs_dim != frame_w:
        raise SystemExit(
            "train.heading_adv_norm obs-width mismatch: expected "
            f"{frame_w} (n_act={n_act}) got {obs_dim} -- this run's "
            "obs layout does not match the plain walk-task assumption; "
            "fix the index math or leave this lever off")
    model.heading_adv_norm_enabled = True
    model.heading_adv_norm_cos_max = float(cos_max)
    model._heading_adv_norm_vref_idx = idx


HEADING_ADV_NORM_WANDB_KEYS = (
    "train/heading_adv_norm_off_axis_frac",
    "train/heading_adv_norm_applied",
    "train/heading_adv_norm_on_std_pre",
    "train/heading_adv_norm_off_std_pre",
)


def heading_adv_norm_wandb_payload(logger) -> dict:
    """Pulls this module's SB3-logger keys (recorded by
    ``_heading_adv_norm_step`` before ``super().train()`` runs each
    rollout) into a plain dict for a caller's own ``wandb.log(payload)``
    call — train_ppo_mjx.py builds its W&B charts from a hand-built
    payload dict, not a generic SB3-logger bridge (same gap
    heading_selfdistill_wandb_payload closes; CURRENT_TRUTHS/walkcurr
    STATUS 2026-09-09 ~17:1x). Zero-cost / additive-only: ``logger=None``
    or a key never recorded this rollout yields an empty/partial dict,
    never raises."""
    out: dict = {}
    if logger is None:
        return out
    name_to_value = getattr(logger, "name_to_value", None)
    if not name_to_value:
        return out
    for k in HEADING_ADV_NORM_WANDB_KEYS:
        v = name_to_value.get(k)
        if v is not None:
            out[k] = float(v)
    return out


def make_heading_adv_norm_ppo_class(base_cls):
    """``HeadingAdvNormPPO``: ``base_cls`` (compose with BCAnchorPPO/
    MirrorPPO/YawCreditPPO/HeadingSelfDistillPPO as needed) + one
    per-heading-group advantage renormalization pre-step, run BEFORE
    ``super().train()`` touches (flattens in place) the rollout
    buffer."""

    class HeadingAdvNormPPO(base_cls):
        heading_adv_norm_enabled: bool = False
        heading_adv_norm_cos_max: float = 0.5

        def train(self) -> None:
            self._heading_adv_norm_step()
            super().train()

        def _heading_adv_norm_step(self) -> None:
            if not getattr(self, "heading_adv_norm_enabled", False):
                return
            idx = getattr(self, "_heading_adv_norm_vref_idx", None)
            if idx is None:
                return  # not attached -- defensive no-op, never crash
            buf = self.rollout_buffer
            if getattr(buf, "generator_ready", False):
                raise RuntimeError(
                    "_heading_adv_norm_step must run before "
                    "super().train() consumes the rollout buffer")
            obs = np.asarray(buf.observations)
            n_steps, n_envs, obs_dim = obs.shape
            n_total = n_steps * n_envs
            obs_flat = obs.reshape(n_total, obs_dim)
            adv = np.asarray(buf.advantages)
            orig_shape = adv.shape
            orig_dtype = adv.dtype
            adv_flat = adv.reshape(-1).astype(np.float64)
            cos_max = float(getattr(self, "heading_adv_norm_cos_max",
                                    0.5))
            cos_h = heading_cos(obs_flat[:, idx:idx + 2])
            off_axis = cos_h <= cos_max
            off_axis_frac = float(off_axis.mean())
            logger = getattr(self, "logger", None)
            n_off = int(off_axis.sum())
            n_on = n_total - n_off
            if n_off < 8 or n_on < 8:
                if logger is not None:
                    logger.record(
                        "train/heading_adv_norm_off_axis_frac",
                        off_axis_frac)
                    logger.record("train/heading_adv_norm_applied", 0)
                return  # one group too small this rollout -- no-op
            on_std = float(adv_flat[~off_axis].std())
            off_std = float(adv_flat[off_axis].std())
            if on_std <= 1e-8 or off_std <= 1e-8:
                if logger is not None:
                    logger.record(
                        "train/heading_adv_norm_off_axis_frac",
                        off_axis_frac)
                    logger.record("train/heading_adv_norm_applied", 0)
                    logger.record("train/heading_adv_norm_on_std_pre",
                                  on_std)
                    logger.record("train/heading_adv_norm_off_std_pre",
                                  off_std)
                return  # degenerate/no-variance group -- no-op
            out = adv_flat.copy()
            out[~off_axis] = (adv_flat[~off_axis]
                              - adv_flat[~off_axis].mean()) / on_std
            out[off_axis] = (adv_flat[off_axis]
                             - adv_flat[off_axis].mean()) / off_std
            buf.advantages = out.reshape(orig_shape).astype(orig_dtype)
            if logger is not None:
                logger.record("train/heading_adv_norm_off_axis_frac",
                              off_axis_frac)
                logger.record("train/heading_adv_norm_applied", 1)
                logger.record("train/heading_adv_norm_on_std_pre", on_std)
                logger.record("train/heading_adv_norm_off_std_pre",
                              off_std)

    return HeadingAdvNormPPO
