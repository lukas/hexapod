"""``--height-weight-gain`` tests (standwalk STATUS 2026-09-24 ~06:0x
named lever, follow-up to the dagger2_riseextra FAIL/NULL result: more
rise-only DAgger episode DENSITY did not touch rise-height precision
because flat per-timestep action-MSE gives a badly-mis-terminated
episode no stronger a gradient than a near-perfect one).

Locks:
1. ``_height_err_mm``: None outside rise/lower context or when the
   env hasn't installed ``_z0``/``_h_target`` yet; the signed mm value
   otherwise, matching eval_modeseq.py's own
   ``chassis_z() - (_z0 + _h_target)`` convention exactly.
2. ``_bc_episode_weight``: exactly 1.0 whenever gain<=0, mode!="rise"
   or height_err_mm is None (every non-rise/off-lever path is a
   pure no-op); strictly increasing in |height_err_mm| otherwise.
3. ``train_student`` end to end: gain=0.0 (the default) reproduces the
   ORIGINAL uniform-mask action loss bit-for-bit even when episodes
   carry very different height_err_mm values (the new 5th field is
   inert until explicitly turned on); gain>0.0 measurably shifts the
   per-episode loss weighting the way the pure helper predicts.
4. ``mirror_augment_episodes``/``collect``/``collect_dagger`` all now
   emit/accept the 5-tuple ``(mode, obs, act, val, height_err_mm)`` —
   covered for collect/collect_dagger by a fake-env smoke check (no
   real MuJoCo stepping, mechanics only).

Follow-up (2026-09-24, hgain3 gate FAIL/NULL: gain=3.0 EPISODE-scalar
weighting left rise success flat -- 5-7/30 vs the unweighted parent's
6/30, same overshoot failure signature): ``--height-weight-mode
timestep`` weights each TICK by its own instantaneous height error
instead of the episode's terminal one.
5. ``_bc_step_weights``: dispatches to ``_bc_episode_weight`` unchanged
   for a scalar/None 5th field (bit-exact with the pre-existing
   lever); for an array, returns a same-length per-tick weight array,
   still an exact no-op whenever gain<=0 or mode!="rise".
6. ``collect``/``collect_dagger`` with ``height_err_series=True``
   capture a per-tick trace (not just the terminal value) for rise/
   lower episodes only, unaffected for every other mode.
7. ``train_student`` end to end with an array 5th field: measurably
   different loss trajectory than gain=0.0, and than the old episode-
   scalar shape given the SAME terminal error (proves the per-tick
   weight distribution, not just its mean, matters).
"""
from __future__ import annotations

import types

import numpy as np
import pytest
import torch as th

from gymnasium import spaces

from rl_move.sim.distill_gru import (
    _bc_episode_weight, _bc_step_weights, _height_err_mm, train_student,
)


def _lr_sched(_progress: float) -> float:
    return 3e-4


def _gru_policy(obs_dim: int = 12, act_dim: int = 4, hidden: int = 8):
    from rl_move.sim.gru_policy import GruActorCriticPolicy
    obs_sp = spaces.Box(-np.inf, np.inf, (obs_dim,), np.float32)
    act_sp = spaces.Box(-1.0, 1.0, (act_dim,), np.float32)
    return GruActorCriticPolicy(obs_sp, act_sp, _lr_sched,
                                lstm_hidden_size=hidden, n_lstm_layers=1,
                                enable_critic_lstm=True, shared_lstm=False)


def _fake_student(policy):
    return types.SimpleNamespace(policy=policy)


def _fake_episode(mode: str, t: int, obs_dim: int, act_dim: int,
                  height_err_mm, seed: int):
    rng = np.random.default_rng(seed)
    obs = rng.normal(size=(t, obs_dim)).astype(np.float32)
    act = rng.uniform(-1, 1, size=(t, act_dim)).astype(np.float32)
    val = rng.normal(size=(t,)).astype(np.float32)
    return (mode, obs, act, val, height_err_mm)


class _FakeEnv:
    """Bare-minimum stand-in for the attrs ``_height_err_mm`` reads —
    no MuJoCo, just the four fields sim_env.py installs on a real
    rise/lower reset."""

    def __init__(self, z0, h_target, chassis_z, chassis_bid=0):
        self._z0 = z0
        self._h_target = h_target
        self._chassis_bid = chassis_bid

        class _D:
            pass
        d = _D()
        d.xpos = np.zeros((chassis_bid + 1, 3))
        d.xpos[chassis_bid, 2] = chassis_z
        self.data = d


# ---------------------------------------------------------------- (1)

def test_height_err_mm_none_outside_rise_lower():
    env = _FakeEnv(z0=0.05, h_target=0.083, chassis_z=0.13)
    assert _height_err_mm(env, "walk") is None
    assert _height_err_mm(env, "hold") is None


