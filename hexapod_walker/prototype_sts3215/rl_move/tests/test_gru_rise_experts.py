"""Tests for gru_policy.RiseKindGruActorCriticPolicy + its warm-start
transplant (dual_to_rise_experts_transplant) -- standwalk rise flat/
bridge precision gap, 2026-09-24 ~21:3x.

Three independent shared-representation mechanisms (exposure-frequency
reweight, explicit-onehot input conditioning, gradient-level disjoint-
minibatch isolation) all converged on the identical flat-0/bridge-2/
crouch-5 fingerprint on the gru-dual-rlfinetune-rise lineage. This
class is the named remaining lever: genuinely SEPARATE WEIGHTS per
rise start-kind, carved out of DualGruActorCriticPolicy's core_b
(stance). These tests mirror test_gru_policy.py's Dual/Triple sections:
routing correctness, gradient isolation, save/load, and the Dual->
RiseExperts transplant (both same-width and obs-widening-with-padding
forms, since no pre-existing Dual checkpoint has the new
rise_start_kind_gate obs channel).
"""
from __future__ import annotations

import numpy as np
import pytest
import torch as th

import gymnasium as gym
from gymnasium import spaces

from rl_move.sim.gru_policy import (
    DualGruActorCriticPolicy,
    GruActorCriticPolicy,
    N_MODE_OBS,
    RiseKindGruActorCriticPolicy,
    _N_RISE_KIND,
    dual_to_rise_experts_transplant,
    is_recurrent_checkpoint,
    load_checkpoint_auto,
)

N_CORE = 3


def _mode_tail(slot: int) -> np.ndarray:
    t = np.zeros(N_MODE_OBS, dtype=np.float32)
    t[slot] = 1.0
    return t


def _kind_tail(idx: int | None) -> np.ndarray:
    t = np.zeros(_N_RISE_KIND, dtype=np.float32)
    if idx is not None:
        t[idx] = 1.0
    return t


HOLD, RISE, LOWER, WALK, TURN, QUAD = range(6)
FLAT, BRIDGE, CROUCH = range(3)


class _TinyRiseEnv(gym.Env):
    """Obs tail = [rise-kind one-hot(3), mode one-hot(6)]. Cycles
    through walk/hold/lower/rise(flat/bridge/crouch)/rise(unmatched)
    across episodes so training exercises every gate branch."""

    _CASES = [
        (WALK, None), (HOLD, None), (LOWER, None),
        (RISE, FLAT), (RISE, BRIDGE), (RISE, CROUCH), (RISE, None),
    ]

    def __init__(self):
        self.observation_space = spaces.Box(
            -1, 1, (N_CORE + _N_RISE_KIND + N_MODE_OBS,), dtype=np.float32)
        self.action_space = spaces.Box(-1, 1, (2,), dtype=np.float32)
        self._t = 0
        self._ep = 0

    def _obs(self):
        core = self.np_random.uniform(-1, 1, N_CORE).astype(np.float32)
        slot, kind = self._CASES[self._ep % len(self._CASES)]
        return np.concatenate([core, _kind_tail(kind), _mode_tail(slot)])

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self._t = 0
        self._ep += 1
        return self._obs(), {}

    def step(self, action):
        self._t += 1
        return self._obs(), 0.0, False, self._t >= 8, {}


def _rke_model(hidden=8, env_ctor=_TinyRiseEnv, **kw):
    from sb3_contrib import RecurrentPPO
    return RecurrentPPO(
        RiseKindGruActorCriticPolicy, env_ctor(),
        n_steps=8, batch_size=16, n_epochs=1, seed=0, device="cpu",
        policy_kwargs=dict(lstm_hidden_size=hidden, net_arch=[16]), **kw)


def _dual_model_narrow(hidden=8, log_std_split=False, **kw):
    """A DualGru model over the OLD (no rise-kind-gate) obs width --
    the real-world parent shape (mode_onehot=1 only)."""
    from sb3_contrib import RecurrentPPO

    class _NarrowDualEnv(gym.Env):
        def __init__(self):
            self.observation_space = spaces.Box(
                -1, 1, (N_CORE + N_MODE_OBS,), dtype=np.float32)
            self.action_space = spaces.Box(-1, 1, (2,), dtype=np.float32)
            self._t = 0
            self._ep = 0

        def _obs(self):
            core = self.np_random.uniform(-1, 1, N_CORE).astype(np.float32)
            slot = (WALK, HOLD, RISE)[self._ep % 3]
            return np.concatenate([core, _mode_tail(slot)])

        def reset(self, *, seed=None, options=None):
            super().reset(seed=seed)
            self._t = 0
            self._ep += 1
            return self._obs(), {}

        def step(self, action):
            self._t += 1
            return self._obs(), 0.0, False, self._t >= 8, {}

    return RecurrentPPO(
        DualGruActorCriticPolicy, _NarrowDualEnv(),
        n_steps=8, batch_size=16, n_epochs=1, seed=0, device="cpu",
        policy_kwargs=dict(lstm_hidden_size=hidden, net_arch=[16],
                           log_std_split=log_std_split), **kw)


