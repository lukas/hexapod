"""joint_task per-joint-class action BOX (2026-08-30, walkcurr final
literature-replication wave, operator ruling).

Smith/Kostrikov/Levine 2022 ("Walk in the Park") ablation-proved that a
TIGHT symmetric action box around the standing stance is CRUCIAL for
from-scratch legged RL discovery; Rudin 2021 legged_gym likewise learns
residual actions around a standing pose. The operator ruled such a box
IN-BOUNDS for walkcurr rule (a): a pure search-space bound with zero
temporal/gait structure, same class as the accepted joint_action_bias.

These tests pin the cfg-gated implementation
(goal.joint_action_box_{yaw,hip,knee}_deg, default 0.0 = OFF =
bit-exact legacy):
- OFF is bit-exact with the legacy/bias mapping;
- ON: a=0 lands exactly on the bias-shifted stance center, a=+-1 lands
  exactly center +- box (clipped to hardware axis limits);
- every possible action stays inside the box (bounded excursion);
- the zero-action rollout STANDS (no belly-sit collapse) — the box
  preserves the joint_action_bias fix it is centered on.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "linux_control", ROOT / "linux_control" / "urt2_setup"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

pytest.importorskip("mujoco")

from rl_move.sim.joint_task import action_to_q_rad  # noqa: E402
from test_joint_action_bias import (  # noqa: E402
    FIX_BIAS_OVERRIDES, _zero_action_height_drop_mm)
from test_task_semantics import _make_walk_env, SLIPWALK_OVERRIDES  # noqa: E402

# The final-wave dose (operator: Walk-in-the-Park proportions
# yaw ~+-11 / hip ~+-23 / knee ~+-23 deg, "tune to our geometry"):
# hip bias is 40 (not the sv arms' 45) because operator commit
# 88d852c3 (08-28) moved the raw hip mid-range -25 -> -20, so +40
# recenters a=0 on the semantics bank's WALK_PLANT hip=20 exactly;
# hip box is +-20 so the box [0, 40] sits exactly inside the hardware
# hip limit (-80, 40); knee [57, 103] and yaw [-11, 11] fit their
# limits untouched.
BOX_OVERRIDES = {
    ("goal", "joint_action_bias_hip_deg"): 40.0,   # -20 -> 20
    ("goal", "joint_action_bias_knee_deg"): 15.0,  # 65 -> 80
    ("goal", "joint_action_box_yaw_deg"): 11.0,
    ("goal", "joint_action_box_hip_deg"): 20.0,
    ("goal", "joint_action_box_knee_deg"): 23.0,
}


def test_default_box_is_inactive_and_bit_exact():
    """No box keys set -> flag off and the mapping is byte-identical to
    the legacy path (with and without the bias)."""
    for ov in (SLIPWALK_OVERRIDES,
               {**SLIPWALK_OVERRIDES, **FIX_BIAS_OVERRIDES}):
        env = _make_walk_env(0, ov)
        assert not env._joint_action_box_active
        rng = np.random.default_rng(1)
        for _ in range(10):
            a = rng.uniform(-1.0, 1.0, env.n_act)
            q, ok, _ = env._act_to_q(a)
            assert ok
            if ("goal", "joint_action_bias_hip_deg") in ov:
                ref = action_to_q_rad(
                    np.clip(a + env._joint_action_bias, -1.0, 1.0))
            else:
                ref = action_to_q_rad(a)
            assert np.array_equal(q, ref)
        env.close()


def test_box_zero_action_is_the_stance_center():
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **BOX_OVERRIDES})
    assert env._joint_action_box_active
    q0, ok, _ = env._act_to_q(np.zeros(env.n_act))
    assert ok
    q0_deg = np.degrees(q0).reshape(6, 3)
    assert np.allclose(q0_deg[:, 0], 0.0, atol=1e-6)
    assert np.allclose(q0_deg[:, 1], 20.0, atol=1e-6)
    assert np.allclose(q0_deg[:, 2], 80.0, atol=1e-6)
    env.close()


def test_box_extremes_land_on_center_plus_minus_box():
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **BOX_OVERRIDES})
    q_hi = np.degrees(env._act_to_q(np.ones(env.n_act))[0]).reshape(6, 3)
    q_lo = np.degrees(env._act_to_q(-np.ones(env.n_act))[0]).reshape(6, 3)
    assert np.allclose(q_hi[:, 0], 11.0, atol=1e-6)
    assert np.allclose(q_lo[:, 0], -11.0, atol=1e-6)
    assert np.allclose(q_hi[:, 1], 40.0, atol=1e-6)   # 20+20, = hw limit
    assert np.allclose(q_lo[:, 1], 0.0, atol=1e-6)
    assert np.allclose(q_hi[:, 2], 103.0, atol=1e-6)
    assert np.allclose(q_lo[:, 2], 57.0, atol=1e-6)
    env.close()


def test_box_clips_into_axis_range():
    """An oversized box must clip at the hardware axis limits, never
    raise/NaN or exceed them."""
    ov = {**SLIPWALK_OVERRIDES, **BOX_OVERRIDES,
          ("goal", "joint_action_box_hip_deg"): 200.0,
          ("goal", "joint_action_box_knee_deg"): 300.0}
    env = _make_walk_env(0, ov)
    q_hi = np.degrees(env._act_to_q(np.ones(env.n_act))[0]).reshape(6, 3)
    q_lo = np.degrees(env._act_to_q(-np.ones(env.n_act))[0]).reshape(6, 3)
    assert np.all(np.isfinite(q_hi)) and np.all(np.isfinite(q_lo))
    assert np.all(q_hi[:, 1] <= 40.0 + 1e-6)
    assert np.all(q_lo[:, 1] >= -80.0 - 1e-6)
    assert np.all(q_hi[:, 2] <= 150.0 + 1e-6)
    assert np.all(q_lo[:, 2] >= -20.0 - 1e-6)
    env.close()


def test_box_bounds_every_action():
    """Bounded excursion: no action can command a target outside
    center +- box (the whole point of the search-space bound)."""
    env = _make_walk_env(0, {**SLIPWALK_OVERRIDES, **BOX_OVERRIDES})
    center = env._joint_action_box_center
    box = env._joint_action_box_rad
    rng = np.random.default_rng(2)
    for _ in range(20):
        a = rng.uniform(-1.0, 1.0, env.n_act)
        q, ok, _ = env._act_to_q(a)
        assert ok
        assert np.all(q <= center + box + 1e-12)
        assert np.all(q >= center - box - 1e-12)
    env.close()


def test_box_zero_action_still_stands():
    """The box preserves the joint_action_bias fix it is centered on:
    a constant zero action stands near reference height instead of the
    legacy -110mm belly-sit collapse."""
    drop_mm, roll_deg, pitch_deg = _zero_action_height_drop_mm(
        dict(BOX_OVERRIDES))
    assert drop_mm < 30.0, (
        f"zero-action collapse regressed under the box: sank {drop_mm}mm")
    assert abs(roll_deg) < 5.0 and abs(pitch_deg) < 5.0
