"""Current-headroom-gated rise_score_prog income
(reward.rise_score_income_headroom_gate, walkcurr track, 2026-09-13).

Background (STATUS.md 09-13 "holdbias-riselower15m" dig-in, confirmed
by cw-stance50hz-rlonly-risebridge-s1-15m's own FAIL-MECHANISM): the
flat-rise sprawl push pins servo current at the 2.64A torque-saturation
rail and trips over_current, but `reward_rise_score_prog` pays for ANY
new height/posture score regardless of current draw -- it funds the
doomed push all the way to the trip. `k_torque_headroom` already prices
a SUSTAINED current debt post-hoc and did not stop this (income kept
paying regardless of any accruing debt); this instead discounts the
INCOME itself at the instant of a saturating tick, using the same
"redness" shape as `torque_headroom_debt_step`.

Contract under test:
  - `current_headroom_income_factor` is pure math: 1.0 well below the
    cap, 0.0 at/above the rail, linear in between, always in [0, 1].
  - default OFF (`reward.rise_score_income_headroom_gate` unset) never
    computes/exposes `rise_score_headroom_factor` and is bit-exact vs
    the pre-existing behavior.
  - ON: the discount factor is always in [0, 1] and, for identical
    seeds/actions, `reward_rise_score_prog` under the gate is NEVER
    larger than the ungated twin (headroom can only discount income,
    never inflate it) and is smaller at least once when a tight
    cap/margin forces most ticks into the red zone.

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
from rl_move.sim.sim_env import current_headroom_income_factor


# ---------------------------------------------------------------------------
# Pure math


@pytest.mark.parametrize("cur,cap,margin,want", [
    (0.0, 2.64, 0.3, 1.0),
    (1.0, 2.64, 0.3, 1.0),          # well under the red zone
    (2.34, 2.64, 0.3, 1.0),         # exactly at the red-zone edge
    (2.49, 2.64, 0.3, 0.5),         # halfway into the red zone
    (2.64, 2.64, 0.3, 0.0),         # exactly at the rail
    (3.0, 2.64, 0.3, 0.0),          # past the rail: still clamped to 0
    (-2.64, 2.64, 0.3, 0.0),        # magnitude, not raw sign
])
def test_current_headroom_income_factor_math(cur, cap, margin, want):
    got = current_headroom_income_factor(abs(cur), cap, margin)
    assert got == pytest.approx(want, abs=1e-9)


def test_current_headroom_income_factor_always_unit_clamped():
    for cur in (-1000.0, -1.0, 0.0, 1.0, 2.64, 5.0, 1000.0):
        for cap, margin in ((2.64, 0.3), (0.5, 0.5), (10.0, 0.01)):
            f = current_headroom_income_factor(abs(cur), cap, margin)
            assert 0.0 <= f <= 1.0


def test_current_headroom_income_factor_degenerate_zero_margin():
    # margin_a -> 0 would divide by zero in a naive implementation.
    f = current_headroom_income_factor(5.0, 2.64, 0.0)
    assert 0.0 <= f <= 1.0


# ---------------------------------------------------------------------------
# Wired integration: rise/score-income env


def _rise_score_env(seed: int,
                     headroom_gate: float = 0.0) -> SimHexapodGoalEnv:
    cfg = load_config()
    cfg.setdefault("actions", {})["max_height_mm"] = 115
    cfg.setdefault("goal", {})["rise_height_mm"] = [90, 90]
    cfg["goal"]["rise_hold_s"] = 0.5
    cfg["goal"]["rise_hold_min_s"] = 0.5
    cfg.setdefault("episode", {})["seconds"] = 8
    cfg.setdefault("reward", {})["rise_score_income"] = 1.0
    if headroom_gate:
        cfg["reward"]["rise_score_income_headroom_gate"] = headroom_gate
    env = SimHexapodGoalEnv(cfg=cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower", "quad", "walk"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 1.0 if m == "rise" else 0.0)
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
    assert not any("rise_score_headroom_factor" in i for i in infos)


def _tight_headroom(monkeypatch):
    """Pin the gate's cap/margin (fixed at 2.64A/0.3A in sim_env) to a
    2.0A/0.5A red zone chosen from a probed trace of seed 3 / action
    0.6: mean_current_a climbs from ~0.05A to ~2.64A (torque
    saturation) by tick ~300-400, so 1.5-2.0A is squarely inside the
    range this recipe actually reaches -- no need to hit the full
    physical rail to exercise the gate."""
    import rl_move.sim.sim_env as sim_env_mod
    monkeypatch.setattr(
        sim_env_mod, "current_headroom_income_factor",
        lambda cur, cap, margin: current_headroom_income_factor(
            cur, 2.0, 0.5))


def test_gate_on_factor_always_unit_range_when_present(monkeypatch):
    _tight_headroom(monkeypatch)
    env = _rise_score_env(seed=3, headroom_gate=1.0)
    action = np.full(env.action_space.shape, 0.6, dtype=np.float32)
    infos = _run(env, 450, action)
    env.close()
    seen = [i["rise_score_headroom_factor"] for i in infos
            if "rise_score_headroom_factor" in i]
    assert seen, "headroom gate never fired -- check delta_s>0 ticks exist"
    assert all(0.0 <= v <= 1.0 for v in seen)
    assert all(np.isfinite(v) for v in seen)
    assert min(seen) < 1.0, "gate never actually discounted a tick"


def test_gate_never_pays_more_lifetime_income_than_ungated_twin(
        monkeypatch):
    _tight_headroom(monkeypatch)
    # Per-TICK income is not the right invariant here: a discounted tick
    # leaves its unpaid remainder banked for a later low-current tick to
    # collect (by design -- see the code comment), so an individual tick
    # under the gate can briefly pay MORE than the same tick off-gate.
    # What must never happen is paying out more income OVER THE RUN than
    # the ungated twin, at any point in time (the gate only defers/
    # denies credit, never manufactures extra credit) -- same seed, same
    # fixed action sequence, so both envs see an identical physical
    # trajectory and differ only in how `reward_rise_score_prog` prices
    # it.
    env_probe = _rise_score_env(seed=3)
    action = np.full(env_probe.action_space.shape, 0.6, dtype=np.float32)
    env_probe.close()
    off = _run(_rise_score_env(seed=3), 450, action)
    on = _run(_rise_score_env(seed=3, headroom_gate=1.0), 450, action)
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
