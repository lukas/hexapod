"""reward.k_rise_decouple — height-without-curl decoupling price
(walkcurr rise track, 2026-09-14).

Background: a `--rollout-trace-out` per-tick trace off a FAILING
flat-start rise episode (`cw-stance50hz-rlonly-risepretuck-dose{2,8}-
s1-canary2m`, both CANARY FAIL - MECHANISM this cycle) showed ALL SIX
legs' pitch+knee servos pinned at/near the 2.64A ceiling simultaneously
for >1.5s while `footprint_err_end_mm` stayed at the ~52mm stuck band
(feet never moved toward the plant anchor) even though torso height
climbed 0->53mm over the same window: the policy pushes the body
straight UP in Z from the original (splayed) foot XY layout instead of
pulling feet IN (shrinking curl_dist) first. Every closed lever on
this sub-problem (current-headroom-gate, geometry/score-income gate,
two-phase-freeze, curl-pretrain, current_pretuck) priced CURRENT,
SCORE-INCOME, or a TRAINING STAGE in isolation; none of them couple
the two live state signals (curl_dist, h_rel) together. This term
does: while pre-tuck, any positive torso height gained on a tick where
curl_dist did NOT also shrink is charged quadratically -- height
gained WHILE curling is free.

Contract under test:
  - default OFF (`reward.k_rise_decouple` unset/0) is bit-exact: no
    `reward_rise_decouple` key ever appears, and stepped rewards are
    byte-identical to a keyless env on the same seed/action sequence.
  - ON, curl_dist held NON-improving (monkeypatched, one-way latch
    threshold unreached) while a real action sequence moves the body:
    the term fires (present, <= 0) at least once.
  - ON, curl_dist held MONOTONICALLY improving (same real action
    sequence, threshold unreached): the term never fires, even though
    height also changes -- height gained while curling is free.
  - ON, crouch start: the term never fires even with an aggressive
    (already-satisfied-anyway) threshold -- mirrors current_pretuck's
    own crouch exemption.
  - Latch mechanics: once curl_dist crosses the threshold on some
    tick, the term stays silent on every later tick even if curl_dist
    is made to read as "untucked, non-improving" again -- a one-way
    latch, not a per-tick re-check.

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
              k_decouple: float = 0.0,
              curl_mm: float | None = None) -> SimHexapodGoalEnv:
    cfg = load_config()
    cfg.setdefault("goal", {})["rise_height_mm"] = [90, 90]
    cfg["goal"]["rise_hold_s"] = 0.3
    cfg["goal"]["rise_hold_min_s"] = 0.3
    cfg["goal"]["rise_ramp_s"] = 2.0
    cfg.setdefault("episode", {})["seconds"] = 8
    if k_decouple:
        cfg.setdefault("reward", {})["k_rise_decouple"] = k_decouple
        if curl_mm is not None:
            cfg["reward"]["rise_decouple_curl_mm"] = curl_mm
    env = SimHexapodGoalEnv(cfg=cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 1.0 if m == "rise" else 0.0)
    g.force_rise_start = force_start
    return env


def _rng_actions(env, n, seed=0):
    rng = np.random.default_rng(seed)
    return [rng.uniform(-1, 1, env.action_space.shape).astype(np.float32)
            for _ in range(n)]


def _run(env, actions):
    env.reset()
    out = []
    for act in actions:
        _, _, term, trunc, info = env.step(act)
        out.append(dict(info))
        if term or trunc:
            break
    return out


def test_default_off_never_present():
    env = _rise_env(seed=1)
    infos = _run(env, _rng_actions(env, 40))
    env.close()
    assert all("reward_rise_decouple" not in info for info in infos)


def test_default_off_rewards_bit_exact():
    cfg_a = load_config()
    cfg_b = load_config()
    cfg_b.setdefault("reward", {})["k_rise_decouple"] = 0.0
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
        assert "reward_rise_decouple" not in info_a
        assert "reward_rise_decouple" not in info_b
        if term_a or trunc_a:
            break
    env_a.close()
    env_b.close()


def test_fires_when_curl_not_improving(monkeypatch):
    env = _rise_env(seed=2, force_start="flat", k_decouple=1.0,
                     curl_mm=1.0)  # unreachable within the window
    actions = _rng_actions(env, 30, seed=1)
    env.reset()
    monkeypatch.setattr(env, "_curl_dist", lambda: 0.2)  # constant, delta<=0
    infos = []
    for act in actions:
        _, _, term, trunc, info = env.step(act)
        infos.append(dict(info))
        if term or trunc:
            break
    env.close()
    fired = [i for i in infos if "reward_rise_decouple" in i]
    assert fired, "expected the decouple price to fire while curl is flat"
    assert all(i["reward_rise_decouple"] <= 0.0 for i in fired)


def test_silent_when_curl_monotonically_improves(monkeypatch):
    env = _rise_env(seed=2, force_start="flat", k_decouple=1.0,
                     curl_mm=1.0)  # unreachable within the window
    actions = _rng_actions(env, 30, seed=1)
    env.reset()
    seq = {"v": 0.2}

    def _shrinking(self=None):
        seq["v"] = max(seq["v"] - 0.01, 0.0)
        return seq["v"]
    monkeypatch.setattr(env, "_curl_dist", _shrinking)
    infos = []
    for act in actions:
        _, _, term, trunc, info = env.step(act)
        infos.append(dict(info))
        if term or trunc:
            break
    env.close()
    assert all("reward_rise_decouple" not in i for i in infos), (
        "height gained while curl_dist is monotonically shrinking must "
        "never be charged"
    )


def test_crouch_start_exempt():
    env = _rise_env(seed=1, force_start="crouch", k_decouple=1.0,
                     curl_mm=1000.0)
    infos = _run(env, _rng_actions(env, 40))
    env.close()
    assert all("reward_rise_decouple" not in info for info in infos)


def test_latch_is_one_way_not_per_tick_recheck(monkeypatch):
    env = _rise_env(seed=1, force_start="flat", k_decouple=1.0,
                     curl_mm=50.0)
    actions = _rng_actions(env, 20, seed=3)
    env.reset()
    seq = {0: 0.2, 1: 0.2, 2: 0.2, 3: 0.01}  # tucks (<=50mm) at tick 3

    def _fake(self=None):
        i = env._step_i
        if i in seq:
            return seq[i]
        return 0.2  # would read "untucked, flat" again after the latch
    monkeypatch.setattr(env, "_curl_dist", _fake)
    infos = []
    for act in actions:
        _, _, term, trunc, info = env.step(act)
        infos.append(dict(info))
        if term or trunc:
            break
    env.close()
    fired = ["reward_rise_decouple" in i for i in infos]
    latch_idx = fired.index(False, fired.index(True) + 1) if True in fired \
        else None
    # Once curl_dist reads <=50mm (tick index 3, i.e. step_i==3 after
    # _step_finish's own increment), the latch must engage permanently.
    post_latch = fired[4:]
    assert all(f is False for f in post_latch), (
        "latch must stay engaged once curl_dist crosses the threshold, "
        "even though the monkeypatch later reports 'untucked, flat' again"
    )