# ---------------------------------------------------------------------------
# Gate / routing
# ---------------------------------------------------------------------------

def test_gate5_routes_correctly():
    model = _rke_model()
    pol = model.policy
    pol.set_training_mode(False)
    with th.no_grad():
        pol.action_net.weight.zero_()
        pol.action_net.bias.fill_(0.1)     # a = loco
        pol.action_net_b.weight.zero_()
        pol.action_net_b.bias.fill_(0.2)   # b = stance
        pol.action_net_rf.weight.zero_()
        pol.action_net_rf.bias.fill_(0.3)  # rise flat
        pol.action_net_rb.weight.zero_()
        pol.action_net_rb.bias.fill_(0.4)  # rise bridge
        pol.action_net_rc.weight.zero_()
        pol.action_net_rc.bias.fill_(0.5)  # rise crouch

    rows = [
        (WALK, None, 0.1), (TURN, None, 0.1), (QUAD, None, 0.1),
        (HOLD, None, 0.2), (LOWER, None, 0.2),
        (RISE, None, 0.2),      # unmatched kind -> falls back to stance
        (RISE, FLAT, 0.3), (RISE, BRIDGE, 0.4), (RISE, CROUCH, 0.5),
    ]
    obs = th.as_tensor(np.stack([
        np.concatenate([np.full(N_CORE, 0.1, np.float32),
                       _kind_tail(kind), _mode_tail(slot)])
        for slot, kind, _ in rows]))
    h = th.zeros(5, len(rows), 8)
    starts = th.ones(len(rows))
    with th.no_grad():
        dist, _ = pol.get_distribution(obs, (h, th.zeros_like(h)), starts)
        mean = dist.distribution.mean
    exp = th.tensor([[v, v] for _, _, v in rows])
    assert th.allclose(mean, exp, atol=1e-6), f"gate5 routing broken: {mean}"


def _rke_param_groups(pol):
    a = (list(pol.lstm_actor.core_a.parameters())
         + list(pol.lstm_critic.core_a.parameters())
         + list(pol.mlp_extractor.parameters())
         + list(pol.action_net.parameters())
         + list(pol.value_net.parameters()) + [pol.log_std])
    b = (list(pol.lstm_actor.core_b.parameters())
         + list(pol.lstm_critic.core_b.parameters())
         + list(pol.mlp_extractor_b.parameters())
         + list(pol.action_net_b.parameters())
         + list(pol.value_net_b.parameters()) + [pol.log_std_b])
    rf = (list(pol.lstm_actor.core_rf.parameters())
          + list(pol.lstm_critic.core_rf.parameters())
          + list(pol.mlp_extractor_rf.parameters())
          + list(pol.action_net_rf.parameters())
          + list(pol.value_net_rf.parameters()) + [pol.log_std_rf])
    rb = (list(pol.lstm_actor.core_rb.parameters())
          + list(pol.lstm_critic.core_rb.parameters())
          + list(pol.mlp_extractor_rb.parameters())
          + list(pol.action_net_rb.parameters())
          + list(pol.value_net_rb.parameters()) + [pol.log_std_rb])
    rc = (list(pol.lstm_actor.core_rc.parameters())
          + list(pol.lstm_critic.core_rc.parameters())
          + list(pol.mlp_extractor_rc.parameters())
          + list(pol.action_net_rc.parameters())
          + list(pol.value_net_rc.parameters()) + [pol.log_std_rc])
    return {"a": a, "b": b, "rf": rf, "rb": rb, "rc": rc}


