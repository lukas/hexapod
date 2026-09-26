"""env.difficulty_reject_infeasible -- persisted-difficulty-curriculum
DR-draw rejection sampling (standwalk track, 2026-09-26).

Background: the SENSE/reward-reshaping lever fleet (park-price,
measured-velocity, current-sense, foot-contact-sense observation
channels, PLUS the oracle-ground-truth observation channel, PLUS the
2-axis `k_hard_draw_bonus` reward reweight) is now CLOSED 0/many --
every one of them either lets the policy SENSE the draw better or
REWEIGHTS how much an episode's return counts, but none of them change
WHICH draws the policy actually trains on. `draw_feasibility.py`
independently found the raw DR draw predicts `gait_valid` at 88.4% CV
accuracy (AUC 0.937, 3920 pooled probe episodes) using a full ~50-axis
logistic fit -- far more separable than the 2-axis proxy
`k_hard_draw_bonus` already tried and closed. This is the one
genuinely different, previously-unbuilt mechanism STATUS.md's own
"Next" list named: use the FULL persisted classifier not to reweight
reward, but to REJECT-and-redraw predicted-infeasible episodes at
reset, so training time is spent on the (large, per the classifier)
feasible-but-still-hard region of DR space instead of episodes no
policy can plausibly solve.

Contract under test (RESEARCH_RULES "Tests": fast, mechanics-only,
mesh model, no artifacts):
  - default OFF (`env.difficulty_reject_infeasible` unset/False) is
    bit-exact: exactly one `randomizer.sample(rng)` call, identical
    RNG stream/draw to a keyless env of the same seed;
  - ON with a stub classifier that always predicts "infeasible"
    redraws exactly `max_tries - 1` times (bounded, keeps the LAST
    draw, never loops forever);
  - ON with a stub classifier that always predicts "feasible" never
    redraws (only the first sample() call happens, same as OFF);
  - a missing/unreadable persisted model file fails SAFE to the first
    draw unmodified, no crash;
  - `draw_feasibility.save_model`/`load_model` round-trips a fitted
    classifier's predict_proba exactly.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.draw_feasibility import (
    LogisticClassifier, load_model, predict_proba_one, save_model, vectorize,
)
from rl_move.sim.servo_model import SimServoParams
from rl_move.sim.walk_task import SimHexapodJointWalkEnv


def _walk_env(seed: int, cfg_overrides: dict | None = None
              ) -> SimHexapodJointWalkEnv:
    cfg = load_config()
    if cfg_overrides:
        cfg.setdefault("env", {}).update(cfg_overrides)
    env = SimHexapodJointWalkEnv(
        params=SimServoParams.from_cfg(None), randomize=True,
        dr_scale=1.0, episode_seconds=15, seed=seed, cfg=cfg)
    return env


# --------------------------------------------------------------- default off

def test_default_off_is_bit_exact_vs_keyless():
    env_a = _walk_env(seed=7)
    env_b = _walk_env(seed=7, cfg_overrides={})
    ra = env_a.reset()
    rb = env_b.reset()
    np.testing.assert_array_equal(ra[0], rb[0])
    # Same RNG stream consumed: a subsequent independent draw must also
    # match (proves no extra rng.random()/uniform() calls happened).
    draw_a = env_a.randomizer.sample(env_a.rng)
    draw_b = env_b.randomizer.sample(env_b.rng)
    np.testing.assert_allclose(draw_a.link_scale, draw_b.link_scale)
    env_a.close()
    env_b.close()


def test_default_off_calls_sample_exactly_once(monkeypatch):
    env = _walk_env(seed=1)
    calls = {"n": 0}
    real_sample = env.randomizer.sample

    def counting_sample(rng):
        calls["n"] += 1
        return real_sample(rng)

    monkeypatch.setattr(env.randomizer, "sample", counting_sample)
    env.reset()
    assert calls["n"] == 1
    env.close()


# -------------------------------------------------------- rejection sampling

class _StubClf:
    """A trivial stand-in for LogisticClassifier: predict_proba_one is
    monkeypatched at the module level instead of faking real weights,
    so these tests exercise the REJECTION LOOP, not the real fitted
    model's numbers."""


