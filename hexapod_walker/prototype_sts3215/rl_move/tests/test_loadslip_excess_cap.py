"""reward.loadslip_excess_cap — bound the k_loadslip_excess per-tick
penalty's tail (standwalk track, 2026-09-21).

`walk_reward_gates.loaded_slip_gate`'s direct excess charge prices
`max(ratio - loadslip_ok, 0.0)` with NO ceiling: `ratio` (slip_m /
max(progress_m, floor)) has a floor on its denominator but nothing
bounds its numerator, so a foot that keeps sliding while progress
stays pinned near the floor can push the excess arbitrarily far past
`loadslip_max`. This is the named mechanism behind two independent
collapses: `cw-walk50hz-mlp-powercurrent-widedr-s0-r2` (env/
reward_loadslip_excess growing monotonically to -1.36/tick, crashing
ep_rew_mean from +938 to a -450..-750 flat plateau) and the GRU
fromcont DR-ladder's third collapse `cw-walk50hz-gru-dr050-ladder-s0`
(env/walk_loadslip_ratio climbing to ~6.1-6.2, reward falling then
flattening negative). See rl_docs/tracks/standwalk/STATUS.md 2026-09-21
~22:1x/~22:2x.

This mirrors the existing, already-shipped
`walk_leg_loadslip_ratio_excess_cap` sibling in the same file
(0.0=OFF / >0 caps) — this is the first live dose of that pattern,
applied to the plain (non-per-leg) `k_loadslip_excess` charge.

Contract under test (direct call into `loaded_slip_gate`, no rollout):
  - default (key absent/0, or any value <=0) is bit-exact OFF: the
    charge uses the raw uncapped excess, identical to pre-cap code;
  - cap > 0 clamps ONLY the priced excess (`reward_loadslip_excess`),
    never the raw `walk_loadslip_ratio`/measured excess telemetry;
  - an episode whose raw excess never reaches the cap is unaffected
    (cap is a ceiling, not a rescale).
"""
from __future__ import annotations

import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.servo_model import SimServoParams
from rl_move.sim import walk_reward_gates


BASE_KEYS = {
    ("reward", "k_loadslip_excess"): 10.0,
    ("reward", "loadslip_ok"): 3.0,
    ("reward", "loadslip_max"): 6.0,
}


def _cfg(extra=None):
    cfg = load_config()
    for (sec, leaf), val in {**BASE_KEYS, **(extra or {})}.items():
        cfg.setdefault(sec, {})[leaf] = val
    return cfg


def _env(extra=None, seed=0):
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = _cfg(extra)
    params = SimServoParams.from_cfg(cfg)
    env = SimHexapodJointWalkEnv(
        params=params, randomize=False, dr_scale=0.0,
        episode_seconds=2.0, seed=seed, cfg=cfg)
    env.reset()
    return env


def _price(env, slip_m, prog_m, s_ref=0.2):
    """Pin the cumulative loadslip bookkeeping to an exact
    slip/progress pair (prev_on all False => this call adds nothing
    new to either accumulator) then call the gate directly."""
    env._ls_prev_on = [False] * 6
    env._ls_slip_m = slip_m
    env._ls_prog_m = prog_m
    info = {}
    r_prog, r_walk, reward, support_gate = walk_reward_gates.loaded_slip_gate(
        env, 0.0, info, 0.0, 0.0, 0.0, s_ref, 1.0)
    return reward, info


def test_default_off_uncapped_raw_excess_charged():
    env = _env()
    # ratio = 9.7 / 0.1 = 97; excess = 97 - 3 = 94
    reward, info = _price(env, slip_m=9.7, prog_m=0.1)
    expected = -10.0 * 94.0 * env.dt
    assert reward == pytest.approx(expected, rel=0, abs=1e-9)
    assert info["reward_loadslip_excess"] == pytest.approx(expected)
    assert info["walk_loadslip_excess_raw"] == pytest.approx(94.0)


def test_zero_and_negative_cap_are_bit_exact_off():
    env0 = _env()
    env_explicit0 = _env({("reward", "loadslip_excess_cap"): 0.0})
    env_neg = _env({("reward", "loadslip_excess_cap"): -5.0})
    r0, _ = _price(env0, slip_m=9.7, prog_m=0.1)
    r1, _ = _price(env_explicit0, slip_m=9.7, prog_m=0.1)
    r2, _ = _price(env_neg, slip_m=9.7, prog_m=0.1)
    assert r0 == r1 == r2


def test_cap_bounds_the_priced_excess_not_the_raw_one():
    env = _env({("reward", "loadslip_excess_cap"): 3.0})
    # raw excess 94, cap 3.0 -> priced excess must clamp to 3.0
    reward, info = _price(env, slip_m=9.7, prog_m=0.1)
    expected = -10.0 * 3.0 * env.dt
    assert reward == pytest.approx(expected, rel=0, abs=1e-9)
    assert info["reward_loadslip_excess"] == pytest.approx(expected)
    # telemetry keeps reporting the true (uncapped) excess
    assert info["walk_loadslip_excess_raw"] == pytest.approx(94.0)


def test_cap_is_a_ceiling_not_a_rescale_below_the_cap():
    env_capped = _env({("reward", "loadslip_excess_cap"): 3.0})
    env_uncapped = _env()
    # ratio = 3.5/1.0 = 3.5; excess = 0.5, well under the 3.0 cap
    r_capped, _ = _price(env_capped, slip_m=3.5, prog_m=1.0)
    r_uncapped, _ = _price(env_uncapped, slip_m=3.5, prog_m=1.0)
    assert r_capped == pytest.approx(r_uncapped)
