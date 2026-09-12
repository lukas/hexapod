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
import pytest

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


# -- blend_s (smooth mode-transition window) --------------------------------
# todaypolicy STATUS 2026-09-12 named item (b): "build a real handoff
# (smooth blend over the mode-transition window, not the probe's hard
# switch)". blend_s=0.0 (the default, used by every prior recorded probe
# run) must stay bit-exact with the pre-blend hard switch; blend_s>0
# ramps linearly instead of snapping.

def test_blend_zero_matches_hard_switch_on_turn_tick():
    env = _FakeEnv(vx_ref=0.0, vy_ref=0.0, wz_ref=0.25)
    model = _FakeModel()
    hard = _ComposedPolicy(model, env, compose=True)
    blended0 = _ComposedPolicy(model, env, compose=True, blend_s=0.0)
    act_hard, _ = hard.predict(np.zeros(4))
    act_b0, _ = blended0.predict(np.zeros(4))
    np.testing.assert_array_equal(act_hard, act_b0)


def test_blend_zero_matches_hard_switch_on_walk_tick():
    env = _FakeEnv(vx_ref=0.08, vy_ref=0.0, wz_ref=0.0)
    model = _FakeModel()
    hard = _ComposedPolicy(model, env, compose=True)
    blended0 = _ComposedPolicy(model, env, compose=True, blend_s=0.0)
    act_hard, _ = hard.predict(np.zeros(4))
    act_b0, _ = blended0.predict(np.zeros(4))
    np.testing.assert_array_equal(act_hard, act_b0)
    np.testing.assert_array_equal(act_b0, model.action)


def test_blend_ramps_up_gradually_on_turn_entry():
    # dt=0.02 (from _FakeEnv), blend_s=0.1 -> 5 ticks to reach w=1.0.
    env = _FakeEnv(vx_ref=0.0, vy_ref=0.0, wz_ref=0.25)
    model = _FakeModel()
    pol = _ComposedPolicy(model, env, compose=True, blend_s=0.1)
    weights = []
    for _ in range(5):
        pol.predict(np.zeros(4))
        weights.append(pol._blend_w)
    # monotonically increasing, reaches exactly 1.0 at tick 5, never
    # overshoots.
    assert weights == sorted(weights)
    assert all(0.0 <= w <= 1.0 for w in weights)
    assert weights[0] == pytest.approx(0.2)
    assert weights[-1] == pytest.approx(1.0)
    # a mid-ramp tick's action must be a genuine convex combination:
    # closer to neither the pure-teacher nor pure-policy extreme.
    env2 = _FakeEnv(vx_ref=0.0, vy_ref=0.0, wz_ref=0.25)
    pol2 = _ComposedPolicy(model, env2, compose=True, blend_s=0.1)
    pol2.predict(np.zeros(4))  # w=0.2
    act, _ = pol2.predict(np.zeros(4))  # w=0.4
    assert not np.array_equal(act, model.action)


def test_blend_ramps_down_gradually_on_turn_exit_not_instant():
    env = _FakeEnv(vx_ref=0.0, vy_ref=0.0, wz_ref=0.25)
    model = _FakeModel()
    pol = _ComposedPolicy(model, env, compose=True, blend_s=0.1)
    for _ in range(5):
        pol.predict(np.zeros(4))
    assert pol._blend_w == pytest.approx(1.0)
    # switch the same env/policy to a straight-walk command -- the
    # hard-switch mechanism would snap _blend_w straight to 0 on this
    # very tick; the blended one must not.
    env.__dict__.update(_FakeEnv(vx_ref=0.08, vy_ref=0.0, wz_ref=0.0).__dict__)
    act, _ = pol.predict(np.zeros(4))
    assert pol._blend_w == pytest.approx(0.8)
    assert not np.array_equal(act, model.action), (
        "must still be blending toward the policy action, not snapped yet")


def test_blend_weight_never_exceeds_bounds_on_rapid_retoggle():
    env = _FakeEnv(vx_ref=0.0, vy_ref=0.0, wz_ref=0.25)
    model = _FakeModel()
    pol = _ComposedPolicy(model, env, compose=True, blend_s=0.1)
    for i in range(20):
        if i % 2 == 0:
            env.__dict__.update(
                _FakeEnv(vx_ref=0.0, vy_ref=0.0, wz_ref=0.25).__dict__)
        else:
            env.__dict__.update(
                _FakeEnv(vx_ref=0.08, vy_ref=0.0, wz_ref=0.0).__dict__)
        pol.predict(np.zeros(4))
        assert 0.0 <= pol._blend_w <= 1.0


def test_blend_reset_clears_weight():
    env = _FakeEnv(vx_ref=0.0, vy_ref=0.0, wz_ref=0.25)
    model = _FakeModel()
    pol = _ComposedPolicy(model, env, compose=True, blend_s=0.1)
    for _ in range(5):
        pol.predict(np.zeros(4))
    assert pol._blend_w == pytest.approx(1.0)
    pol.reset()
    assert pol._blend_w == 0.0


def test_summary_reports_blend_fields():
    env = _FakeEnv(vx_ref=0.0, vy_ref=0.0, wz_ref=0.25)
    model = _FakeModel()
    pol = _ComposedPolicy(model, env, compose=True, blend_s=0.15)
    pol.predict(np.zeros(4))
    s = pol.summary()
    assert s["blend_s"] == 0.15
    assert 0.0 < s["final_blend_w"] <= 1.0
