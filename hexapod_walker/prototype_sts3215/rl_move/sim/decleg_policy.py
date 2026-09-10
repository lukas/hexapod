"""Decentralized per-leg actor policy (walkcurr rung-1, operator-registered
literature: Schilling et al., IROS 2020, arXiv:2005.11164).

Six independent per-leg actor modules (default 2x64) replace the single
centralized MLP actor: the action for leg i is a function ONLY of that
leg's local state (its 3 joint positions, 3 joint velocities, 3
previous-action dims) plus the shared body/command state (tilt, gyro,
goal/command tail).  No cross-leg connections exist anywhere on the
action path — coordination has to emerge through the body/environment,
which is the paper's central claim (their centralized baseline "got
stuck more often in local minima", exactly the walkcurr campaign's
15-classes-frozen signature; the decentralized arm reached the
centralized arm's final performance in less than half the training
time and out-performed it at convergence, p=.011).

The critic stays CENTRALIZED (full observation) — a standard
centralized-training/decentralized-execution split; the critic
vanishes at deployment so the saved action path is per-leg by
construction.

ADDENDUM 2026-09-10 (DESIGN_NOTE_2026-09-10_offaxis_frontpair.md, 13th
mechanism class on the front-pair off-axis-heading sacrifice, after
decleg's own plain/gSDE/half-gravity arms all closed FAIL): the
INDEPENDENT-tower default above cannot transfer skill between legs by
construction — leg0/leg5 (mounted closest to the forward axis) must
independently rediscover, from their own scarce off-axis experience,
the wide-swing trajectory legs mounted broadside/rear already get for
free from THEIR easy headings. Two new, default-OFF constructor
kwargs target that directly and are meant to be tried TOGETHER (see
each kwarg's own docstring below for why alone is not the hypothesis):
``share_leg_weights`` (tie all six towers to ONE set of weights) and
``heading_rel_idx`` (feed each tower the commanded heading rotated
into ITS OWN mount frame, via ``heading_rel_cos_sin``, so the same
physical situation reads identically to every leg regardless of mount
angle — the shared tower's precondition for actually transferring
anything). Neither changes behavior unless explicitly passed; the
plain decentralized path above is unaffected.

Obs layout contract (joint-family tasks, ``obs.history_frames == 1``):

    [ 0:18]  q_rel        (leg-major: leg i owns dims 3i..3i+2)
    [18:36]  qd           (same order)
    [36:38]  tilt
    [38:41]  gyro
    [41:59]  prev_action  (same order)
    [59: W]  goal/command tail (+ walk vel feedback etc.) — shared

``joint_walk_leg_slices(obs_width)`` computes the index sets; the
trainer fills them into policy_kwargs after the venv reports its obs
width, mirroring the asym-critic post-venv pattern.  policy_kwargs
(incl. the index lists) are stored in the model file, so PPO.load
reconstructs the exact same wiring for eval.
"""
from __future__ import annotations

import math

import numpy as np
import torch
from torch import nn

from stable_baselines3.common.policies import ActorCriticPolicy

N_LEGS = 6
ACT_PER_LEG = 3

# Mesh mount angles (mesh_mujoco/hexapod_mesh_mjx.xml, leg-major order
# matching joint_walk_leg_slices' leg 0..5): L0=+30, L1=+90, L2=+150,
# L3=-150, L4=-90, L5=-30 degrees off the forward (+x) body axis. This
# is the SAME fact DESIGN_NOTE_2026-09-10_offaxis_frontpair.md names as
# the geometric root cause of the front-pair (leg0/leg5) off-axis-
# heading sacrifice: those two legs need the LARGEST reorientation of
# any leg for a 90-180 degree command. Used only by the optional
# --decleg-heading-rel feature below (heading_rel_cos_sin); has no
# effect unless a caller passes heading_rel_idx.
LEG_MOUNT_ANGLES_DEG = (30.0, 90.0, 150.0, -150.0, -90.0, -30.0)


def leg_mount_unit_vectors(mount_angles_deg=LEG_MOUNT_ANGLES_DEG
                           ) -> list[tuple[float, float]]:
    """[(cos(mount_i), sin(mount_i)), ...] for each leg's mount angle."""
    return [(math.cos(math.radians(a)), math.sin(math.radians(a)))
            for a in mount_angles_deg]


