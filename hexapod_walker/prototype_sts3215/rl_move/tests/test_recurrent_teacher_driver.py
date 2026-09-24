"""RecurrentTeacherDriver / wrap_teacher_driver (2026-09-24, standwalk
stage-2 distillation-tool audit).

Found auditing distill_gru.py before funding the row-3 stand+walk
distillation task (both current champions are GRU checkpoints): every
teacher-driving loop called bare ``teacher.predict(obs)`` (silently
re-zeroing hidden state every tick -- the same "lobotomy" bug
RecurrentPredictor fixed for eval/drive tools 2026-08-28) AND
``teacher.policy.predict_values(obs_tensor)`` with no
lstm_states/episode_starts at all -- RecurrentActorCriticPolicy.
predict_values *requires* both positionally, so this does not degrade
silently, it raises TypeError the instant a GRU teacher is used.
RecurrentPredictor alone does not fix this either: its .predict() only
threads the ACTOR's hidden state, never the critic's own separate LSTM
(enable_critic_lstm=True is RecurrentPPO's default). These tests lock:

1. wrap_teacher_driver passes a plain (non-recurrent) PPO through
   unchanged (identity, no wrapping overhead/behavior change);
2. for a RecurrentPPO, .step() returns a real (action, value) pair
   whose ACTION matches manual policy.forward threading exactly;
3. .step()'s VALUE actually depends on the threaded critic state (it
   diverges from a naive "always pass a fresh zero state" per-tick
   value read, once memory accumulates) -- the exact defect being
   fixed;
4. .reset() clears both threaded states: the first post-reset call
   reproduces the original step-0 (action, value) pair exactly;
5. .predict() (action-only convenience) returns the same action as
   .step() while still advancing the SAME shared state pair (a caller
   that calls .predict() then .step() must not have inconsistent
   history).
"""
from __future__ import annotations

import numpy as np


import gymnasium as gym


def _tiny_env():
    return gym.make("Pendulum-v1")


def _tiny_recurrent(seed=0):
    from sb3_contrib import RecurrentPPO
    return RecurrentPPO(
        "MlpLstmPolicy", _tiny_env(), seed=seed, n_steps=8, batch_size=8,
        policy_kwargs=dict(lstm_hidden_size=16, net_arch=[16]),
        device="cpu")


def test_plain_ppo_passthrough_identity():
    from stable_baselines3 import PPO
    from rl_move.sim.gru_policy import wrap_teacher_driver
    m = PPO("MlpPolicy", _tiny_env(), seed=0, n_steps=8, batch_size=8,
            policy_kwargs=dict(net_arch=[16]), device="cpu")
    assert wrap_teacher_driver(m) is m


def test_recurrent_dispatches_to_driver():
    from rl_move.sim.gru_policy import (RecurrentTeacherDriver,
                                        wrap_teacher_driver)
    m = _tiny_recurrent()
    wrapped = wrap_teacher_driver(m)
    assert isinstance(wrapped, RecurrentTeacherDriver)
    assert wrapped.observation_space == m.observation_space
    assert wrapped.action_space == m.action_space


def test_step_action_matches_manual_forward_threading():
    import torch as th
    from sb3_contrib.common.recurrent.type_aliases import RNNStates
    from rl_move.sim.gru_policy import wrap_teacher_driver

    m = _tiny_recurrent()
    driver = wrap_teacher_driver(m)
    rng = np.random.default_rng(0)
    obs_seq = [rng.normal(size=3).astype(np.float32) for _ in range(6)]

    got_actions = []
    for o in obs_seq:
        a, _v = driver.step(o, deterministic=True)
        got_actions.append(np.asarray(a).copy())

    # Manual reference: thread (pi, vf) states through policy.forward
    # directly, the same call RecurrentPPO's own rollout collection
    # makes.
    policy = m.policy
    shape = policy.lstm_hidden_state_shape
    z = th.zeros(shape)
    states = RNNStates((z, z.clone()), (z.clone(), z.clone()))
    starts = th.ones((1,), dtype=th.float32)
    want_actions = []
    for o in obs_seq:
        obs_t, _ = policy.obs_to_tensor(o[None])
        with th.no_grad():
            actions, _values, _lp, states = policy.forward(
                obs_t, states, starts, deterministic=True)
        starts = th.zeros((1,), dtype=th.float32)
        want_actions.append(actions.cpu().numpy().reshape(-1).copy())

    for g, w in zip(got_actions, want_actions):
        np.testing.assert_array_equal(np.asarray(g).reshape(-1), w)


