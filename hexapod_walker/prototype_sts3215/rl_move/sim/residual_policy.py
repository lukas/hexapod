"""Design A: frozen forward-walk base + trainable residual turn adapter.

Built 2026-09-27 for walkcurr's mixed walk+turn saga (STATUS.md
2026-09-27 ~01:0x, "lever (iii)"). Every closed lever so far (reward
pricing schedules, termination-cap schedules, warm-start init/
sequencing, the recurrent single-shared-core architecture) asks ONE
network to learn balance-under-turn and turn-tracking jointly, with
the SAME weights doing both. This module is categorically different:
it NEVER lets turn-authority gradients touch the weights that already
know how to stay upright walking forward.

Mechanism
---------
``load_frozen_base(ckpt_path)`` loads an existing SB3 PPO or SAC
checkpoint (any lineage -- its OWN training algorithm no longer
matters once frozen) and wraps its actor mean-action MLP
(``FrozenBaseWrapper``) so it can be called as a plain, gradient-free
``obs -> raw_mean_action`` function. Every parameter has
``requires_grad=False`` and the module stays in ``eval()`` mode
forever (enforced by ``ResidualActor.train()`` below, which always
re-pins it to eval even when the surrounding actor flips to train
mode).

``ResidualActor`` (subclasses SB3's own ``sac.policies.Actor``) composes
the frozen base with a small NEW trainable residual MLP (the ``Actor``
base class's own ``latent_pi``/``mu``/``log_std``, sized by
``net_arch=[adapter_hidden]`` -- reuses stock SB3 machinery rather than
inventing a second one). The composed pre-squash mean is:

    mean_actions = atanh(clip(frozen_base(obs[..., :base_obs_dim]))) \
                   + adapter_scale * mu_adapter(latent_pi_adapter(obs))

i.e. the frozen base's own bounded action is round-tripped through
``atanh`` so it becomes the correct pre-squash target for SAC's
``SquashedDiagGaussianDistribution`` (which applies ``tanh`` to
whatever ``mean_actions`` it is given): with ``mu_adapter`` zero-
initialized (mirrors the existing ``--gru-experts-adapter`` zero-init-
residual precedent in ``gru_policy.py``), the composed DETERMINISTIC
action is bit-identical (float32 round-trip, ~1e-6) to the frozen
base's own action at construction time -- a true single-lever
addition: the base's stance/balance quality is a hard floor that
training can only ADD to, never erode, unlike every closed warm-start
arm where the SAME weights that started stable were free to drift
under the mixed-task gradient.

The frozen base's own obs width may be NARROWER than this run's obs
(e.g. it never saw a later-appended yaw-rate command channel): the
extra trailing columns are simply dropped before calling the frozen
net (mirrors ``obs_pad_transplant``'s own append-at-end convention,
``rl_move/sim/obs_transplant.py``) -- the frozen net gets exactly the
obs shape it was trained on, always.

Only the adapter's own ``latent_pi``/``mu``/``log_std`` and a FRESH
critic (built by the surrounding ``ResidualSACPolicy``/SAC machinery,
unrelated to the frozen base) receive gradients. The frozen base's
parameters are folded into the policy's own ``state_dict()`` (so a
saved checkpoint is self-contained and reproducible off this exact
file for eval), but excluded from the actor's optimizer implicitly:
``requires_grad=False`` means autograd never builds a graph edge into
them, so their ``.grad`` stays ``None`` forever, and ``Adam.step()``
skips any parameter whose ``.grad is None`` -- no explicit filtering
needed (verified in ``test_residual_policy.py``).

Wiring: ``train_ppo_mjx.py``'s ``--algo sac`` path,
``--residual-frozen-base <ckpt>`` (mutually exclusive with
``--init-from`` -- this is a fresh SAC critic/adapter build over a
frozen, already-trained actor, not a checkpoint continuation),
``--residual-adapter-hidden`` (default 64), ``--residual-adapter-
scale`` (default 0.1).
"""
from __future__ import annotations