def heading_rel_cos_sin(cos_cmd, sin_cmd, mount_cos: float,
                        mount_sin: float):
    """Rotate a commanded-heading unit vector ``(cos_cmd, sin_cmd)``
    (world/body frame, forward = (1, 0)) into ONE leg's own mount-
    angle-relative frame: returns ``(cos_rel, sin_rel)``, the SAME
    command re-expressed relative to that leg's own straight-ahead
    direction (its mount angle). Plain 2D frame rotation by
    ``-mount_angle`` (``cos_rel = cos(cmd - mount)``,
    ``sin_rel = sin(cmd - mount)``), pure ``+``/``-``/``*`` so it
    works identically on python floats, numpy arrays, or torch
    tensors (autograd-transparent).

    Why this matters (DESIGN_NOTE_2026-09-10_offaxis_frontpair.md
    addendum, 13th mechanism class): every leg's mount angle differs
    (LEG_MOUNT_ANGLES_DEG), so the SAME raw world-frame heading means
    a very different physical ask per leg — leg2 (mount +150) sees a
    +150 command as "your easy/aligned direction", leg0 (mount +30)
    sees the SAME +150 command as "120 degrees off your own
    straight-ahead". Expressing the command in each leg's OWN frame
    makes physically-equivalent asks look IDENTICAL across legs
    regardless of which leg is asked, which is the precondition for a
    weight-TIED per-leg tower (--decleg-share-legs) to transfer a
    skill learned by one leg's easy heading directly onto another
    leg's hard heading, instead of every leg having to independently
    rediscover it (decleg's own independent-tower default cannot do
    this even in principle: no weight sharing exists for anything to
    transfer through)."""
    cos_rel = cos_cmd * mount_cos + sin_cmd * mount_sin
    sin_rel = sin_cmd * mount_cos - cos_cmd * mount_sin
    return cos_rel, sin_rel


def joint_walk_leg_slices(obs_width: int
                          ) -> tuple[list[list[int]], list[int]]:
    """(leg_obs_idx, shared_obs_idx) for the joint-family obs layout.

    Works for any tail width (obs 68/72/74 variants): everything from
    dim 59 on is shared command/feedback state.
    """
    obs_width = int(obs_width)
    if obs_width < 59:
        raise ValueError(
            f"obs width {obs_width} is not a joint-family layout "
            "(need >= 59 dims: 18q+18qd+2tilt+3gyro+18prev)")
    legs = []
    for i in range(N_LEGS):
        legs.append([3 * i, 3 * i + 1, 3 * i + 2,
                     18 + 3 * i, 18 + 3 * i + 1, 18 + 3 * i + 2,
                     41 + 3 * i, 41 + 3 * i + 1, 41 + 3 * i + 2])
    shared = list(range(36, 41)) + list(range(59, obs_width))
    return legs, shared


def _mlp(in_dim: int, hidden: tuple[int, ...],
         activation_fn: type[nn.Module]) -> nn.Sequential:
    layers: list[nn.Module] = []
    last = in_dim
    for h in hidden:
        layers += [nn.Linear(last, int(h)), activation_fn()]
        last = int(h)
    return nn.Sequential(*layers)


class _PerLegHead(nn.Module):
    """Block-diagonal action head: leg i's latent chunk -> 3 action
    dims, leg-major concat (matches the joint/action ordering)."""

    def __init__(self, n_legs: int, latent_per_leg: int,
                 act_per_leg: int = ACT_PER_LEG):
        super().__init__()
        self.n_legs = int(n_legs)
        self.latent_per_leg = int(latent_per_leg)
        self.heads = nn.ModuleList(
            [nn.Linear(latent_per_leg, act_per_leg)
             for _ in range(n_legs)])

    def forward(self, latent: torch.Tensor) -> torch.Tensor:
        chunks = torch.split(latent, self.latent_per_leg, dim=-1)
        return torch.cat([h(c) for h, c in zip(self.heads, chunks)],
                         dim=-1)


