"""reward.current_hot_bootstrap_steps — trainer-driven softening of
ONLY k_current_hot for an early bootstrap window (standwalk track,
2026-09-12, dualbc7-anchor14coef1-...-termcost3 lineage late-tail
over_current spike).

Root cause (09-12 ~12:5x): env/mean_current_a climbs monotonically as
walk+rise income consolidates over MANY MILLION steps, crossing the
over_current safety cutoff en masse once income growth outpaces a
FLAT per-tick current price. Four independent flat-dose arms
(k_current_hot in {0,3,6}, term_cost_per_remaining_s in {0,3}) all
show the identical dose-independent late-training tail shape; a
flat dose of 12 froze the gait entirely when applied from
initialization on an earlier lineage. This bootstrap is a
STRUCTURALLY different lever from re-dosing the same flat coefficient:
introduce a HIGHER terminal dose gradually (mirrors
apply_loadslip_bootstrap_frac's own convention exactly) so the policy
never sees the freeze-inducing dose from step 0, while the price is
still rising through the late-training window where the overshoot
happens.

Contract under test (mirrors test_loadslip_bootstrap.py's construction
exactly):
  - default (key absent/0) is bit-exact OFF: no bootstrap state, apply
    raises, scale is 1.0, and stepped rewards match a keyless env;
  - ARMED env sits at the FULL charge until broadcast (scale 1.0) —
    same "sits at target, not start" convention as the loadslip
    bootstrap (a safety-relevant charge must default to its validated
    value for any eval/play path that never broadcasts);
  - frac 0 -> min_frac, 0.5 -> midpoint, >=1 -> 1.0, clamped;
  - fail-closed: min_frac outside [0, 1] raises at construction;
  - the live scale actually changes k_current_hot's reward specifically
    (an unrelated reward term must NOT scale).
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.servo_model import SimServoParams

BOOT_KEYS = {
    ("reward", "current_hot_bootstrap_steps"): 1_000_000,
    ("reward", "k_current_hot"): 6.0,
    ("reward", "current_hot_a"): 1.0,
}


def _cfg(extra=None):
    cfg = load_config()
    for (sec, leaf), val in (extra or {}).items():
        cfg.setdefault(sec, {})[leaf] = val
    return cfg


def _env(extra=None, seed=0, episode_seconds=2.0):
    from rl_move.sim.sim_env import SimHexapodBalanceEnv
    cfg = _cfg(extra)
    params = SimServoParams.from_cfg(cfg)
    return SimHexapodBalanceEnv(
        params=params, randomize=False, dr_scale=0.0,
        episode_seconds=episode_seconds, seed=seed, cfg=cfg)


def test_default_off_bit_exact_and_apply_raises():
    env = _env()
    assert env._current_hot_bootstrap is None
    assert env._current_hot_bootstrap_override is None
    assert env._current_hot_scale() == 1.0
    with pytest.raises(RuntimeError, match="not armed"):
        env.apply_current_hot_bootstrap_frac(0.5)
    env0 = _env({("reward", "current_hot_bootstrap_steps"): 0})
    assert env0._current_hot_bootstrap is None


def test_default_off_rewards_bit_exact():
    """An env whose cfg carries steps=0 must produce byte-identical
    rewards to a keyless env on the same seed/action sequence."""
    env_a = _env(seed=3)
    env_b = _env({("reward", "current_hot_bootstrap_steps"): 0},
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
    assert env._current_hot_bootstrap is not None
    assert env._current_hot_bootstrap_override is None
    assert env._current_hot_scale() == 1.0


def test_frac_mapping_and_clamping():
    keys = dict(BOOT_KEYS)
    keys[("reward", "current_hot_bootstrap_min_frac")] = 0.2
    env = _env(keys)
    out = env.apply_current_hot_bootstrap_frac(0.0)
    assert out["scale"] == pytest.approx(0.2)
    out = env.apply_current_hot_bootstrap_frac(0.5)
    assert out["scale"] == pytest.approx(0.6)
    out = env.apply_current_hot_bootstrap_frac(2.0)   # clamps
    assert out["scale"] == pytest.approx(1.0)
    out = env.apply_current_hot_bootstrap_frac(-1.0)  # clamps
    assert out["scale"] == pytest.approx(0.2)
    assert env._current_hot_scale() == pytest.approx(0.2)
    # default min_frac when the key is absent (0.30 — see the
    # sim_env.py __init__ block docstring)
    env2 = _env(BOOT_KEYS)
    out2 = env2.apply_current_hot_bootstrap_frac(0.0)
    assert out2["scale"] == pytest.approx(0.30)


def test_bad_min_frac_fails_closed():
    keys = dict(BOOT_KEYS)
    keys[("reward", "current_hot_bootstrap_min_frac")] = 1.5
    with pytest.raises(ValueError, match="must be in"):
        _env(keys)
    keys[("reward", "current_hot_bootstrap_min_frac")] = -0.1
    with pytest.raises(ValueError, match="must be in"):
        _env(keys)


def test_scale_moves_current_hot_only():
    """The bootstrap live-scale getter must move independently of an
    unrelated dense reward term's own coefficient."""
    keys = dict(BOOT_KEYS)
    keys[("reward", "k_load_even")] = 4.0
    env = _env(keys, seed=7)
    env.reset(seed=7)
    env.apply_current_hot_bootstrap_frac(0.0)  # scale -> min_frac 0.30
    assert env._current_hot_scale() == pytest.approx(0.30)
    env.apply_current_hot_bootstrap_frac(1.0)
    assert env._current_hot_scale() == pytest.approx(1.0)