def test_height_err_mm_none_when_attrs_missing():
    env = types.SimpleNamespace()  # no _z0/_h_target/_chassis_bid at all
    assert _height_err_mm(env, "rise") is None


def test_height_err_mm_matches_eval_modeseq_convention():
    # chassis_z - (z0 + h_target), in mm; z0=0.05, h_target=0.083 ->
    # target absolute height 0.133m; landed at 0.140m -> +7mm overshoot.
    env = _FakeEnv(z0=0.05, h_target=0.083, chassis_z=0.140)
    err = _height_err_mm(env, "rise")
    assert err is not None
    assert err == pytest.approx(7.0, abs=1e-6)
    # lower context uses the identical formula
    env2 = _FakeEnv(z0=0.05, h_target=-0.02, chassis_z=0.025)
    err2 = _height_err_mm(env2, "lower")
    assert err2 == pytest.approx(-5.0, abs=1e-6)


# ---------------------------------------------------------------- (2)

def test_bc_episode_weight_is_noop_when_gain_off_or_not_rise():
    assert _bc_episode_weight("rise", 40.0, gain=0.0) == 1.0
    assert _bc_episode_weight("walk", 40.0, gain=2.0) == 1.0
    assert _bc_episode_weight("lower", 40.0, gain=2.0) == 1.0
    assert _bc_episode_weight("rise", None, gain=2.0) == 1.0
    assert _bc_episode_weight("seq", None, gain=2.0) == 1.0


def test_bc_episode_weight_increases_with_height_err():
    small = _bc_episode_weight("rise", 5.0, gain=1.0)
    big = _bc_episode_weight("rise", 60.0, gain=1.0)
    assert small > 1.0
    assert big > small
    # exact linear formula: 1 + gain * |err| / 50mm
    assert small == pytest.approx(1.0 + 5.0 / 50.0)
    assert big == pytest.approx(1.0 + 60.0 / 50.0)
    # sign of the error must not matter
    assert _bc_episode_weight("rise", -60.0, gain=1.0) == big


# ---------------------------------------------------------------- (3)

def test_train_student_default_gain_reproduces_uniform_loss():
    """Two episodes with WILDLY different height_err_mm, gain=0.0:
    the run must be bit-for-bit identical to a manually-constructed
    all-1.0-weight batch (proves the new weighting plumbing is a true
    no-op at the documented default, not merely 'close')."""
    obs_dim, act_dim = 10, 4
    eps_lever_off = [
        _fake_episode("rise", 6, obs_dim, act_dim, 0.5, seed=1),
        _fake_episode("rise", 6, obs_dim, act_dim, 500.0, seed=2),
    ]
    # Identical obs/act/val, but height_err_mm stripped (as if the
    # lever's plumbing never existed) -- the gain=0.0 run over
    # eps_lever_off must match a run over this reference bit-for-bit.
    eps_reference = [(m, o, a, v, None) for m, o, a, v, _h in eps_lever_off]

    th.manual_seed(0)
    policy_a = _gru_policy(obs_dim, act_dim)
    th.manual_seed(0)
    policy_b = _gru_policy(obs_dim, act_dim)
    for p_a, p_b in zip(policy_a.parameters(), policy_b.parameters()):
        assert th.allclose(p_a, p_b)

    np.random.seed(42)
    loss_off = train_student(_fake_student(policy_a), eps_lever_off,
                             epochs=2, batch_eps=8,
                             height_weight_gain=0.0)
    np.random.seed(42)
    loss_ref = train_student(_fake_student(policy_b), eps_reference,
                             epochs=2, batch_eps=8,
                             height_weight_gain=0.0)
    assert loss_off == pytest.approx(loss_ref, abs=1e-9)
    for p_a, p_b in zip(policy_a.parameters(), policy_b.parameters()):
        assert th.allclose(p_a, p_b, atol=1e-7)


def test_train_student_nonzero_gain_changes_the_loss_trajectory():
    """Sanity: turning the lever ON with a real height_err_mm spread
    must produce a DIFFERENT trained policy than gain=0.0 (mechanics
    wired end to end, not a dead parameter)."""
    obs_dim, act_dim = 10, 4
    eps = [
        _fake_episode("rise", 6, obs_dim, act_dim, 2.0, seed=1),
        _fake_episode("rise", 6, obs_dim, act_dim, 80.0, seed=2),
    ]

    th.manual_seed(0)
    policy_off = _gru_policy(obs_dim, act_dim)
    th.manual_seed(0)
    policy_on = _gru_policy(obs_dim, act_dim)

    np.random.seed(7)
    train_student(_fake_student(policy_off), eps, epochs=3, batch_eps=8,
                  height_weight_gain=0.0)
    np.random.seed(7)
    train_student(_fake_student(policy_on), eps, epochs=3, batch_eps=8,
                  height_weight_gain=2.0)

    diffs = [float((p1 - p2).detach().abs().max())
            for p1, p2 in zip(policy_off.parameters(),
                              policy_on.parameters())]
    assert max(diffs) > 1e-6, "nonzero height_weight_gain had no effect"


