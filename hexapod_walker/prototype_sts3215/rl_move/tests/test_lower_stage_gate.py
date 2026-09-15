"""Staged multi-phase descent: dynamic ramp-advance gate
(goal.lower_stage_gate, walkcurr track, 2026-09-13).

Background (RL_LOG 09-13, `cw-stance50hz-rlonly-lowerscoreprog-{s0,s1}`
/ `-lowerratchetpartial-{s0,s1}` / `-lowerdenseposture-{s0,s1}`): THREE
independent reward-side levers on the same from-plant lower depth gap
(~40mm height_err_end, flat since the first 6M run) all FAIL-MECHANISM
at the same magnitude -- repricing what depth income pays never moves
the ramp the policy is actually commanded to follow, because
`goal.height_ref` (what the policy observes via `TaskGoal.as_obs`;
this recipe's own reward terms read `h_rel`/`self._h_target` directly
and never consume `height_ref`) advances on a fixed WALL-CLOCK schedule
(`goal.lower_ramp_s`) regardless of whether the feet are actually
staying planted on the way down.

This is not a fourth re-price: it makes the ramp's own ADVANCE (not
just its onset, unlike the rise curl-gate this mirrors) conditional on
a genuine per-tick sub-goal -- a measured fraction of feet loaded above
`goal.lower_stage_load_ref_n` -- by freezing the trajectory index fed
to `_current_goal()` for as long as the sub-goal is unmet, up to a
capped extra wait (`goal.lower_stage_gate_max_extra_s`) so an episode
that never plants still eventually gets scored on the attempt rather
than stalling forever.

Contract under test:
  - default OFF (`goal.lower_stage_gate` unset) is bit-exact: the
    height ramp advances on the natural precomputed schedule the whole
    episode, `_lower_gate_freeze_ticks` stays 0.
  - ON, planted-load threshold set unreachably high: the ramp is
    deferred through the whole capped extra-wait window, then forced
    to proceed anyway (no infinite stall).
  - ON, planted-load threshold trivially met (a stationary plant start
    under a zero action is already fully loaded): behaves bit-
    identically to the gate being off -- no deferral at all.
  - the freeze counter only ever moves for `lower` episodes; a rise
    episode run alongside a lower-gated cfg is untouched.

RESEARCH_RULES "Tests": fast, mechanics only, mesh model default, no
artifacts, no rollout-ranking.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import SimHexapodGoalEnv


def _lower_env(seed: int, stage_gate: float = 0.0) -> SimHexapodGoalEnv:
    cfg = load_config()
    cfg.setdefault("goal", {})["lower_hold_s"] = 0.3
    cfg["goal"]["lower_ramp_s"] = 2.0
    cfg.setdefault("episode", {})["seconds"] = 8
    if stage_gate:
        cfg["goal"]["lower_stage_gate"] = stage_gate
    env = SimHexapodGoalEnv(cfg=cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 1.0 if m == "lower" else 0.0)
    return env


def _rise_env(seed: int, stage_gate_cfg: float = 0.0) -> SimHexapodGoalEnv:
    """A RISE episode with a lower-stage-gate cfg present, to prove the
    lower-only gate never touches a rise episode's schedule."""
    cfg = load_config()
    cfg.setdefault("goal", {})["rise_height_mm"] = [90, 90]
    cfg["goal"]["rise_hold_s"] = 0.3
    cfg["goal"]["rise_hold_min_s"] = 0.3
    cfg["goal"]["rise_ramp_s"] = 2.0
    cfg.setdefault("episode", {})["seconds"] = 8
    if stage_gate_cfg:
        cfg["goal"]["lower_stage_gate"] = stage_gate_cfg
    env = SimHexapodGoalEnv(cfg=cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 1.0 if m == "rise" else 0.0)
    g.force_rise_start = "flat"
    return env


def _run(env, n_steps, action):
    env.reset()
    out = []
    for _ in range(n_steps):
        _, _, term, trunc, info = env.step(action)
        out.append(dict(info))
        if term or trunc:
            break
    return out


def _first_ramp_tick(infos):
    """First index whose height_ref_mm departs from ~0 (a lower ramp is
    signed negative, same |.| > eps test the rise gate tests use)."""
    for i, info in enumerate(infos):
        if abs(info.get("height_ref_mm", 0.0)) > 1e-6:
            return i
    return None


def test_default_off_ramps_on_the_natural_schedule():
    env = _lower_env(seed=1)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 300, action)
    hold_n = env._lower_ramp_i0
    env.close()
    first = _first_ramp_tick(infos)
    assert first is not None
    # Bit-exact: the ramp begins exactly at the precomputed schedule
    # tick, never deferred (freeze_ticks stays 0 whole episode).
    assert first == hold_n - 1
    assert all(info.get("lower_gate_freeze_ticks", 0.0) == 0.0
               for info in infos)


def test_gate_on_defers_ramp_while_unplanted_then_unlocks():
    unplanted_s = 0.4
    # Report the feet as unplanted for the first 0.4 s of gate checks
    # (well under the gate's fixed 5 s extra-wait cap), then planted --
    # the gate must hold exactly through that window regardless of what
    # the (zero) action does, then let the ramp advance.
    env = _lower_env(seed=1, stage_gate=1.0)
    n_unplanted = int(round(unplanted_s / env.dt))
    checks = {"n": 0}

    def _planted_frac(load_ref_n):
        checks["n"] += 1
        return 0.0 if checks["n"] <= n_unplanted else 1.0

    env._lower_stage_planted_frac = _planted_frac
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 400, action)
    hold_n = env._lower_ramp_i0
    env.close()
    first = _first_ramp_tick(infos)
    assert first is not None
    # Ramp must NOT start at the original schedule tick (deferred)...
    assert first > hold_n
    # ...but must not stall past hold_n + the unplanted window either.
    assert first <= hold_n + n_unplanted + 1


def test_gate_unlocks_when_planted_frac_trivially_met():
    # Default load_ref_n=1.0N / frac_min=0.7: a stationary plant start
    # under a zero action is already fully loaded (6/6 feet down), so
    # the gate must never defer -- ramp begins at the natural schedule
    # tick, same as gate-off.
    env = _lower_env(seed=1, stage_gate=1.0)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 300, action)
    hold_n = env._lower_ramp_i0
    env.close()
    first = _first_ramp_tick(infos)
    assert first is not None
    assert first == hold_n - 1


def test_freeze_ticks_zero_when_gate_off():
    env = _lower_env(seed=1, stage_gate=0.0)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    env.reset()
    for _ in range(50):
        env.step(action)
        assert env._lower_gate_freeze_ticks == 0
    env.close()


def test_lower_gate_cfg_does_not_touch_rise_episode_schedule():
    # A rise episode run with goal.lower_stage_gate=1 present in cfg
    # must ramp on ITS OWN natural schedule, unaffected -- the two gates
    # are mode-exclusive.
    env = _rise_env(seed=1, stage_gate_cfg=1.0)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 300, action)
    hold_n = env._rise_ramp_i0
    env.close()
    first = _first_ramp_tick(infos)
    assert first is not None
    assert first == hold_n - 1
    assert all(info.get("rise_gate_freeze_ticks", 0.0) == 0.0
               for info in infos)
