"""TwoStageLowerPolicy (2026-10-04): deterministic-tick handoff between
a lower-role descent checkpoint and a terminal-hold specialist. Pure
mechanics test, no mujoco/SB3 -- fake predict() stubs are enough to
pin the switch-tick contract."""
from __future__ import annotations

import numpy as np
import pytest

from rl_move.sim.two_stage_lower_policy import TwoStageLowerPolicy


class _FakeSpace:
    def __init__(self, shape):
        self.shape = shape


class _FakeModel:
    def __init__(self, tag: str, obs_dim: int = 4):
        self.tag = tag
        self.observation_space = _FakeSpace((obs_dim,))
        self.calls = []
        self.reset_calls = 0

    def predict(self, obs, deterministic: bool = True):
        self.calls.append((np.asarray(obs).copy(), deterministic))
        return np.array([self.tag]), None

    def reset(self):
        self.reset_calls += 1


def test_switch_tick_zero_always_specialist():
    base, spec = _FakeModel("base"), _FakeModel("spec")
    pol = TwoStageLowerPolicy(base, spec, switch_tick=0)
    for _ in range(3):
        a, _ = pol.predict(np.zeros(4))
        assert a[0] == "spec"
    assert len(base.calls) == 0
    assert len(spec.calls) == 3


def test_switch_happens_at_exact_tick():
    base, spec = _FakeModel("base"), _FakeModel("spec")
    pol = TwoStageLowerPolicy(base, spec, switch_tick=3)
    tags = [pol.predict(np.zeros(4))[0][0] for _ in range(6)]
    assert tags == ["base", "base", "base", "spec", "spec", "spec"]


def test_reset_rewinds_tick_and_propagates():
    base, spec = _FakeModel("base"), _FakeModel("spec")
    pol = TwoStageLowerPolicy(base, spec, switch_tick=2)
    for _ in range(4):
        pol.predict(np.zeros(4))
    assert pol._t == 4
    pol.reset()
    assert pol._t == 0
    assert base.reset_calls == 1 and spec.reset_calls == 1
    a, _ = pol.predict(np.zeros(4))
    assert a[0] == "base", "post-reset tick 0 must use base again"


def test_negative_switch_tick_rejected():
    base, spec = _FakeModel("base"), _FakeModel("spec")
    with pytest.raises(ValueError):
        TwoStageLowerPolicy(base, spec, switch_tick=-1)


def test_observation_space_mismatch_raises():
    base, spec = _FakeModel("base", obs_dim=68), _FakeModel("spec", obs_dim=4)
    pol = TwoStageLowerPolicy(base, spec, switch_tick=1)
    with pytest.raises(ValueError, match="obs widths"):
        _ = pol.observation_space


def test_observation_space_matches_when_equal():
    base, spec = _FakeModel("base", obs_dim=68), _FakeModel("spec", obs_dim=68)
    pol = TwoStageLowerPolicy(base, spec, switch_tick=1)
    assert pol.observation_space.shape == (68,)
