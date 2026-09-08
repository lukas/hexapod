"""reward.walk_loadslip_bootstrap_steps — trainer-driven softening of
ONLY k_loadslip_excess for an early bootstrap window (walkcurr track,
08-23, fwd4 dig-in follow-up).

Four straight rung-1 from-scratch arms (fwd1, fwd2-swing,
fwd2-swingterm800, fwd3-chargeramp, fwd4-logstd0, fwd4-entboost — all
FAIL) froze into a tilt-safe splayed crouch with
env/walk_freeprog_score flat/negative the whole 2M budget. The
walk-charge ramp (reward.walk_charge_ramp_steps) already loosens the
three DISCOVERY-FRICTION charges (k_park_duty, k_walk_idle_charge,
k_walk_heading) but deliberately EXCLUDES k_loadslip_excess (bank
finding: scaling it down TOGETHER with the other three at their
shared min_frac=0.15 made 'skate'/'shuffle' beat every honest
standing/wrong-way behavior). This is a narrower, SEPARATE lever: only
k_loadslip_excess, only for a short early bootstrap window, annealing
back UP to the full bank-proven dose — the untried lever the
walkcurr/STATUS.md "Next" section names.

Contract under test (mirrors test_walk_charge_ramp.py's construction
exactly):
  - default (key absent/0) is bit-exact OFF: no bootstrap state, apply
    raises, scale is 1.0, and stepped rewards match a keyless env;
  - ARMED env sits at the FULL charge until broadcast (scale 1.0);
  - frac 0 -> min_frac, 0.5 -> midpoint, >=1 -> 1.0, clamped;
  - fail-closed: min_frac outside [0, 1] raises at construction;
  - the live scale actually changes k_loadslip_excess specifically
    (heading, unrelated, must NOT scale).
"""
from __future__ import annotations


import numpy as np
import pytest


pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.servo_model import SimServoParams

BOOT_KEYS = {
    ("reward", "walk_loadslip_bootstrap_steps"): 1_000_000,
    ("reward", "k_walk_heading"): 0.5,
    ("reward", "k_loadslip_excess"): 4.5,
}


def _cfg(extra=None):
    cfg = load_config()
    for (sec, leaf), val in (extra or {}).items():
        cfg.setdefault(sec, {})[leaf] = val
    return cfg


def _env(extra=None, seed=0, episode_seconds=2.0):
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = _cfg(extra)
    params = SimServoParams.from_cfg(cfg)
    return SimHexapodJointWalkEnv(
        params=params, randomize=False, dr_scale=0.0,
        episode_seconds=episode_seconds, seed=seed, cfg=cfg)


def test_default_off_bit_exact_and_apply_raises():
    env = _env()
    assert env._ls_bootstrap is None
    assert env._ls_bootstrap_override is None
    assert env._loadslip_excess_scale() == 1.0
    with pytest.raises(RuntimeError, match="not armed"):
        env.apply_loadslip_bootstrap_frac(0.5)
    env0 = _env({("reward", "walk_loadslip_bootstrap_steps"): 0})
    assert env0._ls_bootstrap is None


def test_default_off_rewards_bit_exact():
    """An env whose cfg carries steps=0 must produce byte-identical
    rewards to a keyless env on the same seed/action sequence."""
    env_a = _env(seed=3)
    env_b = _env({("reward", "walk_loadslip_bootstrap_steps"): 0},
                  seed=3)
    env_a.reset(seed=3)
    env_b.reset(seed=3)
    rng = np.random.default_rng(0)
    for _ in range(25):
        act = rng.uniform(-1, 1, env_a.action_space.shape).astype(
            np.float32)
        _, ra, term_a, trunc_a, _ = env_a.step(act)
        _, rb, term_b, trunc_b, _ = env_b.step(act)
        assert ra == rb
        assert (term_a, trunc_a) == (term_b, trunc_b)
        if term_a or trunc_a:
            break


def test_armed_unbroadcast_sits_at_full_charge():
    env = _env(BOOT_KEYS)
    assert env._ls_bootstrap is not None
    assert env._ls_bootstrap_override is None
    assert env._loadslip_excess_scale() == 1.0


def test_frac_mapping_and_clamping():
    keys = dict(BOOT_KEYS)
    keys[("reward", "walk_loadslip_bootstrap_min_frac")] = 0.2
    env = _env(keys)
    out = env.apply_loadslip_bootstrap_frac(0.0)
    assert out["excess_scale"] == pytest.approx(0.2)
    out = env.apply_loadslip_bootstrap_frac(0.5)
    assert out["excess_scale"] == pytest.approx(0.6)
    out = env.apply_loadslip_bootstrap_frac(2.0)   # clamps
    assert out["excess_scale"] == pytest.approx(1.0)
    out = env.apply_loadslip_bootstrap_frac(-1.0)  # clamps
    assert out["excess_scale"] == pytest.approx(0.2)
    assert env._loadslip_excess_scale() == pytest.approx(0.2)
    # default min_frac when the key is absent (0.65 — measured
    # separately from the walk-charge ramp's 0.40; see the
    # module docstring / retired pre-v2 semantics bank)
    env2 = _env(BOOT_KEYS)
    out2 = env2.apply_loadslip_bootstrap_frac(0.0)
    assert out2["excess_scale"] == pytest.approx(0.65)


def test_bad_min_frac_fails_closed():
    keys = dict(BOOT_KEYS)
    keys[("reward", "walk_loadslip_bootstrap_min_frac")] = 1.5
    with pytest.raises(ValueError, match="must be in"):
        _env(keys)
    keys[("reward", "walk_loadslip_bootstrap_min_frac")] = -0.1
    with pytest.raises(ValueError, match="must be in"):
        _env(keys)


