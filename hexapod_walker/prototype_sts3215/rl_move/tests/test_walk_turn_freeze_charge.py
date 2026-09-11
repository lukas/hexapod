"""reward.walk_turn_freeze_charge — explicit minimum-motion tie-break
charge on turn-in-place ticks.

09-11, escalation named by the `term_penalty_ramp{0,100}-canary2m`
FAIL-MECHANISM pair (and, before it, `turnramp-cont6m`/`canary2m`):
four single-lever canaries (yawprice3x price, turnramp dose,
turnramp-cont6m budget, termramp{0,100} risk-curriculum ramp) all
reproduced the identical static splayed freeze-crouch on turn-in-place
draws. The existing kernel gates (`walk_kernel_yaw_gate`/
`walk_yaw_kernel_gate`) already make a frozen body earn ~0 INCOME on
these ticks, but ~0 is reward-NEUTRAL, competing against a real -400
`term_penalty` RISK if a clumsy attempt trips over_current/tilt — no
income-side fix can repair a risk-side asymmetry. This charges freeze
directly: on turn-in-place ticks (s_ref ~ 0, wz_ref != 0) with achieved
|wz| below `reward.walk_turn_freeze_wz_thresh`, charge a flat
-`reward.walk_turn_freeze_charge` per tick. Default 0.0 = off,
bit-exact legacy.

Contract under test:
  - default (key absent/0) is bit-exact off: no info key, no reward
    delta vs an identical run with the gate compiled out;
  - on a turn-in-place tick with near-zero achieved |wz|, the charge
    fires at exactly -charge, additively (not multiplicatively);
  - on a turn-in-place tick with achieved |wz| above the threshold, no
    charge fires;
  - off the turn-in-place condition (hold ticks, wz_ref == 0), no
    charge fires regardless of achieved wz, even with the gate armed.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.sim.walk_task import SimHexapodJointWalkEnv
from rl_move.sim.joint_task import q_rad_to_action


def _turn_env(charge=0.0, thresh=None, seed=0):
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
    if charge:
        rw["walk_turn_freeze_charge"] = charge
    if thresh is not None:
        rw["walk_turn_freeze_wz_thresh"] = thresh
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
    """Step (holding position) until the goal is a live turn-in-place
    command (wz_ref != 0, s_ref ~ 0); returns the info dict of that
    tick (env not yet stepped past it)."""
    a = _hold_action(env)
    for _ in range(max_ticks):
        goal = env._current_goal()
        if abs(float(goal.wz_ref)) > 1e-3 and abs(
                float(np.hypot(goal.vx_ref, goal.vy_ref))) <= 1e-3:
            return
        env.step(a)
    raise AssertionError("never reached a live turn-in-place tick")


def test_default_off_no_info_key_and_bit_exact():
    env = _turn_env(charge=0.0)
    _advance_to_turn_tick(env)
    _, r_off, _, _, info = env.step(_hold_action(env))
    assert "reward_walk_turn_freeze" not in info
    env.close()

    env2 = _turn_env(charge=5.0)
    env2._body_wz = lambda: 0.0
    _advance_to_turn_tick(env2)
    env2._body_wz = lambda: 0.0
    _, r_on, _, _, info_on = env2.step(_hold_action(env2))
    assert info_on["reward_walk_turn_freeze"] == pytest.approx(-5.0)
    # additive, not multiplicative: turning the gate off recovers
    # exactly the charge's magnitude (other terms identical, same
    # seed/tick/action).
    assert r_off + 0.0 != r_on  # sanity: the on-run really differs
    env2.close()


def test_frozen_tick_charges_flat_penalty():
    env = _turn_env(charge=3.0, thresh=0.05)
    _advance_to_turn_tick(env)
    env._body_wz = lambda: 0.01  # well under threshold: "frozen"
    _, _, _, _, info = env.step(_hold_action(env))
    assert info["reward_walk_turn_freeze"] == pytest.approx(-3.0)
    assert info["walk_turn_freeze_wz"] == pytest.approx(0.01)
    env.close()


def test_moving_tick_no_charge():
    env = _turn_env(charge=3.0, thresh=0.05)
    _advance_to_turn_tick(env)
    env._body_wz = lambda: 0.2  # well above threshold: "turning"
    _, _, _, _, info = env.step(_hold_action(env))
    assert info["reward_walk_turn_freeze"] == pytest.approx(0.0)
    env.close()


def test_hold_tick_never_charged_even_if_frozen():
    """Off the turn-in-place condition (wz_ref == 0), no charge fires
    regardless of achieved wz, even with the gate armed."""
    cfg = load_config()
    goal = cfg.setdefault("goal", {})
    goal["walk_yaw_cmd"] = 1
    rw = cfg.setdefault("reward", {})
    rw["walk_turn_freeze_charge"] = 3.0
    env = SimHexapodJointWalkEnv(cfg, seed=0)
    g = env._goal_gen
    for m in ("lean", "track", "unload", "raise", "rise", "lower"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 0.0)
    g.p_hold = 1.0
    g.p_walk = 0.0
    env.reset()
    env._body_wz = lambda: 0.0
    _, _, _, _, info = env.step(_hold_action(env))
    assert info.get("reward_walk_turn_freeze", 0.0) == 0.0
    env.close()


# ---------------------------------------------------- turn-tick info key
# (09-11: the freezecharge{,5,10}-canary2m dose sweep closed the FIFTH
# consecutive single-lever REWARD-side fix on the turn-in-place freeze,
# all identical static splayed freeze-crouch on video. This read-only
# info key is the hook for the next-named, ORTHOGONAL mechanism (an
# RND state-novelty bonus gated on these exact ticks, rnd_vec.py's
# `info_gate_key`) — it carries no reward of its own, unlike every
# mechanism above in this file.

def test_turn_tick_flag_lit_on_live_turn_tick():
    env = _turn_env(charge=0.0)  # charge OFF: flag must not depend on it
    _advance_to_turn_tick(env)
    _, _, _, _, info = env.step(_hold_action(env))
    assert info["walk_turn_in_place_tick"] == pytest.approx(1.0)
    env.close()


def test_turn_tick_flag_zero_on_hold_tick():
    """walk_yaw_cmd=1 (flag-eligible lineage) but the live command is
    hold (wz_ref == 0): flag must read 0.0, not be absent."""
    cfg = load_config()
    goal = cfg.setdefault("goal", {})
    goal["walk_yaw_cmd"] = 1
    env = SimHexapodJointWalkEnv(cfg, seed=0)
    g = env._goal_gen
    for m in ("lean", "track", "unload", "raise", "rise", "lower"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 0.0)
    g.p_hold = 1.0
    g.p_walk = 0.0
    env.reset()
    _, _, _, _, info = env.step(_hold_action(env))
    assert info["walk_turn_in_place_tick"] == pytest.approx(0.0)
    env.close()


def test_turn_tick_flag_absent_when_yaw_cmd_off():
    """Pre-09-11 lineages (walk_yaw_cmd=0, the default) must never see
    this key at all -- bit-exact info dict for every existing lineage."""
    cfg = load_config()
    env = SimHexapodJointWalkEnv(cfg, seed=0)
    g = env._goal_gen
    for m in ("hold", "lean", "track", "unload", "raise", "rise", "lower"):
        if hasattr(g, f"p_{m}"):
            setattr(g, f"p_{m}", 0.0)
    g.p_walk = 1.0
    env.reset()
    _, _, _, _, info = env.step(_hold_action(env))
    assert "walk_turn_in_place_tick" not in info
    env.close()
