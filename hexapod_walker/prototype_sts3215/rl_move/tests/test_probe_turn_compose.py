"""_ComposedPolicy (probe_turn_compose.py) -- mechanics-only unit tests.

No mujoco, no checkpoint, no physics: a fake env/model exercise the
tick-classification and action-substitution logic in isolation
(<< 1s). See probe_turn_compose.py's module docstring for the WHY
(amp track turn-in-place freeze, 6/6 RL-side levers closed 09-11) and
the real-checkpoint validation this unit-tests the mechanics of
(logs/probe_turn_compose/capsevprob70_canary2m_tip1/report.json:
raw gait_valid=False/sacrificed 4 legs vs composed gait_valid=True/
sacrificed none, same seeds, mean|wz|_turn ~3.5x higher).
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from rl_move.sim.probe_turn_compose import _ComposedPolicy


class _FakeModel:
    def __init__(self):
        self.reset_calls = 0
        self.action = np.full(18, 0.25, dtype=np.float32)

    def predict(self, obs, deterministic=True):
        return self.action.copy(), None

    def reset(self):
        self.reset_calls += 1


class _FakeEnv:
    """Only the attributes/methods _ComposedPolicy touches."""

    def __init__(self, vx_ref, vy_ref, wz_ref):
        self._goal = SimpleNamespace(vx_ref=vx_ref, vy_ref=vy_ref,
                                     wz_ref=wz_ref)
        self._step_i = 3
        self.dt = 0.02

    def _current_goal(self):
        return self._goal

    def _body_wz(self):
        return 0.0


def test_passthrough_when_compose_false_even_on_turn_tick():
    env = _FakeEnv(vx_ref=0.0, vy_ref=0.0, wz_ref=0.25)  # turn-in-place
    model = _FakeModel()
    pol = _ComposedPolicy(model, env, compose=False)
    act, _ = pol.predict(np.zeros(4))
    np.testing.assert_array_equal(act, model.action)
    assert pol.turn_ticks == 1  # still counted for reporting
    assert pol.total_ticks == 1


def test_compose_true_substitutes_action_on_turn_tick():
    env = _FakeEnv(vx_ref=0.0, vy_ref=0.0, wz_ref=0.25)
    model = _FakeModel()
    pol = _ComposedPolicy(model, env, compose=True)
    act, _ = pol.predict(np.zeros(4))
    assert not np.array_equal(act, model.action), (
        "composed action must differ from the raw policy action on a "
        "live turn-in-place tick")
    assert pol.turn_ticks == 1


def test_compose_true_passthrough_on_straight_walk_tick():
    env = _FakeEnv(vx_ref=0.08, vy_ref=0.0, wz_ref=0.0)  # straight walk
    model = _FakeModel()
    pol = _ComposedPolicy(model, env, compose=True)
    act, _ = pol.predict(np.zeros(4))
    np.testing.assert_array_equal(act, model.action)
    assert pol.turn_ticks == 0
    assert pol.walk_ticks == 1


def test_compose_true_passthrough_on_combined_tick():
    # vx_ref!=0 AND wz_ref!=0 is NOT the turn-in-place gate (matches
    # walk_task.py's own s_ref<=1e-3 condition) -- combined ticks stay
    # on the real policy.
    env = _FakeEnv(vx_ref=0.08, vy_ref=0.0, wz_ref=0.25)
    model = _FakeModel()
    pol = _ComposedPolicy(model, env, compose=True)
    act, _ = pol.predict(np.zeros(4))
    np.testing.assert_array_equal(act, model.action)
    assert pol.turn_ticks == 0


def test_compose_true_passthrough_on_pure_hold_tick():
    # vx_ref==0 AND wz_ref==0 (a true stop/hold) is neither walk nor
    # turn-in-place -- zero is the correct commanded behavior, must not
    # be routed to the scripted teacher.
    env = _FakeEnv(vx_ref=0.0, vy_ref=0.0, wz_ref=0.0)
    model = _FakeModel()
    pol = _ComposedPolicy(model, env, compose=True)
    act, _ = pol.predict(np.zeros(4))
    np.testing.assert_array_equal(act, model.action)
    assert pol.turn_ticks == 0
    assert pol.walk_ticks == 1


def test_reset_clears_counters_and_forwards_to_model():
    env = _FakeEnv(vx_ref=0.0, vy_ref=0.0, wz_ref=0.25)
    model = _FakeModel()
    pol = _ComposedPolicy(model, env, compose=True)
    pol.predict(np.zeros(4))
    assert pol.turn_ticks == 1
    pol.reset()
    assert pol.turn_ticks == 0
    assert pol.total_ticks == 0
    assert model.reset_calls == 1


def test_summary_reports_none_when_no_ticks_of_that_class_seen():
    env = _FakeEnv(vx_ref=0.08, vy_ref=0.0, wz_ref=0.0)
    model = _FakeModel()
    pol = _ComposedPolicy(model, env, compose=True)
    pol.predict(np.zeros(4))
    s = pol.summary()
    assert s["turn_ticks"] == 0
    assert s["mean_abs_wz_turn"] is None
    assert s["mean_abs_wz_walk"] == 0.0
