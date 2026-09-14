"""ease.gravity_scale_dr_{lo,hi} (2026-09-14, walkcurr flat-start-rise
gravity-ANNEAL grid closure — see sim_env.py comment at the definition
site for the full rationale). Per-episode PERSISTENT MIXTURE of
gravity difficulty (each env independently samples one scalar in
[lo, hi] every reset via the same self.rng every other DR axis uses),
as opposed to the pre-existing ease.gravity_scale single GLOBAL value
a sched.* ramp can only move sequentially (and which the 3-arm anneal
grid showed forgets the easy end once the ramp passes it, at any LR).

Contract under test:
- default OFF (both keys unset) is bit-exact — falls through to the
  existing single-value ease.gravity_scale path untouched;
- setting only one of the pair raises;
- inverted / non-positive range raises;
- lo == hi behaves like the single-value case at that scale (no draw);
- lo < hi: repeated resets draw DIFFERENT values spanning the range
  (this is the whole point — a persistent mixture, not one value per
  process);
- each draw actually reaches model.opt.gravity magnitude (direction
  preserved), same application path as the single-value mechanism;
- composes with ease.rise_flat_only exactly like the single-value
  case (non-qualifying episodes are undone back to nominal).
"""
from __future__ import annotations

import numpy as np
import pytest

mujoco = pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.sim_env import SimHexapodBalanceEnv


def _make_env(ease: dict | None, *, randomize: bool = False,
              seed: int = 0, **kw):
    cfg = load_config()
    if ease is not None:
        cfg["ease"] = dict(ease)
    return SimHexapodBalanceEnv(seed=seed, cfg=cfg, randomize=randomize,
                                episode_seconds=2.0, **kw)


def test_dr_off_is_bitexact():
    obs_ref, _ = _make_env(None, seed=3).reset()
    env = _make_env(None, seed=3)
    o, _ = env.reset()
    assert np.array_equal(o, obs_ref)
    assert env._ease_g == 1.0


def test_dr_one_sided_raises():
    env = _make_env({"gravity_scale_dr_lo": 0.4})
    with pytest.raises(ValueError, match="must both be set"):
        env.reset()
    env2 = _make_env({"gravity_scale_dr_hi": 1.0})
    with pytest.raises(ValueError, match="must both be set"):
        env2.reset()


def test_dr_inverted_range_raises():
    env = _make_env({"gravity_scale_dr_lo": 1.0, "gravity_scale_dr_hi": 0.4})
    with pytest.raises(ValueError, match="lo <= hi"):
        env.reset()


def test_dr_nonpositive_raises():
    env = _make_env({"gravity_scale_dr_lo": 0.0, "gravity_scale_dr_hi": 1.0})
    with pytest.raises(ValueError, match="lo <= hi"):
        env.reset()


def test_dr_lo_eq_hi_is_single_value():
    env = _make_env({"gravity_scale_dr_lo": 0.5, "gravity_scale_dr_hi": 0.5})
    env.reset()
    assert env._ease_g == pytest.approx(0.5)
    assert np.allclose(env.model.opt.gravity,
                       0.5 * np.asarray(env._base_gravity), rtol=1e-9)


def test_dr_draws_span_the_range_across_resets():
    env = _make_env({"gravity_scale_dr_lo": 0.4, "gravity_scale_dr_hi": 1.0},
                    seed=7)
    draws = []
    for _ in range(60):
        env.reset()
        draws.append(env._ease_g)
    draws = np.asarray(draws)
    assert draws.min() >= 0.4 and draws.max() <= 1.0
    # a real persistent mixture: not collapsed to one value, and it
    # actually reaches near both ends over enough draws
    assert draws.std() > 0.05
    assert draws.min() < 0.55
    assert draws.max() > 0.85


def test_dr_reaches_model_gravity_with_dr_on():
    env = _make_env({"gravity_scale_dr_lo": 0.4, "gravity_scale_dr_hi": 0.4},
                    randomize=True, dr_scale=0.5, seed=1)
    base = _make_env(None, randomize=True, dr_scale=0.5, seed=1)
    env.reset()
    base.reset()
    g_e = np.asarray(env._ep_rand.gravity_vec, float)
    g_b = np.asarray(base._ep_rand.gravity_vec, float)
    assert np.allclose(g_e, 0.4 * g_b, rtol=1e-9)
    assert np.allclose(g_e / np.linalg.norm(g_e),
                       g_b / np.linalg.norm(g_b), rtol=1e-9)
    assert np.allclose(env.model.opt.gravity, g_e)


def _rise_only_cfg(**goal_overrides):
    g = {"p_hold": 0.0, "p_lean": 0.0, "p_track": 0.0, "p_unload": 0.0,
         "p_raise": 0.0, "p_rise": 1.0, "p_lower": 0.0}
    g.update(goal_overrides)
    return {"goal": g}


def test_dr_composes_with_rise_flat_only_scoping():
    """The DR-range mechanism composes with the existing scoping gate
    exactly like the single-value mechanism does: a flat-start rise
    episode gets an eased draw, a bridge-start rise episode in the
    SAME config (same env, same cfg) is undone back to nominal."""
    from rl_move.sim.joint_task import SimHexapodJointGoalEnv

    cfg = _rise_only_cfg()
    cfg["ease"] = {"gravity_scale_dr_lo": 0.4, "gravity_scale_dr_hi": 0.4,
                   "rise_flat_only": 1.0}

    env_flat = SimHexapodJointGoalEnv(randomize=False, cfg=cfg)
    env_flat._goal_gen.force_rise_start = "flat"
    env_flat.reset()
    assert env_flat._ease_g == pytest.approx(0.4)

    env_bridge = SimHexapodJointGoalEnv(randomize=False, cfg=cfg)
    env_bridge._goal_gen.force_rise_start = "bridge"
    env_bridge.reset()
    assert env_bridge._ease_g == 1.0
