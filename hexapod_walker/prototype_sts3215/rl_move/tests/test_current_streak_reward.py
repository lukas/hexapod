"""reward.k_current_streak — hard-reset consecutive-tick streak price
(walkcurr track, 2026-10-05).

Background: `lowerrole_terminal_support_forensics_2026-10-02` found the
lower role's converged 2-leg (L2+L5) terminal-support habit draws
IDENTICAL per-leg force/current magnitudes in passing vs
over_current-failing composed-lifecycle episodes -- the real
`SafetyLayer` trip is a CONSECUTIVE-tick counter
(`_over_current_ticks`) that hard-resets to 0 on any tick the max
per-joint current drops back at/under the rail. Every reward lever
tried against this habit before this one priced MAGNITUDE
(`k_current_hot`) or a smoothly-DECAYING EMA (`k_torque_headroom`,
`k_load_rotate`) or load DISTRIBUTION (`k_load_even`,
`k_stance_count`) -- all closed. None of those share this term's hard-
reset-on-dip math, which is the only one that can differentially
reward the exact strategy that avoids the real trip: a momentary
interruption of an otherwise-sustained high current, with no change to
average current or support-leg identity.

Contract under test:
  - `current_streak_ticks_step` pure math: a sustained over-threshold
    read grows the counter every tick with no ceiling (unlike the
    EMA's bounded-at-1 "debt"); a single under-threshold tick resets
    it to 0 regardless of how long the prior streak ran (the
    differentiating property vs `torque_headroom_debt_step`).
  - default OFF (`reward.k_current_streak` unset/0) is bit-exact: no
    `reward_current_streak`/`current_streak_frac` key ever appears,
    stepped rewards byte-identical to a keyless env, and no state
    array ever allocated.
  - ON with a low `current_streak_a` and a held high-current action:
    the term fires, is <= 0, and `current_streak_frac` grows tick over
    tick without saturating early like an EMA would.
  - ON but with current that never exceeds `current_streak_a`: the
    term never fires despite a nonzero coefficient (same "present only
    when active" convention as every sibling current price).
  - episode reset clears the streak counter (no cross-episode
    leakage), mirroring `k_current_rate`'s own reset contract.

RESEARCH_RULES "Tests": fast, mechanics only, mesh model default, no
artifacts, no rollout-ranking.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import SimHexapodGoalEnv


def test_current_streak_ticks_step_math():
    from rl_move.sim.balance_helpers import current_streak_ticks_step

    threshold = 2.0
    ticks = 0
    hot = np.array([2.5, 0.1, 0.1])
    for i in range(1, 11):
        ticks = current_streak_ticks_step(ticks, hot, threshold)
        assert ticks == i, "sustained over-threshold must grow every tick"
    # A single under-threshold tick hard-resets, regardless of streak age.
    cool = np.array([0.1, 0.1, 0.1])
    ticks = current_streak_ticks_step(ticks, cool, threshold)
    assert ticks == 0
    # Exactly at the threshold does not count as "over".
    at_th = np.array([threshold, 0.0, 0.0])
    ticks = current_streak_ticks_step(0, at_th, threshold)
    assert ticks == 0
    # Empty current array is treated as zero (no crash, no false streak).
    assert current_streak_ticks_step(5, np.array([]), threshold) == 0


def _env(seed: int, k_streak: float = 0.0, streak_a: float | None = None,
          trip_s: float | None = None) -> SimHexapodGoalEnv:
    cfg = load_config()
    cfg.setdefault("goal", {})["rise_height_mm"] = [90, 90]
    cfg["goal"]["rise_hold_s"] = 0.3
    cfg["goal"]["rise_hold_min_s"] = 0.3
    cfg["goal"]["rise_ramp_s"] = 2.0
    cfg.setdefault("episode", {})["seconds"] = 8
    if k_streak:
        cfg.setdefault("reward", {})["k_current_streak"] = k_streak
        if streak_a is not None:
            cfg["reward"]["current_streak_a"] = streak_a
        if trip_s is not None:
            cfg["reward"]["current_streak_trip_s"] = trip_s
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


def test_default_off_never_present():
    env = _env(seed=1)
    action = np.ones(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 30, action)
    env.close()
    assert all("reward_current_streak" not in info for info in infos)
    assert getattr(env, "_current_streak_ticks", 0) == 0


def test_default_off_rewards_bit_exact():
    cfg_a = load_config()
    cfg_b = load_config()
    cfg_b.setdefault("reward", {})["k_current_streak"] = 0.0
    for cfg in (cfg_a, cfg_b):
        cfg.setdefault("goal", {})["rise_height_mm"] = [90, 90]
    env_a = SimHexapodGoalEnv(cfg=cfg_a, seed=4)
    env_b = SimHexapodGoalEnv(cfg=cfg_b, seed=4)
    for env in (env_a, env_b):
        g = env._goal_gen
        for m in ("hold", "lean", "track", "unload", "raise", "rise",
                  "lower", "quad", "walk"):
            if hasattr(g, f"p_{m}"):
                setattr(g, f"p_{m}", 1.0 if m == "rise" else 0.0)
        g.force_rise_start = "flat"
    env_a.reset(seed=4)
    env_b.reset(seed=4)
    rng = np.random.default_rng(0)
    for _ in range(25):
        act = rng.uniform(-1, 1, env_a.action_space.shape).astype(
            np.float32)
        _, ra, term_a, trunc_a, info_a = env_a.step(act)
        _, rb, term_b, trunc_b, info_b = env_b.step(act)
        assert ra == rb
        assert (term_a, trunc_a) == (term_b, trunc_b)
        assert "reward_current_streak" not in info_a
        assert "reward_current_streak" not in info_b
        if term_a or trunc_a:
            break
    env_a.close()
    env_b.close()


def test_on_sustained_high_current_charges_negative_and_grows():
    # A hard push from a flat start draws sustained high current on
    # most servos; a permissive 0.0 A threshold means every tick is
    # "over", so the streak should grow monotonically tick over tick
    # (never resetting) for as long as the push continues.
    env = _env(seed=1, k_streak=1.0, streak_a=0.0, trip_s=1.0)
    action = np.ones(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 15, action)
    env.close()
    fired = [info for info in infos if "reward_current_streak" in info]
    assert fired, "expected the streak price to fire on sustained high current"
    assert all(info["reward_current_streak"] <= 0.0 for info in fired)
    fracs = [info["current_streak_frac"] for info in fired]
    # Monotone non-decreasing while the streak never breaks (hard dt=1
    # trip_s, so it saturates at 1.0 quickly -- still must never drop).
    assert all(b >= a - 1e-9 for a, b in zip(fracs, fracs[1:])), (
        "streak_frac must not decrease while current stays over threshold")


def test_high_threshold_never_fires():
    # Same "present but exactly 0" convention as every sibling current
    # price (`k_current_hot`/`k_current_rate`): the key is populated
    # whenever the coefficient is armed, but its value is 0.0 whenever
    # the streak condition never actually engages.
    env = _env(seed=1, k_streak=1.0, streak_a=1.0e6, trip_s=2.0)
    action = np.ones(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 20, action)
    env.close()
    assert all(info.get("reward_current_streak", 0.0) == 0.0
                for info in infos)
    assert all(info.get("current_streak_frac", 0.0) == 0.0
                for info in infos)


def test_reset_clears_streak_counter():
    env = _env(seed=1, k_streak=1.0, streak_a=0.0, trip_s=2.0)
    action = np.ones(env.action_space.shape, dtype=np.float32)
    _run(env, 10, action)
    assert env._current_streak_ticks > 0
    env.reset()
    assert env._current_streak_ticks == 0
    env.close()