def test_train_student_runs_on_mixed_none_and_real_height_err():
    """A dataset mixing seq episodes (height_err_mm=None), non-rise
    single-mode episodes and real rise height_err_mm values must not
    crash (the exact mixture main() assembles: sequence demos + the
    single-mode initial pass + the rise-only extra pass)."""
    obs_dim, act_dim = 10, 4
    eps = [
        ("seq", *_fake_episode("seq", 5, obs_dim, act_dim, None, 3)[1:]),
        _fake_episode("walk", 5, obs_dim, act_dim, None, seed=4),
        _fake_episode("rise", 5, obs_dim, act_dim, 33.0, seed=5),
    ]
    policy = _gru_policy(obs_dim, act_dim)
    loss = train_student(_fake_student(policy), eps, epochs=1,
                         batch_eps=8, height_weight_gain=1.0)
    assert np.isfinite(loss)


# ---------------------------------------------------------------- (5)

def test_bc_step_weights_dispatches_scalar_unchanged():
    for mode, herr, gain in [("rise", 40.0, 0.0), ("walk", 40.0, 2.0),
                             ("lower", 40.0, 2.0), ("rise", None, 2.0),
                             ("rise", 60.0, 1.0), ("rise", -60.0, 1.0)]:
        assert (_bc_step_weights(mode, herr, gain)
                == _bc_episode_weight(mode, herr, gain))


def test_bc_step_weights_array_is_noop_when_gain_off_or_not_rise():
    series = np.array([5.0, 60.0, 0.0, 90.0], dtype=np.float32)
    for mode, gain in [("rise", 0.0), ("walk", 2.0), ("lower", 2.0),
                       ("hold", 5.0)]:
        w = _bc_step_weights(mode, series, gain)
        assert isinstance(w, np.ndarray) and w.shape == series.shape
        assert np.allclose(w, 1.0)


def test_bc_step_weights_array_matches_per_tick_formula():
    series = np.array([5.0, 60.0, -60.0], dtype=np.float32)
    w = _bc_step_weights("rise", series, gain=1.0)
    assert w == pytest.approx(1.0 + np.abs(series) / 50.0, abs=1e-6)
    # a series with the SAME terminal value but a different early
    # trace must NOT collapse to the same weight vector -- proves the
    # per-tick shape is actually used, not just the last element.
    series2 = np.array([500.0, 500.0, -60.0], dtype=np.float32)
    w2 = _bc_step_weights("rise", series2, gain=1.0)
    assert w2[0] != pytest.approx(w[0])
    assert w2[-1] == pytest.approx(w[-1])  # same terminal error


# ---------------------------------------------------------------- (6)

class _FakePolicy:
    def predict_values(self, _obs_tensor):
        return th.zeros(1, 1)


class _FakeTeacher:
    """Deterministic zero-action teacher/value pair for collect/
    collect_dagger smoke tests -- no real policy, just the two calls
    ``_teacher_act_value``/``student.predict`` need to succeed."""

    def __init__(self):
        self.policy = _FakePolicy()

    def predict(self, obs, deterministic=True, state=None,
               episode_start=None):
        act = np.zeros(4, dtype=np.float32)
        return act, state


class _FakeCollectEnv:
    """Minimal env stand-in for collect()/collect_dagger()'s own
    stepping loop: fixed-length rise episode, chassis height ramping
    linearly toward the target so consecutive ticks have DIFFERENT
    height errors (the property height_err_series is supposed to
    capture)."""

    def __init__(self, mode="rise", n_steps=5, obs_dim=10, act_dim=4):
        self.mode, self.n_steps, self._t = mode, n_steps, 0
        self.obs_dim, self.act_dim = obs_dim, act_dim
        self._z0, self._h_target, self._chassis_bid = 0.05, 0.083, 0

        class _D:
            pass
        self.data = _D()
        self.data.xpos = np.zeros((1, 3))
        self.data.xpos[0, 2] = self._z0

    def reset(self, *_a, **_kw):
        self._t = 0
        self.data.xpos[0, 2] = self._z0
        return np.zeros(self.obs_dim, dtype=np.float32), \
            {"goal_mode": self.mode}

    def step(self, _act):
        self._t += 1
        # chassis height climbs a different amount each tick -> a
        # non-constant per-tick height-error trace.
        self.data.xpos[0, 2] = self._z0 + 0.01 * self._t
        done = self._t >= self.n_steps
        return (np.zeros(self.obs_dim, dtype=np.float32), 0.0, done,
                False, {})

    def set_goal_mix(self, _mix):
        pass


