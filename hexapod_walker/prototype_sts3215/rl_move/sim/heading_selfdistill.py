"""heading_selfdistill.py — advantage-filtered self-distillation of a
PPO policy's own successful stochastic action samples toward its MEAN
(walkcurr, 09-09).

WHY THIS EXISTS: the widen8/headexplore campaign (CURRENT_TRUTHS
2026-09-09 ~16:2x, walkcurr track) closed the "hold action noise wide
and wait" lever 3/3 seeds, 2 independent budgets (2M, 10M): a global
wide `log_std` makes the STOCHASTIC policy sometimes find a valid gait
at the 5 chronically-broken off-axis headings (up to 14/15
det-off-axis-equivalent via the sto panel), but the DETERMINISTIC mean
stays at literal 0/15 the entire time — a stable equilibrium, not an
undertrained transient. The closure named two candidate NEXT levers
that push the mean directly; this module builds candidate 2
(self-distillation), not candidate 1 (a heading-weighted entropy
bonus), because a plain-vanilla ``DiagGaussianDistribution.entropy()``
depends ONLY on ``log_std`` (a single vector, state-INDEPENDENT for
this recipe — no ``--use-sde``), never on the mean-network output
(``Normal(mean, std).entropy()`` is analytically independent of
``mean``). Re-weighting that entropy term per sample cannot move the
mean-network weights at all, only how fast a single shared `log_std`
anneals — a strictly weaker version of a lever this exact lineage
already tested directly (holding `log_std` flat) and found
insufficient. Candidate 2 is the one that can mechanically work: it
adds a supervised regression term that touches the mean-network
weights directly.

WHAT THIS BUILDS: one extra optimizer step (matching this codebase's
established aux-loss house style — mirror.py / bc_anchor.py /
yaw_critic.py all run a separate step around ``super().train()``
rather than editing sb3-contrib/SB3 internals) that regresses the
policy's own MEAN action toward the ACTUALLY-SAMPLED action of
rollout ticks that were (a) commanded at an off-axis heading (cos of
the commanded heading vs. forward <= ``heading_selfdistill_cos_max``)
and (b) scored a positive, above-average GAE advantage under the
SAME single value function and reward signal PPO's own surrogate loss
already uses. No new value head, no new reward channel, no teacher —
this is plain advantage-weighted regression (AWR-style) restricted to
the heading band the mean is stuck at.

RULE (a) READ (walkcurr's no-gait-clock/no-BC-teacher/no-motion-prior
contract; see OPERATOR_QUESTIONS.md q_20260909T16xxZ for the full
writeup): the distillation TARGET is the policy's OWN on-policy
stochastic sample from THIS rollout, never an external reference,
scripted trajectory, teacher network, or fixed motion clip. The
FILTER (positive normalized advantage) is the identical reward-derived
signal PPO's clipped surrogate already uses to decide which actions to
reinforce — this module does not introduce any new objective a
demonstration/teacher could smuggle in through, only a second,
unclipped optimizer step applied to a heading-restricted, advantage-
filtered subset of the SAME batch. Not a rule-(a) violation.

RISK CONTAINMENT (RESEARCH_RULES: never let a new mechanism silently
reshape a shared default path):
- New cfg key ``train.heading_selfdistill_coef`` (default 0.0 = OFF):
  off runs are bit-exact — ``_heading_selfdistill_step`` returns before
  touching the buffer, the policy, or the optimizer.
- ``attach_heading_selfdistill`` (the "never silently no-op at launch"
  contract) validates, ONCE at attach time, that this run's obs layout
  matches the plain-walk-task assumption this module's index math
  hardcodes (no phase-clock / yaw-rate-command / mode-onehot /
  recover-plant-q / fault-health obs tails, no stacked history frames)
  — raises ``SystemExit`` loudly on a mismatch instead of silently
  indexing the wrong columns. ``n_act`` (and therefore the index) is
  read from the LIVE action space, never guessed from cfg.
- The step no-ops (returns without raising) whenever this rollout has
  no usable signal (degenerate/zero-variance advantage, or fewer than
  8 off-axis positive-advantage samples) — a quiet rollout never
  crashes mid-training.
- ``train.heading_selfdistill_grad_clip`` (default 0.0 = no clip)
  bounds the extra step's gradient norm, matching
  ``yaw_credit_grad_clip``'s own post-canary safety addition.

See rl_move/tests/test_heading_selfdistill.py for the off-path
bit-exact test, the index/frame-width derivation test against a
synthetic obs vector, the advantage-filter/weighting unit tests, and a
short real-PPO integration smoke test that the extra step actually
changes the mean-network weights (and only those) when armed.
"""
from __future__ import annotations

import numpy as np
import torch as th

from rl_move.env import GOAL_DIM

from .walk_task import N_VEL_OBS, WALK_GOAL_DIM


# ---------------------------------------------------------------------
# Obs-layout index math (plain walk-task frame only; see
# attach_heading_selfdistill's validation for the supported subset).
# ---------------------------------------------------------------------

