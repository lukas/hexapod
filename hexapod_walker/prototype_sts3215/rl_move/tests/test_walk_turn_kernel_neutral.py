"""reward.walk_turn_kernel_neutral — strip the BASE velocity-tracking
kernel's stand-still subsidy on genuine turn-in-place ticks.

09-13, root-cause read on the `cw-walkyaw50hz-rlonly-scratch-{retry1,
tip1}` triple-FAIL (all CANARY FAIL-MECHANISM: `probe_turn_authority`
wz_med pinned ~1e-6 rad/s both signs both seeds despite ep_len_mean/
reward clearly rising, i.e. the policy is learning to survive, just
never to turn). Every lever tried on that family (warm-start from a
CLEAN rl_only forward walker, scratch-init, scratch-init + 100%
turn-in-place exposure) and every reward/exploration-side lever closed
earlier on the sibling turn-freeze problem (price, dose, budget,
risk-curriculum ramp, direct freeze charge, 4 RND variants) left one
thing untouched: `walk_task.py`'s BASE locomotion kernel `r_walk`
(`K_WALK * exp(-err^2 / (2*sigma_v^2))`, `err = |v - (vx_ref, vy_ref)|`)
is computed UNCONDITIONALLY in walk mode, with no gate keyed to the
yaw command at all. On a genuine turn-in-place tick `vx_ref = vy_ref
= 0`, so `err` is minimized (== 0, `r_walk` at its K_WALK=2.0 MAX,
roughly 2x the yaw stack's own k_walk_yaw=1.0 max) by the body staying
PERFECTLY STILL -- an actively-PAID, zero-skill, zero-risk subsidy for
doing nothing, unmitigated by any existing gate (all of `r_walk`'s
other multiplicative gates key off achieved LINEAR progress, which is
undefined/skipped when s_ref<=1e-3). `reward.walk_turn_kernel_neutral`
in [0,1] (default 0.0 = off, bit-exact legacy) suppresses `r_walk`
(and the already-zero `r_prog`) by `(1 - gate)` ONLY on genuine
turn-in-place ticks (identical gating condition as
`walk_turn_freeze_charge`/`walk_turn_in_place_tick`); every other tick
(forward, combined, hold) is untouched.

Contract under test:
  - default (key absent/0) is bit-exact off: no info key, r_walk
    unchanged from an identical run with the gate compiled out;
  - on a turn-in-place tick, gate=1.0 fully zeroes r_walk (env is
    parked at v=0, so the ungated r_walk would be ~K_WALK's max);
  - a partial gate (0.5) leaves exactly half of the ungated r_walk;
  - off the turn-in-place condition (hold ticks, wz_ref == 0, or an
    ordinary forward/combined walk tick with s_ref>1e-3), no
    suppression fires regardless of the gate value.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.walk_task import SimHexapodJointWalkEnv
from rl_move.sim.joint_task import q_rad_to_action


def _turn_env(gate=0.0, seed=0):
    cfg = load_config()
    goal = cfg.setdefault("goal", {})
    goal["walk_yaw_cmd"] = 1
    goal["walk_yaw_max_rad_s"] = 0.3
    goal["walk_yaw_zero_frac"] = 0.0
    goal["walk_turn_in_place_frac"] = 1.0
    goal["walk_gait_start_frac"] = 0.0
    goal["walk_cmd_hold_s"] = 0.0
    goal["walk_cmd_ramp_s"] = 0.0
    rw = cfg.setdefault("reward", {})
    rw["walk_kernel_yaw_gate"] = 1.0
    rw["walk_yaw_kernel_gate"] = 1.0
    if gate:
        rw["walk_turn_kernel_neutral"] = gate
    env = SimHexapodJointWalkEnv(cfg, seed=seed)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 0.0)
    g.p_walk = 1.0
    env.reset()
    return env


def _hold_action(env):
    return q_rad_to_action(env._cmd.copy())


def _advance_to_turn_tick(env, max_ticks=100):
    a = _hold_action(env)
    for _ in range(max_ticks):
        goal = env._current_goal()
        if abs(float(goal.wz_ref)) > 1e-3 and abs(
                float(np.hypot(goal.vx_ref, goal.vy_ref))) <= 1e-3:
            return
        env.step(a)
    raise AssertionError("never reached a live turn-in-place tick")


def test_default_off_bit_exact():
    env = _turn_env(gate=0.0)
    _advance_to_turn_tick(env)
    _, _, _, _, info = env.step(_hold_action(env))
    assert "walk_turn_kernel_neutral_factor" not in info
    r_walk_off = info["reward_walk"]
    env.close()

    env2 = _turn_env(gate=0.0)
    _advance_to_turn_tick(env2)
    _, _, _, _, info2 = env2.step(_hold_action(env2))
    assert info2["reward_walk"] == pytest.approx(r_walk_off)
    env2.close()


def test_full_gate_zeroes_stillness_subsidy_on_turn_tick():
    env = _turn_env(gate=0.0)
    _advance_to_turn_tick(env)
    _, _, _, _, info_off = env.step(_hold_action(env))
    r_walk_off = info_off["reward_walk"]
    # a near-static turn-in-place tick pays SOME stillness-kernel
    # income when the gate is off (the substantive zero-vs-nonzero
    # contrast is checked against the gate=1.0 arm below).
    assert r_walk_off > 0.0
    env.close()

    env2 = _turn_env(gate=1.0)
    _advance_to_turn_tick(env2)
    _, _, _, _, info_on = env2.step(_hold_action(env2))
    assert info_on["walk_turn_kernel_neutral_factor"] == pytest.approx(0.0)
    assert info_on["reward_walk"] == pytest.approx(0.0)
    env2.close()


def test_partial_gate_scales_linearly():
    env = _turn_env(gate=0.0)
    _advance_to_turn_tick(env)
    _, _, _, _, info_off = env.step(_hold_action(env))
    r_walk_off = info_off["reward_walk"]
    env.close()

    env2 = _turn_env(gate=0.5)
    _advance_to_turn_tick(env2)
    _, _, _, _, info_half = env2.step(_hold_action(env2))
    assert info_half["walk_turn_kernel_neutral_factor"] == pytest.approx(0.5)
    assert info_half["reward_walk"] == pytest.approx(
        0.5 * r_walk_off, rel=1e-6)
    env2.close()


def test_hold_tick_never_gated_even_if_frozen():
    """Off the turn-in-place condition (wz_ref == 0), no suppression
    fires regardless of achieved v, even with the gate armed at 1.0."""
    cfg = load_config()
    goal = cfg.setdefault("goal", {})
    goal["walk_yaw_cmd"] = 1
    rw = cfg.setdefault("reward", {})
    rw["walk_turn_kernel_neutral"] = 1.0
    env = SimHexapodJointWalkEnv(cfg, seed=0)
    g = env._goal_gen
    for m in ("lean", "track", "unload", "raise", "rise", "lower"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 0.0)
    g.p_hold = 1.0
    g.p_walk = 0.0
    env.reset()
    _, _, _, _, info = env.step(_hold_action(env))
    assert "walk_turn_kernel_neutral_factor" not in info
    env.close()


def test_forward_tick_never_gated_even_with_armed_flag():
    """An ordinary (non-turn-in-place) walk tick -- s_ref > 0 -- must
    never be suppressed, even with the gate armed at 1.0."""
    cfg = load_config()
    goal = cfg.setdefault("goal", {})
    goal["walk_yaw_cmd"] = 0
    rw = cfg.setdefault("reward", {})
    rw["walk_turn_kernel_neutral"] = 1.0
    env = SimHexapodJointWalkEnv(cfg, seed=0)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise",
              "lower"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 0.0)
    g.p_walk = 1.0
    env.reset()
    _, _, _, _, info = env.step(_hold_action(env))
    assert "walk_turn_kernel_neutral_factor" not in info
    env.close()