def test_collect_height_err_series_captures_per_tick_trace():
    from rl_move.sim.distill_gru import collect
    env = _FakeCollectEnv(mode="rise", n_steps=5)
    teacher = _FakeTeacher()
    rng = np.random.default_rng(0)
    eps = collect({"rise": env}, {"stance": (teacher, env.obs_dim),
                                  "walk": (teacher, env.obs_dim)},
                 {"rise": 1}, stochastic_frac=0.0, rng=rng,
                 height_err_series=True)
    assert len(eps) == 1
    mode, obs, act, val, h_err = eps[0]
    assert mode == "rise"
    assert isinstance(h_err, np.ndarray)
    assert h_err.shape[0] == obs.shape[0] == 5
    # strictly increasing height (climbing toward target) -> strictly
    # increasing (less negative / more overshot) height error trace.
    assert np.all(np.diff(h_err) > 0)


def test_collect_height_err_series_off_keeps_scalar():
    from rl_move.sim.distill_gru import collect
    env = _FakeCollectEnv(mode="rise", n_steps=5)
    teacher = _FakeTeacher()
    rng = np.random.default_rng(0)
    eps = collect({"rise": env}, {"stance": (teacher, env.obs_dim),
                                  "walk": (teacher, env.obs_dim)},
                 {"rise": 1}, stochastic_frac=0.0, rng=rng,
                 height_err_series=False)
    mode, obs, act, val, h_err = eps[0]
    assert h_err is None or np.ndim(h_err) == 0


def test_collect_dagger_height_err_series_captures_per_tick_trace():
    from rl_move.sim.distill_gru import collect_dagger
    env = _FakeCollectEnv(mode="rise", n_steps=4)
    teacher = _FakeTeacher()
    student = types.SimpleNamespace(predict=teacher.predict)
    eps = collect_dagger({"rise": env},
                         student,
                         {"stance": (teacher, env.obs_dim),
                          "walk": (teacher, env.obs_dim)},
                         {"rise": 1}, height_err_series=True)
    mode, obs, act, val, h_err = eps[0]
    assert mode == "rise"
    assert isinstance(h_err, np.ndarray) and h_err.shape[0] == 4
    assert np.all(np.diff(h_err) > 0)


# ---------------------------------------------------------------- (7)

def test_train_student_timestep_weight_differs_from_episode_weight():
    """Two rise episodes with the SAME terminal height_err_mm (so the
    old episode-scalar weight is identical either way) but different
    early-trace shapes must train DIFFERENTLY when given as a
    per-tick array vs collapsed to that one terminal scalar -- proves
    the per-tick distribution (not just its endpoint) reaches the
    gradient."""
    obs_dim, act_dim = 10, 4
    terminal = 80.0
    ep_a_series = np.array([80.0, 80.0, 80.0, 80.0, 80.0, 80.0],
                           dtype=np.float32)
    ep_b_series = np.array([1.0, 2.0, 3.0, 5.0, 40.0, 80.0],
                           dtype=np.float32)

    def _mk(series):
        rng = np.random.default_rng(9)
        obs = rng.normal(size=(6, obs_dim)).astype(np.float32)
        act = rng.uniform(-1, 1, size=(6, act_dim)).astype(np.float32)
        val = rng.normal(size=(6,)).astype(np.float32)
        return ("rise", obs, act, val, series)

    eps_flat = [_mk(ep_a_series)]
    eps_ramped = [_mk(ep_b_series)]
    eps_scalar = [("rise", eps_flat[0][1], eps_flat[0][2], eps_flat[0][3],
                  terminal)]

    def _train(eps):
        th.manual_seed(0)
        policy = _gru_policy(obs_dim, act_dim)
        np.random.seed(3)
        train_student(_fake_student(policy), eps, epochs=3, batch_eps=8,
                      height_weight_gain=1.0)
        return policy

    p_flat = _train(eps_flat)
    p_ramped = _train(eps_ramped)
    p_scalar = _train(eps_scalar)

    # flat-constant-80 series must reproduce the old scalar-80 result
    # exactly (both are a uniform weight of 1+80/50 every tick).
    for p1, p2 in zip(p_flat.parameters(), p_scalar.parameters()):
        assert th.allclose(p1, p2, atol=1e-7)
    # a ramped trace (same terminal 80, different early shape) must
    # diverge from the flat/scalar result.
    diffs = [float((p1 - p2).detach().abs().max())
            for p1, p2 in zip(p_flat.parameters(), p_ramped.parameters())]
    assert max(diffs) > 1e-6