class _DecLegExtractor(nn.Module):
    """MlpExtractor stand-in: per-leg actor towers + centralized
    value tower.  forward_actor output = concat of per-leg latents
    (leg-major), consumed by the block-diagonal _PerLegHead."""

    def __init__(self, feature_dim: int,
                 leg_obs_idx: list[list[int]],
                 shared_obs_idx: list[int],
                 leg_hidden: tuple[int, ...],
                 value_arch: tuple[int, ...],
                 activation_fn: type[nn.Module],
                 device: torch.device | str = "auto",
                 share_leg_weights: bool = False,
                 heading_rel_idx: tuple[int, int] | None = None,
                 leg_mount_deg: tuple[float, ...] = LEG_MOUNT_ANGLES_DEG):
        super().__init__()
        if not leg_obs_idx:
            raise ValueError("leg_obs_idx is empty — the trainer must "
                             "fill it (joint_walk_leg_slices)")
        n_local = len(leg_obs_idx[0])
        if any(len(ix) != n_local for ix in leg_obs_idx):
            raise ValueError("ragged leg_obs_idx")
        flat = [j for ix in leg_obs_idx for j in ix]
        if len(set(flat)) != len(flat):
            raise ValueError("leg_obs_idx sets overlap between legs")
        self.latent_dim_pi = int(leg_hidden[-1]) * len(leg_obs_idx)
        self.latent_dim_vf = int(value_arch[-1])
        # --decleg-heading-rel (default heading_rel_idx=None = bit-
        # exact off, no extra input dims): append [cos_rel, sin_rel]
        # -- the commanded heading rotated into THIS leg's own mount
        # frame (heading_rel_cos_sin) -- to every leg's local input.
        self._heading_rel_on = heading_rel_idx is not None
        n_extra = 2 if self._heading_rel_on else 0
        in_dim = len(shared_obs_idx) + n_local + n_extra
        # --decleg-share-legs (default False = bit-exact off, current
        # independent-tower behavior): build ONE tower and reference
        # it N_LEGS times. nn.Module.named_parameters()/.parameters()
        # dedup by tensor identity, so the optimizer sees each weight
        # exactly once and gradients from every leg's forward pass
        # accumulate into the SAME parameter (standard weight-tying,
        # same mechanism as an RNN cell reused across timesteps).
        if share_leg_weights:
            _shared_tower = _mlp(in_dim, tuple(leg_hidden), activation_fn)
            self.leg_nets = nn.ModuleList(
                [_shared_tower for _ in leg_obs_idx])
        else:
            self.leg_nets = nn.ModuleList(
                [_mlp(in_dim, tuple(leg_hidden), activation_fn)
                 for _ in leg_obs_idx])
        self.share_leg_weights = bool(share_leg_weights)
        self.value_net = _mlp(feature_dim, tuple(value_arch),
                              activation_fn)
        # Non-persistent index buffers: no state_dict entries (the
        # lists live in policy_kwargs), move with .to(device).
        for i, ix in enumerate(leg_obs_idx):
            self.register_buffer(
                f"_leg_idx_{i}",
                torch.as_tensor(list(ix), dtype=torch.long),
                persistent=False)
        self.register_buffer(
            "_shared_idx",
            torch.as_tensor(list(shared_obs_idx), dtype=torch.long),
            persistent=False)
        self.n_legs = len(leg_obs_idx)
        if self._heading_rel_on:
            self._heading_idx0 = int(heading_rel_idx[0])
            mounts = leg_mount_unit_vectors(leg_mount_deg)
            if len(mounts) != self.n_legs:
                raise ValueError(
                    f"leg_mount_deg has {len(mounts)} entries, need "
                    f"{self.n_legs} (one per leg)")
            self._mount_cos = [c for c, _ in mounts]
            self._mount_sin = [s for _, s in mounts]

    def forward(self, features: torch.Tensor
                ) -> tuple[torch.Tensor, torch.Tensor]:
        return self.forward_actor(features), self.forward_critic(features)

    def forward_actor(self, features: torch.Tensor) -> torch.Tensor:
        shared = torch.index_select(features, -1, self._shared_idx)
        if self._heading_rel_on:
            vx = features[..., self._heading_idx0]
            vy = features[..., self._heading_idx0 + 1]
            s = torch.hypot(vx, vy)
            mask = s > 1e-6
            s_safe = s.clamp_min(1e-6)
            # Stop commands (near-zero norm) read as (cos, sin) =
            # (1, 0) -- "forward", same convention as
            # heading_selfdistill.heading_cos.
            cos_t = torch.where(mask, vx / s_safe, torch.ones_like(vx))
            sin_t = torch.where(mask, vy / s_safe, torch.zeros_like(vy))
        outs = []
        for i in range(self.n_legs):
            idx = getattr(self, f"_leg_idx_{i}")
            local = torch.index_select(features, -1, idx)
            parts = [shared, local]
            if self._heading_rel_on:
                cos_rel, sin_rel = heading_rel_cos_sin(
                    cos_t, sin_t, self._mount_cos[i], self._mount_sin[i])
                parts.append(torch.stack([cos_rel, sin_rel], dim=-1))
            outs.append(self.leg_nets[i](torch.cat(parts, dim=-1)))
        return torch.cat(outs, dim=-1)

    def forward_critic(self, features: torch.Tensor) -> torch.Tensor:
        return self.value_net(features)