@pytest.mark.parametrize("slot,kind,hot", [
    (WALK, None, "a"), (HOLD, None, "b"), (RISE, FLAT, "rf"),
    (RISE, BRIDGE, "rb"), (RISE, CROUCH, "rc"),
])
def test_gradient_isolation(slot, kind, hot):
    from sb3_contrib.common.recurrent.type_aliases import RNNStates

    model = _rke_model()
    pol = model.policy
    obs = th.as_tensor(np.stack([np.concatenate([
        np.random.default_rng(i).uniform(-1, 1, N_CORE).astype(np.float32),
        _kind_tail(kind), _mode_tail(slot)]) for i in range(8)]))
    actions = th.zeros(8, 2)
    h = th.zeros(5, 8, 8)
    states = RNNStates((h, th.zeros_like(h)), (h.clone(), th.zeros_like(h)))
    starts = th.ones(8)

    groups = _rke_param_groups(pol)
    for plist in groups.values():
        for p in plist:
            p.grad = None
    values, log_prob, entropy = pol.evaluate_actions(
        obs, actions, states, starts)
    (values.sum() + log_prob.sum()).backward()

    for name, plist in groups.items():
        norm = sum(float(p.grad.abs().sum())
                   for p in plist if p.grad is not None)
        if name == hot:
            assert norm > 0.0, f"active expert {name!r} received no gradient"
        else:
            assert norm == 0.0, (
                f"gradient leaked into gated-out expert {name!r} "
                f"(slot={slot}, kind={kind}, norm={norm})")


def test_save_load_stateful_roundtrip(tmp_path):
    from sb3_contrib import RecurrentPPO

    model = _rke_model()
    model.learn(64)
    zip_path = tmp_path / "rke.zip"
    model.save(zip_path)
    assert is_recurrent_checkpoint(zip_path)
    loaded = load_checkpoint_auto(zip_path)
    assert isinstance(loaded, RecurrentPPO)
    assert isinstance(loaded.policy, RiseKindGruActorCriticPolicy)

    rng = np.random.default_rng(7)
    obs_seq = []
    cases = [(WALK, None), (HOLD, None), (RISE, FLAT),
             (RISE, BRIDGE), (RISE, CROUCH)]
    for i in range(10):
        slot, kind = cases[i % len(cases)]
        obs_seq.append(np.concatenate([
            rng.uniform(-1, 1, N_CORE).astype(np.float32),
            _kind_tail(kind), _mode_tail(slot)]))
    for m in (model, loaded):
        m.policy.set_training_mode(False)

    def rollout(m):
        acts, state = [], None
        ep_start = np.ones((1,), dtype=bool)
        for o in obs_seq:
            a, state = m.predict(o, state=state, episode_start=ep_start,
                                 deterministic=True)
            ep_start = np.zeros((1,), dtype=bool)
            acts.append(a)
        assert state[0].shape == (5, 1, 8), \
            f"rise-experts state facade broken: {state[0].shape}"
        return np.stack(acts)

    np.testing.assert_array_equal(rollout(model), rollout(loaded))


def test_bptt_forward_matches_entry_points():
    model = _rke_model()
    pol = model.policy
    pol.set_training_mode(False)
    t_len, b = 5, 3
    rng = np.random.default_rng(3)
    cases = [(WALK, None), (RISE, BRIDGE), (HOLD, None)]
    obs = np.zeros((t_len, b, N_CORE + _N_RISE_KIND + N_MODE_OBS),
                   dtype=np.float32)
    for k in range(b):
        slot, kind = cases[k]
        for t in range(t_len):
            obs[t, k] = np.concatenate([
                rng.uniform(-1, 1, N_CORE).astype(np.float32),
                _kind_tail(kind), _mode_tail(slot)])
    feats = th.as_tensor(obs)
    with th.no_grad():
        mu_bptt, _ = pol.bptt_forward(feats)
        flat = feats.transpose(0, 1).reshape(t_len * b, -1)
        starts = th.zeros(t_len * b)
        h = th.zeros(5, b, 8)
        dist, _ = pol.get_distribution(flat, (h, th.zeros_like(h)), starts)
        mu_ref = dist.distribution.mean.reshape(b, t_len, -1).transpose(0, 1)
    assert th.allclose(mu_bptt, mu_ref, atol=1e-5), \
        "bptt_forward diverges from the production sequence path"


def test_log_std_core_targeting():
    pol = _rke_model().policy
    stds = pol._log_stds()
    assert len(stds) == 5
    assert stds[0] is pol.log_std
    assert stds[1] is pol.log_std_b
    assert stds[2] is pol.log_std_rf
    assert stds[3] is pol.log_std_rb
    assert stds[4] is pol.log_std_rc
    assert pol._log_std_core("walk") == (pol.log_std,)
    assert pol._log_std_core("stance") == (pol.log_std_b,)
    assert pol._log_std_core("rise_flat") == (pol.log_std_rf,)
    assert pol._log_std_core("rise_bridge") == (pol.log_std_rb,)
    assert pol._log_std_core("rise_crouch") == (pol.log_std_rc,)
    assert pol._log_std_core("nonsense") is None


