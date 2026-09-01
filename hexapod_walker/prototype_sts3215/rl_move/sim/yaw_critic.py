"""yaw_critic.py — reward-decomposed (yaw-component) critic + advantage
for standwalk turn-authority RETENTION (09-01).

WHY THIS EXISTS: the entire single-update-size-constraint mechanism
family (actor-freeze, value-warmup, kl-rollback at doses 0.05/0.02/
~0.01) is CLOSED (standwalk STATUS.md 09-01, klrolldriftmatch matched-
drift confirmed n=4, klrolltight2 guard-reject-all closure) at a
durable ceiling of pos~0.075-0.09 / neg~-0.10 to -0.12 turn-authority
(``probe_turn_authority`` wz_med, PASS bar >=0.10 both signs). The
campaign's own root cause (``probe_yaw_credit.py``, 08-31): the yaw
reward channel fires a real, sizeable per-tick income, but the ONE
shared value function's advantage is dominated by the much larger
walk-forward reward, so the critic never anticipates a yaw-toward-
command tick as "better than expected" — the yaw credit signal is
drowned, not absent. Slowing/gating the UPDATE (this whole closed
family) cannot fix a credit-assignment problem inside a single scalar
advantage; it only changes how fast the walk-dominated advantage
erodes whatever turn skill BC-anchor mirror-augment supplied at init.

WHAT THIS BUILDS: a SECOND, INDEPENDENT value head (``value_net_yaw``,
mirroring the existing dual-core ``value_net``/``value_net_b`` head
pattern in ``gru_policy.DualGruActorCriticPolicy``) trained via its
OWN GAE computed off the ``reward_walk_yaw`` component alone (already
emitted per-tick in ``info`` whenever ``reward.k_walk_yaw>0`` — see
``probe_yaw_credit.RewardComponentCollector``/``smoke_yaw_quad.py``).
A yaw-only advantage (normalized) drives a SEPARATE, additional actor
policy-gradient step — a plain REINFORCE-with-baseline step, not a
second call into sb3-contrib's clipped surrogate: because this step
runs from the SAME (not-yet-updated-this-iteration) weights the
rollout was collected with, PPO's ratio = exp(new_logp - old_logp) is
identically 1 at that point and its GRADIENT already reduces exactly
to the plain policy-gradient form (d/dtheta ratio = ratio *
d(log_prob)/dtheta), so clipping has no effect here and is skipped
for simplicity — this is mathematically the same update a "sum the
advantages into the PPO loss" design would produce on epoch 0 of the
main update, just spent as its own optimizer step (matching this
codebase's established aux-loss house style: ``mirror.py``/
``bc_anchor.py`` both run a SEPARATE step after/around
``super().train()`` rather than editing sb3-contrib internals).

Everything here is restricted to CORE A (the locomotion/walk core of
``DualGruActorCriticPolicy`` — the ``_group()`` classification in
``bc_anchor.py`` calls this "a"): the yaw reward only ever fires on
walk/turn ticks, which route through core A by construction
(``walk_task.MODE_ONEHOT_ORDER``); ticks are additionally MASKED to
``gate>0.5`` (locomotion-family) before either the value regression or
the actor step sees them, so stance-family (core B) ticks never
contribute a stray gradient through this mechanism.

RISK CONTAINMENT (RESEARCH_RULES: never let a new mechanism silently
reshape a shared default path):
- New cfg keys ``train.yaw_credit_coef`` / ``train.yaw_credit_vf_coef``
  default 0.0 = OFF; ``attach_yaw_credit`` / the collect callback are
  only wired in when at least one is > 0 (train_ppo_mjx.py). Off runs
  are bit-exact: no extra module, no extra forward pass, no extra
  optimizer step.
- The value_net_yaw head only ever reads a DETACHED copy of the
  shared core-A critic trunk features (``mlp_extractor.forward_
  critic`` output) — its regression gradient cannot perturb the
  weights the MAIN value function (``value_net``) also reads. The
  actor step is NOT detached (influencing the actor is the entire
  point), so it is real new-code training surface — canary first.
- ``_yaw_credit_step`` no-ops (does not raise) if the collector
  callback never ran or the buffer has too few locomotion ticks this
  rollout — a missing wiring step degrades to a silent no-op, never a
  crash mid-training. ``attach_yaw_credit`` itself DOES raise loudly
  at attach time on a misconfigured setup (wrong policy class, dead
  reward channel) — the bc_anchor "never silently no-op at launch"
  contract.

See rl_docs/tracks/standwalk/STATUS.md 09-01 for the campaign context
and rl_move/tests/test_yaw_critic.py for the GAE-vs-SB3 cross-check
and the off-path bit-exactness tests.
"""
from __future__ import annotations

