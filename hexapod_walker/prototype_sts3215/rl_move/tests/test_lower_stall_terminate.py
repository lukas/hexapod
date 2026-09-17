"""Unit tests for safety.lower_stall_terminate_s (2026-09-17, walkcurr
achievability-audit follow-up).

`probe_lower_achievability.py` (frozen open-loop action, no policy) found
the trained LOWER descent target range (25-55mm) draws well under 0.5A
holding still at every depth tested -- nowhere near the 2.9A safety
trip -- so the persistent ~28-31mm/0-2-of-12-ok floor every reward-
pricing/gate lever left untouched is NOT a torque-budget/reachability
limit. This is the "absorbing states beat prices; must come WITH a
termination, never instead of one" (op ruling 08-24) fix for LOWER's
own safe/no-progress absorbing state, mirroring hold_min_load/
walk_idle exactly:

  - safety.lower_stall_terminate_s: consecutive seconds the best
    (smallest) |height error| reached this lower segment may go
    without improving by safety.lower_stall_improve_mm before the
    episode ends (the usual termination penalty applies).
  - safety.lower_stall_terminate_grace_s: window after the ramp's own
    onset exempt from the check (never during the pre-ramp hold, when
    height_ref is still 0).
  - safety.lower_stall_active_floor_mm: the check only ever runs while
    the CURRENT |height error| exceeds this floor -- a policy already
    tracking closely has nothing left to "improve" and is never
    penalized for it.
  - Default lower_stall_terminate_s=0.0 = OFF, bit-exact legacy: no
    new state read that changes behavior, no reward change.

Fast (~seconds): short episodes, scripted zero action (no policy).
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import SimHexapodGoalEnv
from rl_move.sim.servo_model import SimServoParams

FC_GOAL = {
    ("goal", "p_hold"): 0.0, ("goal", "p_lean"): 0.0,
    ("goal", "p_track"): 0.0, ("goal", "p_unload"): 0.0,
    ("goal", "p_raise"): 0.0, ("goal", "p_rise"): 0.0,
    ("goal", "p_lower"): 1.0,
}


def _lower_env(extra=None, episode_seconds=8.0, lower_mm=40.0):
    cfg = load_config()
    for (sec, leaf), val in {**FC_GOAL, **(extra or {})}.items():
        cfg.setdefault(sec, {})[leaf] = val
    env = SimHexapodGoalEnv(
        params=SimServoParams.from_cfg(None), randomize=False,
        dr_scale=0.0, episode_seconds=episode_seconds, seed=0, cfg=cfg)
    # Pin the target depth (no randomness) and turn off the two
    # reset-side lower variants (belly-start / mid-descent partial) so
    # every episode is the plain plant->ramp->target descent this test
    # reasons about.
    env._goal_gen.lower_m = (lower_mm * 0.001, lower_mm * 0.001)
    env._goal_gen.lower_belly_start_frac = 0.0
    env._goal_gen.lower_partial_frac = 0.0
    return env


def _freeze_action(env):
    """All-zero body-offset action: commands NO additional height
    offset at all, regardless of the goal ref -- the scripted
    "frozen/no-progress" behavior this termination targets (a policy
    that never learns to track a receding height reference)."""
    return np.zeros(env.action_space.shape, dtype=np.float32)


def test_default_off_never_terminates_on_a_frozen_action():
    env = _lower_env(episode_seconds=8.0)
    env.reset(seed=0)
    for step in range(env.episode_steps - 1):
        _o, _r, term, _trunc, info = env.step(_freeze_action(env))
        assert not term, (step, info.get("termination_reason"))
    env.close()


def test_armed_terminates_a_frozen_non_tracking_descent():
    env = _lower_env(extra={
        ("safety", "lower_stall_terminate_s"): 0.5,
        ("safety", "lower_stall_terminate_grace_s"): 0.5,
        ("safety", "lower_stall_improve_mm"): 3.0,
    }, episode_seconds=8.0)
    env.reset(seed=0)
    act = _freeze_action(env)
    fired = False
    for step in range(env.episode_steps - 1):
        _o, _r, term, trunc, info = env.step(act)
        if term:
            fired = True
            assert info["termination_reason"] == "lower_stall"
            break
        assert not trunc
    assert fired, "lower_stall never fired on a frozen non-tracking descent"
    env.close()


def test_grace_window_is_respected():
    # grace covers the whole episode -> never fires even armed.
    env = _lower_env(extra={
        ("safety", "lower_stall_terminate_s"): 0.2,
        ("safety", "lower_stall_terminate_grace_s"): 100.0,
        ("safety", "lower_stall_improve_mm"): 3.0,
    }, episode_seconds=4.0)
    env.reset(seed=0)
    act = _freeze_action(env)
    for step in range(env.episode_steps - 1):
        _o, _r, term, _trunc, info = env.step(act)
        assert not term, (step, info.get("termination_reason"))
    env.close()


def test_pre_ramp_hold_never_counts_as_stalled():
    # Only step through the 1.0s pre-ramp hold (height_ref == 0
    # throughout) of a normal-length episode -- even a hair-trigger
    # dose must never fire in this window, since there is genuinely
    # nothing to stall on yet.
    env = _lower_env(extra={
        ("safety", "lower_stall_terminate_s"): 0.05,
        ("safety", "lower_stall_terminate_grace_s"): 0.0,
        ("safety", "lower_stall_improve_mm"): 3.0,
    }, episode_seconds=8.0)
    env.reset(seed=0)
    act = _freeze_action(env)
    hold_steps = int(round(1.0 / env.dt)) - 2  # stay inside lower_hold_s
    for step in range(hold_steps):
        _o, _r, term, _trunc, info = env.step(act)
        assert not term, (step, info.get("termination_reason"))
    env.close()


def test_low_s_counter_resets_across_episodes():
    env = _lower_env(extra={
        ("safety", "lower_stall_terminate_s"): 10.0,  # long enough not
        ("safety", "lower_stall_terminate_grace_s"): 0.0,  # to fire in
        ("safety", "lower_stall_improve_mm"): 3.0,       # 1 episode
    }, episode_seconds=3.0)
    env.reset(seed=0)
    act = _freeze_action(env)
    for _ in range(env.episode_steps - 1):
        env.step(act)
    assert env._lower_stall_low_s > 0.0
    env.reset(seed=0)
    assert env._lower_stall_low_s == 0.0
    assert env._lower_stall_best_mm is None
    assert env._lower_stall_ramp_start_step is None
    env.close()


def test_a_genuinely_tracking_descent_never_stalls():
    """The decisive selectivity check: a policy that ACTUALLY tracks
    the ramp (scripted open-loop action == goal ref, the same
    convention probe_lower_achievability.py uses) must never trip the
    stall termination, at a dose that reliably kills the frozen
    non-tracker above -- otherwise the mechanism would punish honest
    descent, not just the absorbing no-progress state."""
    env = _lower_env(extra={
        ("safety", "lower_stall_terminate_s"): 0.5,
        ("safety", "lower_stall_terminate_grace_s"): 0.5,
        ("safety", "lower_stall_improve_mm"): 3.0,
    }, episode_seconds=8.0, lower_mm=40.0)
    env.reset(seed=0)
    max_h_m = float(env.cfg.get("actions", {}).get("max_height_mm", 5.0)) \
        * 0.001
    for step in range(env.episode_steps - 1):
        h_ref = env._goal_traj.height[min(step, len(env._goal_traj.height) - 1)]
        a = np.zeros(env.action_space.shape, dtype=np.float32)
        a[2] = np.clip(h_ref / max_h_m, -1.0, 1.0)
        _o, _r, term, _trunc, info = env.step(a)
        assert not term, (step, info.get("termination_reason"))
    env.close()


def test_off_by_default_matches_zero_key_absent():
    a = _lower_env(episode_seconds=3.0)
    b = _lower_env(extra={("safety", "lower_stall_terminate_s"): 0.0},
                   episode_seconds=3.0)
    a.reset(seed=0)
    b.reset(seed=0)
    act_a, act_b = _freeze_action(a), _freeze_action(b)
    for _ in range(a.episode_steps - 1):
        oa = a.step(act_a)
        ob = b.step(act_b)
        assert oa[1] == pytest.approx(ob[1])
        assert oa[2] == ob[2] == False
    a.close()
    b.close()