def heading_vref_index(n_act: int) -> int:
    """0-based start index of the ``[vx_ref, vy_ref]`` pair inside ONE
    plain-walk-task obs frame (before any optional phase/yaw-cmd/mode/
    recover/fault tail), given the live action-space width ``n_act``.
    Matches ``WalkGoal.as_obs``'s layout: q_rel(18) + qd(18) + tilt(2)
    + gyro(3) + prev_action(n_act) + goal_base(``GOAL_DIM``=9) +
    [vx_ref, vy_ref]."""
    from .sim_env import N_OBS
    return (N_OBS - 6 + int(n_act)) + GOAL_DIM


def heading_frame_width(n_act: int) -> int:
    """Width of ONE plain-walk-task obs frame (no optional tails)."""
    from .sim_env import N_OBS
    return (N_OBS - 6 + int(n_act)) + WALK_GOAL_DIM + N_VEL_OBS


def heading_cos(vref_xy: np.ndarray) -> np.ndarray:
    """Cosine of the commanded heading vs. forward, from the scaled
    ``[vx_ref, vy_ref]`` obs columns (shape (N, 2)). Uniform scaling
    (``VEL_SCALE``) cancels out of the ratio, so the raw obs values
    work directly. Stop commands (``hypot(vx,vy)~0``) read as
    ``cos=1.0`` (treated as "forward", i.e. never counted off-axis —
    there is no commanded heading to distill toward)."""
    vx = vref_xy[:, 0].astype(np.float64)
    vy = vref_xy[:, 1].astype(np.float64)
    s = np.hypot(vx, vy)
    cos_h = np.ones_like(vx)
    nz = s > 1e-6
    cos_h[nz] = vx[nz] / s[nz]
    return np.clip(cos_h, -1.0, 1.0)


def attach_heading_selfdistill(model, *, coef: float, grad_clip: float,
                               cos_max: float, cfg: dict | None) -> None:
    """Validates the plain-walk-task obs-layout assumption this module
    hardcodes and sets the coefficients ``HeadingSelfDistillPPO.
    train()`` reads. Raises loudly (never a silent no-op at launch) on
    a config this module does not yet support."""
    from rl_move.config import cfg_get
    for section, leaf, label in (
            ("goal", "walk_phase_obs", "goal.walk_phase_obs"),
            ("goal", "walk_yaw_cmd", "goal.walk_yaw_cmd"),
            ("obs", "mode_onehot", "obs.mode_onehot"),
            ("obs", "recover_plant_q", "obs.recover_plant_q"),
            ("obs", "fault_health", "obs.fault_health")):
        if float(cfg_get(cfg, section, leaf, default=0.0) or 0.0) != 0.0:
            raise SystemExit(
                f"train.heading_selfdistill_coef requires {label}=0 "
                "(this module's obs-index math assumes the plain "
                "walk-task frame layout only -- unbuilt for phase/"
                "yaw-cmd/mode/recover/fault obs tails)")
    hist_n = int(cfg_get(cfg, "obs", "history_frames", default=1) or 1)
    if hist_n != 1:
        raise SystemExit(
            "train.heading_selfdistill_coef requires "
            "obs.history_frames=1 (unbuilt for stacked-history frames)")
    n_act = int(model.action_space.shape[0])
    idx = heading_vref_index(n_act)
    frame_w = heading_frame_width(n_act)
    obs_dim = int(model.observation_space.shape[0])
    if obs_dim != frame_w:
        raise SystemExit(
            "train.heading_selfdistill_coef obs-width mismatch: "
            f"expected {frame_w} (n_act={n_act}) got {obs_dim} -- this "
            "run's obs layout does not match the plain walk-task "
            "assumption; fix the index math or leave this lever off")
    from stable_baselines3.common.distributions import (
        DiagGaussianDistribution,
    )
    if not isinstance(model.policy.action_dist, DiagGaussianDistribution):
        raise SystemExit(
            "train.heading_selfdistill_coef requires a plain "
            "DiagGaussianDistribution actor (no gSDE/squashed dist -- "
            "unbuilt for those, and the whole point is a state-"
            "independent-std architecture whose entropy term cannot "
            "move the mean, which is why this module exists instead "
            "of a heading-weighted entropy bonus)")
    model.heading_selfdistill_coef = float(coef)
    model.heading_selfdistill_grad_clip = float(grad_clip)
    model.heading_selfdistill_cos_max = float(cos_max)
    model._heading_selfdistill_vref_idx = idx


HEADING_SELFDISTILL_WANDB_KEYS = (
    "train/heading_selfdistill_loss",
    "train/heading_selfdistill_off_axis_frac",
    "train/heading_selfdistill_n_keep",
)