class DecLegActorCriticPolicy(ActorCriticPolicy):
    """ActorCriticPolicy with a strictly decentralized per-leg actor.

    Extra policy_kwargs:
      ``leg_obs_idx``       six lists of obs indices (leg-local dims)
      ``shared_obs_idx``    obs indices every module sees (body+command)
      ``leg_hidden``        per-leg tower widths, default (64, 64)
      ``share_leg_weights`` tie one tower's weights across all six legs
                            instead of six independent towers (default
                            False = original independent-tower path,
                            bit-exact). DESIGN_NOTE_2026-09-10_
                            offaxis_frontpair.md addendum (13th
                            mechanism class).
      ``heading_rel_idx``   ``(vx_ref_idx, vy_ref_idx)`` into the raw
                            obs — when set, every leg tower also gets
                            [cos_rel, sin_rel] (heading_rel_cos_sin),
                            the commanded heading rotated into THAT
                            leg's own mount frame. Default None = no
                            extra input dims, bit-exact off. Pairs with
                            ``share_leg_weights`` (see module docstring
                            for why the combination, not either alone,
                            is the actual hypothesis under test).
      ``leg_mount_deg``     per-leg mount angles for heading_rel_idx,
                            default LEG_MOUNT_ANGLES_DEG (mesh-derived).

    net_arch's vf side (or the plain list) is the centralized critic
    tower; the pi side is ignored (the per-leg towers replace it).
    """

    def __init__(self, observation_space, action_space, lr_schedule,
                 *args, leg_obs_idx=(), shared_obs_idx=(),
                 leg_hidden=(64, 64), share_leg_weights=False,
                 heading_rel_idx=None,
                 leg_mount_deg=LEG_MOUNT_ANGLES_DEG, **kwargs):
        self.leg_obs_idx = [list(map(int, ix)) for ix in leg_obs_idx]
        self.shared_obs_idx = list(map(int, shared_obs_idx))
        self.leg_hidden = tuple(int(h) for h in leg_hidden)
        self.share_leg_weights = bool(share_leg_weights)
        self.heading_rel_idx = (None if heading_rel_idx is None
                                else tuple(int(x) for x in heading_rel_idx))
        self.leg_mount_deg = tuple(float(x) for x in leg_mount_deg)
        super().__init__(observation_space, action_space, lr_schedule,
                         *args, **kwargs)

    def _value_arch(self) -> tuple[int, ...]:
        na = self.net_arch
        if isinstance(na, dict):
            vf = na.get("vf", [64, 64])
        elif na and isinstance(na[0], dict):   # legacy [dict] form
            vf = na[0].get("vf", [64, 64])
        else:
            vf = list(na) if na else [64, 64]
        return tuple(int(x) for x in vf)

    def _build_mlp_extractor(self) -> None:
        self.mlp_extractor = _DecLegExtractor(
            self.features_dim, self.leg_obs_idx, self.shared_obs_idx,
            self.leg_hidden, self._value_arch(), self.activation_fn,
            device=self.device,
            share_leg_weights=self.share_leg_weights,
            heading_rel_idx=self.heading_rel_idx,
            leg_mount_deg=self.leg_mount_deg)

    def _build(self, lr_schedule) -> None:
        super()._build(lr_schedule)
        act_dim = int(np.prod(self.action_space.shape))
        n_legs = len(self.leg_obs_idx)
        if act_dim != n_legs * ACT_PER_LEG:
            raise ValueError(
                f"action dim {act_dim} != {n_legs} legs x "
                f"{ACT_PER_LEG} — decleg needs the raw joint action "
                "space (joint-family tasks)")
        # Replace the dense Linear(latent_pi, 18) — which would
        # re-couple the legs — with the block-diagonal per-leg head,
        # then rebuild the optimizer (super()._build registered the
        # old head's params).
        self.action_net = _PerLegHead(
            n_legs, int(self.leg_hidden[-1]), ACT_PER_LEG)
        if self.ortho_init:
            for h in self.action_net.heads:
                h.apply(lambda m: self.init_weights(m, gain=0.01))
        self.action_net = self.action_net.to(self.device)
        self.optimizer = self.optimizer_class(
            self.parameters(), lr=lr_schedule(1),
            **self.optimizer_kwargs)
