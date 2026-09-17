"""Mechanics-only tests for the rl_only lifecycle-composition handoff
tool (walkcurr, 2026-09-17): the pure physical-state copy helper, no
mujoco/PPO/rollouts, per RESEARCH_RULES "Tests"."""
from types import SimpleNamespace

import numpy as np

from rl_move.sim.eval_lifecycle_handoff_rlonly import (
    PhysicalState,
    apply_physical_state,
    capture_physical_state,
)


def _fake_env(n=4):
    data = SimpleNamespace(
        qpos=np.arange(n, dtype=float),
        qvel=np.arange(n, dtype=float) * 2.0,
        ctrl=np.arange(n, dtype=float) * 3.0,
        act=np.zeros(0),
    )
    safety = SimpleNamespace(_last_safe=np.arange(n, dtype=float) * 5.0)
    return SimpleNamespace(data=data, safety=safety)


def test_capture_physical_state_copies_not_aliases():
    env = _fake_env()
    state = capture_physical_state(env)
    env.data.qpos[0] = 999.0
    env.safety._last_safe[0] = 999.0
    assert state.qpos[0] == 0.0
    assert state.last_safe[0] == 0.0


def test_apply_physical_state_overwrites_destination_arrays():
    src = _fake_env()
    state = capture_physical_state(src)
    dst = _fake_env()
    dst.data.qpos[:] = -1.0
    dst.data.qvel[:] = -1.0
    dst.data.ctrl[:] = -1.0
    dst.safety._last_safe[:] = -1.0
    apply_physical_state(dst, state)
    assert np.array_equal(dst.data.qpos, state.qpos)
    assert np.array_equal(dst.data.qvel, state.qvel)
    assert np.array_equal(dst.data.ctrl, state.ctrl)
    assert np.array_equal(dst.safety._last_safe, state.last_safe)
    # mutating the source state's captured array afterward must not
    # leak into the destination env (own copy, not aliased)
    state.last_safe[0] = 12345.0
    assert dst.safety._last_safe[0] != 12345.0


def test_apply_physical_state_handles_empty_act():
    env = _fake_env()
    state = PhysicalState(qpos=np.zeros(4), qvel=np.zeros(4),
                           ctrl=np.zeros(4), act=None,
                           last_safe=np.zeros(4))
    # must not raise even though env.data.act is size-0
    apply_physical_state(env, state)