import numpy as np
import torch as th
from stable_baselines3.common.callbacks import BaseCallback


# --------------------------------------------------------------------
# Pure-numpy GAE — verified bit-identical to
# stable_baselines3.common.buffers.RolloutBuffer.compute_returns_and_
# advantage (see test_yaw_critic.py::test_compute_gae_matches_sb3).
# --------------------------------------------------------------------

def compute_gae(rewards: np.ndarray, values: np.ndarray,
                episode_starts: np.ndarray, last_values: np.ndarray,
                last_dones: np.ndarray, *, gamma: float,
                gae_lambda: float) -> tuple[np.ndarray, np.ndarray]:
    """(n_steps, n_envs) rewards/values/episode_starts -> (advantages,
    returns), same shape. ``last_values``/``last_dones``: (n_envs,) —
    the bootstrap value estimate and done flag one step past the
    buffer's end (SB3's own ``compute_returns_and_advantage`` args)."""
    rewards = np.asarray(rewards, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    episode_starts = np.asarray(episode_starts, dtype=np.float64)
    n_steps, n_envs = rewards.shape
    advantages = np.zeros_like(rewards)
    last_gae_lam = np.zeros(n_envs, dtype=np.float64)
    last_values = np.asarray(last_values, dtype=np.float64)
    last_non_terminal = 1.0 - np.asarray(last_dones, dtype=np.float64)
    for step in reversed(range(n_steps)):
        if step == n_steps - 1:
            next_non_terminal = last_non_terminal
            next_values = last_values
        else:
            next_non_terminal = 1.0 - episode_starts[step + 1]
            next_values = values[step + 1]
        delta = (rewards[step] + gamma * next_values * next_non_terminal
                 - values[step])
        last_gae_lam = (delta + gamma * gae_lambda * next_non_terminal
                        * last_gae_lam)
        advantages[step] = last_gae_lam
    returns = advantages + values
    return advantages, returns


def _swap_flat(arr: np.ndarray) -> np.ndarray:
    """(n_steps, n_envs, ...) -> (n_envs * n_steps, ...), env-major
    (time contiguous within each env) — matches
    ``RolloutBuffer.swap_and_flatten`` / the layout
    ``gru_policy.GruActorCriticPolicy._process_sequence`` expects when
    told ``n_seq = h0.shape[1]`` parallel sequences."""
    shape = arr.shape
    if len(shape) < 3:
        shape = (*shape, 1)
    return arr.swapaxes(0, 1).reshape(shape[0] * shape[1], *shape[2:])


# --------------------------------------------------------------------
# Policy-side: the extra head + the two recompute helpers.
# --------------------------------------------------------------------

def attach_yaw_value_head(policy) -> None:
    """Idempotent. Adds a yaw-only value head (deep-copied architecture
    of ``value_net``, core-A/locomotion only) if not already present.

    DELIBERATELY NOT a registered ``nn.Module`` attribute (unlike
    ``value_net_b``/``log_std_b``, which the constructor itself owns
    and which therefore round-trip through save/load via the
    checkpoint's own ``policy_kwargs``): every launch on this campaign
    is a WARM START (``--init-from``), and ``BaseAlgorithm.load()``
    reconstructs the policy from the CHECKPOINT's OWN saved
    ``policy_kwargs`` — a constructor kwarg added only at attach-time
    has nowhere to round-trip to, so it would need to be threaded
    through every consumer of a yaw-credit-enabled checkpoint
    (``probe_turn_authority``, ``pod_eval``, the gate harness, the
    trainer's own background video helper) or every one of them raises
    ``Unexpected key(s) in state_dict: "value_net_yaw.*"`` on load
    (hit for real, 09-01 canary attempt 1: the bg-video helper crashed
    exactly this way). Keeping the head OUT of ``policy.state_dict()``
    entirely sidesteps the whole problem: every checkpoint this run
    saves is byte-identical in shape to a non-yaw-credit checkpoint,
    loadable by every existing tool unmodified. The head is stored in
    a plain ``list`` (invisible to ``nn.Module``'s parameter/
    state_dict traversal, which only follows registered Parameter/
    Module children) and its parameters are added to the EXISTING
    optimizer via ``add_param_group`` — NOT a full optimizer rebuild,
    which would discard the Adam momentum ``.load()`` restores for
    every pre-existing (warm-started) parameter.

    Cost of this choice: the yaw head does not persist across a
    training restart/respec boundary (each resume re-attaches a FRESH
    head). Acceptable for an auxiliary, experimental credit signal —
    it does not touch the actor's own warm-started weights, which are
    the ones this campaign actually needs to survive a restart.
    """
    from .gru_policy import DualGruActorCriticPolicy
    if not isinstance(policy, DualGruActorCriticPolicy):
        raise ValueError("attach_yaw_value_head requires a "
                         "DualGruActorCriticPolicy (pass --gru-dual)")
    if getattr(policy, "_yaw_value_head_holder", None) is not None:
        return
    import copy
    head = copy.deepcopy(policy.value_net)
    policy._yaw_value_head_holder = [head]
    # A SEPARATE optimizer, not policy.optimizer.add_param_group(...):
    # SB3 saves policy.optimizer.state_dict() into every checkpoint,
    # and an added param group changes its SHAPE -- a plain (yaw-
    # credit-unaware) RecurrentPPO.load() reconstructs a fresh
    # single-group optimizer from the checkpoint's own policy_kwargs,
    # then torch.optim.Optimizer.load_state_dict raises "loaded state
    # dict has a different number of parameter groups" (hit for real,
    # 09-01 canary attempt 2 -- see test_yaw_credit_checkpoint_
    # loadable_by_a_plain_recurrentppo). A fully independent optimizer
    # that SB3 never knows about, never saves, and never restores
    # sidesteps this completely, and as a bonus never disturbs the
    # Adam momentum ``.load()`` restores for every pre-existing
    # (warm-started) parameter in the MAIN optimizer.
    lr = policy.optimizer.defaults["lr"]
    policy._yaw_value_optimizer = policy.optimizer_class(
        head.parameters(), lr=lr, **policy.optimizer_kwargs)


def _yaw_head(policy):
    holder = getattr(policy, "_yaw_value_head_holder", None)
    if holder is None:
        raise RuntimeError("attach_yaw_value_head was not called on "
                           "this policy")
    return holder[0]


def value_yaw_over_sequence(policy, obs_flat: th.Tensor,
                            episode_starts_flat: th.Tensor,
                            h0: th.Tensor, *,
                            detach_trunk: bool = True) -> th.Tensor:
    """Recompute ``value_net_yaw(s)`` at EVERY position of a flattened
    rollout (or a single timestep — both are just "sequences of
    length >=1"), via the exact deterministic core-A critic recurrence
    (``GruActorCriticPolicy._process_sequence``) collection itself
    used, so the read is collection-time-consistent as long as the
    policy weights have not changed since (call this BEFORE any
    gradient step touches the shared trunk this iteration).

    ``obs_flat``/``episode_starts_flat``: env-major flattened buffer
    arrays (``_swap_flat``). ``h0``: the RAW (pre episode-start-mask —
    masking happens inside ``_process_sequence`` from
    ``episode_starts_flat``, exactly like the live rollout did)
    core-A critic hidden state at the first position of each sequence,
    shape ``(1, n_seq, H)`` where ``n_seq = obs_flat.shape[0] //
    seq_len`` is inferred by ``_process_sequence`` from ``h0.shape[1]``.
    """
    from .gru_policy import GruActorCriticPolicy
    from stable_baselines3.common.policies import ActorCriticPolicy
    head = _yaw_head(policy)
    feats = super(ActorCriticPolicy, policy).extract_features(
        obs_flat, policy.vf_features_extractor)
    zero = th.zeros_like(h0)
    out_a, _ = GruActorCriticPolicy._process_sequence(
        feats, (h0, zero), episode_starts_flat, policy.lstm_critic.core_a)
    trunk = policy.mlp_extractor.forward_critic(out_a)
    if detach_trunk:
        trunk = trunk.detach()
    return head(trunk).flatten()


def actor_mean_core_a_over_sequence(policy, obs_flat: th.Tensor,
                                    episode_starts_flat: th.Tensor,
                                    h0: th.Tensor) -> th.Tensor:
    """Core-A-only actor mean over a flattened rollout sequence — the
    undetached counterpart of ``value_yaw_over_sequence`` used for the
    extra yaw-advantage policy-gradient step (this one is meant to
    move the shared actor trunk; that is the entire point)."""
    from .gru_policy import GruActorCriticPolicy
    from stable_baselines3.common.policies import ActorCriticPolicy
    feats = super(ActorCriticPolicy, policy).extract_features(
        obs_flat, policy.pi_features_extractor)
    zero = th.zeros_like(h0)
    out_a, _ = GruActorCriticPolicy._process_sequence(
        feats, (h0, zero), episode_starts_flat, policy.lstm_actor.core_a)
    return policy.action_net(policy.mlp_extractor.forward_actor(out_a))


# --------------------------------------------------------------------
# Rollout-time collection: pair reward_walk_yaw with buffer positions.
# --------------------------------------------------------------------

def make_yaw_credit_collect_callback():
    """Fills ``model._yawcred_rew`` (n_steps, n_envs) float32 with
    ``info["reward_walk_yaw"]`` (0.0 when absent), in lockstep with
    ``RecurrentPPO.collect_rollouts``'s own step counter — same
    ``self.locals``-reading pattern as
    ``bc_anchor.BCAnchorCollectCallback``."""

    class YawCreditCollectCallback(BaseCallback):
        def _on_rollout_start(self) -> None:
            n_envs = self.training_env.num_envs
            n_steps = int(self.model.n_steps)
            self.model._yawcred_rew = np.zeros(
                (n_steps, n_envs), dtype=np.float32)
            self._t = 0

        def _on_step(self) -> bool:
            infos = self.locals.get("infos", ())
            buf = getattr(self.model, "_yawcred_rew", None)
            if buf is not None and self._t < buf.shape[0]:
                buf[self._t] = [float(info.get("reward_walk_yaw", 0.0))
                                for info in infos]
            self._t += 1
            return True

    return YawCreditCollectCallback()


# --------------------------------------------------------------------
# PPO composition.
# --------------------------------------------------------------------

def make_yaw_credit_ppo_class(base_cls):
    """``YawCreditPPO``: ``base_cls`` (pass ``BCAnchorPPO``/
    ``MirrorPPO`` to compose) + one yaw-value regression step and one
    yaw-advantage actor step, run BEFORE ``super().train()`` touches
    (flattens in place) the rollout buffer."""

    class YawCreditPPO(base_cls):
        yaw_credit_coef: float = 0.0
        yaw_credit_vf_coef: float = 0.0
        # Trust-region cap for the extra actor policy-gradient step
        # ONLY (09-01, post-canary-FAIL follow-up: cw-standwalk-stage2-
        # dualbc6-turncap-mirroraug-yawcredit-canary-rr1 read WORSE
        # turn authority than its matched coef=0 control on BOTH
        # signs at coef=1.0/vf=0.5 -- the pg step below is a plain,
        # UNCLIPPED policy-gradient update sharing the main actor
        # optimizer, exactly the update-SIZE shape the whole closed
        # freeze/value-warmup/kl-rollback family exists to guard
        # against. Default 0.0 = OFF/no clip (bit-exact vs the
        # canary's own behavior when unset -- see
        # test_yaw_credit_grad_clip_off_path_bit_exact).
        yaw_credit_grad_clip: float = 0.0

        def _excluded_save_params(self) -> list:
            # Rollout data, not model state (the yaw value head lives
            # in policy._yaw_value_head_holder, a plain list invisible
            # to nn.Module's own state_dict traversal -- see
            # attach_yaw_value_head's docstring for why it must stay
            # that way).
            return super()._excluded_save_params() + ["_yawcred_rew"]

        def train(self) -> None:
            self._yaw_credit_step()
            super().train()

        def _yaw_credit_step(self) -> None:
            coef = float(getattr(self, "yaw_credit_coef", 0.0))
            vf_coef = float(getattr(self, "yaw_credit_vf_coef", 0.0))
            if coef <= 0.0 and vf_coef <= 0.0:
                return
            policy = self.policy
            if getattr(policy, "_yaw_value_head_holder", None) is None:
                return  # not attached -- defensive no-op, never crash
            buf = self.rollout_buffer
            if getattr(buf, "generator_ready", False):
                # Must run before the FIRST buf.get() this iteration
                # reshapes hidden_states_vf/observations in place.
                raise RuntimeError(
                    "_yaw_credit_step must run before super().train() "
                    "consumes the rollout buffer")
            # collect_rollouts leaves the policy in eval mode
            # (set_training_mode(False), sb3-contrib convention); a
            # cuDNN RNN backward pass REQUIRES training mode to have
            # been set before its matching forward pass or the C++
            # backend raises ("cudnn RNN backward can only be called
            # in training mode") -- caught on-pod (GPU/cuDNN), not by
            # the CPU unit tests (cuDNN isn't in the CPU path at all).
            # super().train() would flip this right back to True
            # itself in a moment; doing it here first just makes OUR
            # forward+backward passes consistent too.
            policy.set_training_mode(True)
            yaw_rew = getattr(self, "_yawcred_rew", None)
            n_steps, n_envs = buf.rewards.shape
            if (yaw_rew is None
                    or tuple(yaw_rew.shape) != (n_steps, n_envs)):
                return  # collector callback never wired -- silent no-op
            last_obs = getattr(self, "_last_obs", None)
            last_states = getattr(self, "_last_lstm_states", None)
            last_starts = getattr(self, "_last_episode_starts", None)
            if last_obs is None or last_states is None:
                return

            device = self.device
            obs_flat = th.as_tensor(
                _swap_flat(np.asarray(buf.observations)),
                device=device, dtype=th.float32)
            ep_starts_flat = th.as_tensor(
                _swap_flat(np.asarray(buf.episode_starts)).reshape(-1),
                device=device, dtype=th.float32)
            h0_vf = th.as_tensor(
                np.asarray(buf.hidden_states_vf[0, 0:1]),
                device=device, dtype=th.float32)

            with th.no_grad():
                value_yaw_grid = value_yaw_over_sequence(
                    policy, obs_flat, ep_starts_flat, h0_vf,
                    detach_trunk=True,
                ).reshape(n_envs, n_steps).transpose(0, 1).cpu().numpy()

                obs_boot = th.as_tensor(
                    np.asarray(last_obs), device=device, dtype=th.float32)
                starts_boot = th.as_tensor(
                    np.asarray(last_starts, dtype=np.float32),
                    device=device)
                h_boot = last_states.vf[0][0:1].to(device)
                value_yaw_boot = value_yaw_over_sequence(
                    policy, obs_boot, starts_boot, h_boot,
                    detach_trunk=True).cpu().numpy()

            adv_yaw, ret_yaw = compute_gae(
                yaw_rew, value_yaw_grid,
                np.asarray(buf.episode_starts, dtype=np.float64),
                value_yaw_boot, np.asarray(last_starts, dtype=np.float64),
                gamma=float(buf.gamma), gae_lambda=float(buf.gae_lambda))

            gate_flat = policy._gate(obs_flat).flatten() > 0.5
            n_mask = int(gate_flat.sum().item())
            if n_mask < 8:
                return  # too few locomotion ticks this rollout to fit

            logger = getattr(self, "logger", None)
            if vf_coef > 0.0:
                value_yaw_pred = value_yaw_over_sequence(
                    policy, obs_flat, ep_starts_flat, h0_vf,
                    detach_trunk=True)
                ret_yaw_flat = th.as_tensor(
                    _swap_flat(ret_yaw).reshape(-1), device=device,
                    dtype=th.float32)
                vf_loss = th.nn.functional.mse_loss(
                    value_yaw_pred[gate_flat], ret_yaw_flat[gate_flat])
                yaw_opt = policy._yaw_value_optimizer
                yaw_opt.zero_grad()
                (vf_coef * vf_loss).backward()
                yaw_opt.step()
                if logger is not None:
                    logger.record("train/yaw_credit_vf_loss",
                                  float(vf_loss.item()))

            if coef > 0.0:
                h0_pi = th.as_tensor(
                    np.asarray(buf.hidden_states_pi[0, 0:1]),
                    device=device, dtype=th.float32)
                mean_a = actor_mean_core_a_over_sequence(
                    policy, obs_flat, ep_starts_flat, h0_pi)
                gate_ones = th.ones(
                    (mean_a.shape[0], 1), device=device)
                dist = policy._dist_from_mean(mean_a, gate_ones)
                actions_flat = th.as_tensor(
                    _swap_flat(np.asarray(buf.actions)),
                    device=device, dtype=th.float32)
                log_prob = dist.log_prob(actions_flat)
                adv_yaw_flat = th.as_tensor(
                    _swap_flat(adv_yaw).reshape(-1), device=device,
                    dtype=th.float32)
                adv_m = adv_yaw_flat[gate_flat]
                adv_norm = (adv_m - adv_m.mean()) / (adv_m.std() + 1e-8)
                pg_loss = -(log_prob[gate_flat] * adv_norm.detach()).mean()
                policy.optimizer.zero_grad()
                (coef * pg_loss).backward()
                clip = float(getattr(self, "yaw_credit_grad_clip", 0.0))
                grad_norm = None
                if clip > 0.0:
                    # Clips ONLY this step's gradients -- zero_grad()
                    # just above means no other params carry a stale
                    # .grad at this point, and the main super().train()
                    # PPO update below does its own independent
                    # zero_grad/backward/(optional) clip per epoch, so
                    # this never touches the main step's trust region.
                    grad_norm = float(th.nn.utils.clip_grad_norm_(
                        policy.parameters(), clip))
                policy.optimizer.step()
                if logger is not None:
                    logger.record("train/yaw_credit_pg_loss",
                                  float(pg_loss.item()))
                    logger.record("train/yaw_credit_adv_yaw_mean",
                                  float(adv_m.mean().item()))
                    if grad_norm is not None:
                        logger.record("train/yaw_credit_grad_norm",
                                      grad_norm)
            if logger is not None:
                logger.record("train/yaw_credit_n_masked", float(n_mask))

    return YawCreditPPO


def attach_yaw_credit(model, *, coef: float, vf_coef: float,
                      cfg: dict | None, grad_clip: float = 0.0) -> None:
    """Validates the run can actually produce a live signal (same
    "never silently no-op at launch" contract as
    ``bc_anchor.attach_bc_anchor``), attaches the value head, and sets
    the coefficients the ``YawCreditPPO.train()`` override reads."""
    from rl_move.config import cfg_get
    from .gru_policy import DualGruActorCriticPolicy
    if not isinstance(model.policy, DualGruActorCriticPolicy):
        raise SystemExit(
            "train.yaw_credit_coef/_vf_coef require --gru-dual (the "
            "yaw-value head hangs off DualGruActorCriticPolicy's "
            "core-A/locomotion critic)")
    k_yaw = float(cfg_get(cfg, "reward", "k_walk_yaw", default=0.0) or 0.0)
    if k_yaw <= 0.0:
        raise SystemExit(
            "train.yaw_credit_coef/_vf_coef set but reward.k_walk_yaw "
            "<= 0 -- the env would never emit reward_walk_yaw and the "
            "mechanism would silently no-op")
    attach_yaw_value_head(model.policy)
    model.yaw_credit_coef = float(coef)
    model.yaw_credit_vf_coef = float(vf_coef)
    model.yaw_credit_grad_clip = float(grad_clip)
