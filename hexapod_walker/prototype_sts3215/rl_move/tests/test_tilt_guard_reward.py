"""reward.k_tilt_guard — dense tilt guard-band price (standwalk
s1-cont2m2 dig-in, 2026-09-23).

Background: the hold/track income kernel's tilt width
(reward.track_sigma_deg, 1.5 deg) saturates to ~0 by ~4 deg while the
tilt_roll/tilt_pitch termination cliff sits at safety.max_roll_deg
(10 deg on the stand recipes) — a gradient-blind band the s1-cont2m2
FAIL's quasi-static roll drift (hold/sto/2, 10.4 deg trip) lived in.
tilt_guard_reward charges every non-walk tick
  -k * dt * clip((frac - start)/(1 - start), 0, 1),
frac = worst-axis |tilt - ref| / termination envelope — the SAME
measure/reference/envelope the termination reads.

Contract under test:
  - default OFF (`reward.k_tilt_guard` unset/0) is bit-exact: no
    `reward_tilt_guard` key ever appears and stepped rewards are
    byte-identical to a keyless env on the same seed/actions.
  - ON with start_frac=0 (any nonzero tilt charges): the term fires
    on ordinary hold ticks and is <= 0, bounded by k*dt per tick.
  - ON with start_frac=0.99: a quiet hold never enters the band, the
    term never fires despite a nonzero coefficient.

RESEARCH_RULES "Tests": fast, mechanics only, mesh model default, no
artifacts, no rollout-ranking.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import SimHexapodGoalEnv


def _hold_env(seed: int, k_guard: float = 0.0,
              start_frac: float | None = None) -> SimHexapodGoalEnv:
    cfg = load_config()
    cfg.setdefault("episode", {})["seconds"] = 6
    if k_guard:
        cfg.setdefault("reward", {})["k_tilt_guard"] = k_guard
        if start_frac is not None:
            cfg["reward"]["tilt_guard_start_frac"] = start_frac
    env = SimHexapodGoalEnv(cfg=cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 1.0 if m == "hold" else 0.0)
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
    env = _hold_env(seed=1)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 40, action)
    env.close()
    assert all("reward_tilt_guard" not in info for info in infos)


def test_default_off_rewards_bit_exact():
    cfg_a = load_config()
    cfg_b = load_config()
    cfg_b.setdefault("reward", {})["k_tilt_guard"] = 0.0
    env_a = SimHexapodGoalEnv(cfg=cfg_a, seed=4)
    env_b = SimHexapodGoalEnv(cfg=cfg_b, seed=4)
    for env in (env_a, env_b):
        g = env._goal_gen
        for m in ("hold", "lean", "track", "unload", "raise", "rise",
                  "lower", "quad", "walk"):
            if hasattr(g, f"p_{m}"):
                setattr(g, f"p_{m}", 1.0 if m == "hold" else 0.0)
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
        assert "reward_tilt_guard" not in info_a
        assert "reward_tilt_guard" not in info_b
        if term_a or trunc_a:
            break
    env_a.close()
    env_b.close()


def test_on_zero_start_fires_negative_and_bounded():
    env = _hold_env(seed=1, k_guard=5.0, start_frac=0.0)
    rng = np.random.default_rng(2)
    env.reset()
    fired = []
    for _ in range(40):
        act = rng.uniform(-0.5, 0.5,
                          env.action_space.shape).astype(np.float32)
        _, _, term, trunc, info = env.step(act)
        if "reward_tilt_guard" in info:
            fired.append(info["reward_tilt_guard"])
        if term or trunc:
            break
    env.close()
    assert fired, "start_frac=0 must charge any nonzero tilt"
    assert all(v <= 0.0 for v in fired)
    assert all(v >= -5.0 * env.dt - 1e-9 for v in fired), \
        "per-tick charge must be bounded by k*dt"


def test_on_high_start_never_fires_on_quiet_hold():
    env = _hold_env(seed=1, k_guard=5.0, start_frac=0.99)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 40, action)
    env.close()
    assert all("reward_tilt_guard" not in info for info in infos)
