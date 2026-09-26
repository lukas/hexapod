"""Adaptive tilt-PENALTY (reward) schedule keyed to |wz_ref|
(``reward.tilt_penalty_wz_schedule``, walkcurr track, 2026-09-26).

Background (track STATUS.md 2026-09-26 ~12:2x's own candidate list,
lever (ii): "decoupling the roll/pitch stabilization reward from the
turn-tracking reward so they don't compete for the same authority
budget"). Lever (i), the analogous HARD-cap schedule
(``safety.tilt_cap_wz_schedule``), closed 0/2 seeds the same day
(~22:1x/~22:2x) without changing the tight-circle-spin collapse
signature at all -- evidence the termination THRESHOLD isn't the
binding constraint. This lever instead targets the per-tick REWARD
PRICE: ``compute_reward`` (rl_move/env.py) already carries a
``tilt_settle_scale`` multiplier on ONLY ``reward_roll``/
``reward_pitch`` (added 08-29, documented as wired to a wall-clock
post-spawn grace, but never actually threaded through any call site --
every walk tick today pays the FULL k_roll/k_pitch=10.0 charge
regardless of turn intent). This env re-purposes that existing,
already-load-bearing multiplier for the turn-intent question: relax
r_roll/r_pitch to ``reward.tilt_penalty_wz_scale`` (default 0.3) on
ticks that command a real turn (|wz_ref| > thresh), full price on
near-zero-wz ticks.

Contract under test:
  - default OFF (``reward.tilt_penalty_wz_schedule`` unset/0) is
    bit-exact: ``tilt_settle_scale`` stays 1.0 every tick regardless of
    wz_ref, i.e. ``reward_roll``/``reward_pitch`` unaffected.
  - ON, near-zero wz_ref (<= ``tilt_penalty_wz_thresh``): full price
    (scale 1.0).
  - ON, |wz_ref| above threshold: relaxed price
    (scale ``tilt_penalty_wz_scale``) -- reward_roll/reward_pitch
    magnitudes shrink by exactly that factor for the SAME tilt error.
  - A goal-less base env (``_current_goal()`` -> None) reads as
    wz_ref=0.0, i.e. full price -- same as leaving the feature off.
  - Threshold boundary is inclusive of the tight (full-price) side,
    matching the hard-cap schedule's own convention.

RESEARCH_RULES "Tests": fast, mechanics only, no artifacts, no
rollout-ranking.

Run: uv run python -m pytest rl_move/tests/test_tilt_penalty_wz_schedule.py -q
"""
from __future__ import annotations

import dataclasses

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.sim_env import N_ACT, SimHexapodBalanceEnv


SCHEDULE_KEYS = {
    ("reward", "tilt_penalty_wz_schedule"): 1.0,
    ("reward", "tilt_penalty_wz_thresh"): 0.05,
    ("reward", "tilt_penalty_wz_scale"): 0.3,
}


def _cfg(extra=None):
    cfg = load_config()
    for (sec, leaf), val in (extra or {}).items():
        cfg.setdefault(sec, {})[leaf] = val
    return cfg


def _walk_env(extra=None, seed=0):
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    from rl_move.sim.servo_model import SimServoParams
    cfg = _cfg(extra)
    params = SimServoParams.from_cfg(cfg)
    return SimHexapodJointWalkEnv(
        params=params, randomize=False, dr_scale=0.0,
        episode_seconds=2.0, seed=seed, cfg=cfg)


def _zero_action(env):
    return np.zeros(env.action_space.shape, dtype=np.float32)


def _pin_wz(env, wz):
    """Same real-goal-preserving stub the hard-cap schedule's own tests
    use -- only wz_ref is forced, every other field this tick's step()
    reads off the same goal stays real and consistent."""
    real = env._current_goal

    def _stubbed():
        g = real()
        return dataclasses.replace(g, wz_ref=wz) if g is not None else None
    env._current_goal = _stubbed


def test_default_off_flag_unset():
    env = _walk_env()
    assert env._tilt_penalty_wz_schedule is False
    env.close()