# ---------------------------------------------------------------------------
# dual_to_rise_experts_transplant
# ---------------------------------------------------------------------------

def test_transplant_wrong_types_refused():
    from sb3_contrib import RecurrentPPO

    old = _dual_model_narrow()
    not_rke = RecurrentPPO(
        GruActorCriticPolicy, _TinyRiseEnv(),
        n_steps=8, batch_size=16, n_epochs=1, seed=0, device="cpu",
        policy_kwargs=dict(lstm_hidden_size=8, net_arch=[16]))
    with pytest.raises(SystemExit, match="RiseKindGruActorCriticPolicy"):
        dual_to_rise_experts_transplant(old, not_rke)

    rke = _rke_model()
    not_dual = RecurrentPPO(
        GruActorCriticPolicy, _TinyRiseEnv(),
        n_steps=8, batch_size=16, n_epochs=1, seed=0, device="cpu",
        policy_kwargs=dict(lstm_hidden_size=8, net_arch=[16]))
    with pytest.raises(SystemExit, match="DualGruActorCriticPolicy"):
        dual_to_rise_experts_transplant(not_dual, rke)


def test_transplant_same_width_core_b_seeds_rise_experts():
    """No obs widening (n_pad=0): core_a/core_b verbatim, rf/rb/rc each
    a COPY of core_b (independent storage)."""
    from sb3_contrib import RecurrentPPO

    class _SameWidthRiseEnv(_TinyRiseEnv):
        pass

    old = _dual_model_narrow()
    old.learn(64)

    class _NarrowLikeNew(gym.Env):
        # Same width as the Dual parent -- exercises the n_pad=0 path.
        def __init__(self):
            self.observation_space = spaces.Box(
                -1, 1, (N_CORE + N_MODE_OBS,), dtype=np.float32)
            self.action_space = spaces.Box(-1, 1, (2,), dtype=np.float32)

        def reset(self, *, seed=None, options=None):
            return np.zeros(N_CORE + N_MODE_OBS, np.float32), {}

        def step(self, action):
            return np.zeros(N_CORE + N_MODE_OBS, np.float32), 0.0, False, \
                True, {}

    new = RecurrentPPO(
        RiseKindGruActorCriticPolicy, _NarrowLikeNew(),
        n_steps=8, batch_size=16, n_epochs=1, seed=1, device="cpu",
        policy_kwargs=dict(lstm_hidden_size=8, net_arch=[16]))
    copied = dual_to_rise_experts_transplant(old, new, n_pad=0)
    assert "log_std_rf" in copied and "log_std_rb" in copied \
        and "log_std_rc" in copied
    op, npd = old.policy, new.policy
    for pa_old, pa_new in zip(op.lstm_actor.core_a.parameters(),
                              npd.lstm_actor.core_a.parameters()):
        assert th.equal(pa_old, pa_new)
    for pb_old, pb_new in zip(op.lstm_actor.core_b.parameters(),
                              npd.lstm_actor.core_b.parameters()):
        assert th.equal(pb_old, pb_new)
    for suf in ("rf", "rb", "rc"):
        core = getattr(npd.lstm_actor, f"core_{suf}")
        for pb_old, pr_new in zip(op.lstm_actor.core_b.parameters(),
                                  core.parameters()):
            assert th.equal(pb_old, pr_new)
    assert th.equal(op.log_std, npd.log_std_rf)
    assert th.equal(op.log_std, npd.log_std)
    # Independent storage.
    with th.no_grad():
        npd.log_std_rf.data.add_(1.0)
    assert not th.equal(op.log_std, npd.log_std_rf)