def test_value_depends_on_threaded_critic_state():
    """The exact bug being fixed: predict_values(obs) alone (no
    lstm_states) either crashes (missing required args) or -- if a
    caller patched around that by re-zeroing state every call -- would
    read a critic that never saw the episode. Confirm .step()'s value
    actually moves once memory accumulates, by contrasting against a
    stateless per-tick value read (fresh zero critic state every
    tick, matching what a naive caller would get if it didn't crash)."""
    import torch as th
    from sb3_contrib.common.recurrent.type_aliases import RNNStates
    from rl_move.sim.gru_policy import wrap_teacher_driver

    m = _tiny_recurrent(seed=1)
    driver = wrap_teacher_driver(m)
    rng = np.random.default_rng(1)
    obs_seq = [rng.normal(size=3).astype(np.float32) for _ in range(8)]

    threaded_vals = [driver.step(o, deterministic=True)[1] for o in obs_seq]

    policy = m.policy
    shape = policy.lstm_hidden_state_shape
    stateless_vals = []
    for o in obs_seq:
        z = th.zeros(shape)
        states = RNNStates((z, z.clone()), (z.clone(), z.clone()))
        starts = th.ones((1,), dtype=th.float32)  # always "new episode"
        obs_t, _ = policy.obs_to_tensor(o[None])
        with th.no_grad():
            _a, values, _lp, _s = policy.forward(
                obs_t, states, starts, deterministic=True)
        stateless_vals.append(float(values.item()))

    # step 0 agrees (both start from a zero state)...
    assert abs(threaded_vals[0] - stateless_vals[0]) < 1e-6
    # ...but must diverge once memory accumulates (untrained but
    # nonzero recurrent weights).
    diffs = [abs(t - s) for t, s in
             zip(threaded_vals[1:], stateless_vals[1:])]
    assert max(diffs) > 1e-6, (
        "critic state threading had no effect -- driver is not "
        f"carrying the critic's own hidden state (max diff "
        f"{max(diffs):.2e})")


def test_reset_restores_step0_pair():
    from rl_move.sim.gru_policy import wrap_teacher_driver

    m = _tiny_recurrent(seed=2)
    driver = wrap_teacher_driver(m)
    rng = np.random.default_rng(2)
    obs_seq = [rng.normal(size=3).astype(np.float32) for _ in range(5)]
    a0, v0 = driver.step(obs_seq[0], deterministic=True)
    a0, v0 = np.asarray(a0).copy(), v0
    for o in obs_seq[1:]:
        driver.step(o, deterministic=True)
    driver.reset()
    a0b, v0b = driver.step(obs_seq[0], deterministic=True)
    np.testing.assert_array_equal(np.asarray(a0b), a0)
    assert abs(v0b - v0) < 1e-6


def test_predict_matches_step_action_and_shares_state():
    from rl_move.sim.gru_policy import wrap_teacher_driver

    m = _tiny_recurrent(seed=3)
    driver = wrap_teacher_driver(m)
    rng = np.random.default_rng(3)
    obs_seq = [rng.normal(size=3).astype(np.float32) for _ in range(4)]

    # Interleave .predict() and .step() calls on the SAME object; the
    # action from .predict() at tick i must equal what .step() would
    # have returned (same forward call under the hood), and the shared
    # state must keep advancing consistently either way.
    a_predict, _ = driver.predict(obs_seq[0], deterministic=True)
    a_step, _v = driver.step(obs_seq[1], deterministic=True)

    driver.reset()
    a_step_ref, _ = driver.step(obs_seq[0], deterministic=True)
    driver_state_after_first = driver._states
    a_predict_ref, _ = driver.predict(obs_seq[1], deterministic=True)

    np.testing.assert_array_equal(np.asarray(a_predict), np.asarray(a_step_ref))
    np.testing.assert_array_equal(np.asarray(a_step), np.asarray(a_predict_ref))
    assert driver_state_after_first is not None
