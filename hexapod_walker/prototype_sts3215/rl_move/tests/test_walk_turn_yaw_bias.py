"""goal.walk_turn_yaw_bias_deg -- turn-in-place YAW STEERING bias.

09-17, walkyaw 21st mechanism class. CURRENT_TRUTHS.md's `tkn2` closure
(20 independently-tried classes: income pricing, termination risk, 4x
RND, curriculum exposure, self-distillation, kernel-neutrality,
command-difficulty easing, warm-start-vs-scratch, obs-pad-transplant)
names the next honest lever as "a genuinely different architecture/
observation/ACTION-SPACE redesign, not a further dose" -- every one of
those 20 classes left `env/walk_wz` pinned at the noise floor while
ep_len_mean/reward visibly rose. None of them ever touched the RAW
ACTION's own steering symmetry: a fresh policy's near-zero mean output
has equal probability of twisting the body either way on a genuine
turn-in-place tick, so there is no persistent "lean this way" signal
for PPO's advantage estimator to climb. `goal.walk_turn_yaw_bias_deg`
(default 0.0 = OFF, bit-exact legacy) adds a small CONSTANT per-tick
offset (signed by sign(wz_ref)) to every leg's own yaw-joint TARGET,
ONLY on genuine turn-in-place ticks (identical gating condition as
`reward.walk_turn_kernel_neutral`/`walk_turn_freeze_charge`:
hypot(vx_ref,vy_ref)<=1e-3 and abs(wz_ref)>1e-3), applied in
JOINT-ANGLE space in `SimHexapodJointGoalEnv._act_to_q` after whichever
of box/bias/legacy decode already ran.

Contract under test (goal forced via a monkeypatched `_current_goal`
so the check is deterministic, not dependent on when the RNG happens
to sample a given command sign):
  - default (key absent/0) never enters the new block: a genuine
    turn-in-place tick's proposed joint targets are unaffected;
  - a positive wz_ref command gets a POSITIVE yaw offset on every leg,
    a negative command gets a NEGATIVE offset, magnitude == bias_deg
    (in radians), matched against a bias=0 sibling on the identical
    clipped action;
  - off the turn-in-place condition (an ordinary forward/combined walk
    tick with s_ref>1e-3, or wz_ref==0), no offset is applied
    regardless of the armed bias value;
  - the offset stays clipped inside the joint's own hardware axis
    range even at an extreme dose.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("mujoco")

from rl_move.config import load_config
from rl_move.robot_state import DEG2RAD
from rl_move.safety import AXIS_LIMITS_DEG
from rl_move.sim.walk_task import SimHexapodJointWalkEnv
from rl_move.sim.joint_task import q_rad_to_action


def _env(bias_deg=0.0, seed=0):
    cfg = load_config()
    goal = cfg.setdefault("goal", {})
    goal["walk_yaw_cmd"] = 1
    if bias_deg:
        goal["walk_turn_yaw_bias_deg"] = bias_deg
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


def _force_goal(env, vx_ref=0.0, vy_ref=0.0, wz_ref=0.0):
    env._current_goal = lambda: SimpleNamespace(
        vx_ref=vx_ref, vy_ref=vy_ref, wz_ref=wz_ref)


def _proposed_q(env):
    """The raw (pre-safety-slew) `_act_to_q` output for the current
    hold-in-place action, matching the exact call site `_step_begin`
    uses."""
    a = _hold_action(env)
    clipped, bad = env.safety.validate_action(a, n_act=env.n_act)
    assert not bad
    q, ok, reason = env._act_to_q(clipped)
    assert ok and reason == ""
    return np.asarray(q, dtype=float)


def test_default_off_never_enters_bias_block():
    env = _env(bias_deg=0.0)
    assert env._turn_yaw_bias_deg == 0.0
    _force_goal(env, wz_ref=0.27)
    q = _proposed_q(env)

    env2 = _env(bias_deg=0.0)
    _force_goal(env2, wz_ref=0.27)
    q2 = _proposed_q(env2)
    assert np.allclose(q, q2)


def test_positive_wz_gets_positive_yaw_offset():
    bias_deg = 10.0
    env_off = _env(bias_deg=0.0, seed=3)
    _force_goal(env_off, wz_ref=0.27)
    q_off = _proposed_q(env_off)

    env_on = _env(bias_deg=bias_deg, seed=3)
    _force_goal(env_on, wz_ref=0.27)
    q_on = _proposed_q(env_on)

    delta = q_on[0::3] - q_off[0::3]
    assert np.allclose(delta, bias_deg * DEG2RAD, atol=1e-9)
    # Only the yaw axis (index 0 mod 3) moves; hip/knee untouched.
    assert np.allclose(q_on[1::3], q_off[1::3])
    assert np.allclose(q_on[2::3], q_off[2::3])


def test_negative_wz_gets_negative_yaw_offset():
    bias_deg = 10.0
    env_off = _env(bias_deg=0.0, seed=7)
    _force_goal(env_off, wz_ref=-0.27)
    q_off = _proposed_q(env_off)

    env_on = _env(bias_deg=bias_deg, seed=7)
    _force_goal(env_on, wz_ref=-0.27)
    q_on = _proposed_q(env_on)

    delta = q_on[0::3] - q_off[0::3]
    assert np.allclose(delta, -bias_deg * DEG2RAD, atol=1e-9)


def test_forward_tick_never_gated_even_with_armed_bias():
    env_off = _env(bias_deg=0.0, seed=1)
    _force_goal(env_off, vx_ref=0.06, vy_ref=0.0, wz_ref=0.0)
    q_off = _proposed_q(env_off)

    env_on = _env(bias_deg=10.0, seed=1)
    _force_goal(env_on, vx_ref=0.06, vy_ref=0.0, wz_ref=0.0)
    q_on = _proposed_q(env_on)

    assert np.allclose(q_on, q_off)


def test_combined_walk_and_turn_tick_never_gated():
    """s_ref > 1e-3 with a simultaneous wz_ref is a COMBINED tick, not
    a genuine turn-in-place tick -- must not be gated either."""
    env_off = _env(bias_deg=0.0, seed=2)
    _force_goal(env_off, vx_ref=0.04, vy_ref=0.0, wz_ref=0.15)
    q_off = _proposed_q(env_off)

    env_on = _env(bias_deg=10.0, seed=2)
    _force_goal(env_on, vx_ref=0.04, vy_ref=0.0, wz_ref=0.15)
    q_on = _proposed_q(env_on)

    assert np.allclose(q_on, q_off)


def test_hold_tick_never_gated_even_with_armed_bias():
    env_off = _env(bias_deg=0.0, seed=0)
    _force_goal(env_off, wz_ref=0.0)
    q_off = _proposed_q(env_off)

    env_on = _env(bias_deg=10.0, seed=0)
    _force_goal(env_on, wz_ref=0.0)
    q_on = _proposed_q(env_on)

    assert np.allclose(q_on, q_off)


def test_offset_clips_inside_axis_range():
    yaw_lo, yaw_hi = AXIS_LIMITS_DEG[0]
    huge_bias = (yaw_hi - yaw_lo)  # far larger than any sane dose
    env = _env(bias_deg=huge_bias, seed=5)
    _force_goal(env, wz_ref=0.27)
    q = _proposed_q(env)
    yaw_q_deg = q[0::3] / DEG2RAD
    assert np.all(yaw_q_deg <= yaw_hi + 1e-6)
    assert np.all(yaw_q_deg >= yaw_lo - 1e-6)


def test_non_yaw_cmd_env_never_gated():
    """`_yaw_cmd` off entirely (walk_yaw_cmd=0): even a hand-forced
    nonzero wz_ref must never trigger the bias (matches the real
    training population, where the obs doesn't carry wz_ref either)."""
    cfg = load_config()
    env_off = SimHexapodJointWalkEnv(cfg, seed=4)
    env_off.reset()
    _force_goal(env_off, wz_ref=0.27)
    q_off = _proposed_q(env_off)

    cfg2 = load_config()
    cfg2.setdefault("goal", {})["walk_turn_yaw_bias_deg"] = 10.0
    env_on = SimHexapodJointWalkEnv(cfg2, seed=4)
    env_on.reset()
    _force_goal(env_on, wz_ref=0.27)
    q_on = _proposed_q(env_on)

    assert np.allclose(q_on, q_off)