def test_transplant_with_obs_pad_matches_parent_at_zero_pad():
    """Real-world shape: old Dual has NO rise-kind-gate columns, new
    RiseKindGru is 3 dims wider (inserted right before mode_onehot).
    Zero-padded transplant must reproduce the parent's exact forward
    pass on core_a/core_b when the new columns are held at zero, and
    seed rf/rb/rc from the PADDED core_b (not the raw pre-pad one)."""
    from sb3_contrib import RecurrentPPO

    old = _dual_model_narrow()
    old.learn(64)
    n_old = N_CORE + N_MODE_OBS
    insert_at = N_CORE  # right before the old obs's own mode tail

    class _WideRiseEnv(gym.Env):
        def __init__(self):
            self.observation_space = spaces.Box(
                -1, 1, (n_old + _N_RISE_KIND,), dtype=np.float32)
            self.action_space = spaces.Box(-1, 1, (2,), dtype=np.float32)

        def reset(self, *, seed=None, options=None):
            return np.zeros(n_old + _N_RISE_KIND, np.float32), {}

        def step(self, action):
            return np.zeros(n_old + _N_RISE_KIND, np.float32), 0.0, \
                False, True, {}

    new = RecurrentPPO(
        RiseKindGruActorCriticPolicy, _WideRiseEnv(),
        n_steps=8, batch_size=16, n_epochs=1, seed=1, device="cpu",
        policy_kwargs=dict(lstm_hidden_size=8, net_arch=[16]))
    copied = dual_to_rise_experts_transplant(
        old, new, n_pad=_N_RISE_KIND, insert_at=insert_at)
    assert "lstm_actor.core_rf.weight_ih_l0" in copied

    op, npd = old.policy, new.policy
    op.set_training_mode(False)
    npd.set_training_mode(False)
    rng = np.random.default_rng(11)
    core_vals = rng.uniform(-1, 1, N_CORE).astype(np.float32)
    for slot in (WALK, HOLD):
        old_obs = np.concatenate([core_vals, _mode_tail(slot)])
        new_obs = np.concatenate([
            core_vals[:insert_at], np.zeros(_N_RISE_KIND, np.float32),
            core_vals[insert_at:], _mode_tail(slot)])
        h_old = th.zeros(2, 1, 8)
        h_new = th.zeros(5, 1, 8)
        starts = th.ones(1)
        with th.no_grad():
            d_old, _ = op.get_distribution(
                th.as_tensor(old_obs[None]), (h_old, th.zeros_like(h_old)),
                starts)
            d_new, _ = npd.get_distribution(
                th.as_tensor(new_obs[None]), (h_new, th.zeros_like(h_new)),
                starts)
        assert th.allclose(d_old.distribution.mean, d_new.distribution.mean,
                           atol=1e-5), f"zero-pad divergence at slot={slot}"

    # rf/rb/rc seeded from the PADDED core_b, i.e. identical to the
    # new model's own (post-transplant) core_b -- not the old model's
    # raw (narrower) one, which would be a shape mismatch anyway.
    for suf in ("rf", "rb", "rc"):
        core = getattr(npd.lstm_actor, f"core_{suf}")
        for pb_new, pr_new in zip(npd.lstm_actor.core_b.parameters(),
                                  core.parameters()):
            assert th.equal(pb_new, pr_new)


def test_transplant_log_std_split_source_seeds_from_log_std_b():
    """Real-world shape: the Dual parent this lever actually targets
    was trained with --gru-dual-log-std-split (core_b's exploration
    std independently annealed for rise/hold/lower stability). The
    rise-kind experts must inherit THAT value, not core_a's unrelated
    log_std, and RiseKindGru's own (always-present) log_std_b must
    equal the source's real log_std_b, not a copy of log_std."""
    from sb3_contrib import RecurrentPPO

    old = _dual_model_narrow(log_std_split=True)
    with th.no_grad():
        # Make core_a's and core_b's log_std DISTINGUISHABLE so a
        # wrong source mapping (log_std instead of log_std_b) is
        # caught, not accidentally masked by equal initial values.
        old.policy.log_std.data.fill_(-1.0)
        old.policy.log_std_b.data.fill_(-4.0)

    class _NarrowLikeNew(gym.Env):
        def __init__(self):
            self.observation_space = spaces.Box(
                -1, 1, (N_CORE + N_MODE_OBS,), dtype=np.float32)
            self.action_space = spaces.Box(-1, 1, (2,), dtype=np.float32)

        def reset(self, *, seed=None, options=None):
            return np.zeros(N_CORE + N_MODE_OBS, np.float32), {}

        def step(self, action):
            return np.zeros(N_CORE + N_MODE_OBS, np.float32), 0.0, False, \
                True, {}

    new = RecurrentPPO(
        RiseKindGruActorCriticPolicy, _NarrowLikeNew(),
        n_steps=8, batch_size=16, n_epochs=1, seed=1, device="cpu",
        policy_kwargs=dict(lstm_hidden_size=8, net_arch=[16]))
    copied = dual_to_rise_experts_transplant(old, new, n_pad=0)
    assert "log_std_b" in copied
    npd = new.policy
    assert th.equal(npd.log_std, old.policy.log_std)
    assert th.equal(npd.log_std_b, old.policy.log_std_b)
    for suf in ("rf", "rb", "rc"):
        assert th.equal(getattr(npd, f"log_std_{suf}"), old.policy.log_std_b), \
            f"log_std_{suf} should inherit core_b's SPLIT std, not core_a's"
