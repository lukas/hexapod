"""GRU recurrent actor-critic policy for sb3-contrib's RecurrentPPO.

sb3-contrib 2.9.0 ships RecurrentPPO with LSTM cells only. This module
provides ``GruActorCriticPolicy``: the same RecurrentActorCriticPolicy,
but with ``nn.GRU`` in place of ``nn.LSTM`` for the actor (and, by
default, the critic).

Why this works without touching RecurrentPPO itself:

- RecurrentPPO only reads ``policy.lstm_actor.num_layers`` /
  ``.hidden_size`` (both exist on nn.GRU) and threads opaque
  ``(h, c)`` state tuples through rollout collection and the
  RecurrentRolloutBuffer.
- ALL cell-type-specific math lives in one static method,
  ``_process_sequence``, which we override. A GRU has no cell state,
  so the ``c`` slot of every state tuple is simply carried through
  untouched (it stays zeros forever). Slightly wasteful buffer memory,
  zero behavioral difference.

Checkpoints save/load through the normal SB3 zip path: the zip pickles
this class, so ``RecurrentPPO.load`` reconstructs it as long as
``rl_move.sim.gru_policy`` is importable (same convention as
``asym_policy.AsymActorCriticPolicy``).

Use ``load_checkpoint_auto`` to load a checkpoint without knowing
whether it is a plain PPO/MLP zip or a RecurrentPPO/GRU zip.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch as th
from torch import nn

from sb3_contrib.common.recurrent.policies import RecurrentActorCriticPolicy


class GruActorCriticPolicy(RecurrentActorCriticPolicy):
    """RecurrentActorCriticPolicy with GRU cells instead of LSTM.

    Constructor args are identical to RecurrentActorCriticPolicy
    (``lstm_hidden_size``, ``n_lstm_layers``, ``shared_lstm``,
    ``enable_critic_lstm``, ``lstm_kwargs`` keep their names so the
    kwargs stored in existing-style checkpoints stay compatible).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Replace the LSTMs the parent built with GRUs of the same
        # geometry. num_layers/hidden_size/input_size all match, so
        # RecurrentPPO's state-shape bookkeeping is unaffected.
        self.lstm_actor = nn.GRU(
            self.lstm_actor.input_size,
            self.lstm_actor.hidden_size,
            num_layers=self.lstm_actor.num_layers,
            **self.lstm_kwargs,
        )
        if self.lstm_critic is not None:
            self.lstm_critic = nn.GRU(
                self.lstm_critic.input_size,
                self.lstm_critic.hidden_size,
                num_layers=self.lstm_critic.num_layers,
                **self.lstm_kwargs,
            )
        # The parent's optimizer was built over the (now discarded)
        # LSTM parameters; rebuild it over the live module set.
        lr = self.optimizer.defaults["lr"]
        self.optimizer = self.optimizer_class(
            self.parameters(), lr=lr, **self.optimizer_kwargs)

    @staticmethod
    def _process_sequence(
        features: th.Tensor,
        lstm_states: tuple[th.Tensor, th.Tensor],
        episode_starts: th.Tensor,
        lstm: nn.GRU,
    ) -> tuple[th.Tensor, tuple[th.Tensor, th.Tensor]]:
        """GRU forward pass mirroring the parent's LSTM version.

        ``lstm_states`` is the (h, c) tuple RecurrentPPO carries; only
        h is used, c passes through untouched (always zeros).
        """
        h, c_unused = lstm_states[0], lstm_states[1]
        n_seq = h.shape[1]
        # Batch to sequence: (padded batch, feat) -> (len, n_seq, feat).
        features_sequence = features.reshape(
            (n_seq, -1, lstm.input_size)).swapaxes(0, 1)
        episode_starts = episode_starts.reshape((n_seq, -1)).swapaxes(0, 1)

        # No resets inside the sequence: single fused GRU call.
        if th.all(episode_starts == 0.0):
            gru_output, h = lstm(features_sequence, h)
            gru_output = th.flatten(
                gru_output.transpose(0, 1), start_dim=0, end_dim=1)
            return gru_output, (h, c_unused)

        gru_output = []
        for feat, episode_start in zip(
                features_sequence, episode_starts, strict=True):
            hidden, h = lstm(
                feat.unsqueeze(dim=0),
                # Reset hidden state where a new episode begins.
                (1.0 - episode_start).view(1, n_seq, 1) * h,
            )
            gru_output += [hidden]
        gru_output = th.flatten(
            th.cat(gru_output).transpose(0, 1), start_dim=0, end_dim=1)
        return gru_output, (h, c_unused)


# --- Dual-core (mode-gated) GRU -------------------------------------
#
# Born from the cw-arch-gru-anchor1..3 closure (08-12): a SINGLE shared
# GRU trunk cannot hold sharp anchored stance skills and a displacing
# walk at once — anchor3 proved the interference is PPO's own gradient
# through the shared trunk (walk froze even with the anchor gradient
# detached from it), while ft1 proved walk survives 10M steps of RL
# when nothing else competes for the trunk. So: give locomotion and
# stance their own complete cores (GRU + actor/critic heads each) and
# route per sample by the obs.mode_onehot tail. Both cores run every
# tick (their memories stay warm across mode changes); only the OUTPUT
# is selected, so each core receives gradient exclusively from its own
# skill family's ticks. Interference is gone by construction, yet it
# is still one checkpoint, one predict() interface, one brain to
# deploy.
#
# REQUIREMENT: the env must append the 6-wide skill-family one-hot at
# the obs tail (obs.mode_onehot=1). Slot order is frozen in
# walk_task.MODE_ONEHOT_ORDER = (hold, rise, lower, walk, turn, quad);
# locomotion = the last three slots (walk/turn/quad — getup rides the
# walk family), stance = the first three. test_gru_policy.py
# cross-checks this against walk_task so the two can never drift.

N_MODE_OBS = 6          # width of the obs-tail one-hot
_N_LOCO_SLOTS = 3       # trailing slots (walk, turn, quad) = core A


class _DualGRU(nn.Module):
    """Two parallel single-layer GRU cores behind one state facade.

    ``num_layers=2`` is a lie in the stacked-layer sense: it makes
    RecurrentPPO size its opaque state buffers as (2, n_envs, H) so
    row 0 threads core A (locomotion) and row 1 core B (stance).
    """

    def __init__(self, input_size: int, hidden_size: int, **gru_kwargs):
        super().__init__()
        self.core_a = nn.GRU(input_size, hidden_size, **gru_kwargs)
        self.core_b = nn.GRU(input_size, hidden_size, **gru_kwargs)
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = 2  # facade: 2 state rows, not stacked layers


