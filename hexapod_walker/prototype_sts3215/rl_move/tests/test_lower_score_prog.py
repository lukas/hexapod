"""LOWER depth-ratchet income (reward.lower_score_prog, walkcurr track,
2026-09-13).

Background (RL_LOG/STATUS.md 09-13 ~21:2x): the `lowerpartial-{s0,s1}`
pair CLOSED the start-state-curriculum family 2/2 seeds -- the ~-6mm
"park above the wall" freeze survives both `lowerheavy` (exposure-only)
and `lowerpartial` (mid-descent-seeding). Both verdicts named the same
next lever: lower has no ratcheted "credit for genuine descent" analog
of `reward_rise_score_prog` at all -- only the moving-reference
`reward_rise_progress`/milestone terms (which also apply to lower, per
their own "works for rise and lower alike" comment), and those price
the CURRENT tick's ref-tracking delta, not a standing income for having
actually gotten lower.

`reward.lower_score_prog` adds `reward_lower_score`: a potential-based
ratchet on `lower_depth_frac` (0..1, fraction of the episode's own
signed target depth reached, clamped, computed by the pure
`lower_depth_frac()` helper), paid only on new best-ever depth reached
this episode (same construction as `_score_best`), plus a continuous
`reward_lower_track` tracking-error charge (NOT ratcheted) so idle
parking at any partial depth keeps costing instead of going quiet once
its one-time ratchet income is collected.

Contract under test:
  - `lower_depth_frac()` pure math: 0 at/above the start pose, 1 at/past
    the signed target, clamped, and 0.0 for a non-lower (h_target>=0)
    target so a caller never needs an extra branch.
  - default OFF (`reward.lower_score_prog` unset) never exposes
    `reward_lower_score`/`lower_depth_frac` and leaves
    `reward_rise_progress` non-zero-eligible during a lower episode
    (legacy path untouched).
  - ON: `reward_lower_score` is always >= 0 (a ratchet income can never
    go negative) and its lifetime sum tracks the ratcheted best depth
    (`k_lower_score_prog * final_best_depth_frac`, up to a paid-per-tick
    quantization epsilon); `reward_rise_progress`/`reward_rise_milestone`
    are exactly zero every tick of that same episode (the old stream is
    replaced, not stacked); and a policy that never moves keeps paying a
    strictly negative `reward_lower_track` every tick (parking is not
    free).

RESEARCH_RULES "Tests": fast, mechanics + one short wired-env
integration check, no rollout ranking, no artifacts, mesh model.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.goal_task import SimHexapodGoalEnv
from rl_move.sim.balance_helpers import lower_depth_frac


# ---------------------------------------------------------------------------
# Pure math


@pytest.mark.parametrize("h_rel_m,h_target_m,want", [
    (0.0, -0.05, 0.0),        # at the start pose
    (-0.025, -0.05, 0.5),     # halfway down
    (-0.05, -0.05, 1.0),      # exactly at target
    (-0.08, -0.05, 1.0),      # past target: clamped
    (0.01, -0.05, 0.0),       # rose above start: clamped, not negative
    (-0.025, 0.05, 0.0),      # non-lower (positive) target -> always 0
    (-0.025, 0.0, 0.0),       # zero target (guarded, no div-by-zero)
])
def test_lower_depth_frac_math(h_rel_m, h_target_m, want):
    got = lower_depth_frac(h_rel_m, h_target_m)
    assert got == pytest.approx(want, abs=1e-9)


def test_lower_depth_frac_always_unit_clamped():
    for h_rel_m in (0.02, 0.0, -0.01, -0.03, -0.05, -0.07, -1.0):
        for h_target_m in (-0.02, -0.05, -0.1):
            f = lower_depth_frac(h_rel_m, h_target_m)
            assert 0.0 <= f <= 1.0


# ---------------------------------------------------------------------------
# Wired integration: forced LOWER episode


def _lower_env(seed: int, score_prog: float = 0.0) -> SimHexapodGoalEnv:
    cfg = load_config()
    cfg.setdefault("goal", {})["lower_height_mm"] = [40, 40]
    cfg["goal"]["lower_hold_s"] = 0.2
    cfg.setdefault("episode", {})["seconds"] = 6
    if score_prog:
        cfg.setdefault("reward", {})["lower_score_prog"] = score_prog
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
    return out


def test_default_off_never_exposes_the_new_keys_and_legacy_income_lives():
    env = _lower_env(seed=1)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 300, action)
    env.close()
    assert not any("reward_lower_score" in i for i in infos)
    assert not any("lower_depth_frac" in i for i in infos)
    assert any("reward_rise_progress" in i for i in infos), \
        "test setup never entered a lower episode with a real target"


def test_gate_on_ratchet_income_never_negative_and_replaces_legacy_stream():
    env = _lower_env(seed=1, score_prog=1.0)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 300, action)
    env.close()
    scored = [i for i in infos if "reward_lower_score" in i]
    assert scored, "lower_score_prog gate never fired"
    assert all(i["reward_lower_score"] >= -1e-9 for i in scored)
    assert all(0.0 <= i["lower_depth_frac"] <= 1.0 for i in scored)
    # legacy moving-reference income is replaced (exactly zero), not
    # stacked alongside the new ratchet.
    assert all(i.get("reward_rise_progress", 0.0) == 0.0 for i in scored)
    assert all(i.get("reward_rise_milestone", 0.0) == 0.0 for i in scored)
    # a genuinely idle policy (zero action from a settled plant pose)
    # keeps paying the continuous tracking charge every tick -- parking
    # is not free even after any early ratchet income is banked.
    assert all(i["reward_lower_track"] < 0.0 for i in scored)


def test_gate_on_lifetime_ratchet_income_matches_best_depth_reached():
    env = _lower_env(seed=1, score_prog=1.0)
    action = np.zeros(env.action_space.shape, dtype=np.float32)
    infos = _run(env, 300, action)
    env.close()
    scored = [i for i in infos if "reward_lower_score" in i]
    k = 100.0  # k_lower_score_prog default
    lifetime = sum(i["reward_lower_score"] for i in scored)
    best_depth = max(i["lower_depth_frac"] for i in scored)
    # The ratchet baseline is seeded with the FIRST tick's own depth_frac
    # (same "don't pay the starting posture" convention as _score_best),
    # so lifetime income tracks the best depth reached PAST that seed,
    # not the raw best_depth from an arbitrary zero baseline.
    first_depth = scored[0]["lower_depth_frac"]
    assert lifetime == pytest.approx(
        k * max(best_depth - first_depth, 0.0), abs=1e-6)