from typing import Any

_ATANH_CLIP = 0.999995  # keeps atanh finite; ~1e-6 corner-case slack


def _atanh(x):
    import torch as th
    x = th.clamp(x, -_ATANH_CLIP, _ATANH_CLIP)
    return 0.5 * th.log((1.0 + x) / (1.0 - x))


class FrozenBaseWrapper:
    """Wraps a loaded SB3 policy's actor mean-action network as a
    frozen (no-grad, eval-mode-forever), obs-width-sliced callable.

    Not an ``nn.Module`` on purpose: kept OUT of ``ResidualActor``'s
    normal submodule/parameter tree isn't required (its params still
    need ``requires_grad=False`` + registration so ``state_dict()``
    saves/restores them, see ``ResidualActor`` below, which explicitly
    calls ``add_module``) but this class itself is a thin dataclass-ish
    holder so ``load_frozen_base`` can be unit-tested without
    constructing a full ``Actor``.
    """

    def __init__(self, policy_net, action_net, base_obs_dim: int):
        self.policy_net = policy_net
        self.action_net = action_net
        self.base_obs_dim = int(base_obs_dim)
        for net in (self.policy_net, self.action_net):
            for p in net.parameters():
                p.requires_grad = False
            net.eval()

    def __call__(self, obs):
        import torch as th
        with th.no_grad():
            base_obs = (obs[..., : self.base_obs_dim]
                        if self.base_obs_dim < obs.shape[-1] else obs)
            latent = self.policy_net(base_obs)
            return self.action_net(latent)


def load_frozen_base(ckpt_path: str, device: str = "cpu"
                      ) -> tuple[FrozenBaseWrapper, int]:
    """Load an SB3 PPO or SAC checkpoint, freeze its actor mean-net.

    Tries PPO first (``ActorCriticPolicy``: ``mlp_extractor.policy_net``
    + ``action_net``), falls back to SAC (``SACPolicy``:
    ``actor.latent_pi`` + ``actor.mu``) -- either way the result is a
    plain ``obs -> raw_mean_action`` callable; the source algorithm no
    longer matters once frozen. Returns ``(wrapper, base_obs_dim)``.
    """
    from stable_baselines3 import PPO, SAC
    try:
        m = PPO.load(ckpt_path, device=device)
        policy_net = m.policy.mlp_extractor.policy_net
        action_net = m.policy.action_net
    except Exception:
        m = SAC.load(ckpt_path, device=device)
        policy_net = m.policy.actor.latent_pi
        action_net = m.policy.actor.mu
    base_obs_dim = int(m.observation_space.shape[0])
    wrapper = FrozenBaseWrapper(policy_net, action_net, base_obs_dim)
    return wrapper, base_obs_dim


