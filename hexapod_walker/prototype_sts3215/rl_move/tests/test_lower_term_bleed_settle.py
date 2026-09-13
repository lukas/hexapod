"""LOWER terminal bleed-settlement (reward.lower_term_bleed_settle,
walkcurr track, 2026-09-13).

Background (RL_LOG/STATUS.md 09-13, `lowerscoreprog-s1-track01-cont15m`
FAIL-MECHANISM): the pre-registered A/B fork on `k_lower_score_track`
fired -- weakening the continuous `reward_lower_track` charge
(1.0->0.1) to stop the pricing inversion (a surviving parked lower
episode integrates far more bleed than the flat termination fee, so an
early tip-over is cheaper than parking) just makes `env/lower_depth_frac`
plateau/decay instead of climbing, while the unchanged k=1.0 sibling
keeps climbing. The gate's own escalation: the fix is not scale --
charge the REMAINING bleed a survivor would have paid, once, at
termination, so a strong per-tick charge can stay strong without a
death discount.

`reward.lower_term_bleed_settle` (default OFF) adds
`reward_lower_term_bleed` on any SAFETY termination (never truncation)
of a `lower_score_prog` episode: `-k_lower_score_track * (1 -
depth_frac) ** 2 * remaining_ticks`, i.e. the same per-tick
`reward_lower_track` rate the episode was already paying, projected
over however many ticks were left. Optional `lower_term_bleed_settle_max`
caps the one-time charge (default 0 = uncapped), mirroring
`term_cost_max`'s bounded-terminal-cost convention.

Contract under test:
  - default OFF: no `reward_lower_term_bleed` key ever appears, even on
    a forced early termination of a `lower_score_prog` episode.
  - ON, no termination (episode reaches truncation/time limit): the key
    is absent -- this is a DEATH settlement, not a per-tick charge.
  - ON with a forced early safety termination: the key appears exactly
    once, is <= 0, and matches the closed-form
    `-k * (1 - depth_frac_at_death)**2 * remaining_ticks` within a
    float epsilon.
  - ON with `k_lower_score_track=0`: settlement is always exactly 0
    (nothing to settle when the underlying charge itself is off).
  - `lower_term_bleed_settle_max` caps the charge.

RESEARCH_RULES "Tests": fast, mechanics only, no rollout ranking, no
artifacts, mesh model.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import SimHexapodGoalEnv


def _lower_env(seed: int, *, score_prog: float = 1.0,
               settle: float = 0.0, k_track: float | None = None,
               settle_max: float | None = None,
               force_trip: bool = False) -> SimHexapodGoalEnv:
    cfg = load_config()
    cfg.setdefault("goal", {})["lower_height_mm"] = [40, 40]
    cfg["goal"]["lower_hold_s"] = 0.2
    cfg.setdefault("episode", {})["seconds"] = 6
    r = cfg.setdefault("reward", {})
    if score_prog:
        r["lower_score_prog"] = score_prog
    if settle:
        r["lower_term_bleed_settle"] = settle
    if k_track is not None:
        r["k_lower_score_track"] = k_track
    if settle_max is not None:
        r["lower_term_bleed_settle_max"] = settle_max
    if force_trip:
        # Deterministic, fast, immediate `over_current` safety
        # termination -- independent of any policy/action luck, so the
        # settlement math can be checked exactly on the very first tick
        # (`rem_ticks` a large, known value).
        s = cfg.setdefault("safety", {})
        s["max_current_a"] = 0.01
        s["over_current_trip_s"] = 0.001
    env = SimHexapodGoalEnv(cfg=cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 1.0 if m == "lower" else 0.0)
    return env


def _run(env, n_steps, action):
    env.reset()
    out = []
    for _ in range(n_steps):
        _, _, term, trunc, info = env.step(action)
        out.append(dict(info))
        if term or trunc:
            break
    return out, term


def _trip_action(env):
    return np.ones(env.action_space.shape, dtype=np.float32) * 0.5


def test_default_off_never_exposes_the_key():
    env = _lower_env(seed=1, settle=0.0, force_trip=True)
    infos, term = _run(env, 400, _trip_action(env))
    env.close()
    assert term, "expected the forced-trip cfg to terminate immediately"
    assert not any("reward_lower_term_bleed" in i for i in infos)


def test_on_but_no_termination_never_charges():
    # Zero action never trips safety -> episode truncates naturally;
    # the settlement (a DEATH charge) must never fire.
    env = _lower_env(seed=1, settle=1.0)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos, term = _run(env, 400, action)
    env.close()
    assert not term, "expected this episode to reach truncation, not terminate"
    assert not any("reward_lower_term_bleed" in i for i in infos)


def test_on_with_forced_termination_matches_closed_form():
    env = _lower_env(seed=3, settle=1.0, force_trip=True)
    infos, term = _run(env, 600, _trip_action(env))
    env.close()
    assert term, "expected the forced-trip cfg to terminate immediately"
    hits = [i for i in infos if "reward_lower_term_bleed" in i]
    assert len(hits) == 1, "settlement must fire exactly once, at death"
    last = infos[-1]
    depth_frac = last["lower_depth_frac"]
    k = float(env.cfg["reward"].get(
        "k_lower_score_track", 1.0))
    rem_ticks = env._active_episode_steps() - env._step_i
    want = -k * (1.0 - depth_frac) ** 2 * rem_ticks
    assert last["reward_lower_term_bleed"] == pytest.approx(want, rel=1e-6)
    assert last["reward_lower_term_bleed"] <= 0.0
    assert rem_ticks > 100, "test setup should trip near episode start"


def test_zero_k_track_means_zero_settlement():
    env = _lower_env(seed=3, settle=1.0, k_track=0.0, force_trip=True)
    infos, term = _run(env, 600, _trip_action(env))
    env.close()
    assert term, "expected the forced-trip cfg to terminate immediately"
    assert not any("reward_lower_term_bleed" in i for i in infos), \
        "k_lower_score_track=0 must leave nothing to settle"


def test_settle_max_caps_the_charge():
    env = _lower_env(seed=3, settle=1.0, settle_max=1.0, force_trip=True)
    infos, term = _run(env, 600, _trip_action(env))
    env.close()
    assert term
    hits = [i for i in infos if "reward_lower_term_bleed" in i]
    assert len(hits) == 1
    assert hits[0]["reward_lower_term_bleed"] == pytest.approx(-1.0)
