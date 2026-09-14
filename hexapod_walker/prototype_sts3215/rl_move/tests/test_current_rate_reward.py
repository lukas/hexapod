"""reward.k_current_rate — current RATE-of-rise price (walkcurr rise
track, 2026-09-14).

Background: CURRENT_TRUTHS.md's 2026-09-14 ~06:4x entry closed the
entire cap-based action-space-gating family (10/10 null: capping
either the height ramp or the joint-rate/slew ceiling just replays the
policy's own chosen simultaneous-six-leg-max-current trajectory in
slow motion — the cap cannot distinguish "many legs slowly" from "one
leg quickly"). That entry's own named next-viable direction, staying
`rl_only`-clean, was "a reward term on a property the POLICY'S OWN
rollout can self-referentially measure (e.g. bounding the rate-of-
current-RISE, not matching a target profile)". This term does exactly
that: it charges (quadratically) the tick-over-tick RATE of increase
of each servo's current, above a threshold in A/s, whenever the
policy is in rise mode — unlike `k_current_hot`/`k_current_pretuck`/
`k_current_income` (which all price the *level* of current, not its
rate of change) and unlike the closed cap-based gates (which throttle
the *joint angle's* rate of motion, not the current itself). No
scripted/target profile is read anywhere (only this env's own
previous tick), so it stays demonstration-free.

Contract under test:
  - default OFF (`reward.k_current_rate` unset/0) is bit-exact: no
    `reward_current_rate` key ever appears, and stepped rewards are
    byte-identical to a keyless env on the same seed/action sequence.
  - ON with a permissive (0 A/s) threshold and a current trace that
    is actually rising tick-over-tick: the term fires and is <= 0.
  - ON with a threshold high enough that the observed rate never
    exceeds it: the term never fires (present nowhere), even though
    the coefficient is nonzero.
  - the term is scoped to rise mode only: forcing a non-rise mode
    (hold) never fires it even with an aggressive (permissive)
    threshold.
  - episode reset clears the previous-tick baseline: the first tick
    after reset never reads a bogus rate against the FINAL current of
    the previous episode (no cross-episode leakage).

RESEARCH_RULES "Tests": fast, mechanics only, mesh model default, no
artifacts, no rollout-ranking.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import SimHexapodGoalEnv


def _rise_env(seed: int, force_start: str = "flat",
              k_rate: float = 0.0,
              rate_a_per_s: float | None = None,
              mode: str = "rise") -> SimHexapodGoalEnv:
    cfg = load_config()
    cfg.setdefault("goal", {})["rise_height_mm"] = [90, 90]
    cfg["goal"]["rise_hold_s"] = 0.3
    cfg["goal"]["rise_hold_min_s"] = 0.3
    cfg["goal"]["rise_ramp_s"] = 2.0
    cfg.setdefault("episode", {})["seconds"] = 8
    if k_rate:
        cfg.setdefault("reward", {})["k_current_rate"] = k_rate
        if rate_a_per_s is not None:
            cfg["reward"]["current_rate_a_per_s"] = rate_a_per_s
    env = SimHexapodGoalEnv(cfg=cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 1.0 if m == mode else 0.0)
    if mode == "rise":
        g.force_rise_start = force_start
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
    env = _rise_env(seed=1)
    action = np.ones(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 60, action)
    env.close()
    assert all("reward_current_rate" not in info for info in infos)


def test_default_off_rewards_bit_exact():
    cfg_a = load_config()
    cfg_b = load_config()
    cfg_b.setdefault("reward", {})["k_current_rate"] = 0.0
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
        assert "reward_current_rate" not in info_a
        assert "reward_current_rate" not in info_b
        if term_a or trunc_a:
            break
    env_a.close()
    env_b.close()


def test_on_rising_current_charges_negative():
    # A hard push (action=+1 on every joint) from a flat start draws a
    # fast-rising current on most servos tick over tick; a 0 A/s
    # threshold charges any positive rate at all.
    env = _rise_env(seed=1, force_start="flat", k_rate=1.0,
                     rate_a_per_s=0.0)
    action = np.ones(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 10, action)
    env.close()
    fired = [info for info in infos if "reward_current_rate" in info]
    assert fired, "expected the rate price to fire on a rising trace"
    assert all(info["reward_current_rate"] <= 0.0 for info in fired)


def test_high_threshold_never_fires():
    # An enormous A/s bar is never exceeded by any physically-real
    # per-tick current swing at this dt, so the term's own value must
    # stay exactly 0.0 on every tick despite a nonzero coefficient (the
    # key itself is present whenever the coefficient is armed in rise
    # mode, same convention as `k_current_hot`).
    env = _rise_env(seed=1, force_start="flat", k_rate=1.0,
                     rate_a_per_s=1.0e6)
    action = np.ones(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 20, action)
    env.close()
    assert all(info.get("reward_current_rate", 0.0) == 0.0
                for info in infos)


def test_scoped_to_rise_mode_only():
    env = _rise_env(seed=1, k_rate=1.0, rate_a_per_s=0.0, mode="hold")
    action = np.ones(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 30, action)
    env.close()
    assert all("reward_current_rate" not in info for info in infos)


def test_reset_clears_previous_tick_baseline(monkeypatch):
    # Drive current up hard, then reset, then confirm the very first
    # post-reset tick does not see a bogus rate computed against the
    # previous episode's final (high) current.
    env = _rise_env(seed=1, force_start="flat", k_rate=1.0,
                     rate_a_per_s=0.0)
    action = np.ones(env.action_space.shape, dtype=np.float32)
    _run(env, 10, action)
    assert getattr(env, "_prev_current_rate", None) is not None
    env.reset()
    assert env._prev_current_rate is None
    env.close()