def _build_residual_actor_class():
    """Deferred class factory (torch/SB3 imported lazily, mirrors the
    rest of this codebase's lazy-heavy-import convention)."""
    import torch as th
    from torch import nn
    from stable_baselines3.sac.policies import Actor, SACPolicy, LOG_STD_MIN, LOG_STD_MAX

    class ResidualActor(Actor):
        """SAC actor: frozen-base mean + trainable zero-init residual.

        See module docstring for the composition formula. ``net_arch``
        (passed through by ``SACPolicy.make_actor``/``actor_kwargs``,
        set to ``[adapter_hidden]`` by ``ResidualSACPolicy``) sizes the
        adapter's OWN ``latent_pi``/``mu``/``log_std`` -- built by the
        stock ``Actor.__init__`` this class inherits from, then the
        ``mu`` head is zero-initialized here for bit-exact-at-init.
        """

        def __init__(self, *args, frozen_base: FrozenBaseWrapper,
                     adapter_scale: float = 0.1, **kwargs):
            super().__init__(*args, **kwargs)
            self.frozen_base = frozen_base
            self.adapter_scale = float(adapter_scale)
            # Register the frozen net as a real submodule so .to(device)/
            # state_dict()/load_state_dict() carry it (self-contained,
            # reproducible checkpoint) -- but its own .requires_grad is
            # already False (set in FrozenBaseWrapper.__init__), so it
            # never receives a gradient and needs no optimizer filtering
            # (Adam.step() skips any param whose .grad is None).
            self.add_module("frozen_base_policy_net", frozen_base.policy_net)
            self.add_module("frozen_base_action_net", frozen_base.action_net)
            # zero-init residual mean head: composed action == frozen
            # base's own action at construction time (bit-exact modulo
            # the atanh/tanh float32 round-trip, ~1e-6).
            nn.init.zeros_(self.mu.weight)
            nn.init.zeros_(self.mu.bias)

        def train(self, mode: bool = True):
            super().train(mode)
            # the frozen base NEVER leaves eval mode, regardless of what
            # the surrounding actor/policy is doing (no dropout/BN in
            # these MLPs today, but this is the correct contract even
            # if one is ever added upstream).
            self.frozen_base.policy_net.eval()
            self.frozen_base.action_net.eval()
            return self

        def get_action_dist_params(self, obs):
            base_raw = self.frozen_base(obs)
            base_mean = _atanh(base_raw)
            features = self.extract_features(obs, self.features_extractor)
            latent_pi = self.latent_pi(features)
            residual = self.mu(latent_pi)
            mean_actions = base_mean + self.adapter_scale * residual
            log_std = self.log_std(latent_pi)
            log_std = th.clamp(log_std, LOG_STD_MIN, LOG_STD_MAX)
            return mean_actions, log_std, {}

    class ResidualSACPolicy(SACPolicy):
        """``SACPolicy`` whose actor is a ``ResidualActor`` wrapping a
        frozen base loaded from ``frozen_base_ckpt``. ``net_arch`` may
        be a plain list (used for BOTH actor-adapter and critic, not
        the intended use) or -- always, when wired via
        ``--residual-frozen-base`` in ``train_ppo_mjx.py`` -- the dict
        form ``{"pi": [adapter_hidden], "qf": critic_arch}`` so the
        adapter can stay small while the critic keeps full capacity
        ("a fresh critic", the design's own phrase).
        """

        def __init__(self, *args, frozen_base_ckpt: str,
                     adapter_hidden: int = 64, adapter_scale: float = 0.1,
                     **kwargs):
            self._frozen_base_ckpt = str(frozen_base_ckpt)
            self._adapter_hidden = int(adapter_hidden)
            self._adapter_scale = float(adapter_scale)
            super().__init__(*args, **kwargs)

        def make_actor(self, features_extractor=None):
            actor_kwargs = self._update_features_extractor(
                self.actor_kwargs, features_extractor)
            frozen_base, _ = load_frozen_base(self._frozen_base_ckpt,
                                               device=str(self.device))
            return ResidualActor(
                **actor_kwargs, frozen_base=frozen_base,
                adapter_scale=self._adapter_scale).to(self.device)

    return ResidualActor, ResidualSACPolicy


# Public names resolved lazily (torch/SB3 import cost) the first time
# either is needed, then cached -- mirrors gru_policy.py's own module-
# level class-definition pattern but deferred so importing this file
# never requires torch (kept import-light like obs_transplant.py).
_ResidualActor = None
_ResidualSACPolicy = None


def get_residual_actor_class():
    global _ResidualActor, _ResidualSACPolicy
    if _ResidualActor is None:
        _ResidualActor, _ResidualSACPolicy = _build_residual_actor_class()
    return _ResidualActor


def get_residual_sac_policy_class():
    global _ResidualActor, _ResidualSACPolicy
    if _ResidualSACPolicy is None:
        _ResidualActor, _ResidualSACPolicy = _build_residual_actor_class()
    return _ResidualSACPolicy