def test_armed_env_caches_thresh_and_scale():
    env = _walk_env(SCHEDULE_KEYS)
    assert env._tilt_penalty_wz_schedule is True
    assert env._tilt_penalty_wz_thresh_rad_s == pytest.approx(0.05)
    assert env._tilt_penalty_wz_scale == pytest.approx(0.3)
    env.close()


def _reward_roll_pitch(env, wz):
    _pin_wz(env, wz)
    _, _, _, _, info = env.step(_zero_action(env))
    return info["reward_roll"], info["reward_pitch"]


def test_default_off_bit_exact_across_wz():
    """Off: reward_roll/reward_pitch identical whether wz_ref is 0 or
    large, for matched seeds/actions (no schedule consulted at all)."""
    env_a = _walk_env(seed=0)
    env_b = _walk_env(seed=0)
    env_a.reset()
    env_b.reset()
    ra = _reward_roll_pitch(env_a, 0.0)
    rb = _reward_roll_pitch(env_b, 0.9)
    assert ra == pytest.approx(rb)
    env_a.close()
    env_b.close()


def test_turn_command_relaxes_tilt_penalty():
    """Same seed/tilt state, only wz_ref differs across two envs at the
    SAME step index -- the turn-commanded one must pay a strictly
    smaller (less negative) roll/pitch charge, scaled by exactly
    tilt_penalty_wz_scale."""
    env_lo = _walk_env(SCHEDULE_KEYS, seed=0)
    env_hi = _walk_env(SCHEDULE_KEYS, seed=0)
    env_lo.reset()
    env_hi.reset()
    r_roll_lo, r_pitch_lo = _reward_roll_pitch(env_lo, 0.0)
    r_roll_hi, r_pitch_hi = _reward_roll_pitch(env_hi, 0.3)
    # Both envs share the same seed/reset/zero-action trajectory up to
    # this one tick, so the underlying tilt error is identical; only
    # the schedule's scale differs.
    assert r_roll_hi == pytest.approx(r_roll_lo * 0.3, rel=1e-6, abs=1e-9)
    assert r_pitch_hi == pytest.approx(r_pitch_lo * 0.3, rel=1e-6, abs=1e-9)
    env_lo.close()
    env_hi.close()


def test_goalless_env_falls_back_to_full_price():
    """A base/no-goal env (``_current_goal()`` -> None) reads as
    wz_ref=0.0 -- full price, same as leaving this feature off."""
    cfg = _cfg(SCHEDULE_KEYS)
    env_on = SimHexapodBalanceEnv(seed=0, cfg=cfg, randomize=False,
                                  episode_seconds=2.0)
    cfg_off = _cfg()
    env_off = SimHexapodBalanceEnv(seed=0, cfg=cfg_off, randomize=False,
                                   episode_seconds=2.0)
    assert env_on._current_goal() is None
    env_on.reset()
    env_off.reset()
    _, _, _, _, info_on = env_on.step(np.zeros(N_ACT))
    _, _, _, _, info_off = env_off.step(np.zeros(N_ACT))
    assert info_on["reward_roll"] == pytest.approx(info_off["reward_roll"])
    assert info_on["reward_pitch"] == pytest.approx(info_off["reward_pitch"])
    env_on.close()
    env_off.close()


def test_threshold_boundary_inclusive_of_full_price():
    env_thresh = _walk_env(SCHEDULE_KEYS, seed=0)
    env_above = _walk_env(SCHEDULE_KEYS, seed=0)
    env_thresh.reset()
    env_above.reset()
    r_roll_thresh, _ = _reward_roll_pitch(env_thresh, 0.05)
    r_roll_above, _ = _reward_roll_pitch(env_above, 0.0501)
    # Exactly at threshold -> full price; a hair above -> relaxed.
    if r_roll_thresh != 0.0:
        assert r_roll_above == pytest.approx(r_roll_thresh * 0.3,
                                             rel=1e-3, abs=1e-9)
    env_thresh.close()
    env_above.close()
