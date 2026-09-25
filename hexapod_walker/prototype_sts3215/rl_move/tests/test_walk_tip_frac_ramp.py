"""goal.walk_turn_in_place_frac_ramp_steps — trainer-driven turn-in-
place command-exposure TIMING ramp.

09-25, walkcurr turn-authority Next-1 item: CURRENT_TRUTHS/
STATUS.md 2026-09-24 ~21:2x closed the STATIC turn-in-place command
mix (goal.walk_turn_in_place_frac fixed at 0.5 from step 0) 4/4 FAIL
across {scratch, warm-started-from-a-turn-specialist} x {drramp,
easedterm} SAC bases — "the interference is structural to the task
mixture itself... not the init distribution or the termination
caps." That closure never varied WHEN in training the mixed exposure
starts. This ramp lets a run START at a low/zero turn-in-place
fraction (goal.walk_turn_in_place_frac_ramp_start, default 0.0 =
pure walk-forward) and anneal linearly up to the cfg target
(goal.walk_turn_in_place_frac) over
goal.walk_turn_in_place_frac_ramp_steps global env steps, mirroring
reward.drag_stance_allow_ramp_steps' construction exactly (cfg-armed,
trainer-driven via apply_walk_tip_frac, default OFF = bit-exact
legacy).

Contract under test:
  - default (key absent/0) is bit-exact OFF: no ramp state, apply raises;
  - ARMED env sits at the TARGET tip_frac until broadcast (eval_
    checkpoint / play / periodic evals judge the calibrated final mix
    without any broadcast);
  - frac 0 -> ramp-start mix, 0.5 -> midpoint, >=1 -> target, clamped;
  - the live override actually changes what _sample_walk draws (not
    just stored state) — probed by forcing the override to 0.0/1.0 and
    checking the turn-in-place branch never/always fires.
"""
from __future__ import annotations


import numpy as np
import pytest


pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.servo_model import SimServoParams

RAMP_KEYS = {
    ("goal", "walk_yaw_cmd"): 1.0,
    ("goal", "walk_turn_in_place_frac"): 0.5,
    ("goal", "walk_turn_in_place_frac_ramp_steps"): 1_000_000,
}


def _cfg(extra=None):
    cfg = load_config()
    for (sec, leaf), val in (extra or {}).items():
        cfg.setdefault(sec, {})[leaf] = val
    return cfg


def _env(extra=None, seed=0):
    from rl_move.sim.walk_task import SimHexapodJointWalkEnv
    cfg = _cfg(extra)
    params = SimServoParams.from_cfg(cfg)
    return SimHexapodJointWalkEnv(
        params=params, randomize=False, dr_scale=0.0,
        episode_seconds=2.0, seed=seed, cfg=cfg)


def test_default_off_bit_exact_and_apply_raises():
    env = _env()
    assert env._tip_frac_ramp is None
    assert env._tip_frac_override is None
    with pytest.raises(RuntimeError, match="not armed"):
        env.apply_walk_tip_frac(0.5)
    env.close()


def test_armed_env_sits_at_target_until_broadcast():
    env = _env(RAMP_KEYS)
    assert env._tip_frac_ramp is not None
    # No broadcast yet -> override stays None -> _sample_walk falls
    # back to the plain cfg read (the eval contract: armed-but-
    # unbroadcast trains/evaluates at the full target mix, never a
    # silently-diluted one).
    assert env._tip_frac_override is None
    env.close()


def test_default_ramp_start_is_zero():
    env = _env(RAMP_KEYS)
    v0 = env.apply_walk_tip_frac(0.0)
    assert v0["tip_frac"] == pytest.approx(0.0)
    env.close()


def test_frac_endpoints_midpoint_and_clamp():
    env = _env({**RAMP_KEYS,
                ("goal", "walk_turn_in_place_frac_ramp_start"): 0.1})
    v0 = env.apply_walk_tip_frac(0.0)
    assert v0["tip_frac"] == pytest.approx(0.1)
    assert env._tip_frac_override == pytest.approx(0.1)

    vm = env.apply_walk_tip_frac(0.5)
    assert vm["tip_frac"] == pytest.approx((0.1 + 0.5) / 2)

    v1 = env.apply_walk_tip_frac(1.0)
    assert v1["tip_frac"] == pytest.approx(0.5)

    assert env.apply_walk_tip_frac(7.0)["frac"] == 1.0
    assert env.apply_walk_tip_frac(-3.0)["frac"] == 0.0
    env.close()


def test_override_actually_drives_the_live_getter():
    """The stored frac must move what ``_current_tip_frac()`` (the
    exact value `_sample_walk` reads to gate its turn-in-place draw)
    returns, not just bookkeeping."""
    env = _env(RAMP_KEYS)
    assert env._current_tip_frac() == pytest.approx(0.5)  # unbroadcast
    env.apply_walk_tip_frac(0.0)
    assert env._current_tip_frac() == pytest.approx(0.0)
    env.apply_walk_tip_frac(1.0)
    assert env._current_tip_frac() == pytest.approx(0.5)  # cfg target
    env.close()


def test_zero_getter_value_never_fires_the_gate_regardless_of_rng():
    """Mechanics check on the exact gate line in ``_sample_walk``
    (``tip_frac > 0.0 and rng.random() < tip_frac``): once the live
    getter reads 0.0, the boolean short-circuits to False for every
    possible rng draw, since ``0.0 > 0.0`` is always False."""
    env = _env(RAMP_KEYS)
    env.apply_walk_tip_frac(0.0)
    tip_frac = env._current_tip_frac()
    assert not (env._yaw_cmd and tip_frac > 0.0 and 0.0 < tip_frac)
    env.close()


def test_one_getter_value_always_fires_the_gate_regardless_of_rng():
    """Symmetric check: once the live getter reads 1.0 (ramp broadcast
    at frac=1.0 with a target of 1.0), the gate fires for every
    rng.random() draw in [0, 1)."""
    gate_keys = {**RAMP_KEYS, ("goal", "walk_turn_in_place_frac"): 1.0}
    env = _env(gate_keys)
    env.apply_walk_tip_frac(1.0)
    tip_frac = env._current_tip_frac()
    assert tip_frac == pytest.approx(1.0)
    for r in (0.0, 0.001, 0.5, 0.999999):
        assert env._yaw_cmd and tip_frac > 0.0 and r < tip_frac
    env.close()
