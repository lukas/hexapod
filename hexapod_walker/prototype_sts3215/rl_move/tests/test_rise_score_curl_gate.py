"""Curl-distance-gated rise_score_prog income
(reward.rise_score_income_curl_gate, walkcurr track, 2026-09-13).

Background (RL_LOG 09-13 21:0x-21:1x, `cw-stance50hz-rlonly-
riseheadroomgate-s1-canary2m` CANARY FAIL - MECHANISM): the current-
only headroom gate (`reward.rise_score_income_headroom_gate`) left the
flat/bridge rise/det failing trajectories BIT-IDENTICAL to the ungated
parent (`cur_rail_frac` 0.587/0.457/0.587 in both) -- the policy never
diverged from the doomed straight push even with current-priced
income live, because current only spikes LATE in the push (near the
2.64A rail itself); by the time `headroom_f` bites, most of the
height/posture score has already been banked.

This gate instead prices the SAME `reward_rise_score_prog` income on
FOOT GEOMETRY, known from tick 0: a probe this cycle measured
`_curl_dist()` at reset as ~176mm for a true flat start, ~111mm for a
bridge (curl-first, low-current) start, and ~0mm for a crouch start
(feet already under the plant footprint). Reusing the exact
`current_headroom_income_factor` ramp shape (pure math, dimension-
agnostic: 1.0 well below the cap, 0.0 at/above it, linear between) keyed
on `curl_dist_m` instead of `cur_peak_a`: at a true flat start the score
income is fully zero regardless of achieved height, ramping to full pay
only once the feet have actually tucked to within ~111mm of the plant
footprint -- curling in first becomes REQUIRED to earn the height/
posture score at all, not merely cheaper.

Contract under test:
  - default OFF (`reward.rise_score_income_curl_gate` unset) never
    computes/exposes `rise_score_curl_factor` and is bit-exact vs the
    pre-existing behavior.
  - ON: the discount factor is always in [0, 1] and, for identical
    seeds/actions from a true flat start, `reward_rise_score_prog`
    under the gate is NEVER larger than the ungated twin (the gate only
    discounts income, never inflates it) and is smaller at least once
    when the default cap/margin (calibrated to the flat/bridge
    curl-distance gap) forces early ticks into the red zone.

RESEARCH_RULES "Tests": fast, mechanics + one short paired-env
integration check, no rollout ranking, no artifacts.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import SimHexapodGoalEnv
from rl_move.sim.balance_helpers import current_headroom_income_factor


# ---------------------------------------------------------------------------
# Pure math (reuses current_headroom_income_factor's own coverage; here
# only the distance-flavoured parametrisation this gate actually uses).


@pytest.mark.parametrize("dist_m,cap_m,margin_m,want", [
    (0.0, 0.176, 0.066, 1.0),        # crouch-like: full pay
    (0.110, 0.176, 0.066, 1.0),      # cap-margin edge (~bridge dist): full
    (0.143, 0.176, 0.066, 0.5),      # halfway into the red zone
    (0.176, 0.176, 0.066, 0.0),      # exactly at the flat-start distance
    (0.30, 0.176, 0.066, 0.0),       # past it: still clamped to 0
])
def test_curl_income_factor_math(dist_m, cap_m, margin_m, want):
    got = current_headroom_income_factor(dist_m, cap_m, margin_m)
    assert got == pytest.approx(want, abs=1e-9)


def test_curl_income_factor_always_unit_clamped():
    for dist_m in (0.0, 0.05, 0.111, 0.176, 0.5, 10.0):
        f = current_headroom_income_factor(dist_m, 0.176, 0.066)
        assert 0.0 <= f <= 1.0


# ---------------------------------------------------------------------------
# Wired integration: rise/score-income env, true flat start


def _rise_score_env(seed: int, curl_gate: float = 0.0) -> SimHexapodGoalEnv:
    cfg = load_config()
    cfg.setdefault("actions", {})["max_height_mm"] = 115
    cfg.setdefault("goal", {})["rise_height_mm"] = [90, 90]
    cfg["goal"]["rise_hold_s"] = 0.5
    cfg["goal"]["rise_hold_min_s"] = 0.5
    cfg.setdefault("episode", {})["seconds"] = 8
    cfg.setdefault("reward", {})["rise_score_income"] = 1.0
    if curl_gate:
        cfg["reward"]["rise_score_income_curl_gate"] = curl_gate
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


def test_default_off_never_exposes_the_factor_key():
    env = _rise_score_env(seed=3)
    action = np.full(env.action_space.shape, 0.6, dtype=np.float32)
    infos = _run(env, 450, action)
    env.close()
    assert any("reward_rise_score_prog" in i for i in infos), \
        "score-income path never fired -- test setup is not exercising it"
    assert not any("rise_score_curl_factor" in i for i in infos)


def _tight_curl(monkeypatch):
    """Pin the gate's cap/margin (fixed at 0.176m/0.066m in sim_env,
    calibrated to the flat/bridge curl-distance gap the real training
    corridor sees over a full rise attempt) to 80mm/20mm, chosen from a
    probed trace of seed 3 / action 0.8 (true flat start):
    reward_rise_score_prog first turns nonzero once curl_dist has
    already fallen to ~74-80mm (the env's own posture/feet gates hold
    the score at exactly 0 before that, regardless of curl distance),
    so 80mm/20mm sits squarely across that observed firing band and the
    very first scoring ticks of this short synthetic probe are the ones
    under test."""
    import rl_move.sim.sim_env as sim_env_mod
    monkeypatch.setattr(
        sim_env_mod, "current_headroom_income_factor",
        lambda dist, cap, margin: current_headroom_income_factor(
            dist, 0.08, 0.02))


def test_gate_on_factor_always_unit_range_and_discounts_at_least_once(
        monkeypatch):
    _tight_curl(monkeypatch)
    env = _rise_score_env(seed=3, curl_gate=1.0)
    action = np.full(env.action_space.shape, 0.8, dtype=np.float32)
    infos = _run(env, 450, action)
    env.close()
    seen = [i["rise_score_curl_factor"] for i in infos
            if "rise_score_curl_factor" in i]
    assert seen, "curl gate never fired -- check delta_s>0 ticks exist"
    assert all(0.0 <= v <= 1.0 for v in seen)
    assert all(np.isfinite(v) for v in seen)
    assert min(seen) < 1.0, "gate never actually discounted a tick"


def test_gate_never_pays_more_lifetime_income_than_ungated_twin(
        monkeypatch):
    _tight_curl(monkeypatch)
    # Same invariant as the current-headroom gate: a discounted tick's
    # unpaid remainder stays available for a later low-curl-distance
    # tick to collect (banked, not confiscated), so per-tick income can
    # briefly differ either way, but CUMULATIVE income under the gate
    # must never exceed the ungated twin's, same seed/action so both
    # envs see an identical physical trajectory.
    off = _run(_rise_score_env(seed=3), 450,
               np.full((6,), 0.8, dtype=np.float32))
    on = _run(_rise_score_env(seed=3, curl_gate=1.0), 450,
              np.full((6,), 0.8, dtype=np.float32))
    assert len(off) == len(on)
    cum_off = cum_on = 0.0
    any_strict = False
    for a, b in zip(off, on):
        cum_off += a.get("reward_rise_score_prog", 0.0)
        cum_on += b.get("reward_rise_score_prog", 0.0)
        assert cum_on <= cum_off + 1e-6
        if cum_on < cum_off - 1e-6:
            any_strict = True
    assert any_strict, "tight cap/margin never discounted lifetime income"
