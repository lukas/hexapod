"""reward.k_current_pretuck — pre-tuck current price (walkcurr rise
track, 2026-09-14).

Background: `probe_rise_current_envelope.py` (RL_LOG 2026-09-14 ~03:1x)
found the mesh-native scripted rise reference clears the corrected
+66%-mass mesh's over_current trip, with real (~16%) margin, ONLY
because it stays near-zero-torque while tucking the feet under the
body and draws real current only AFTER the bridge pose is reached.
Every rise-pricing lever tried before this one (current-headroom-gate,
curl-geometry-gate on the height ramp, two-phase-freeze, curl-pretrain)
targeted "reach the target height/curl faster or more gently"; none
separately priced "don't draw current at all until tucked." This term
does exactly that, keyed on the SAME state-conditioned progress signal
`_rise_gate_tick` already reads (`_curl_dist()` — live FK-measured
feet-to-plant-footprint distance, not a scripted clock, not a motion
prior): while curl_dist has not yet reached the bridge-pose threshold,
any per-servo current above a tight bar is charged quadratically; once
tucked, this term latches OFF for the rest of the episode so the
legitimate press afterward is untaxed by it.

Contract under test:
  - default OFF (`reward.k_current_pretuck` unset/0) is bit-exact: no
    `reward_current_pretuck` key ever appears, and stepped rewards are
    byte-identical to a keyless env on the same seed/action sequence.
  - ON, threshold already satisfied at reset (flat start's own
    curl_dist is comfortably under a loose threshold): the term never
    fires, from the very first tick — mirrors gate-hold's own
    "unlocks immediately" case.
  - ON, threshold unreachable within the tested window and a permissive
    per-servo bar of 0.0 A (so any nonzero current is charged): the
    term fires (present, <= 0) on every early tick.
  - ON, crouch start: the term never fires even with an aggressive
    (already-satisfied-anyway) threshold — the explicit crouch
    exemption mirrors `_rise_gate_tick`'s own.
  - Latch mechanics (monkeypatched `_curl_dist`, no physics
    dependence): once curl_dist crosses the threshold on some tick,
    the term stays silent on every later tick even if curl_dist is
    made to read as "untucked" again — a one-way latch, not a
    per-tick re-check.

RESEARCH_RULES "Tests": fast, mechanics only, mesh model default, no
artifacts, no rollout-ranking.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import SimHexapodGoalEnv
from rl_move.sim.servo_model import SimServoParams
from rl_move.sim.sim_env import SimHexapodBalanceEnv


def _rise_env(seed: int, force_start: str = "flat",
              k_pretuck: float = 0.0,
              curl_mm: float | None = None,
              hot_a: float | None = None) -> SimHexapodGoalEnv:
    cfg = load_config()
    cfg.setdefault("goal", {})["rise_height_mm"] = [90, 90]
    cfg["goal"]["rise_hold_s"] = 0.3
    cfg["goal"]["rise_hold_min_s"] = 0.3
    cfg["goal"]["rise_ramp_s"] = 2.0
    cfg.setdefault("episode", {})["seconds"] = 8
    if k_pretuck:
        cfg.setdefault("reward", {})["k_current_pretuck"] = k_pretuck
        if curl_mm is not None:
            cfg["reward"]["current_pretuck_curl_mm"] = curl_mm
        if hot_a is not None:
            cfg["reward"]["current_pretuck_hot_a"] = hot_a
    env = SimHexapodGoalEnv(cfg=cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 1.0 if m == "rise" else 0.0)
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
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 60, action)
    env.close()
    assert all("reward_current_pretuck" not in info for info in infos)


def test_default_off_rewards_bit_exact():
    cfg_a = load_config()
    cfg_b = load_config()
    cfg_b.setdefault("reward", {})["k_current_pretuck"] = 0.0
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
        assert "reward_current_pretuck" not in info_a
        assert "reward_current_pretuck" not in info_b
        if term_a or trunc_a:
            break
    env_a.close()
    env_b.close()


def test_on_threshold_already_met_never_fires():
    # flat start curl_dist ~176mm; a loose 200mm threshold is already
    # satisfied at reset, so the term must be silent from tick 0 --
    # mirrors the curl-gate's own "unlocks immediately" case.
    env = _rise_env(seed=1, force_start="flat", k_pretuck=1.0,
                     curl_mm=200.0, hot_a=0.0)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 60, action)
    env.close()
    assert all("reward_current_pretuck" not in info for info in infos)


def test_on_threshold_unreached_charges_negative():
    # flat start curl_dist ~176mm, an unreachable 1mm threshold within
    # this short a window, and a permissive 0.0 A bar so any nonzero
    # current is charged -- the term must fire and be <= 0 on early
    # ticks.
    env = _rise_env(seed=1, force_start="flat", k_pretuck=1.0,
                     curl_mm=1.0, hot_a=0.0)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 10, action)
    env.close()
    fired = [info for info in infos if "reward_current_pretuck" in info]
    assert fired, "expected the pre-tuck price to fire while untucked"
    assert all(info["reward_current_pretuck"] <= 0.0 for info in fired)


def test_crouch_start_exempt():
    env = _rise_env(seed=1, force_start="crouch", k_pretuck=1.0,
                     curl_mm=1000.0, hot_a=0.0)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 60, action)
    env.close()
    assert all("reward_current_pretuck" not in info for info in infos)


def test_latch_is_one_way_not_per_tick_recheck(monkeypatch):
    env = _rise_env(seed=1, force_start="flat", k_pretuck=1.0,
                     curl_mm=50.0, hot_a=0.0)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    env.reset()
    seq = {0: 0.2, 1: 0.2, 2: 0.2, 3: 0.01}  # tucks (<=50mm) at tick 3
    real_curl_dist = env._curl_dist

    def _fake(self=None):
        i = env._step_i
        if i in seq:
            return seq[i]
        return 0.2  # would read "untucked" again after the latch
    monkeypatch.setattr(env, "_curl_dist", _fake)
    fired = []
    for _ in range(8):
        _, _, term, trunc, info = env.step(action)
        fired.append("reward_current_pretuck" in info)
        if term or trunc:
            break
    env.close()
    # Ticks 0-2 (pre-latch, step_i becomes 1,2,3 after _step_finish's
    # own increment) untucked -> fires; from the tick that reads
    # curl_dist<=threshold onward it must latch and stay silent even
    # though the monkeypatch later reports "untucked" (0.2) again.
    assert fired[0] is True
    assert any(fired[:4]), "expected at least one pre-latch firing tick"
    latch_idx = fired.index(False, 0) if False in fired else None
    assert latch_idx is not None, "latch never engaged"
    assert all(f is False for f in fired[latch_idx:]), (
        "latch must stay engaged once curl_dist crosses the threshold, "
        "even if curl_dist is reported as untucked again later")