class DualGruActorCriticPolicy(GruActorCriticPolicy):
    """Mode-gated dual-core GRU policy (locomotion core + stance core).

    Same constructor surface as GruActorCriticPolicy. Requires the
    default recurrent layout (critic GRU enabled, no shared_lstm, no
    SDE) and n_lstm_layers=1 per core.
    """

    def __init__(self, *args, log_std_split: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        if self.lstm_critic is None or self.shared_lstm:
            raise ValueError(
                "DualGruActorCriticPolicy requires enable_critic_lstm="
                "True and shared_lstm=False (the defaults)")
        if self.use_sde:
            raise ValueError("DualGruActorCriticPolicy does not support "
                             "use_sde")
        if self.lstm_actor.num_layers != 1:
            raise ValueError("DualGruActorCriticPolicy requires "
                             "n_lstm_layers=1 (one layer per core)")
        import copy

        self.lstm_actor = _DualGRU(
            self.lstm_actor.input_size, self.lstm_actor.hidden_size,
            **self.lstm_kwargs)
        self.lstm_critic = _DualGRU(
            self.lstm_critic.input_size, self.lstm_critic.hidden_size,
            **self.lstm_kwargs)
        # predict() sizes zero states off this: (rows, 1, H).
        self.lstm_hidden_state_shape = (
            2, 1, self.lstm_actor.hidden_size)
        # Core B's own heads. deepcopy keeps the architecture in sync
        # with whatever net_arch built core A's heads; the two diverge
        # immediately under their disjoint per-mode gradients.
        self.mlp_extractor_b = copy.deepcopy(self.mlp_extractor)
        self.action_net_b = copy.deepcopy(self.action_net)
        self.value_net_b = copy.deepcopy(self.value_net)
        # PER-CORE log_std SPLIT (08-27, anchor4-stdanneal/anchor5-
        # stdmild dose-bracket dig-in): default OFF / bit-exact — the
        # mean and value are already mixed per-core via the mode gate
        # (action_net/action_net_b, value_net/value_net_b above), but
        # the exploration std used to be ONE shared nn.Parameter
        # (self.log_std, inherited from the base class) applied
        # identically to every tick regardless of which core is
        # active. A full 2-dose x 2-seed magnitude bracket on that
        # shared scalar (log_std_final -1.0/-2.0/-4.0, see standwalk
        # STATUS.md 08-27) found NO shared value that both protects
        # walk's still-fragile exploration and cools stance's
        # stochastic-hold failure: -4.0 fixes hold but wrecks walk on
        # every seed; -2.0/-1.0 leave hold untouched (one seed even
        # regresses on walk at -1.0). ``log_std_split=True`` adds a
        # second learnable ``log_std_b`` for core B (stance) and mixes
        # it with the SAME per-tick gate used for the mean/value
        # (``gate * log_std + (1-gate) * log_std_b``), so an anneal
        # schedule can now target ONLY the stance core
        # (train_ppo_mjx.py's ``--log-std-anneal-core stance``) while
        # core A (walk) keeps its own independently-trained std.
        # False (default) constructs nothing extra and
        # ``_dist_from_mean`` takes the old single-``log_std`` path —
        # bit-identical to pre-08-27 behavior.
        self.log_std_split = bool(log_std_split)
        if self.log_std_split:
            self.log_std_b = nn.Parameter(
                self.log_std.data.clone(), requires_grad=True)
        lr = self.optimizer.defaults["lr"]
        self.optimizer = self.optimizer_class(
            self.parameters(), lr=lr, **self.optimizer_kwargs)

    # -- gating --------------------------------------------------

    @staticmethod
    def _gate(obs_or_feats: th.Tensor) -> th.Tensor:
        """(..., obs) -> (..., 1); 1.0 = locomotion family (core A).

        Reads the frozen obs-tail one-hot. Exactly one slot is lit per
        tick, so summing the trailing locomotion slots is exact.
        """
        loco = obs_or_feats[..., -_N_LOCO_SLOTS:]
        return loco.sum(dim=-1, keepdim=True).clamp(0.0, 1.0)

    def _dual_sequence(self, features, lstm_states, episode_starts, dual):
        """Run BOTH cores over the sequence; return their outputs and
        the repacked (h, c) with h rows [core_a, core_b]."""
        base = GruActorCriticPolicy._process_sequence
        h, c = lstm_states[0], lstm_states[1]
        out_a, (h_a, _) = base(
            features, (h[0:1], c[0:1]), episode_starts, dual.core_a)
        out_b, (h_b, _) = base(
            features, (h[1:2], c[1:2]), episode_starts, dual.core_b)
        return out_a, out_b, (th.cat([h_a, h_b], dim=0), c)

    def _actor_mean(self, out_a, out_b, gate):
        mu_a = self.action_net(self.mlp_extractor.forward_actor(out_a))
        mu_b = self.action_net_b(
            self.mlp_extractor_b.forward_actor(out_b))
        return gate * mu_a + (1.0 - gate) * mu_b

    def _critic_value(self, out_a, out_b, gate):
        v_a = self.value_net(self.mlp_extractor.forward_critic(out_a))
        v_b = self.value_net_b(
            self.mlp_extractor_b.forward_critic(out_b))
        return gate * v_a + (1.0 - gate) * v_b

    def _dist_from_mean(self, mean_actions, gate=None):
        if self.log_std_split:
            # Same per-tick blend as the mean/value (gate==1 -> all
            # core A/walk std, gate==0 -> all core B/stance std);
            # gate is (..., 1), log_std is (action_dim,), broadcasts
            # to (..., action_dim) same as the mean-mixing above.
            log_std = gate * self.log_std + (1.0 - gate) * self.log_std_b
        else:
            log_std = self.log_std
        return self.action_dist.proba_distribution(mean_actions, log_std)

    def _log_stds(self):
        """All learnable log_std parameters (reset/uniform-anneal
        helper). One entry when log_std_split is off — bit-identical
        in effect to the pre-split ``pol.log_std.data.fill_(val)``
        path, just routed through this generic loop instead."""
        return (self.log_std, self.log_std_b) if self.log_std_split \
            else (self.log_std,)

    def _log_std_core(self, which: str):
        """log_std_split-only: the param(s) for ONE gated core, so an
        anneal schedule can target just the stance side. Returns None
        (caller falls back to ``_log_stds()``/legacy) when the split
        is off — there is no separate stance parameter to target."""
        if not self.log_std_split:
            return None
        if which == "walk":
            return (self.log_std,)
        if which == "stance":
            return (self.log_std_b,)
        return None

    def enable_log_std_split(self):
        """Retrofit the per-core log_std split onto an ALREADY
        constructed policy. Needed by the plain --init-from warm-start
        path: ``RecurrentPPO.load`` rebuilds the policy from the
        CHECKPOINT's own saved policy_kwargs, so warm-starting a
        pre-split parent silently dropped ``log_std_split=True`` and
        the "stance-only" anneal cooled the one SHARED log_std both
        cores sample from (anchor6-logstdsplit forensics, 08-27: both
        seeds shipped with no log_std_b at all and reproduced the
        anchor4-stdanneal shared-anneal catastrophe verbatim).
        Idempotent. Seeds log_std_b from the current log_std exactly
        like __init__ and rebuilds the optimizer so the new parameter
        actually trains (fresh optimizer state — the architecture
        changed, same policy as any transplant)."""
        if self.log_std_split:
            return
        self.log_std_split = True
        self.log_std_b = nn.Parameter(
            self.log_std.data.clone(), requires_grad=True)
        lr = self.optimizer.defaults["lr"]
        self.optimizer = self.optimizer_class(
            self.parameters(), lr=lr, **self.optimizer_kwargs)

    # -- RecurrentPPO entry points ---------------------------------

    def forward(self, obs, lstm_states, episode_starts,
                deterministic: bool = False):
        features = self.extract_features(obs)
        if self.share_features_extractor:
            pi_features = vf_features = features
        else:
            pi_features, vf_features = features
        gate = self._gate(obs)
        pa, pb, st_pi = self._dual_sequence(
            pi_features, lstm_states.pi, episode_starts, self.lstm_actor)
        va, vb, st_vf = self._dual_sequence(
            vf_features, lstm_states.vf, episode_starts, self.lstm_critic)
        values = self._critic_value(va, vb, gate)
        distribution = self._dist_from_mean(
            self._actor_mean(pa, pb, gate), gate)
        actions = distribution.get_actions(deterministic=deterministic)
        log_prob = distribution.log_prob(actions)
        actions = actions.reshape((-1, *self.action_space.shape))
        from sb3_contrib.common.recurrent.type_aliases import RNNStates
        return actions, values, log_prob, RNNStates(st_pi, st_vf)

    def get_distribution(self, obs, lstm_states, episode_starts):
        from stable_baselines3.common.policies import ActorCriticPolicy
        features = super(ActorCriticPolicy, self).extract_features(
            obs, self.pi_features_extractor)
        gate = self._gate(obs)
        pa, pb, st = self._dual_sequence(
            features, lstm_states, episode_starts, self.lstm_actor)
        return self._dist_from_mean(
            self._actor_mean(pa, pb, gate), gate), st

    def predict_values(self, obs, lstm_states, episode_starts):
        from stable_baselines3.common.policies import ActorCriticPolicy
        features = super(ActorCriticPolicy, self).extract_features(
            obs, self.vf_features_extractor)
        gate = self._gate(obs)
        va, vb, _ = self._dual_sequence(
            features, lstm_states, episode_starts, self.lstm_critic)
        return self._critic_value(va, vb, gate)

    def evaluate_actions(self, obs, actions, lstm_states, episode_starts):
        features = self.extract_features(obs)
        if self.share_features_extractor:
            pi_features = vf_features = features
        else:
            pi_features, vf_features = features
        gate = self._gate(obs)
        pa, pb, _ = self._dual_sequence(
            pi_features, lstm_states.pi, episode_starts, self.lstm_actor)
        va, vb, _ = self._dual_sequence(
            vf_features, lstm_states.vf, episode_starts, self.lstm_critic)
        distribution = self._dist_from_mean(
            self._actor_mean(pa, pb, gate), gate)
        log_prob = distribution.log_prob(actions)
        values = self._critic_value(va, vb, gate)
        return values, log_prob, distribution.entropy()

    # -- auxiliary paths (distillation, BC anchor) ------------------

    def bptt_forward(self, feats: th.Tensor):
        """Whole-episode fused BPTT pass for distill_gru.train_student.

        ``feats`` is (T, B, obs) padded episodes starting at reset
        (zero initial hidden state is the truth). Returns (mu, value).
        """
        gate = self._gate(feats)
        out_a, _ = self.lstm_actor.core_a(feats)
        out_b, _ = self.lstm_actor.core_b(feats)
        mu = self._actor_mean(out_a, out_b, gate)
        v_a, _ = self.lstm_critic.core_a(feats)
        v_b, _ = self.lstm_critic.core_b(feats)
        value = self._critic_value(v_a, v_b, gate)
        return mu, value

    def bc_anchor_mean(self, th_obs: th.Tensor, th_h: th.Tensor,
                       detach_trunk: bool = False):
        """Policy mean at stored hidden states, for the BC anchor's
        auxiliary step (bc_anchor._bc_policy_mean delegates here).

        ``th_h`` is (B, 2*H) flat rows as stored by the anchor ring
        (row-major over the (2, B, H) state: core A then core B).
        With ``detach_trunk`` the feature extractor + both GRU cores
        run under no_grad and their outputs are detached, so the
        anchor loss only trains the per-core actor heads.
        """
        hidden = self.lstm_actor.hidden_size
        h = (th_obs.new_zeros((2, th_obs.shape[0], hidden))
             if th_h is None
             else th_h.reshape(th_obs.shape[0], 2, hidden)
             .transpose(0, 1).contiguous())
        starts = th.zeros(th_obs.shape[0], device=th_obs.device)
        gate = self._gate(th_obs)
        if detach_trunk:
            with th.no_grad():
                feats = self.extract_features(th_obs)
                if not self.share_features_extractor:
                    feats = feats[0]
                pa, pb, _ = self._dual_sequence(
                    feats, (h, th.zeros_like(h)), starts, self.lstm_actor)
            pa, pb = pa.detach(), pb.detach()
        else:
            feats = self.extract_features(th_obs)
            if not self.share_features_extractor:
                feats = feats[0]
            pa, pb, _ = self._dual_sequence(
                feats, (h, th.zeros_like(h)), starts, self.lstm_actor)
        return self._actor_mean(pa, pb, gate)


# --- Triple-core (walk / turn / stance) GRU -------------------------
#
# standwalk item-2 escalation (09-04): the whole open-loop scalar-
# weight/geometry lever family for "walk while turning loses turn
# authority" is closed 8/8 FAIL (bc_anchor_walk_combined_dose axis +
# TripodGait.combined_yaw_arm_scale axis) — every dose/scale strong
# enough to win combined-tick wz blows the pure-turn regression cap,
# the signature of ONE shared representation (DualGruActorCriticPolicy's
# core_a) computing both skills and fighting itself. This gives
# pure-turn ticks (obs.mode_onehot_turn_cmd=1's "turn" bit, walk_task.py)
# their OWN core — core_t — so its gradient can never come from a
# combined-tick sample: complete isolation by construction, the same
# principle _DualGRU used to separate walk from stance. core_b (stance)
# is UNTOUCHED from the Dual contract (same attribute names/shapes) —
# this class only ever ADDS a core between the existing two.
#
# REQUIREMENT: same env contract as Dual (obs.mode_onehot=1) PLUS
# obs.mode_onehot_turn_cmd=1 so the "turn" slot (MODE_ONEHOT_ORDER
# index 4) actually lights on pure-turn ticks — without it "turn"
# never fires (no goal-trajectory mode string sets it) and core_t
# trains on nothing.

_TURN_SLOT = 4  # MODE_ONEHOT_ORDER.index("turn"); frozen, see walk_task.py


class _TripleGRU(nn.Module):
    """Three parallel single-layer GRU cores behind one state facade.

    ``num_layers=3`` is a facade (like _DualGRU's 2 / _QuadGRU's 4):
    RecurrentPPO sizes its opaque state buffers as (3, n_envs, H); row
    0 = core_a (walk/quad), row 1 = core_t (pure turn), row 2 = core_b
    (stance) — this row order is the transplant/bc_anchor contract,
    keep it stable.
    """

    def __init__(self, input_size: int, hidden_size: int, **gru_kwargs):
        super().__init__()
        self.core_a = nn.GRU(input_size, hidden_size, **gru_kwargs)
        self.core_t = nn.GRU(input_size, hidden_size, **gru_kwargs)
        self.core_b = nn.GRU(input_size, hidden_size, **gru_kwargs)
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = 3  # facade: 3 state rows, not stacked layers


class TripleGruActorCriticPolicy(GruActorCriticPolicy):
    """Mode-gated triple-core GRU: locomotion core + turn core + stance
    core.

    core_a and core_b reuse the exact DualGruActorCriticPolicy contract
    (attribute names ``mlp_extractor``/``action_net``/``value_net``/
    ``log_std`` for A, the ``_b``-suffixed set for B) — core_b needs no
    new logic anywhere it is touched today. core_t is new: its own
    ``mlp_extractor_t``/``action_net_t``/``value_net_t`` AND its own
    ``log_std_t`` (unconditional, not behind a flag — a shared std
    would let turn-tick exploration gradient bleed into core_a's
    parameter even though the GRU/heads stay fully separate, defeating
    part of the point). ``log_std`` (core A's) is shared with core_b
    by default, exactly like Dual's ``log_std_split=False`` default —
    this class does not touch that knob.

    Same constructor surface as GruActorCriticPolicy. Requires the
    default recurrent layout (critic GRU enabled, no shared_lstm, no
    SDE) and n_lstm_layers=1 per core, identical restrictions to
    DualGruActorCriticPolicy.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.lstm_critic is None or self.shared_lstm:
            raise ValueError(
                "TripleGruActorCriticPolicy requires enable_critic_lstm="
                "True and shared_lstm=False (the defaults)")
        if self.use_sde:
            raise ValueError("TripleGruActorCriticPolicy does not "
                             "support use_sde")
        if self.lstm_actor.num_layers != 1:
            raise ValueError("TripleGruActorCriticPolicy requires "
                             "n_lstm_layers=1 (one layer per core)")
        import copy

        self.lstm_actor = _TripleGRU(
            self.lstm_actor.input_size, self.lstm_actor.hidden_size,
            **self.lstm_kwargs)
        self.lstm_critic = _TripleGRU(
            self.lstm_critic.input_size, self.lstm_critic.hidden_size,
            **self.lstm_kwargs)
        self.lstm_hidden_state_shape = (
            3, 1, self.lstm_actor.hidden_size)
        # Core B's own heads — identical construction to Dual.
        self.mlp_extractor_b = copy.deepcopy(self.mlp_extractor)
        self.action_net_b = copy.deepcopy(self.action_net)
        self.value_net_b = copy.deepcopy(self.value_net)
        # Core T's own heads + own log_std (see class docstring).
        self.mlp_extractor_t = copy.deepcopy(self.mlp_extractor)
        self.action_net_t = copy.deepcopy(self.action_net)
        self.value_net_t = copy.deepcopy(self.value_net)
        self.log_std_t = nn.Parameter(
            self.log_std.data.clone(), requires_grad=True)
        lr = self.optimizer.defaults["lr"]
        self.optimizer = self.optimizer_class(
            self.parameters(), lr=lr, **self.optimizer_kwargs)

    # -- gating --------------------------------------------------

    @staticmethod
    def _gate3(obs_or_feats: th.Tensor
              ) -> tuple[th.Tensor, th.Tensor, th.Tensor]:
        """(..., obs) -> (g_a, g_t, g_b), each (..., 1), summing to 1.0.

        Reads the frozen obs-tail one-hot (walk_task.MODE_ONEHOT_ORDER
        = hold, rise, lower, walk, turn, quad). g_t lights on the
        "turn" slot alone; g_b sums the three stance slots; g_a is the
        exact remainder (walk+quad) via 1-g_t-g_b, never re-summed
        directly, so the three weights always partition exactly."""
        tail = obs_or_feats[..., -N_MODE_OBS:]
        g_b = tail[..., :_N_LOCO_SLOTS].sum(
            dim=-1, keepdim=True).clamp(0.0, 1.0)
        g_t = tail[..., _TURN_SLOT:_TURN_SLOT + 1].clamp(0.0, 1.0)
        g_a = (1.0 - g_b - g_t).clamp(0.0, 1.0)
        return g_a, g_t, g_b

    def _triple_sequence(self, features, lstm_states, episode_starts,
                         triple):
        """Run ALL THREE cores over the sequence (memories stay warm
        across mode switches); return per-core outputs and the
        repacked (h, c) with h rows [core_a, core_t, core_b]."""
        base = GruActorCriticPolicy._process_sequence
        h, c = lstm_states[0], lstm_states[1]
        out_a, (h_a, _) = base(
            features, (h[0:1], c[0:1]), episode_starts, triple.core_a)
        out_t, (h_t, _) = base(
            features, (h[1:2], c[0:1]), episode_starts, triple.core_t)
        out_b, (h_b, _) = base(
            features, (h[2:3], c[0:1]), episode_starts, triple.core_b)
        return out_a, out_t, out_b, (
            th.cat([h_a, h_t, h_b], dim=0), c)

    def _actor_mean(self, out_a, out_t, out_b, g_a, g_t, g_b):
        mu_a = self.action_net(self.mlp_extractor.forward_actor(out_a))
        mu_t = self.action_net_t(
            self.mlp_extractor_t.forward_actor(out_t))
        mu_b = self.action_net_b(
            self.mlp_extractor_b.forward_actor(out_b))
        return g_a * mu_a + g_t * mu_t + g_b * mu_b

    def _critic_value(self, out_a, out_t, out_b, g_a, g_t, g_b):
        v_a = self.value_net(self.mlp_extractor.forward_critic(out_a))
        v_t = self.value_net_t(
            self.mlp_extractor_t.forward_critic(out_t))
        v_b = self.value_net_b(
            self.mlp_extractor_b.forward_critic(out_b))
        return g_a * v_a + g_t * v_t + g_b * v_b

    def _dist_from_mean(self, mean_actions, g_a, g_t, g_b):
        # core_a and core_b share self.log_std (Dual's default,
        # untouched); core_t always has its own — see class docstring.
        log_std = (g_a + g_b) * self.log_std + g_t * self.log_std_t
        return self.action_dist.proba_distribution(mean_actions, log_std)

    def _log_stds(self):
        """Both learnable log_std parameters — warm_log_std_override's
        generic reset hook (train_ppo_mjx.py) uses this exactly like
        Dual's log_std_split=True case."""
        return (self.log_std, self.log_std_t)

    def _log_std_core(self, which: str):
        """--log-std-anneal-core targeting hook (train_ppo_mjx.py),
        same contract as Dual's log_std_split=True case: return the
        param(s) for ONE named core, or None if this policy cannot
        isolate it (caller then fails closed rather than silently
        annealing everything). 'turn' targets ``log_std_t`` (always a
        real, separate parameter on this class). 'walk' targets the
        shared ``log_std`` — but that parameter is ALSO core_b's
        (stance's), since Triple never splits core_a/core_b apart
        (that split is Dual's log_std_split=True, not this class), so
        'stance' returns None: there is no parameter that targets
        stance alone here."""
        if which == "turn":
            return (self.log_std_t,)
        if which == "walk":
            return (self.log_std,)
        return None

    # -- RecurrentPPO entry points ---------------------------------

    def forward(self, obs, lstm_states, episode_starts,
                deterministic: bool = False):
        features = self.extract_features(obs)
        if self.share_features_extractor:
            pi_features = vf_features = features
        else:
            pi_features, vf_features = features
        g_a, g_t, g_b = self._gate3(obs)
        pa, pt, pb, st_pi = self._triple_sequence(
            pi_features, lstm_states.pi, episode_starts, self.lstm_actor)
        va, vt, vb, st_vf = self._triple_sequence(
            vf_features, lstm_states.vf, episode_starts, self.lstm_critic)
        values = self._critic_value(va, vt, vb, g_a, g_t, g_b)
        distribution = self._dist_from_mean(
            self._actor_mean(pa, pt, pb, g_a, g_t, g_b), g_a, g_t, g_b)
        actions = distribution.get_actions(deterministic=deterministic)
        log_prob = distribution.log_prob(actions)
        actions = actions.reshape((-1, *self.action_space.shape))
        from sb3_contrib.common.recurrent.type_aliases import RNNStates
        return actions, values, log_prob, RNNStates(st_pi, st_vf)

    def get_distribution(self, obs, lstm_states, episode_starts):
        from stable_baselines3.common.policies import ActorCriticPolicy
        features = super(ActorCriticPolicy, self).extract_features(
            obs, self.pi_features_extractor)
        g_a, g_t, g_b = self._gate3(obs)
        pa, pt, pb, st = self._triple_sequence(
            features, lstm_states, episode_starts, self.lstm_actor)
        return self._dist_from_mean(
            self._actor_mean(pa, pt, pb, g_a, g_t, g_b),
            g_a, g_t, g_b), st

    def predict_values(self, obs, lstm_states, episode_starts):
        from stable_baselines3.common.policies import ActorCriticPolicy
        features = super(ActorCriticPolicy, self).extract_features(
            obs, self.vf_features_extractor)
        g_a, g_t, g_b = self._gate3(obs)
        va, vt, vb, _ = self._triple_sequence(
            features, lstm_states, episode_starts, self.lstm_critic)
        return self._critic_value(va, vt, vb, g_a, g_t, g_b)

    def evaluate_actions(self, obs, actions, lstm_states, episode_starts):
        features = self.extract_features(obs)
        if self.share_features_extractor:
            pi_features = vf_features = features
        else:
            pi_features, vf_features = features
        g_a, g_t, g_b = self._gate3(obs)
        pa, pt, pb, _ = self._triple_sequence(
            pi_features, lstm_states.pi, episode_starts, self.lstm_actor)
        va, vt, vb, _ = self._triple_sequence(
            vf_features, lstm_states.vf, episode_starts, self.lstm_critic)
        distribution = self._dist_from_mean(
            self._actor_mean(pa, pt, pb, g_a, g_t, g_b), g_a, g_t, g_b)
        log_prob = distribution.log_prob(actions)
        values = self._critic_value(va, vt, vb, g_a, g_t, g_b)
        return values, log_prob, distribution.entropy()

    # -- auxiliary paths (distillation, BC anchor) ------------------

    def bptt_forward(self, feats: th.Tensor):
        """Whole-episode fused BPTT pass for distill_gru.train_student.

        ``feats`` is (T, B, obs) padded episodes starting at reset
        (zero initial hidden state is the truth). Returns (mu, value).
        """
        g_a, g_t, g_b = self._gate3(feats)
        out_a, _ = self.lstm_actor.core_a(feats)
        out_t, _ = self.lstm_actor.core_t(feats)
        out_b, _ = self.lstm_actor.core_b(feats)
        mu = self._actor_mean(out_a, out_t, out_b, g_a, g_t, g_b)
        v_a, _ = self.lstm_critic.core_a(feats)
        v_t, _ = self.lstm_critic.core_t(feats)
        v_b, _ = self.lstm_critic.core_b(feats)
        value = self._critic_value(v_a, v_t, v_b, g_a, g_t, g_b)
        return mu, value

    def bc_anchor_mean(self, th_obs: th.Tensor, th_h: th.Tensor,
                       detach_trunk: bool = False):
        """Policy mean at stored hidden states, for the BC anchor's
        auxiliary step (bc_anchor._bc_policy_mean delegates here).

        ``th_h`` is (B, 3*H) flat rows as stored by the anchor ring
        (row-major over the (3, B, H) state: core A, core T, core B —
        same convention as Dual's (2, B, H) / Experts' (4, B, H)).
        """
        hidden = self.lstm_actor.hidden_size
        h = (th_obs.new_zeros((3, th_obs.shape[0], hidden))
             if th_h is None
             else th_h.reshape(th_obs.shape[0], 3, hidden)
             .transpose(0, 1).contiguous())
        starts = th.zeros(th_obs.shape[0], device=th_obs.device)
        g_a, g_t, g_b = self._gate3(th_obs)
        if detach_trunk:
            with th.no_grad():
                feats = self.extract_features(th_obs)
                if not self.share_features_extractor:
                    feats = feats[0]
                pa, pt, pb, _ = self._triple_sequence(
                    feats, (h, th.zeros_like(h)), starts, self.lstm_actor)
            pa, pt, pb = pa.detach(), pt.detach(), pb.detach()
        else:
            feats = self.extract_features(th_obs)
            if not self.share_features_extractor:
                feats = feats[0]
            pa, pt, pb, _ = self._triple_sequence(
                feats, (h, th.zeros_like(h)), starts, self.lstm_actor)
        return self._actor_mean(pa, pt, pb, g_a, g_t, g_b)


def dual_to_triple_transplant(old_model, new_model) -> list[str]:
    """Warm-start a fresh TripleGruActorCriticPolicy from an already-
    trained DualGruActorCriticPolicy checkpoint (standwalk item-2
    escalation, 09-04).

    core_b (stance) transplants VERBATIM — same attribute names/shapes
    in both policies, Triple never touches core_b's contract. core_a
    (walk) transplants to BOTH the new core_a AND the new core_t: turn
    starts as a COPY of the current combined-tuned walk core, not from
    scratch, so it specializes from already-decent competence instead
    of relearning locomotion from zero — the same convention as every
    other architecture-changing transplant in this file (optimizer
    state is always fresh; only weights carry over). ``log_std_t``
    likewise starts as a copy of the parent's ``log_std``.

    Requires ``old_model.policy`` to be a DualGruActorCriticPolicy and
    ``new_model.policy`` a freshly constructed TripleGruActorCriticPolicy
    with the SAME lstm_hidden_size/net_arch (a shape mismatch raises,
    never silently truncates/pads — this is a same-width core add, not
    an obs-widening transplant like pad_obs_transplant).
    """
    if not isinstance(old_model.policy, DualGruActorCriticPolicy):
        raise SystemExit("dual_to_triple_transplant requires a "
                         "DualGruActorCriticPolicy source checkpoint "
                         f"(got {type(old_model.policy).__name__})")
    if not isinstance(new_model.policy, TripleGruActorCriticPolicy):
        raise SystemExit("dual_to_triple_transplant requires a "
                         "TripleGruActorCriticPolicy destination model "
                         f"(got {type(new_model.policy).__name__})")
    sd_old = old_model.policy.state_dict()
    sd_new = new_model.policy.state_dict()
    copied: list[str] = []

    def _copy(dst_name: str, src_name: str) -> None:
        v_new = sd_new[dst_name]
        v_old = sd_old[src_name]
        if v_new.shape != v_old.shape:
            raise SystemExit(
                "dual_to_triple_transplant: shape mismatch "
                f"{src_name} {tuple(v_old.shape)} -> {dst_name} "
                f"{tuple(v_new.shape)} (hidden_size/net_arch must "
                "match between the Dual parent and the fresh Triple)")
        with th.no_grad():
            v_new.copy_(v_old)
        copied.append(dst_name)

    # Verbatim: every new-policy tensor that ALSO exists in the old
    # policy under the identical name — core_b.*, mlp_extractor_b.*,
    # log_std_b (if log_std_split), log_std, shared feature extractor,
    # core_a.*, mlp_extractor.*, etc. This single pass covers both
    # core_a and core_b at once (Triple's core_a-named tensors are
    # byte-identical in shape/name to Dual's).
    for name in sd_new:
        if name in sd_old:
            _copy(name, name)

    # core_t / log_std_t: brand new names with no old-model
    # counterpart — map each back to its core-A-named source.
    for name in sd_new:
        if name in sd_old:
            continue
        if name == "log_std_t":
            src = "log_std"
        elif ".core_t." in name:
            src = name.replace(".core_t.", ".core_a.")
        elif name.startswith("mlp_extractor_t."):
            src = "mlp_extractor." + name[len("mlp_extractor_t."):]
        elif name.startswith("action_net_t."):
            src = "action_net." + name[len("action_net_t."):]
        elif name.startswith("value_net_t."):
            src = "value_net." + name[len("value_net_t."):]
        else:
            raise SystemExit(
                "dual_to_triple_transplant: unmapped new-only tensor "
                f"{name} — add a mapping rule or this is a genuine "
                "architecture mismatch")
        if src not in sd_old:
            raise SystemExit(
                "dual_to_triple_transplant: mapped source "
                f"{src} (for {name}) not found in the old checkpoint")
        _copy(name, src)

    required = {"lstm_actor.core_b.weight_ih_l0",
               "lstm_actor.core_t.weight_ih_l0", "log_std_t"}
    if not required.issubset(copied):
        raise SystemExit(
            "dual_to_triple_transplant did not copy the expected "
            "core_b/core_t/log_std_t tensors")
    return copied


# --- Rise-start-kind experts (five-core) GRU -------------------------
#
# standwalk rise flat/bridge precision gap, 2026-09-24 ~21:3x: THREE
# independent shared-representation mechanisms (exposure-frequency
# reweight ~17:1x, explicit-onehot input conditioning ~19:1x,
# gradient-level disjoint-minibatch isolation ~21:1x) all converged on
# the IDENTICAL flat-0/10, bridge-2/10, crouch-5/10 fingerprint on the
# `gru-dual-rlfinetune-rise` lineage — evidence the bottleneck is not
# training frequency, not inference burden, and not even gradient
# sharing within one set of weights, but CAPACITY: one shared rise
# body genuinely cannot express three different rise strategies at
# once. This class is the named remaining lever: "a genuinely
# separate-WEIGHTS per-start-kind mixture-of-experts rise head". It
# extends DualGruActorCriticPolicy (core_a=locomotion, core_b=stance)
# by carving the "rise" family OUT of core_b into three brand-new
# dedicated cores (flat/bridge/crouch) while core_b keeps hold+lower+
# any exotic rise start not in the three labeled kinds (e.g. `rise:
# bank`) — hold/lower show no evidence of needing their own split, so
# this is the minimal structural change that targets the diagnosed gap
# without also multiplying hold/lower's already-adequate parameter
# count.
#
# REQUIREMENT: obs.mode_onehot=1 AND obs.rise_start_kind_gate=1 (see
# walk_env_init.init_obs_and_mode_flags / walk_task.py's
# rise_start_kind_gate_onehot) — the rise-kind one-hot is read at the
# fixed offset immediately BEFORE the mode one-hot,
# obs[..., -(N_MODE_OBS+N_RISE_KIND_OBS):-N_MODE_OBS].

_N_RISE_KIND = 3
_RISE_KIND_NAMES = ("flat", "bridge", "crouch")  # walk_task.RISE_START_KIND_LABELS order


class _PentaGRU(nn.Module):
    """Five parallel single-layer GRU cores behind one state facade.

    ``num_layers=5`` is a facade (like _DualGRU's 2 / _TripleGRU's 3):
    row 0 = core_a (loco), row 1 = core_b (stance: hold/lower/other-
    rise), rows 2-4 = core_rf/core_rb/core_rc (rise flat/bridge/
    crouch) — this row order is the transplant contract, keep stable.
    """

    def __init__(self, input_size: int, hidden_size: int, **gru_kwargs):
        super().__init__()
        self.core_a = nn.GRU(input_size, hidden_size, **gru_kwargs)
        self.core_b = nn.GRU(input_size, hidden_size, **gru_kwargs)
        self.core_rf = nn.GRU(input_size, hidden_size, **gru_kwargs)
        self.core_rb = nn.GRU(input_size, hidden_size, **gru_kwargs)
        self.core_rc = nn.GRU(input_size, hidden_size, **gru_kwargs)
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = 5  # facade: 5 state rows, not stacked layers


class RiseKindGruActorCriticPolicy(GruActorCriticPolicy):
    """Dual-core GRU + three dedicated rise-start-kind expert cores.

    core_a/core_b reuse the exact DualGruActorCriticPolicy contract for
    their heads (``mlp_extractor``/``action_net``/``value_net`` for A,
    the ``_b``-suffixed set for B) but, UNLIKE Dual's default, core_b
    ALWAYS gets its OWN learnable ``log_std_b`` (equivalent to Dual's
    ``log_std_split=True`` permanently on) — this class's real-world
    Dual parents are warm-started FROM a log_std_split=True checkpoint
    (core_b's exploration std annealed down independently for rise/
    hold/lower stability), so carrying that split forward is required
    fidelity, not an added feature; ``dual_to_rise_experts_transplant``
    handles both a split and a non-split source. The three new rise
    experts (``_rf``/``_rb``/``_rc`` suffixes) each get their own
    complete head set AND their own learnable log_std (unconditional,
    like TripleGru's core_t) so no exploration-std gradient bleeds
    between rise kinds or back into core_b.

    Same constructor surface as GruActorCriticPolicy. Requires the
    default recurrent layout (critic GRU enabled, no shared_lstm, no
    SDE) and n_lstm_layers=1 per core, identical restrictions to every
    other multi-core policy in this file.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.lstm_critic is None or self.shared_lstm:
            raise ValueError(
                "RiseKindGruActorCriticPolicy requires "
                "enable_critic_lstm=True and shared_lstm=False")
        if self.use_sde:
            raise ValueError("RiseKindGruActorCriticPolicy does not "
                             "support use_sde")
        if self.lstm_actor.num_layers != 1:
            raise ValueError("RiseKindGruActorCriticPolicy requires "
                             "n_lstm_layers=1 (one layer per core)")
        import copy

        self.lstm_actor = _PentaGRU(
            self.lstm_actor.input_size, self.lstm_actor.hidden_size,
            **self.lstm_kwargs)
        self.lstm_critic = _PentaGRU(
            self.lstm_critic.input_size, self.lstm_critic.hidden_size,
            **self.lstm_kwargs)
        self.lstm_hidden_state_shape = (
            5, 1, self.lstm_actor.hidden_size)
        # Core B's own heads — identical construction to Dual.
        self.mlp_extractor_b = copy.deepcopy(self.mlp_extractor)
        self.action_net_b = copy.deepcopy(self.action_net)
        self.value_net_b = copy.deepcopy(self.value_net)
        # Core B's own log_std (see class docstring: always split,
        # unlike Dual's default-off log_std_split).
        self.log_std_b = nn.Parameter(
            self.log_std.data.clone(), requires_grad=True)
        # Three rise-kind experts: own heads + own log_std each,
        # seeded as copies of the BASE (core_a/loco) heads at
        # from-scratch construction time — the warm-start transplant
        # (dual_to_rise_experts_transplant) re-seeds them from the
        # trained core_b instead, which is what any real acquisition
        # run should use (from-scratch here is only for tests/
        # architecture smoke checks).
        for suf in ("rf", "rb", "rc"):
            setattr(self, f"mlp_extractor_{suf}",
                    copy.deepcopy(self.mlp_extractor))
            setattr(self, f"action_net_{suf}",
                    copy.deepcopy(self.action_net))
            setattr(self, f"value_net_{suf}",
                    copy.deepcopy(self.value_net))
            setattr(self, f"log_std_{suf}",
                    nn.Parameter(self.log_std_b.data.clone(),
                                 requires_grad=True))
        lr = self.optimizer.defaults["lr"]
        self.optimizer = self.optimizer_class(
            self.parameters(), lr=lr, **self.optimizer_kwargs)

    # -- gating --------------------------------------------------

    @staticmethod
    def _gate5(obs_or_feats: th.Tensor) -> th.Tensor:
        """(..., obs) -> (..., 5) weights in order (a, b, rf, rb, rc),
        summing to exactly 1.0 per tick.

        Reads the frozen obs tail: rise-kind one-hot (3, flat/bridge/
        crouch) immediately followed by the mode one-hot (6, hold/
        rise/lower/walk/turn/quad). A rise tick whose kind is NOT one
        of the three labeled ones (e.g. an exotic `rise:bank` start)
        falls back to core_b (stance) rather than losing all gate mass
        — ``known_rise`` (the labeled-kind sum) is subtracted out of
        core_b's own `rise` share so the five weights always partition
        exactly regardless of which rise starts this run actually
        exercises."""
        mode = obs_or_feats[..., -N_MODE_OBS:]
        rise_kind = obs_or_feats[
            ..., -(N_MODE_OBS + _N_RISE_KIND): -N_MODE_OBS]
        hold = mode[..., 0:1]
        rise = mode[..., 1:2]
        lower = mode[..., 2:3]
        loco = mode[..., 3:].sum(dim=-1, keepdim=True).clamp(0.0, 1.0)
        rf = rise_kind[..., 0:1].clamp(0.0, 1.0)
        rb = rise_kind[..., 1:2].clamp(0.0, 1.0)
        rc = rise_kind[..., 2:3].clamp(0.0, 1.0)
        known_rise = (rf + rb + rc).clamp(0.0, 1.0)
        stance = (hold + lower + rise - known_rise).clamp(0.0, 1.0)
        return th.cat([loco, stance, rf, rb, rc], dim=-1)

    def _penta_sequence(self, features, lstm_states, episode_starts,
                        penta):
        base = GruActorCriticPolicy._process_sequence
        h, c = lstm_states[0], lstm_states[1]
        cores = (penta.core_a, penta.core_b, penta.core_rf,
                 penta.core_rb, penta.core_rc)
        outs, hs = [], []
        for i, core in enumerate(cores):
            out_i, (h_i, _) = base(
                features, (h[i:i + 1], c[0:1]), episode_starts, core)
            outs.append(out_i)
            hs.append(h_i)
        return outs, (th.cat(hs, dim=0), c)

    def _pi_heads(self):
        return ((self.mlp_extractor, self.action_net),
                (self.mlp_extractor_b, self.action_net_b),
                (self.mlp_extractor_rf, self.action_net_rf),
                (self.mlp_extractor_rb, self.action_net_rb),
                (self.mlp_extractor_rc, self.action_net_rc))

    def _vf_heads(self):
        return ((self.mlp_extractor, self.value_net),
                (self.mlp_extractor_b, self.value_net_b),
                (self.mlp_extractor_rf, self.value_net_rf),
                (self.mlp_extractor_rb, self.value_net_rb),
                (self.mlp_extractor_rc, self.value_net_rc))

    def _log_stds(self):
        """Learnable log_std parameters: core_a's own, core_b's own
        (always split — see class docstring), plus each rise expert's
        own (TripleGru core_t convention)."""
        return (self.log_std, self.log_std_b, self.log_std_rf,
                self.log_std_rb, self.log_std_rc)

    def _actor_mean(self, outs, w):
        mus = [head(mlp.forward_actor(out))
               for (mlp, head), out in zip(self._pi_heads(), outs)]
        return sum(w[..., i:i + 1] * m for i, m in enumerate(mus))

    def _critic_value(self, outs, w):
        vs = [head(mlp.forward_critic(out))
              for (mlp, head), out in zip(self._vf_heads(), outs)]
        return sum(w[..., i:i + 1] * v for i, v in enumerate(vs))

    def _dist_from_mean(self, mean_actions, w):
        # Each of the five experts always has its own log_std (no
        # sharing at all — see class docstring on why core_b is split
        # unconditionally here, unlike Dual's default).
        log_std = (w[..., 0:1] * self.log_std
                   + w[..., 1:2] * self.log_std_b
                   + w[..., 2:3] * self.log_std_rf
                   + w[..., 3:4] * self.log_std_rb
                   + w[..., 4:5] * self.log_std_rc)
        return self.action_dist.proba_distribution(mean_actions, log_std)

    def _log_std_core(self, which: str):
        if which == "walk":
            return (self.log_std,)
        if which == "stance":
            return (self.log_std_b,)
        if which == "rise_flat":
            return (self.log_std_rf,)
        if which == "rise_bridge":
            return (self.log_std_rb,)
        if which == "rise_crouch":
            return (self.log_std_rc,)
        return None

    # -- RecurrentPPO entry points ---------------------------------

    def forward(self, obs, lstm_states, episode_starts,
                deterministic: bool = False):
        features = self.extract_features(obs)
        if self.share_features_extractor:
            pi_features = vf_features = features
        else:
            pi_features, vf_features = features
        w = self._gate5(obs)
        outs_pi, st_pi = self._penta_sequence(
            pi_features, lstm_states.pi, episode_starts, self.lstm_actor)
        outs_vf, st_vf = self._penta_sequence(
            vf_features, lstm_states.vf, episode_starts, self.lstm_critic)
        values = self._critic_value(outs_vf, w)
        distribution = self._dist_from_mean(
            self._actor_mean(outs_pi, w), w)
        actions = distribution.get_actions(deterministic=deterministic)
        log_prob = distribution.log_prob(actions)
        actions = actions.reshape((-1, *self.action_space.shape))
        from sb3_contrib.common.recurrent.type_aliases import RNNStates
        return actions, values, log_prob, RNNStates(st_pi, st_vf)

    def get_distribution(self, obs, lstm_states, episode_starts):
        from stable_baselines3.common.policies import ActorCriticPolicy
        features = super(ActorCriticPolicy, self).extract_features(
            obs, self.pi_features_extractor)
        w = self._gate5(obs)
        outs, st = self._penta_sequence(
            features, lstm_states, episode_starts, self.lstm_actor)
        return self._dist_from_mean(self._actor_mean(outs, w), w), st

    def predict_values(self, obs, lstm_states, episode_starts):
        from stable_baselines3.common.policies import ActorCriticPolicy
        features = super(ActorCriticPolicy, self).extract_features(
            obs, self.vf_features_extractor)
        w = self._gate5(obs)
        outs, _ = self._penta_sequence(
            features, lstm_states, episode_starts, self.lstm_critic)
        return self._critic_value(outs, w)

    def evaluate_actions(self, obs, actions, lstm_states, episode_starts):
        features = self.extract_features(obs)
        if self.share_features_extractor:
            pi_features = vf_features = features
        else:
            pi_features, vf_features = features
        w = self._gate5(obs)
        outs_pi, _ = self._penta_sequence(
            pi_features, lstm_states.pi, episode_starts, self.lstm_actor)
        outs_vf, _ = self._penta_sequence(
            vf_features, lstm_states.vf, episode_starts, self.lstm_critic)
        distribution = self._dist_from_mean(
            self._actor_mean(outs_pi, w), w)
        log_prob = distribution.log_prob(actions)
        values = self._critic_value(outs_vf, w)
        return values, log_prob, distribution.entropy()

    # -- auxiliary paths (distillation, BC anchor) ------------------

    def bptt_forward(self, feats: th.Tensor):
        """Whole-episode fused BPTT pass for distill_gru.train_student.

        ``feats`` is (T, B, obs) padded episodes starting at reset
        (zero initial hidden state is the truth). Returns (mu, value).
        """
        w = self._gate5(feats)
        cores_a = self.lstm_actor
        outs = [cores_a.core_a(feats)[0], cores_a.core_b(feats)[0],
                cores_a.core_rf(feats)[0], cores_a.core_rb(feats)[0],
                cores_a.core_rc(feats)[0]]
        mu = self._actor_mean(outs, w)
        cores_v = self.lstm_critic
        outs_v = [cores_v.core_a(feats)[0], cores_v.core_b(feats)[0],
                  cores_v.core_rf(feats)[0], cores_v.core_rb(feats)[0],
                  cores_v.core_rc(feats)[0]]
        value = self._critic_value(outs_v, w)
        return mu, value

    def bc_anchor_mean(self, th_obs: th.Tensor, th_h: th.Tensor,
                       detach_trunk: bool = False):
        """Policy mean at stored hidden states, for the BC anchor's
        auxiliary step. ``th_h`` is (B, 5*H) flat rows as stored by the
        anchor ring (row-major over the (5, B, H) state: a, b, rf, rb,
        rc — same convention as Dual's (2, B, H) / Triple's (3, B, H)).
        """
        hidden = self.lstm_actor.hidden_size
        h = (th_obs.new_zeros((5, th_obs.shape[0], hidden))
             if th_h is None
             else th_h.reshape(th_obs.shape[0], 5, hidden)
             .transpose(0, 1).contiguous())
        starts = th.zeros(th_obs.shape[0], device=th_obs.device)
        w = self._gate5(th_obs)
        if detach_trunk:
            with th.no_grad():
                feats = self.extract_features(th_obs)
                if not self.share_features_extractor:
                    feats = feats[0]
                outs, _ = self._penta_sequence(
                    feats, (h, th.zeros_like(h)), starts, self.lstm_actor)
            outs = [o.detach() for o in outs]
        else:
            feats = self.extract_features(th_obs)
            if not self.share_features_extractor:
                feats = feats[0]
            outs, _ = self._penta_sequence(
                feats, (h, th.zeros_like(h)), starts, self.lstm_actor)
        return self._actor_mean(outs, w)


def dual_to_rise_experts_transplant(
        old_model, new_model, n_pad: int = 0,
        insert_at: int = -1) -> list[str]:
    """Warm-start a fresh RiseKindGruActorCriticPolicy from an already-
    trained DualGruActorCriticPolicy checkpoint.

    core_a (loco) and core_b (stance) transplant VERBATIM where shapes
    already match. The rise-kind gate one-hot (``obs.
    rise_start_kind_gate=1``) that this policy REQUIRES widens the obs
    by ``n_pad`` (3) dims relative to any pre-existing Dual checkpoint
    (which never had this channel), so this is simultaneously an
    ARCHITECTURE transplant (2 cores -> 5) and an OBS-WIDENING one
    (mirrors ``obs_transplant.pad_obs_transplant``'s zero-pad-at-
    ``insert_at`` contract exactly, generalized to tolerate the
    destination state_dict having extra tensor NAMES the source
    doesn't, which plain ``pad_obs_transplant`` refuses). ``n_pad=0``
    (default) skips padding entirely (exact-shape copy only) for the
    rare case of a same-width warm start.

    The three new rise-kind experts (_rf/_rb/_rc) each start as a copy
    of the parent's core_b (stance) — the SAME body that was already
    trained on all rise starts pooled together, not from scratch — so
    each kind specializes from already-decent shared competence
    instead of relearning rise from zero. This copy happens AFTER
    core_b's own padded columns are written, so each rise expert
    inherits the fully-padded (not raw pre-pad) parent weights.
    ``log_std_rf``/``_rb``/``_rc`` start as copies of core_b's OWN
    log_std -- the parent's ``log_std_b`` if it was built with
    ``log_std_split=True`` (RiseKindGru's destination class always has
    a real, separate ``log_std_b`` regardless of the source, per its
    own docstring, and pass 1 below copies a same-named/same-shape
    ``log_std_b`` verbatim when the source has one), or the parent's
    single shared ``log_std`` when it was NOT split (core_b really did
    use that one value in that case).

    Requires ``old_model.policy`` to be a DualGruActorCriticPolicy and
    ``new_model.policy`` a freshly constructed RiseKindGruActorCriticPolicy
    with the SAME lstm_hidden_size/net_arch (a non-obs-width shape
    mismatch raises).
    """
    if not isinstance(old_model.policy, DualGruActorCriticPolicy):
        raise SystemExit("dual_to_rise_experts_transplant requires a "
                         "DualGruActorCriticPolicy source checkpoint "
                         f"(got {type(old_model.policy).__name__})")
    if not isinstance(new_model.policy, RiseKindGruActorCriticPolicy):
        raise SystemExit("dual_to_rise_experts_transplant requires a "
                         "RiseKindGruActorCriticPolicy destination "
                         f"model (got {type(new_model.policy).__name__})")
    n_new = int(new_model.observation_space.shape[0])
    n_old = int(old_model.observation_space.shape[0])
    if n_new - n_old != n_pad:
        raise SystemExit(
            f"dual_to_rise_experts_transplant: n_pad={n_pad} but obs "
            f"widened by {n_new - n_old} ({n_old} -> {n_new})")
    if insert_at >= 0 and insert_at > n_old:
        raise SystemExit(
            f"dual_to_rise_experts_transplant: insert_at {insert_at} "
            f"out of range for parent obs width {n_old}")
    sd_old = old_model.policy.state_dict()
    sd_new = new_model.policy.state_dict()
    copied: list[str] = []

    def _copy(dst_name: str, src_name: str, sd_src=None) -> None:
        src = sd_old if sd_src is None else sd_src
        v_new = sd_new[dst_name]
        v_old = src[src_name]
        if v_new.shape == v_old.shape:
            with th.no_grad():
                v_new.copy_(v_old)
        elif (n_pad > 0 and v_new.dim() == 2
              and v_new.shape[0] == v_old.shape[0]
              and v_new.shape[1] == n_new and v_old.shape[1] == n_old):
            with th.no_grad():
                v_new.zero_()
                if insert_at < 0:
                    v_new[:, :n_old].copy_(v_old)
                else:
                    v_new[:, :insert_at].copy_(v_old[:, :insert_at])
                    v_new[:, insert_at + n_pad:].copy_(
                        v_old[:, insert_at:])
        else:
            raise SystemExit(
                "dual_to_rise_experts_transplant: shape mismatch "
                f"{src_name} {tuple(v_old.shape)} -> {dst_name} "
                f"{tuple(v_new.shape)} (hidden_size/net_arch must "
                "match between the Dual parent and the fresh "
                "RiseKindGru; only obs-width columns may differ)")
        copied.append(dst_name)

    # Pass 1 — verbatim/padded: every new-policy tensor that ALSO
    # exists in the old policy under the identical name (core_a.*,
    # core_b.*, mlp_extractor(_b).*, log_std, shared feature
    # extractor, ...).
    for name in sd_new:
        if name in sd_old:
            _copy(name, name)
    new_model.policy.load_state_dict(sd_new, strict=True)

    # Pass 2 — the three rise-expert-only tensors: map each back to
    # its core_b-named counterpart, reading from the NEW model's OWN
    # (already fully-padded, just-loaded) state dict rather than the
    # old model's raw one, so a padded column layout is inherited
    # correctly without duplicating the padding logic here.
    #
    # log_std_b FIRST, before anything reads it as a source: if the
    # Dual source had log_std_split=True, pass 1 already copied a
    # real log_std_b verbatim (same name, same shape, no obs-width
    # dependency) and this is a no-op skip (already in sd_old); if the
    # source was NOT split, core_b really did use the single shared
    # log_std, so that is what backfills log_std_b here.
    sd_new2 = new_model.policy.state_dict()
    if "log_std_b" not in sd_old:
        _copy("log_std_b", "log_std", sd_src=sd_new2)
    for name in sd_new2:
        if name in sd_old:
            continue
        if name == "log_std_b":
            continue  # handled above
        matched = False
        for suf in ("rf", "rb", "rc"):
            if name == f"log_std_{suf}":
                _copy(name, "log_std_b", sd_src=sd_new2)
                matched = True
                break
            if f".core_{suf}." in name:
                _copy(name, name.replace(f".core_{suf}.", ".core_b."),
                      sd_src=sd_new2)
                matched = True
                break
            if name.startswith(f"mlp_extractor_{suf}."):
                _copy(name, "mlp_extractor_b."
                      + name[len(f"mlp_extractor_{suf}."):],
                      sd_src=sd_new2)
                matched = True
                break
            if name.startswith(f"action_net_{suf}."):
                _copy(name, "action_net_b."
                      + name[len(f"action_net_{suf}."):],
                      sd_src=sd_new2)
                matched = True
                break
            if name.startswith(f"value_net_{suf}."):
                _copy(name, "value_net_b."
                      + name[len(f"value_net_{suf}."):],
                      sd_src=sd_new2)
                matched = True
                break
        if not matched:
            raise SystemExit(
                "dual_to_rise_experts_transplant: unmapped new-only "
                f"tensor {name} — add a mapping rule or this is a "
                "genuine architecture mismatch")
    new_model.policy.load_state_dict(sd_new2, strict=True)

    required = {"lstm_actor.core_rf.weight_ih_l0",
               "lstm_actor.core_rb.weight_ih_l0",
               "lstm_actor.core_rc.weight_ih_l0",
               "log_std_rf", "log_std_rb", "log_std_rc"}
    if not required.issubset(copied):
        raise SystemExit(
            "dual_to_rise_experts_transplant did not copy the expected "
            "core_rf/core_rb/core_rc/log_std_r* tensors")
    return copied


# --- Mode-experts (four-expert, fully isolated) GRU -----------------
#
# Operator directive fb_20260815T013349_488ffd (08-15, executed via
# operator KICK): the dual-core split removed walk<->stance trunk
# interference, but rise/hold/lower still share the stance core AND
# every expert shares ONE global log_std — modeseq1-r1/dual2 showed
# PPO spending rare hard-start rise competence through exactly those
# shared parameters. This policy gives each skill its own COMPLETE
# expert: RISE, HOLD, LOWER, LOCOMOTION (walk/turn/quad), each with
# its own actor GRU, critic GRU, latent extractors, action/value
# heads, and its own learnable log_std. All four hidden states stay
# warm every tick (memories survive mode switches); only the ACTIVE
# expert's output is selected, so gradients — actor, critic, AND
# exploration std — flow exclusively into the expert whose mode is
# lit. Optional small transition adapter: a residual MLP on the
# selected action mean, zero-initialized (exactly 0 contribution at
# init), architecturally separate so it can never silently rewrite a
# frozen expert body. Default OFF everywhere: nothing constructs this
# class unless --gru-experts / --experts is passed.

EXPERTS_ORDER = ("rise", "hold", "lower", "loco")
N_EXPERTS = 4


class _QuadGRU(nn.Module):
    """Four parallel single-layer GRU cores behind one state facade.

    ``num_layers=4`` is a facade (like _DualGRU's 2): RecurrentPPO
    sizes its opaque state buffers as (4, n_envs, H); row i threads
    the core for EXPERTS_ORDER[i].
    """

    def __init__(self, input_size: int, hidden_size: int, **gru_kwargs):
        super().__init__()
        self.core_rise = nn.GRU(input_size, hidden_size, **gru_kwargs)
        self.core_hold = nn.GRU(input_size, hidden_size, **gru_kwargs)
        self.core_lower = nn.GRU(input_size, hidden_size, **gru_kwargs)
        self.core_loco = nn.GRU(input_size, hidden_size, **gru_kwargs)
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = N_EXPERTS  # facade: 4 state rows

    def cores(self):
        return (self.core_rise, self.core_hold, self.core_lower,
                self.core_loco)


class ModeExpertsGruActorCriticPolicy(GruActorCriticPolicy):
    """Mode-gated four-expert GRU policy with complete per-expert
    gradient isolation (rise / hold / lower / locomotion).

    Same constructor surface as GruActorCriticPolicy plus:
      experts_adapter_hidden: >0 builds the transition adapter — a
        small residual MLP (obs features -> action delta) whose output
        layer is ZERO-initialized, added to the selected expert mean.
        0 (default) = no adapter module, bit-identical selected-expert
        output path.
      experts_adapter_scale: residual multiplier (default 0.05).

    Requires the default recurrent layout (critic GRU enabled, no
    shared_lstm, no SDE, n_lstm_layers=1 per core) and an env with
    obs.mode_onehot=1 (the 6-wide skill one-hot at the obs tail).
    """

    def __init__(self, *args, experts_adapter_hidden: int = 0,
                 experts_adapter_scale: float = 0.05, **kwargs):
        self.experts_adapter_hidden = int(experts_adapter_hidden)
        self.experts_adapter_scale = float(experts_adapter_scale)
        super().__init__(*args, **kwargs)
        if self.lstm_critic is None or self.shared_lstm:
            raise ValueError(
                "ModeExpertsGruActorCriticPolicy requires "
                "enable_critic_lstm=True and shared_lstm=False")
        if self.use_sde:
            raise ValueError("ModeExpertsGruActorCriticPolicy does not "
                             "support use_sde")
        if self.lstm_actor.num_layers != 1:
            raise ValueError("ModeExpertsGruActorCriticPolicy requires "
                             "n_lstm_layers=1 (one layer per core)")
        import copy

        feat_dim = self.lstm_actor.input_size
        self.lstm_actor = _QuadGRU(
            feat_dim, self.lstm_actor.hidden_size, **self.lstm_kwargs)
        self.lstm_critic = _QuadGRU(
            self.lstm_critic.input_size, self.lstm_critic.hidden_size,
            **self.lstm_kwargs)
        self.lstm_hidden_state_shape = (
            N_EXPERTS, 1, self.lstm_actor.hidden_size)
        # Per-expert heads. The base modules (mlp_extractor/action_net/
        # value_net/log_std) serve the LOCO expert (mirrors _DualGRU's
        # core-A convention); rise/hold/lower get deepcopies that
        # diverge immediately under their disjoint gradients.
        for name in ("rise", "hold", "lower"):
            setattr(self, f"mlp_extractor_{name}",
                    copy.deepcopy(self.mlp_extractor))
            setattr(self, f"action_net_{name}",
                    copy.deepcopy(self.action_net))
            setattr(self, f"value_net_{name}",
                    copy.deepcopy(self.value_net))
            setattr(self, f"log_std_{name}",
                    nn.Parameter(self.log_std.data.clone(),
                                 requires_grad=True))
        # Optional transition adapter — zero-init output layer, so the
        # residual is EXACTLY 0 until it is trained.
        if self.experts_adapter_hidden > 0:
            act_dim = self.action_net.out_features
            out = nn.Linear(self.experts_adapter_hidden, act_dim)
            with th.no_grad():
                out.weight.zero_()
                out.bias.zero_()
            self.experts_adapter = nn.Sequential(
                nn.Linear(feat_dim, self.experts_adapter_hidden),
                nn.Tanh(), out)
        else:
            self.experts_adapter = None
        lr = self.optimizer.defaults["lr"]
        self.optimizer = self.optimizer_class(
            self.parameters(), lr=lr, **self.optimizer_kwargs)

    # -- gating --------------------------------------------------

    @staticmethod
    def _experts_weights(obs_or_feats: th.Tensor) -> th.Tensor:
        """(..., obs) -> (..., 4) expert one-hot in EXPERTS_ORDER.

        Obs-tail slot order is frozen in walk_task.MODE_ONEHOT_ORDER =
        (hold, rise, lower, walk, turn, quad); exactly one slot is lit
        per tick, so this selection is exact.
        """
        x = obs_or_feats
        hold = x[..., -6:-5]
        rise = x[..., -5:-4]
        lower = x[..., -4:-3]
        loco = x[..., -3:].sum(dim=-1, keepdim=True).clamp(0.0, 1.0)
        return th.cat([rise, hold, lower, loco], dim=-1)

    def _pi_heads(self):
        return ((self.mlp_extractor_rise, self.action_net_rise),
                (self.mlp_extractor_hold, self.action_net_hold),
                (self.mlp_extractor_lower, self.action_net_lower),
                (self.mlp_extractor, self.action_net))

    def _vf_heads(self):
        return ((self.mlp_extractor_rise, self.value_net_rise),
                (self.mlp_extractor_hold, self.value_net_hold),
                (self.mlp_extractor_lower, self.value_net_lower),
                (self.mlp_extractor, self.value_net))

    def _log_stds(self):
        return (self.log_std_rise, self.log_std_hold,
                self.log_std_lower, self.log_std)

    def _quad_sequence(self, features, lstm_states, episode_starts, quad):
        """Run ALL FOUR cores over the sequence (memories stay warm);
        return per-expert outputs and the repacked (h, c) with h rows
        in EXPERTS_ORDER."""
        base = GruActorCriticPolicy._process_sequence
        h, c = lstm_states[0], lstm_states[1]
        outs, hs = [], []
        for i, core in enumerate(quad.cores()):
            out_i, (h_i, _) = base(
                features, (h[i:i + 1], c[0:1]), episode_starts, core)
            outs.append(out_i)
            hs.append(h_i)
        return outs, (th.cat(hs, dim=0), c)

    def _actor_mean(self, outs, w, features):
        mus = [head(mlp.forward_actor(out))
               for (mlp, head), out in zip(self._pi_heads(), outs)]
        mu = sum(w[..., i:i + 1] * m for i, m in enumerate(mus))
        if self.experts_adapter is not None:
            mu = mu + self.experts_adapter_scale \
                * self.experts_adapter(features)
        return mu

    def _critic_value(self, outs, w):
        vs = [head(mlp.forward_critic(out))
              for (mlp, head), out in zip(self._vf_heads(), outs)]
        return sum(w[..., i:i + 1] * v for i, v in enumerate(vs))

    def _dist(self, mean_actions, w):
        # Per-sample log_std: the one-hot selects the ACTIVE expert's
        # row, so exploration std is per-expert and its gradient never
        # reaches a gated-out expert.
        log_std = w @ th.stack(self._log_stds())
        return self.action_dist.proba_distribution(mean_actions, log_std)

    # -- freezing (Arm A: frozen expert bodies + trainable adapter) --

    def set_experts_frozen(self, frozen: bool = True,
                           include_critic: bool = False):
        """Freeze/unfreeze all four expert ACTOR bodies (GRU cores,
        actor latent nets, action heads, per-expert log_std). Critic
        bodies stay trainable by default (value estimates may keep
        improving without touching behavior); include_critic=True
        freezes them too. The transition adapter always stays
        trainable."""
        req = not frozen
        self.lstm_actor.requires_grad_(req)
        if include_critic:
            self.lstm_critic.requires_grad_(req)
        for (mlp, head) in self._pi_heads():
            mlp.policy_net.requires_grad_(req)
            head.requires_grad_(req)
        if include_critic:
            for (mlp, head) in self._vf_heads():
                mlp.value_net.requires_grad_(req)
                head.requires_grad_(req)
        for p in self._log_stds():
            p.requires_grad = req
        if self.experts_adapter is not None:
            self.experts_adapter.requires_grad_(True)

    # -- RecurrentPPO entry points ---------------------------------

    def forward(self, obs, lstm_states, episode_starts,
                deterministic: bool = False):
        features = self.extract_features(obs)
        if self.share_features_extractor:
            pi_features = vf_features = features
        else:
            pi_features, vf_features = features
        w = self._experts_weights(obs)
        pi_outs, st_pi = self._quad_sequence(
            pi_features, lstm_states.pi, episode_starts, self.lstm_actor)
        vf_outs, st_vf = self._quad_sequence(
            vf_features, lstm_states.vf, episode_starts, self.lstm_critic)
        values = self._critic_value(vf_outs, w)
        distribution = self._dist(
            self._actor_mean(pi_outs, w, pi_features), w)
        actions = distribution.get_actions(deterministic=deterministic)
        log_prob = distribution.log_prob(actions)
        actions = actions.reshape((-1, *self.action_space.shape))
        from sb3_contrib.common.recurrent.type_aliases import RNNStates
        return actions, values, log_prob, RNNStates(st_pi, st_vf)

    def get_distribution(self, obs, lstm_states, episode_starts):
        from stable_baselines3.common.policies import ActorCriticPolicy
        features = super(ActorCriticPolicy, self).extract_features(
            obs, self.pi_features_extractor)
        w = self._experts_weights(obs)
        outs, st = self._quad_sequence(
            features, lstm_states, episode_starts, self.lstm_actor)
        return self._dist(self._actor_mean(outs, w, features), w), st

    def predict_values(self, obs, lstm_states, episode_starts):
        from stable_baselines3.common.policies import ActorCriticPolicy
        features = super(ActorCriticPolicy, self).extract_features(
            obs, self.vf_features_extractor)
        w = self._experts_weights(obs)
        outs, _ = self._quad_sequence(
            features, lstm_states, episode_starts, self.lstm_critic)
        return self._critic_value(outs, w)

    def evaluate_actions(self, obs, actions, lstm_states, episode_starts):
        features = self.extract_features(obs)
        if self.share_features_extractor:
            pi_features = vf_features = features
        else:
            pi_features, vf_features = features
        w = self._experts_weights(obs)
        pi_outs, _ = self._quad_sequence(
            pi_features, lstm_states.pi, episode_starts, self.lstm_actor)
        vf_outs, _ = self._quad_sequence(
            vf_features, lstm_states.vf, episode_starts, self.lstm_critic)
        distribution = self._dist(
            self._actor_mean(pi_outs, w, pi_features), w)
        log_prob = distribution.log_prob(actions)
        values = self._critic_value(vf_outs, w)
        return values, log_prob, distribution.entropy()

    # -- auxiliary paths (distillation, BC anchor) ------------------

    def bptt_forward(self, feats: th.Tensor):
        """Whole-episode fused BPTT pass for distill_gru.train_student.
        ``feats`` is (T, B, obs) padded episodes starting at reset."""
        w = self._experts_weights(feats)
        pi_outs = [core(feats)[0] for core in self.lstm_actor.cores()]
        mu = self._actor_mean(pi_outs, w, feats)
        vf_outs = [core(feats)[0] for core in self.lstm_critic.cores()]
        value = self._critic_value(vf_outs, w)
        return mu, value

    def bc_anchor_mean(self, th_obs: th.Tensor, th_h: th.Tensor,
                       detach_trunk: bool = False):
        """Policy mean at stored hidden states for the BC anchor aux
        step. ``th_h`` is (B, 4*H) flat rows (row-major over the
        (4, B, H) state, EXPERTS_ORDER)."""
        hidden = self.lstm_actor.hidden_size
        h = (th_obs.new_zeros((N_EXPERTS, th_obs.shape[0], hidden))
             if th_h is None
             else th_h.reshape(th_obs.shape[0], N_EXPERTS, hidden)
             .transpose(0, 1).contiguous())
        starts = th.zeros(th_obs.shape[0], device=th_obs.device)
        w = self._experts_weights(th_obs)
        if detach_trunk:
            with th.no_grad():
                feats = self.extract_features(th_obs)
                if not self.share_features_extractor:
                    feats = feats[0]
                outs, _ = self._quad_sequence(
                    feats, (h, th.zeros_like(h)), starts, self.lstm_actor)
            feats = feats.detach()
            outs = [o.detach() for o in outs]
        else:
            feats = self.extract_features(th_obs)
            if not self.share_features_extractor:
                feats = feats[0]
            outs, _ = self._quad_sequence(
                feats, (h, th.zeros_like(h)), starts, self.lstm_actor)
        return self._actor_mean(outs, w, feats)


def is_recurrent_checkpoint(path: str | Path) -> bool:
    """True if the SB3 zip at ``path`` holds a recurrent policy."""
    from stable_baselines3.common.save_util import load_from_zip_file
    data, _, _ = load_from_zip_file(path, device="cpu", load_data=True)
    policy_class = data.get("policy_class")
    try:
        return bool(policy_class) and issubclass(
            policy_class, RecurrentActorCriticPolicy)
    except TypeError:
        return False


def is_sac_checkpoint(path: str | Path) -> bool:
    """True if the SB3 zip at ``path`` holds an off-policy SAC policy.

    Added 2026-08-29 for the walkcurr fallback-ladder SAC probe
    (train_ppo_mjx --algo sac): every eval/viewer path routes through
    ``load_checkpoint_auto``, so SAC checkpoints eval with the same
    harness/video machinery as PPO ones.
    """
    from stable_baselines3.common.save_util import load_from_zip_file
    data, _, _ = load_from_zip_file(path, device="cpu", load_data=True)
    policy_class = data.get("policy_class")
    try:
        from stable_baselines3.sac.policies import SACPolicy
        return bool(policy_class) and issubclass(policy_class, SACPolicy)
    except TypeError:
        return False


def repair_legacy_actor_critic_optimizer(path: str | Path,
                                         out_path: str | Path | None = None
                                         ) -> bool:
    """Fix checkpoints saved by the pre-2026-08-18 attach_actor_critic_lr
    bug (rl_move/sim/update_health.py, found via cw-dynrep-criticD-
    walkcurr3's eval crash): ``save_stock_optimizer`` built the
    save-time stock optimizer over ALL ``model.policy.parameters()``
    (including frozen submodules, e.g. condition-D's frozen dynamics-
    transformer encoder) instead of trainable params only — so its
    single param group has more entries than the trainable-param
    optimizer a freshly-constructed policy builds, and
    ``PPO.load``/``set_parameters`` raises "loaded state dict contains
    a parameter group that doesn't match the size of optimizer's
    group" on every eval/warm-start of the checkpoint. The saved
    optimizer ``state`` is always EMPTY (it is a throwaway fresh Adam
    built only for the zip write, never stepped) so resizing
    ``param_groups[0]['params']`` to the true trainable-param count
    (recorded in ``_ac_state`` as ``n_actor + n_critic``) loses no
    information — it only fixes torch's group-size sanity check.
    Returns True if a repair was written, False if the checkpoint
    didn't need one (no ``_ac_state``, or already correct size).
    """
    import io
    import zipfile
    from stable_baselines3.common.save_util import load_from_zip_file

    path = Path(path)
    data, params, _pv = load_from_zip_file(str(path), device="cpu")
    ac_state = data.get("_ac_state") if isinstance(data, dict) else None
    opt_sd = params.get("policy.optimizer") if params else None
    if not ac_state or not opt_sd or not opt_sd.get("param_groups"):
        return False
    n_true = int(ac_state["n_actor"]) + int(ac_state["n_critic"])
    grp = opt_sd["param_groups"][0]
    if len(grp["params"]) == n_true:
        return False
    grp["params"] = list(range(n_true))
    dest = Path(out_path) if out_path is not None else path
    buf = io.BytesIO()
    with zipfile.ZipFile(path) as zin, \
            zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in zin.namelist():
            if name == "policy.optimizer.pth":
                inner = io.BytesIO()
                th.save(opt_sd, inner)
                zout.writestr(name, inner.getvalue())
            else:
                zout.writestr(name, zin.read(name))
    dest.write_bytes(buf.getvalue())
    return True


class RecurrentPredictor:
    """predict/reset shim for GRU (RecurrentPPO) checkpoints.

    A recurrent policy evaluated through the stateless
    ``model.predict(obs)`` path gets a fresh zero hidden state every
    tick — that evaluates a memory-less lobotomy of the trained policy,
    not the policy. This shim threads the hidden state across steps;
    callers must invoke ``.reset()`` at every episode start (exactly
    where the state must clear).

    Moved here from eval_checkpoint._RecurrentPredictor (2026-08-28
    manual-drive runner-bug audit) so every rollout tool shares ONE
    correct implementation; eval_checkpoint imports it back under its
    old name. Behavior is bit-exact to the original.
    """

    def __init__(self, model):
        self.policy = model.policy
        # Forward these so callers that load-then-check-then-wrap in one
        # step (e.g. hybrid_demo.py's `_load_any_policy`) can still do an
        # obs-space sanity check on the wrapped object; every OTHER
        # caller already checks before wrapping, so this is additive
        # only, never read by them.
        self.observation_space = getattr(model, "observation_space", None)
        self.action_space = getattr(model, "action_space", None)
        self.reset()

    def reset(self) -> None:
        self._state = None
        self._episode_start = np.ones((1,), dtype=bool)

    def predict(self, obs, deterministic: bool = False):
        a, self._state = self.policy.predict(
            obs, state=self._state, episode_start=self._episode_start,
            deterministic=deterministic)
        self._episode_start = np.zeros((1,), dtype=bool)
        return a, None


def wrap_recurrent_predictor(model):
    """Return a state-threading predictor for recurrent checkpoints.

    Non-recurrent models pass through unchanged (their ``predict`` is
    already stateless-correct). Use this in EVERY hand-rolled rollout
    loop instead of calling ``model.predict`` on a RecurrentPPO —
    found live 08-28: manual_drive_session/drive_policy/view ran GRU
    policies with a zero hidden state every tick.
    """
    if getattr(getattr(model, "policy", None), "lstm_actor", None) \
            is not None:
        return RecurrentPredictor(model)
    return model


class RecurrentTeacherDriver:
    """Threads BOTH the actor's and the critic's own recurrent state
    for a RecurrentPPO/GRU TEACHER used as a per-tick action+value
    source (BC/DAgger demo collection) -- via ONE ``policy.forward``
    call per tick, exactly the ``RNNStates(pi, vf)`` convention
    ``RecurrentPPO.collect_rollouts`` itself threads during real
    training.

    Found 2026-09-24 auditing ``distill_gru.py`` before funding the
    standwalk stage-2 distillation task: that module called bare
    ``teacher.predict(obs)`` (silently re-zeroing hidden state every
    tick, the same "lobotomy" bug ``RecurrentPredictor`` fixed for
    eval/drive tools 2026-08-28) AND ``teacher.policy.predict_values
    (obs_tensor)`` with no ``lstm_states``/``episode_starts`` at all --
    ``RecurrentActorCriticPolicy.predict_values`` requires both as
    positional args, so this doesn't silently degrade, it raises
    ``TypeError`` outright the first time a GRU checkpoint (e.g. any
    of this track's own ``cw-stand50hz-gru-...``/``cw-walk50hz-gru-
    ...`` champions) is pointed at ``--stance-teacher-run``/``--walk-
    teacher-run``. ``RecurrentPredictor`` alone does not fix this: its
    ``.predict()`` only threads the ACTOR's hidden state (sb3_contrib's
    own ``predict()`` -> ``_predict()`` -> ``get_distribution`` path
    never touches ``lstm_critic``) -- exactly the gap
    ``probe_yaw_credit.py``'s docstring names for the dual-core case,
    equally true for a plain single-core GRU checkpoint with its own
    separate critic LSTM (``enable_critic_lstm=True``, the RecurrentPPO
    default). Calling ``predict()`` then ``predict_values()`` back to
    back with two independently-tracked states is exactly the trap
    that docstring warns against; this class instead gets both from
    the SAME forward pass so there is only one state pair to get right.

    Non-recurrent (plain PPO/MLP) teachers should keep using the model
    directly -- see ``wrap_teacher_driver`` for the dispatch.
    """

    def __init__(self, model):
        self.model = model
        self.policy = model.policy
        self.observation_space = getattr(model, "observation_space", None)
        self.action_space = getattr(model, "action_space", None)
        self.reset()

    def reset(self) -> None:
        self._states = None
        self._episode_start = np.ones((1,), dtype=bool)

    def _zero_pair(self):
        z = th.zeros(self.policy.lstm_hidden_state_shape,
                     device=self.policy.device)
        return (z, z.clone())

    def step(self, obs, deterministic: bool = False):
        """One tick. Returns ``(action (unbatched np.ndarray), value
        (float))`` and advances the threaded (pi, vf) state pair."""
        from sb3_contrib.common.recurrent.type_aliases import RNNStates

        obs_t, _ = self.policy.obs_to_tensor(np.asarray(obs)[None])
        ep_starts = th.as_tensor(self._episode_start, dtype=th.float32,
                                 device=self.policy.device)
        if self._states is None:
            self._states = RNNStates(self._zero_pair(), self._zero_pair())
        with th.no_grad():
            actions, values, _log_prob, new_states = self.policy.forward(
                obs_t, self._states, ep_starts, deterministic=deterministic)
        self._states = new_states
        self._episode_start = np.zeros((1,), dtype=bool)
        act = actions.cpu().numpy()
        if self.action_space is not None:
            act = act.reshape((-1, *self.action_space.shape))
        val = float(values.cpu().numpy().reshape(-1)[0])
        return act[0], val

    def predict(self, obs, deterministic: bool = False):
        """``RecurrentPredictor``-compatible action-only call (some
        callers only want the action; the value is discarded, but the
        SAME threaded (pi, vf) state pair still advances so a later
        ``.step()`` call on the same object stays consistent)."""
        act, _val = self.step(obs, deterministic=deterministic)
        return act, None


def wrap_teacher_driver(model):
    """Dispatch to ``RecurrentTeacherDriver`` for a recurrent (GRU/
    LSTM) teacher, or pass a plain (non-recurrent) model through
    unchanged -- its stateless ``model.predict()`` / ``policy.
    predict_values(obs_tensor)`` calls are already correct. Use this
    (not ``wrap_recurrent_predictor``) for any BC/DAgger-style teacher
    that needs BOTH actions and values per tick."""
    if getattr(getattr(model, "policy", None), "lstm_actor", None) \
            is not None:
        return RecurrentTeacherDriver(model)
    return model


def load_checkpoint_auto(path: str | Path, device: str = "cpu", env=None):
    """Load an SB3 checkpoint as PPO or RecurrentPPO, whichever wrote it.

    Every eval/viewer code path that used to hardcode ``PPO.load``
    should go through this so GRU checkpoints just work. Falls back to
    ``repair_legacy_actor_critic_optimizer`` (into a sibling
    ``*.optfix.zip``, never mutating the original) on the specific
    optimizer-group-size ValueError those pre-fix checkpoints raise —
    see that function's docstring.
    """
    cls = None
    kwargs = dict(env=env, device=device)
    if is_sac_checkpoint(path):
        from stable_baselines3 import SAC
        cls = SAC
    elif is_recurrent_checkpoint(path):
        from sb3_contrib import RecurrentPPO
        cls = RecurrentPPO
    else:
        from stable_baselines3 import PPO
        cls = PPO
    try:
        return cls.load(path, **kwargs)
    except ValueError as exc:
        if "parameter group" not in str(exc):
            raise
        path = Path(path)
        fixed = path.with_suffix(".optfix.zip")
        if not repair_legacy_actor_critic_optimizer(path, fixed):
            raise
        print(f"[load_checkpoint_auto] repaired legacy optimizer group "
              f"size (pre-08-18 attach_actor_critic_lr bug): {fixed}")
        return cls.load(fixed, **kwargs)
