"""reward.loadslip_excess_log_scale — replace the hard excess CAP with a
strictly-increasing log-compressed price (standwalk track, 2026-09-22).

Close-out of the cap-rescale family: `cw-walk50hz-gru-dr08-ladder-
loadslipcap-{cap45,cap60}-s0` (both NOGO this cycle) showed that raising
`loadslip_excess_cap`'s VALUE does not help dr=0.8 -- it reprices the
SAME measured slip (env/walk_loadslip_ratio statistically flat ~6.9-7.2
across cap=3.0/4.5/6.0) harder, because `min(excess, cap)` has exactly
ZERO gradient in `excess` once `excess > cap`: every tail episode above
the ceiling is priced identically no matter how much worse it is. This
key replaces the pricing SHAPE (not another cap dose): `priced_excess =
log_scale * log1p(excess / log_scale)` matches the raw linear charge's
slope at excess=0 (small-excess dosing unchanged) but grows only
logarithmically for large excess -- bounded like the cap (no single tick
can blow up the per-tick reward) while remaining strictly increasing
(gradient `1/(1+excess/log_scale) > 0` for every finite excess), so even
the worst tail episode still has SOME pressure to reduce slip further.

Contract under test (direct call into `loaded_slip_gate`, no rollout):
  - default (key absent/0, or any value <=0) is bit-exact OFF: falls
    through to the existing hard-cap-or-uncapped legacy path unchanged;
  - log_scale > 0 takes PRIORITY over loadslip_excess_cap (mutually
    exclusive pricing shapes for the same quantity, not stackable);
  - the log price matches the closed-form `scale * log1p(excess/scale)`
    exactly, is strictly increasing in excess (checked via a discrete
    finite-difference gradient at a large excess value), and its slope
    at excess=0 equals the uncapped linear charge's slope (both = 1);
  - telemetry (`walk_loadslip_excess_raw`) keeps reporting the true
    (unpriced) excess exactly as the hard-cap variant does.
"""
from __future__ import annotations

import math

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


def test_default_off_falls_through_to_legacy_uncapped():
    env0 = _env()
    env_explicit0 = _env({("reward", "loadslip_excess_log_scale"): 0.0})
    env_neg = _env({("reward", "loadslip_excess_log_scale"): -1.0})
    r0, _ = _price(env0, slip_m=9.7, prog_m=0.1)
    r1, _ = _price(env_explicit0, slip_m=9.7, prog_m=0.1)
    r2, _ = _price(env_neg, slip_m=9.7, prog_m=0.1)
    # raw excess 94, uncapped legacy price
    expected = -10.0 * 94.0 * env0.dt
    assert r0 == pytest.approx(expected, rel=0, abs=1e-9)
    assert r0 == r1 == r2


def test_default_off_still_respects_legacy_hard_cap_when_that_is_set():
    env = _env({("reward", "loadslip_excess_cap"): 3.0})
    reward, _ = _price(env, slip_m=9.7, prog_m=0.1)
    expected = -10.0 * 3.0 * env.dt
    assert reward == pytest.approx(expected, rel=0, abs=1e-9)


def test_log_scale_takes_priority_over_hard_cap_when_both_set():
    env_log_only = _env({("reward", "loadslip_excess_log_scale"): 3.0})
    env_both = _env({("reward", "loadslip_excess_log_scale"): 3.0,
                      ("reward", "loadslip_excess_cap"): 3.0})
    r_log, _ = _price(env_log_only, slip_m=9.7, prog_m=0.1)
    r_both, _ = _price(env_both, slip_m=9.7, prog_m=0.1)
    # raw excess 94; hard cap=3.0 would price exactly -10*3*dt (30 vs
    # the log price below), so this also checks the two shapes differ.
    hard_cap_price = -10.0 * 3.0 * env_log_only.dt
    assert r_log == r_both
    assert r_log != pytest.approx(hard_cap_price)


def test_log_price_matches_closed_form_and_telemetry_stays_raw():
    scale = 3.0
    env = _env({("reward", "loadslip_excess_log_scale"): scale})
    # ratio = 9.7/0.1 = 97; excess = 94
    reward, info = _price(env, slip_m=9.7, prog_m=0.1)
    excess = 94.0
    expected_priced = scale * math.log1p(excess / scale)
    expected_reward = -10.0 * expected_priced * env.dt
    assert reward == pytest.approx(expected_reward, rel=0, abs=1e-9)
    assert info["reward_loadslip_excess"] == pytest.approx(expected_reward)
    # telemetry keeps reporting the true (uncompressed) excess, same
    # contract as the hard-cap sibling
    assert info["walk_loadslip_excess_raw"] == pytest.approx(excess)


def test_log_price_is_strictly_increasing_even_at_large_excess():
    scale = 3.0
    env = _env({("reward", "loadslip_excess_log_scale"): scale})
    # two large, close excess values (via progress denominator) far
    # past where a hard cap of the same scale would have gone fully
    # flat -- the log price must still show a nonzero (negative-going)
    # gradient at the tail, unlike the hard cap's exact plateau.
    r_a, _ = _price(env, slip_m=97.0, prog_m=1.0)   # excess = 94
    r_b, _ = _price(env, slip_m=197.0, prog_m=1.0)  # excess = 194
    assert r_b < r_a  # strictly more negative (more charged), never flat


def test_log_price_slope_at_zero_excess_matches_uncapped_linear_slope():
    scale = 3.0
    env_log = _env({("reward", "loadslip_excess_log_scale"): scale})
    env_uncapped = _env()
    # tiny excess (ratio just above loadslip_ok=3.0) -> both shapes
    # should price it almost identically (log1p(x)~=x for small x)
    r_log, _ = _price(env_log, slip_m=3.001, prog_m=1.0)
    r_uncapped, _ = _price(env_uncapped, slip_m=3.001, prog_m=1.0)
    assert r_log == pytest.approx(r_uncapped, rel=1e-3)