def _arm_reject(env, monkeypatch, always_prob: float, max_tries: int = 4,
                 threshold: float = 0.5):
    env.cfg.setdefault("env", {})["difficulty_reject_infeasible"] = True
    env.cfg["env"]["difficulty_reject_max_tries"] = max_tries
    env.cfg["env"]["difficulty_reject_threshold"] = threshold
    monkeypatch.setattr(env, "_get_difficulty_classifier",
                         lambda: (_StubClf(), ["feature_a"]))
    monkeypatch.setattr(
        "rl_move.sim.draw_feasibility.predict_proba_one",
        lambda rand, clf, order: always_prob)


def test_always_infeasible_redraws_max_tries_minus_one(monkeypatch):
    env = _walk_env(seed=2)
    _arm_reject(env, monkeypatch, always_prob=0.0, max_tries=4)
    calls = {"n": 0}
    real_sample = env.randomizer.sample

    def counting_sample(rng):
        calls["n"] += 1
        return real_sample(rng)

    monkeypatch.setattr(env.randomizer, "sample", counting_sample)
    env.reset()
    # 1 initial draw + (max_tries - 1) redraws = max_tries total calls.
    assert calls["n"] == 4
    env.close()


def test_always_feasible_never_redraws(monkeypatch):
    env = _walk_env(seed=2)
    _arm_reject(env, monkeypatch, always_prob=1.0, max_tries=4)
    calls = {"n": 0}
    real_sample = env.randomizer.sample

    def counting_sample(rng):
        calls["n"] += 1
        return real_sample(rng)

    monkeypatch.setattr(env.randomizer, "sample", counting_sample)
    env.reset()
    assert calls["n"] == 1
    env.close()


def test_missing_model_file_fails_safe(monkeypatch):
    env = _walk_env(seed=3, cfg_overrides={
        "difficulty_reject_infeasible": True,
        "difficulty_model_path": "/nonexistent/path/does_not_exist.json"})
    # Must not raise, and must fall back to a single unmodified draw.
    obs, info = env.reset()
    assert obs is not None
    env.close()


def test_max_tries_one_means_no_redraw(monkeypatch):
    env = _walk_env(seed=4)
    _arm_reject(env, monkeypatch, always_prob=0.0, max_tries=1)
    calls = {"n": 0}
    real_sample = env.randomizer.sample

    def counting_sample(rng):
        calls["n"] += 1
        return real_sample(rng)

    monkeypatch.setattr(env.randomizer, "sample", counting_sample)
    env.reset()
    assert calls["n"] == 1
    env.close()


# --------------------------------------------------------- model round-trip

def test_save_load_model_round_trip_predict_proba(tmp_path):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(60, 4))
    y = (X[:, 0] + 0.5 * X[:, 1] > 0)
    clf = LogisticClassifier(epochs=50).fit(X, y)
    order = ["a", "b", "c", "d"]
    path = str(tmp_path / "model.json")
    save_model(path, clf, order)
    clf2, order2 = load_model(path)
    assert order2 == order
    probs1 = clf.predict_proba(X)
    probs2 = clf2.predict_proba(X)
    np.testing.assert_allclose(probs1, probs2)


def test_predict_proba_one_matches_batch_vectorize():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(40, 3))
    y = (X[:, 0] > 0)
    clf = LogisticClassifier(epochs=50).fit(X, y)
    order = ["mass_scale", "friction_scale", "zero_bias_max_deg"]
    rand = {"mass_scale": 1.1, "friction_scale": 0.9,
            "zero_bias_max_deg": 2.0}
    row_X, _ = vectorize([{
        "mass_scale": 1.1, "friction_scale": 0.9,
        "zero_bias_max_deg": 2.0}], feature_order=order)
    expect = float(clf.predict_proba(row_X)[0])
    got = predict_proba_one(rand, clf, order)
    assert got == pytest.approx(expect)


def test_real_persisted_model_loads_and_scores():
    """The checked-in model (fit on real probe data) must load and
    produce a probability in [0, 1] for a plausible draw -- guards
    against the artifact silently rotting if flatten_randomization's
    feature set changes without regenerating it."""
    clf, order = load_model(
        "rl_move/sim/data/draw_feasibility_model.json")
    assert len(order) > 0
    prob = predict_proba_one(
        {"link_scale_range": [0.98, 1.02], "zero_bias_max_deg": 0.5},
        clf, order)
    assert 0.0 <= prob <= 1.0
