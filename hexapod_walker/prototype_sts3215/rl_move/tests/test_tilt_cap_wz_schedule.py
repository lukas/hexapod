"""Adaptive tilt-termination-cap schedule keyed to |wz_ref|
(``safety.tilt_cap_wz_schedule``, walkcurr track, 2026-09-26).

Background (track STATUS.md 2026-09-25 ~13:5x / 2026-09-26 ~12:2x,
~16:0x): the SAC walkyaw acquisition family trains under a single
constant relaxed fall-termination tilt cap ("eased cap",
``safety.max_roll_deg``/``max_pitch_deg`` 30 -> 45) for the WHOLE
episode. Both state-machine composition (a dedicated walk-only
specialist) and task-space turn parameterization (a discrete
relative-heading offset instead of a continuous yaw rate) closed 0/2
seeds on this SAME contract with an identical tilt-and-topple collapse
signature -- naming the fixed-cap contract itself, not the command
family, as the remaining suspect. This lever tightens the cap back to
the strict value on near-zero-|wz_ref| ticks (straight walking, holds)
and only relaxes it to the wide cap on ticks that actually command a
turn, so an unstable straight-walking basin can no longer hide behind
a cap meant for turning.

Contract under test:
  - default OFF (``safety.tilt_cap_wz_schedule`` unset/0) is bit-exact:
    ``env.safety.max_roll``/``max_pitch`` stay exactly what
    ``SafetyLayer.__init__`` set from ``safety.max_roll_deg``/
    ``max_pitch_deg``, unchanged by stepping, regardless of the goal's
    wz_ref.
  - ON, near-zero wz_ref (<= ``tilt_cap_wz_thresh``): the tight cap
    applies.
  - ON, |wz_ref| above threshold: the wide (originally-configured) cap
    applies.
  - ON, a goal-less base env (``_current_goal()`` -> None, e.g. a
    plain balance/rise env with no goal_traj): reads as wz_ref=0.0,
    i.e. the tight cap -- same as leaving this feature off with
    ``safety.max_roll_deg``/``max_pitch_deg`` already set to the tight
    value.
  - The schedule re-asserts every tick (mirrors the existing slew-ramp
    re-assert pattern) -- switching the goal's wz_ref between ticks
    switches the live cap on the very next step.

RESEARCH_RULES "Tests": fast, mechanics only, no artifacts, no
rollout-ranking.

Run: uv run python -m pytest rl_move/tests/test_tilt_cap_wz_schedule.py -q
"""
from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.sim_env import N_ACT, SimHexapodBalanceEnv


SCHEDULE_KEYS = {
    ("safety", "max_roll_deg"): 45.0,
    ("safety", "max_pitch_deg"): 45.0,
    ("safety", "tilt_cap_wz_schedule"): 1.0,
    ("safety", "tilt_cap_tight_roll_deg"): 30.0,
    ("safety", "tilt_cap_tight_pitch_deg"): 30.0,
    ("safety", "tilt_cap_wz_thresh"): 0.05,
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
    """Wrap the env's real ``_current_goal`` so every field except
    ``wz_ref`` stays exactly what the live walk-goal sampler produced
    this tick -- only the ONE axis under test is forced, everything
    else (height_ref, vx_ref, ...) that the rest of ``step()`` reads
    off the same goal this tick stays real and consistent."""
    real = env._current_goal

    def _stubbed():
        g = real()
        return dataclasses.replace(g, wz_ref=wz) if g is not None else None
    env._current_goal = _stubbed


def test_default_off_bit_exact():
    env = _walk_env({("safety", "max_roll_deg"): 45.0,
                      ("safety", "max_pitch_deg"): 45.0})
    assert env._tilt_cap_wz_schedule is False
    assert env.safety.max_roll == pytest.approx(math.radians(45.0))
    assert env.safety.max_pitch == pytest.approx(math.radians(45.0))
    env.reset()
    _pin_wz(env, 999.0)
    env.step(_zero_action(env))
    # No re-assert at all when the flag is off -- the wz_ref stub above
    # is never even consulted, so an absurd value has zero effect.
    assert env.safety.max_roll == pytest.approx(math.radians(45.0))
    assert env.safety.max_pitch == pytest.approx(math.radians(45.0))
    env.close()


def test_armed_env_caches_wide_and_tight_values():
    env = _walk_env(SCHEDULE_KEYS)
    assert env._tilt_cap_wz_schedule is True
    assert env._tilt_cap_wide_roll_rad == pytest.approx(math.radians(45.0))
    assert env._tilt_cap_wide_pitch_rad == pytest.approx(math.radians(45.0))
    assert env._tilt_cap_tight_roll_rad == pytest.approx(math.radians(30.0))
    assert env._tilt_cap_tight_pitch_rad == pytest.approx(math.radians(30.0))
    assert env._tilt_cap_wz_thresh_rad_s == pytest.approx(0.05)
    env.close()


def test_near_zero_wz_uses_tight_cap():
    env = _walk_env(SCHEDULE_KEYS)
    env.reset()
    _pin_wz(env, 0.0)
    env.step(_zero_action(env))
    assert env.safety.max_roll == pytest.approx(math.radians(30.0))
    assert env.safety.max_pitch == pytest.approx(math.radians(30.0))
    env.close()


def test_turn_command_uses_wide_cap():
    env = _walk_env(SCHEDULE_KEYS)
    env.reset()
    _pin_wz(env, 0.3)
    env.step(_zero_action(env))
    assert env.safety.max_roll == pytest.approx(math.radians(45.0))
    assert env.safety.max_pitch == pytest.approx(math.radians(45.0))
    env.close()


def test_goalless_env_falls_back_to_tight_cap():
    """A base/no-goal env (``_current_goal()`` -> None) reads as
    wz_ref=0.0 -- the same tight cap as an explicit zero command."""
    cfg = _cfg(SCHEDULE_KEYS)
    env = SimHexapodBalanceEnv(seed=0, cfg=cfg, randomize=False,
                               episode_seconds=2.0)
    assert env._current_goal() is None
    env.reset()
    env.step(np.zeros(N_ACT))
    assert env.safety.max_roll == pytest.approx(math.radians(30.0))
    assert env.safety.max_pitch == pytest.approx(math.radians(30.0))
    env.close()


def test_schedule_re_asserts_every_tick():
    env = _walk_env(SCHEDULE_KEYS)
    env.reset()
    _pin_wz(env, 0.3)
    env.step(_zero_action(env))
    assert env.safety.max_roll == pytest.approx(math.radians(45.0))
    _pin_wz(env, 0.0)
    env.step(_zero_action(env))
    assert env.safety.max_roll == pytest.approx(math.radians(30.0))
    env.close()


def test_threshold_boundary_inclusive_of_tight():
    env = _walk_env(SCHEDULE_KEYS)
    env.reset()
    # Exactly at threshold -> still tight (<=).
    _pin_wz(env, 0.05)
    env.step(_zero_action(env))
    assert env.safety.max_roll == pytest.approx(math.radians(30.0))
    # Just above threshold -> wide.
    _pin_wz(env, 0.0501)
    env.step(_zero_action(env))
    assert env.safety.max_roll == pytest.approx(math.radians(45.0))
    env.close()