def heading_selfdistill_wandb_payload(logger) -> dict:
    """Pulls this module's 3 SB3-logger keys (recorded by
    ``_heading_selfdistill_step`` via ``self.logger.record`` before
    ``super().train()`` runs each rollout) into a plain dict for a
    caller's own ``wandb.log(payload)`` call. train_ppo_mjx.py builds
    its W&B ``train/*``/``rollout/*`` charts entirely from a hand-built
    per-rollout payload dict, not a generic SB3-logger-to-W&B bridge,
    so these keys were otherwise silent on W&B even while the
    mechanism was firing (gap flagged CURRENT_TRUTHS/walkcurr STATUS
    2026-09-09 ~17:1x). Zero-cost / additive-only: ``logger=None`` or
    a key never recorded this rollout (module not attached, coef=0, or
    a no-op rollout) yields an empty/partial dict, never raises."""
    out: dict = {}
    if logger is None:
        return out
    name_to_value = getattr(logger, "name_to_value", None)
    if not name_to_value:
        return out
    for k in HEADING_SELFDISTILL_WANDB_KEYS:
        v = name_to_value.get(k)
        if v is not None:
            out[k] = float(v)
    return out


def make_heading_selfdistill_ppo_class(base_cls):
    """``HeadingSelfDistillPPO``: ``base_cls`` (compose with
    BCAnchorPPO/MirrorPPO/YawCreditPPO as needed) + one advantage-
    filtered, heading-restricted self-distillation optimizer step, run
    BEFORE ``super().train()`` touches (flattens in place) the rollout
    buffer."""

    class HeadingSelfDistillPPO(base_cls):
        heading_selfdistill_coef: float = 0.0
        heading_selfdistill_grad_clip: float = 0.0
        heading_selfdistill_cos_max: float = 0.5

        def train(self) -> None:
            self._heading_selfdistill_step()
            super().train()

        def _heading_selfdistill_step(self) -> None:
            coef = float(getattr(self, "heading_selfdistill_coef", 0.0))
            if coef <= 0.0:
                return
            idx = getattr(self, "_heading_selfdistill_vref_idx", None)
            if idx is None:
                return  # not attached -- defensive no-op, never crash
            buf = self.rollout_buffer
            if getattr(buf, "generator_ready", False):
                raise RuntimeError(
                    "_heading_selfdistill_step must run before "
                    "super().train() consumes the rollout buffer")
            obs = np.asarray(buf.observations)
            n_steps, n_envs, obs_dim = obs.shape
            n_total = n_steps * n_envs
            obs_flat = obs.reshape(n_total, obs_dim)
            act = np.asarray(buf.actions)
            act_flat = act.reshape(n_total, act.shape[-1])
            adv_flat = np.asarray(buf.advantages).reshape(-1).astype(
                np.float64)
            cos_max = float(getattr(self, "heading_selfdistill_cos_max",
                                    0.5))
            cos_h = heading_cos(obs_flat[:, idx:idx + 2])
            off_axis = cos_h <= cos_max
            off_axis_frac = float(off_axis.mean())
            logger = getattr(self, "logger", None)
            adv_std = adv_flat.std()
            if adv_std <= 1e-8:
                if logger is not None:
                    logger.record("train/heading_selfdistill_off_axis_frac",
                                  off_axis_frac)
                    logger.record("train/heading_selfdistill_n_keep", 0)
                return  # degenerate/no-variance advantage -- no-op
            adv_norm = (adv_flat - adv_flat.mean()) / (adv_std + 1e-8)
            weight = np.clip(adv_norm, 0.0, None) * off_axis
            keep = weight > 0.0
            n_keep = int(keep.sum())
            if n_keep < 8:
                if logger is not None:
                    logger.record("train/heading_selfdistill_off_axis_frac",
                                  off_axis_frac)
                    logger.record("train/heading_selfdistill_n_keep",
                                  n_keep)
                return  # too few usable samples this rollout -- no-op
            w = weight[keep]
            w = w / (w.mean() + 1e-8)  # keep loss scale rollout-stable
            device = self.device
            obs_t = th.as_tensor(obs_flat[keep], dtype=th.float32,
                                 device=device)
            act_t = th.as_tensor(act_flat[keep], dtype=th.float32,
                                 device=device)
            w_t = th.as_tensor(w, dtype=th.float32, device=device)
            self.policy.set_training_mode(True)
            dist = self.policy.get_distribution(obs_t)
            mean_act = dist.mode()  # differentiable mean action
            per_sample = ((mean_act - act_t) ** 2).sum(dim=-1)
            loss = (w_t * per_sample).mean() * coef
            self.policy.optimizer.zero_grad()
            loss.backward()
            clip = float(getattr(self, "heading_selfdistill_grad_clip",
                                 0.0))
            if clip > 0.0:
                th.nn.utils.clip_grad_norm_(
                    self.policy.parameters(), clip)
            self.policy.optimizer.step()
            if logger is not None:
                logger.record("train/heading_selfdistill_loss",
                              float(loss.detach().cpu()))
                logger.record("train/heading_selfdistill_off_axis_frac",
                              off_axis_frac)
                logger.record("train/heading_selfdistill_n_keep", n_keep)

    return HeadingSelfDistillPPO
